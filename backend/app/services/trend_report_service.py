import json
import uuid
from dataclasses import replace
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.trend_report import (
    TrendReport,
    TrendReportClaim,
    TrendReportClaimEvidence,
    TrendReportEvidence,
)
from app.models.user import User
from app.schemas.trend_report import (
    TrendReportClaimCreate,
    TrendReportClaimResponse,
    TrendReportCreate,
    TrendReportEvidenceCreate,
    TrendReportEvidenceResponse,
    TrendReportResponse,
)
from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceDeduplicator,
    EvidenceNormalizer,
    EvidenceValidator,
)
from app.services.external_retrieval.provider import SearchProviderResult
from app.services.external_retrieval.multi_platform import MultiPlatformRetrievalResult


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _provider_caveat(provider_status: str, evidence_count: int, message: str | None = None) -> str | None:
    if provider_status == "success" and evidence_count:
        return None
    if provider_status in {"success", "empty"}:
        return (
            "Chưa có đủ bằng chứng hoặc dữ liệu phù hợp từ nguồn. "
            "Không hiển thị số liệu có dẫn nguồn hoặc khẳng định việc thu thập đã thành công."
        )
    detail = f" Thông tin từ nguồn: {message}" if message else ""
    return (
        "Không thể sử dụng nguồn dữ liệu xu hướng bên ngoài. "
        "Hiện chưa có dữ liệu hoặc số liệu mới từ nguồn đáng tin cậy để hiển thị; "
        f"không dùng dữ liệu đã cũ như dữ liệu hiện tại.{detail}"
    )


def _owned_conversation(
    conversation_id: int | None, db: Session, current_user: User
) -> Conversation | None:
    if conversation_id is None:
        return None
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Cuá»™c trÃ² chuyá»‡n khÃ´ng tá»“n táº¡i.")
    return conversation


def _resolve_source(
    data: TrendReportCreate, db: Session, current_user: User
) -> tuple[int | None, int | None]:
    conversation_id = data.conversation_id
    if data.source_message_id is None:
        _owned_conversation(conversation_id, db, current_user)
        return conversation_id, None

    result = (
        db.query(Message, Conversation)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Message.id == data.source_message_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Message nguá»“n khÃ´ng tá»“n táº¡i.")
    message, conversation = result
    if conversation_id is not None and conversation_id != conversation.id:
        raise HTTPException(
            status_code=422,
            detail="source_message_id khÃ´ng thuá»™c conversation_id Ä‘Ã£ gá»­i.",
        )
    return conversation.id, message.id


def _normalize_evidence(
    item: TrendReportEvidenceCreate,
    *,
    reference_now: datetime,
) -> tuple[Evidence, str]:
    raw = Evidence(
        evidence_id=item.evidence_id,
        title=item.title,
        source_url=str(item.source_url),
        publisher=item.publisher,
        retrieved_at=item.retrieved_at,
        published_at=item.published_at,
        excerpt=item.excerpt,
        source_type=item.source_type,
        content_hash=item.content_hash,
        verification_status=item.status,
        confidence=item.confidence,
        metadata=item.metadata,
    )
    normalized = EvidenceNormalizer().normalize(raw)
    if not normalized.is_valid or normalized.evidence is None:
        detail = "; ".join(issue.message for issue in normalized.issues)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evidence khÃ´ng há»£p lá»‡: {detail}",
        )
    validation = EvidenceValidator().validate(
        normalized.evidence,
        now=reference_now,
    )
    fatal = [issue.message for issue in validation.issues if issue.fatal]
    if fatal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evidence khÃ´ng Ä‘áº¡t trust contract: " + "; ".join(fatal),
        )
    return normalized.evidence, validation.status.value


