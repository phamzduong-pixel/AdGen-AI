"""Product Trust evaluation for persisted Trend Radar reports."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.models.evidence_source_policy import EvidenceSourcePolicy
from app.models.trend_report import TrendReport, TrendReportEvidence
from app.models.user import User
from app.schemas.product_trust import SourcePolicyUpsert
from app.services.external_retrieval.evidence import Evidence
from app.services.product_trust.models import (
    ClaimAssessment,
    ClaimOrigin,
    ProductClaim,
)


@dataclass(frozen=True)
class ReportTrustEvaluation:
    """Live report evaluation for callers that must enforce claim actions."""

    summary: dict
    assessments: tuple[tuple[ProductClaim, ClaimAssessment], ...]


def normalize_source_host(value: str) -> str:
    """Return a canonical hostname for a source URL or a policy host."""

    raw = str(value or "").strip().lower()
    if not raw:
        raise ValueError("host must not be empty")
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    host = parsed.hostname
    if not host or parsed.username or parsed.password:
        raise ValueError("host must be a valid hostname")
    try:
        host = host.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as error:
        raise ValueError("host must be a valid hostname") from error
    if len(host) > 255 or any(char.isspace() for char in host):
        raise ValueError("host must be a valid hostname")
    return host


def list_source_policies(
    db: Session,
    current_user: User,
) -> list[EvidenceSourcePolicy]:
    return (
        db.query(EvidenceSourcePolicy)
        .filter(EvidenceSourcePolicy.user_id == current_user.id)
        .order_by(EvidenceSourcePolicy.host.asc())
        .all()
    )


def upsert_source_policy(
    data: SourcePolicyUpsert,
    db: Session,
    current_user: User,
) -> EvidenceSourcePolicy:
    try:
        host = normalize_source_host(data.host)
    except ValueError as error:
        raise ValueError(str(error)) from error

    policy = (
        db.query(EvidenceSourcePolicy)
        .filter(
            EvidenceSourcePolicy.user_id == current_user.id,
            EvidenceSourcePolicy.host == host,
        )
        .first()
    )
    if policy is None:
        policy = EvidenceSourcePolicy(
            user_id=current_user.id,
            host=host,
            decision=data.decision,
            note=data.note,
        )
        db.add(policy)
    else:
        policy.decision = data.decision
        policy.note = data.note
    for report in db.query(TrendReport).filter(TrendReport.user_id == current_user.id).all():
        # A source-policy change invalidates cached trust claims. The next
        # explicit trust evaluation must apply the new policy before a report
        # can expose a Product Trust snapshot again.
        report.product_trust_json = '{}'
    db.commit()
    db.refresh(policy)
    return policy


def _metadata(record: TrendReportEvidence) -> dict:
    try:
        value = json.loads(record.metadata_json or "{}")
    except (TypeError, ValueError):
        value = {}
    return dict(value) if isinstance(value, dict) else {}


def _record_evidence(
    record: TrendReportEvidence,
    linked_claim_ids: Iterable[str],
) -> Evidence:
    metadata = _metadata(record)
    linked = {item for item in linked_claim_ids if item}
    supports = metadata.get("supports_claim_ids", [])
    if not isinstance(supports, (list, tuple, set, frozenset)):
        supports = []
    contradicts = metadata.get("contradicts_claim_ids", [])
    if not isinstance(contradicts, (list, tuple, set, frozenset)):
        contradicts = []
    contradicted_ids = {str(item) for item in contradicts if str(item).strip()}
    metadata["supports_claim_ids"] = sorted(
        ({str(item) for item in supports if str(item).strip()} | linked)
        - contradicted_ids
    )
    return Evidence(
        evidence_id=record.evidence_id,
        title=record.title,
        source_url=record.source_url,
        publisher=record.publisher,
        retrieved_at=record.retrieved_at,
        published_at=record.published_at,
        excerpt=record.excerpt,
        source_type=record.source_type,
        verification_status=record.verification_status,
        confidence=record.confidence,
        content_hash=record.content_hash,
        metadata=metadata,
    )


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _assessment_record(
    claim: ProductClaim,
    assessment: ClaimAssessment,
) -> dict:
    return {
        "claim_id": claim.claim_id,
        "claim_text": claim.claim_text,
        "claim_type": _enum_value(claim.claim_type),
        "status": _enum_value(assessment.status),
        "evidence_ids": list(assessment.evidence_ids),
        "risk_level": _enum_value(assessment.risk_level),
        "recommended_action": _enum_value(assessment.recommended_action),
        "rationale": assessment.rationale,
    }


def evaluate_report_trust_details(
    report: TrendReport,
    db: Session,
    current_user: User,
    *,
    mode: str = "all_evidence",
) -> ReportTrustEvaluation:
    """Evaluate report claims without assigning trust from keywords or URLs."""

    if mode not in {"all_evidence", "verified_only"}:
        raise ValueError("Unsupported Product Trust evaluation mode")

    policies = {
        policy.host: policy.decision
        for policy in list_source_policies(db, current_user)
    }
    evidences: list[Evidence] = []
    excluded_evidence_ids: list[str] = []
    trusted_source_hosts: set[str] = set()

    claim_links_by_evidence: dict[int, list[str]] = {}
    for claim in report.claims:
        for link in claim.evidence_links:
            claim_links_by_evidence.setdefault(link.evidence_id, []).append(
                claim.claim_key
            )

    for record in report.evidences:
        host = normalize_source_host(record.source_url)
        decision = policies.get(host)
        if decision == "excluded":
            excluded_evidence_ids.append(record.evidence_id)
            continue
        if decision == "trusted":
            trusted_source_hosts.add(host)

        evidence = _record_evidence(record, claim_links_by_evidence.get(record.id, ()))
        if mode == "verified_only":
            metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
            if (
                str(evidence.verification_status).lower() != "verified"
                or not str(metadata.get("verification_basis", "")).strip()
            ):
                continue
        evidences.append(evidence)

    claims: list[ProductClaim] = []
    for stored_claim in report.claims:
        origin = (
            ClaimOrigin.EXTERNAL_EVIDENCE
            if stored_claim.claim_type in {"evidence_backed", "product_fact"}
            else ClaimOrigin.AI_INFERENCE
        )
        claims.append(
            ProductClaim(
                claim_id=stored_claim.claim_key,
                claim_text=stored_claim.claim_text,
                claim_type=stored_claim.claim_type,
                origin=origin,
                product_field="trend_report_claim",
            )
        )

    from app.services.product_trust.service import assess_product_claims

    assessments = assess_product_claims(claims, evidences)
    claim_records = [
        _assessment_record(claim, assessment)
        for claim, assessment in zip(claims, assessments)
    ]
    statuses = Counter(item["status"] for item in claim_records)
    actions = {item["recommended_action"] for item in claim_records}
    blocking_claim_ids = [
        item["claim_id"]
        for item in claim_records
        if item["recommended_action"] in {"block", "ask_user"}
    ]
    requires_review = any(
        item["recommended_action"] != "allow"
        or item["status"] != "evidence_supported"
        for item in claim_records
    )

    caveats: list[str] = []
    if excluded_evidence_ids:
        caveats.append(
            "Excluded source policies removed "
            f"{len(excluded_evidence_ids)} evidence record(s) from this evaluation."
        )
    if mode == "verified_only":
        caveats.append(
            "Verified-only mode accepts evidence with verified status and an explicit verification basis."
        )
    if trusted_source_hosts:
        caveats.append(
            "Trusted source decisions are user preferences; they do not prove every source claim."
        )
    if not claims:
        caveats.append("The report contains no structured claims to assess.")
    if not evidences and claims:
        caveats.append("No usable evidence remains for the current trust policy.")

    summary = {
        "report_id": report.report_key,
        "mode": mode,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "can_use_for_generation": not bool(blocking_claim_ids),
        "requires_review": requires_review,
        "blocking_claim_ids": blocking_claim_ids,
        "excluded_evidence_ids": excluded_evidence_ids,
        "trusted_source_hosts": sorted(trusted_source_hosts),
        "claim_counts": dict(statuses),
        "claims": claim_records,
        "caveats": caveats,
    }
    return ReportTrustEvaluation(
        summary=summary,
        assessments=tuple(zip(claims, assessments)),
    )


def evaluate_report_trust(
    report: TrendReport,
    db: Session,
    current_user: User,
    *,
    mode: str = "all_evidence",
) -> dict:
    return evaluate_report_trust_details(
        report,
        db,
        current_user,
        mode=mode,
    ).summary


def persist_report_trust_snapshot(
    report: TrendReport,
    db: Session,
    current_user: User,
    *,
    mode: str = "all_evidence",
) -> dict:
    summary = evaluate_report_trust(
        report,
        db,
        current_user,
        mode=mode,
    )
    report.product_trust_json = json.dumps(summary, ensure_ascii=False)
    return summary