def _evidence_record(
    report_id: int,
    citation_id: str,
    evidence: Evidence,
    status_value: str,
) -> TrendReportEvidence:
    return TrendReportEvidence(
        report_id=report_id,
        evidence_id=evidence.evidence_id,
        citation_id=citation_id,
        title=evidence.title,
        source_url=evidence.source_url,
        publisher=evidence.publisher,
        retrieved_at=evidence.retrieved_at,
        published_at=evidence.published_at,
        excerpt=evidence.excerpt,
        source_type=_value(evidence.source_type),
        verification_status=status_value,
        confidence=evidence.confidence,
        content_hash=evidence.content_hash,
        metadata_json=json.dumps(evidence.metadata or {}, ensure_ascii=False),
    )


def _serialize_evidence(item: TrendReportEvidence) -> TrendReportEvidenceResponse:
    try:
        metadata = json.loads(item.metadata_json or "{}")
    except (TypeError, ValueError):
        metadata = {}
    return TrendReportEvidenceResponse(
        evidence_id=item.evidence_id,
        citation_id=item.citation_id,
        title=item.title,
        source_url=item.source_url,
        publisher=item.publisher,
        retrieved_at=item.retrieved_at,
        published_at=item.published_at,
        excerpt=item.excerpt,
        source_type=item.source_type,
        status=item.verification_status,
        confidence=item.confidence,
        content_hash=item.content_hash,
        metadata=metadata,
    )


def serialize_trend_report(report: TrendReport) -> TrendReportResponse:
    evidences = [_serialize_evidence(item) for item in report.evidences]
    by_id = {item.evidence_id: item for item in evidences}
    claims = []
    for claim in report.claims:
        claim_evidence = [
            by_id[link.evidence.evidence_id]
            for link in claim.evidence_links
            if link.evidence.evidence_id in by_id
        ]
        claims.append(
            TrendReportClaimResponse(
                claim_id=claim.claim_key,
                claim_text=claim.claim_text,
                claim_type=claim.claim_type,
                caveat=claim.caveat,
                evidence=claim_evidence,
            )
        )
    try:
        product_trust = json.loads(report.product_trust_json or '{}')
    except (TypeError, ValueError):
        product_trust = None
    if not isinstance(product_trust, dict) or not product_trust:
        product_trust = None
    return TrendReportResponse(
        product_trust=product_trust,
        report_id=report.report_key,
        request_id=report.request_id,
        user_id=report.user_id,
        conversation_id=report.conversation_id,
        source_message_id=report.source_message_id,
        query=report.query,
        summary=report.summary,
        summary_claim_ids=[claim.claim_key for claim in report.claims] if report.summary else [],
        generated_at=report.generated_at,
        retrieved_at=report.retrieved_at,
        provider_status=report.provider_status,
        caveat=report.caveat,
        source_statuses=json.loads(report.source_statuses_json or "[]"),
        evidences=evidences,
        claims=claims,
    )


def _report_query(db: Session):
    return db.query(TrendReport).options(
        selectinload(TrendReport.evidences).selectinload(TrendReportEvidence.claim_links),
        selectinload(TrendReport.claims)
        .selectinload(TrendReportClaim.evidence_links)
        .joinedload(TrendReportClaimEvidence.evidence),
    )


def _deduplicate_evidence(
    records: list[tuple[Evidence, str]],
) -> tuple[list[tuple[Evidence, str]], dict[str, str], str | None]:
    """Collapse local duplicate groups while retaining the most cautious status."""
    evidence_records = [evidence for evidence, _ in records]
    aliases = {evidence.evidence_id: evidence.evidence_id for evidence in evidence_records}
    statuses = {evidence.evidence_id: status for evidence, status in records}
    duplicates_by_canonical: dict[str, list[str]] = {}

    for group in EvidenceDeduplicator.duplicate_groups(evidence_records):
        canonical = group[0].evidence_id
        duplicate_ids = [item.evidence_id for item in group[1:]]
        if not duplicate_ids:
            continue
        duplicates_by_canonical[canonical] = duplicate_ids
        for duplicate_id in duplicate_ids:
            aliases[duplicate_id] = canonical

        group_statuses = {statuses[item.evidence_id] for item in group}
        if "conflicting" in group_statuses:
            statuses[canonical] = "conflicting"
        elif "stale" in group_statuses:
            statuses[canonical] = "stale"

    deduplicated: list[tuple[Evidence, str]] = []
    for evidence, status_value in records:
        if aliases[evidence.evidence_id] != evidence.evidence_id:
            continue
        duplicate_ids = duplicates_by_canonical.get(evidence.evidence_id, [])
        if duplicate_ids:
            metadata = dict(evidence.metadata or {})
            metadata["deduplicated_evidence_ids"] = duplicate_ids
            metadata["deduplicated_statuses"] = {
                item_id: statuses[aliases[item_id]] for item_id in duplicate_ids
            }
            evidence = replace(evidence, metadata=metadata)
        deduplicated.append((evidence, statuses[evidence.evidence_id]))

    caveat = None
    if duplicates_by_canonical:
        duplicate_count = sum(len(item) for item in duplicates_by_canonical.values())
        caveat = (
            f"Đã loại {duplicate_count} bằng chứng trùng lặp; nguồn trùng không được "
            "trình bày như bằng chứng độc lập."
        )
    return deduplicated, aliases, caveat


def _merge_caveats(*values: str | None) -> str | None:
    items = [value.strip() for value in values if value and value.strip()]
    return " ".join(dict.fromkeys(items)) or None

def create_trend_report_service(
    data: TrendReportCreate,
    db: Session,
    current_user: User,
) -> TrendReportResponse:
    conversation_id, source_message_id = _resolve_source(data, db, current_user)
    reference_now = data.retrieved_at or _now()
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=timezone.utc)

    normalized_evidence: list[tuple[Evidence, str]] = []
    evidence_ids: set[str] = set()
    for item in data.evidences:
        evidence, status_value = _normalize_evidence(item, reference_now=reference_now)
        if evidence.evidence_id in evidence_ids:
            raise HTTPException(status_code=422, detail="Evidence ID bá»‹ trÃ¹ng trong report.")
        evidence_ids.add(evidence.evidence_id)
        normalized_evidence.append((evidence, status_value))

    normalized_evidence, canonical_evidence_ids, deduplication_caveat = _deduplicate_evidence(
        normalized_evidence
    )
    evidence_statuses_by_id = {
        evidence.evidence_id: status_value for evidence, status_value in normalized_evidence
    }

    claim_ids_seen: set[str] = set()
    for claim in data.claims:
        if claim.claim_id in claim_ids_seen:
            raise HTTPException(status_code=422, detail="Claim ID bá»‹ trÃ¹ng trong report.")
        claim_ids_seen.add(claim.claim_id)
        missing = set(claim.evidence_ids) - set(canonical_evidence_ids)
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Claim {claim.claim_id} tham chi\u1ebfu evidence kh\u00f4ng thu\u1ed9c report: {sorted(missing)}",
            )
        if claim.claim_type in {"evidence_backed", "product_fact"}:
            related = [
                evidence_statuses_by_id[canonical_evidence_ids[evidence_id]]
                for evidence_id in claim.evidence_ids
            ]
            if any(value in {"stale", "conflicting"} for value in related):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Claim {claim.claim_id} chá»‰ tham chiáº¿u stale/conflicting evidence; "
                        "hÃ£y ghi nháº­n lÃ  insufficient_evidence."
                    ),
                )

    provider_status = data.provider_status.strip().lower()
    evidence_statuses = {status_value for _, status_value in normalized_evidence}
    automatic_caveat = _provider_caveat(provider_status, len(normalized_evidence))
    if provider_status == "success" and "stale" in evidence_statuses:
        automatic_caveat = (
            "Evidence Ä‘Æ°á»£c lÆ°u nhÆ°ng cÃ³ nguá»“n stale; khÃ´ng trÃ¬nh bÃ y nguá»“n nÃ y "
            "nhÆ° dá»¯ liá»‡u má»›i."
        )
    elif provider_status == "success" and "conflicting" in evidence_statuses:
        automatic_caveat = (
            "Evidence cÃ³ tráº¡ng thÃ¡i conflicting; khÃ´ng káº¿t luáº­n factual khi cÃ¡c "
            "nguá»“n chÆ°a Ä‘Æ°á»£c Ä‘á»‘i chiáº¿u."
        )
    report = TrendReport(
        report_key=uuid.uuid4().hex,
        user_id=current_user.id,
        conversation_id=conversation_id,
        source_message_id=source_message_id,
        request_id=(data.request_id or uuid.uuid4().hex)[:160],
        query=data.query.strip(),
        summary=data.summary.strip() if data.summary else None,
        generated_at=data.generated_at or _now(),
        retrieved_at=reference_now,
        provider_status=provider_status,
        caveat=_merge_caveats(data.caveat, automatic_caveat, deduplication_caveat),
        source_statuses_json=json.dumps(data.source_statuses, ensure_ascii=False),
    )
    db.add(report)
    db.flush()

    records: dict[str, TrendReportEvidence] = {}
    for index, (evidence, status_value) in enumerate(normalized_evidence, start=1):
        record = _evidence_record(report.id, f"S{index}", evidence, status_value)
        db.add(record)
        records[evidence.evidence_id] = record
    db.flush()

    for claim in data.claims:
        caveat = claim.caveat
        if claim.claim_type == "ai_inference" and not caveat:
            caveat = "Đây là suy luận hoặc gợi ý sáng tạo của AI, không phải dữ kiện được bằng chứng hỗ trợ."
        if claim.claim_type == "insufficient_evidence" and not caveat:
            caveat = "Chưa có đủ bằng chứng hoặc dữ liệu; không xem đây là dữ kiện đã xác minh."
        stored_claim = TrendReportClaim(
            report_id=report.id,
            claim_key=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            caveat=caveat,
        )
        db.add(stored_claim)
        db.flush()
        for evidence_id in claim.evidence_ids:
            db.add(
                TrendReportClaimEvidence(
                    claim_id=stored_claim.id,
                    evidence_id=records[canonical_evidence_ids[evidence_id]].id,
                )
            )

    db.flush()
    from app.services.product_trust.report_service import persist_report_trust_snapshot

    trust_report = _report_query(db).filter(TrendReport.id == report.id).first()
    if trust_report is not None:
        persist_report_trust_snapshot(trust_report, db, current_user)

    db.commit()
    stored = get_owned_trend_report(report.report_key, db, current_user)
    return serialize_trend_report(stored)


def get_owned_trend_report(
    report_key: str, db: Session, current_user: User
) -> TrendReport:
    report = (
        _report_query(db)
        .filter(
            TrendReport.report_key == report_key,
            TrendReport.user_id == current_user.id,
            TrendReport.deleted_at.is_(None),
        )
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Trend Report khÃ´ng tá»“n táº¡i.")
    return report


def get_trend_report_service(
    report_key: str, db: Session, current_user: User
) -> TrendReportResponse:
    return serialize_trend_report(get_owned_trend_report(report_key, db, current_user))


def list_trend_reports_service(
    db: Session, current_user: User, source_message_id: int | None = None
) -> list[TrendReportResponse]:
    query = _report_query(db).filter(
        TrendReport.user_id == current_user.id,
        TrendReport.deleted_at.is_(None),
    )
    if source_message_id is not None:
        query = query.filter(TrendReport.source_message_id == source_message_id)
    return [serialize_trend_report(item) for item in query.order_by(TrendReport.generated_at.desc()).all()]


def delete_trend_report_service(
    report_key: str, db: Session, current_user: User
) -> None:
    """Hide an owner-scoped report while retaining its downstream provenance."""
    report = get_owned_trend_report(report_key, db, current_user)
    report.deleted_at = _now()
    db.commit()


def persist_retrieval_report(
    *,
    query: str,
    provider_result: SearchProviderResult,
    db: Session,
    current_user: User,
    conversation_id: int | None = None,
    source_message_id: int | None = None,
) -> TrendReportResponse:
    evidence_inputs = [
        TrendReportEvidenceCreate(
            evidence_id=item.evidence_id,
            title=item.title,
            source_url=item.source_url,
            publisher=item.publisher,
            retrieved_at=item.retrieved_at,
            published_at=item.published_at,
            excerpt=item.excerpt,
            source_type=_value(item.source_type),
            status=_value(item.verification_status),
            confidence=item.confidence,
            content_hash=item.content_hash,
            metadata=item.metadata,
        )
        for item in provider_result.evidences
    ]
    return create_trend_report_service(
        TrendReportCreate(
            query=query,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            provider_status=_value(provider_result.status),
            caveat=provider_result.message,
            evidences=evidence_inputs,
        ),
        db,
        current_user,
    )


def _multi_platform_provider_status(result: MultiPlatformRetrievalResult) -> str:
    statuses = [_value(item.status) for item in result.sources]
    if not statuses:
        return "not_configured"
    if all(item == "success" for item in statuses):
        return "success" if result.evidences else "empty"
    if any(item == "success" for item in statuses):
        return "partial"
    if len(set(statuses)) == 1:
        return statuses[0]
    return "failed"


def _multi_platform_source_statuses(result: MultiPlatformRetrievalResult) -> list[dict]:
    evidence_counts: dict[str, int] = {}
    platform_by_evidence_id: dict[str, str] = {}
    for item in result.evidences:
        platform = str((item.metadata or {}).get("platform", "unknown"))
        evidence_counts[platform] = evidence_counts.get(platform, 0) + 1
        platform_by_evidence_id[item.evidence_id] = platform

    duplicates_by_platform: dict[str, list[str]] = {}
    for duplicate_id, canonical_id in result.duplicate_ids.items():
        platform = platform_by_evidence_id.get(canonical_id, "unknown")
        duplicates_by_platform.setdefault(platform, []).append(duplicate_id)

    statuses = []
    for item in result.sources:
        platform = item.platform
        status = {
            "source": platform,
            "platform": platform,
            "status": _value(item.status),
            "message": item.message,
            "evidence_count": evidence_counts.get(platform, 0),
            "from_cache": result.from_cache,
        }
        duplicate_ids = duplicates_by_platform.get(platform, [])
        if duplicate_ids:
            status["deduplicated_evidence_ids"] = sorted(duplicate_ids)
        statuses.append(status)
    return statuses


def persist_multi_platform_report(
    *,
    query: str,
    retrieval_service,
    db: Session,
    current_user: User,
    request_id: str | None = None,
    conversation_id: int | None = None,
    source_message_id: int | None = None,
    refresh: bool = False,
    max_age_days: int = 30,
) -> TrendReportResponse:
    result = retrieval_service.retrieve(
        query,
        refresh=refresh,
        max_age_days=max_age_days,
    )
    evidence_inputs = [
        TrendReportEvidenceCreate(
            evidence_id=item.evidence_id,
            title=item.title,
            source_url=item.source_url,
            publisher=item.publisher,
            retrieved_at=item.retrieved_at,
            published_at=item.published_at,
            excerpt=item.excerpt,
            source_type=_value(item.source_type),
            status=_value(item.verification_status),
            confidence=item.confidence,
            content_hash=item.content_hash,
            metadata=item.metadata,
        )
        for item in result.evidences
    ]
    source_statuses = _multi_platform_source_statuses(result)
    provider_status = _multi_platform_provider_status(result)
    failed_sources = [
        f"{item['platform']}: {item['status']}"
        for item in source_statuses
        if item["status"] != "success"
    ]
    caveat = None
    if not source_statuses:
        caveat = "Chưa cấu hình nguồn thu thập dữ liệu xu hướng, nên hệ thống chưa thể thu thập dữ liệu mới cho chủ đề này."
    elif failed_sources:
        caveat = (
            "Partial retrieval; successful sources were retained. "
            "Unsuccessful sources: " + ", ".join(failed_sources)
        )
    return create_trend_report_service(
        TrendReportCreate(
            request_id=request_id,
            query=query,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            provider_status=provider_status,
            caveat=caveat,
            source_statuses=source_statuses,
            evidences=evidence_inputs,
        ),
        db,
        current_user,
    )
