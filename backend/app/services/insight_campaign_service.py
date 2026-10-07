"""Deterministic, owner-scoped conversion of trusted angles into campaign artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.advertising_angle import AdvertisingAngle
from app.models.advertising_brief import AdvertisingBrief, CampaignMetricSnapshot
from app.models.campaign import Campaign
from app.models.trend_report import TrendReport
from app.models.user import User
from app.services.product_trust.report_service import evaluate_report_trust_details


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def get_owned_brief(brief_id: int, db: Session, current_user: User) -> AdvertisingBrief:
    brief = db.query(AdvertisingBrief).filter(
        AdvertisingBrief.id == brief_id,
        AdvertisingBrief.owner_user_id == current_user.id,
    ).first()
    if brief is None:
        raise _not_found("Không tìm thấy brief quảng cáo.")
    return brief


def get_owned_metric_snapshot(snapshot_id: int, db: Session, current_user: User) -> CampaignMetricSnapshot:
    snapshot = db.query(CampaignMetricSnapshot).filter(
        CampaignMetricSnapshot.id == snapshot_id,
        CampaignMetricSnapshot.owner_user_id == current_user.id,
    ).first()
    if snapshot is None:
        raise _not_found("Không tìm thấy bản ghi số liệu chiến dịch.")
    return snapshot


def _evidence_ids(angle: AdvertisingAngle) -> tuple[str, ...]:
    try:
        payload = json.loads(angle.source_evidence_ids_json)
    except (TypeError, ValueError):
        payload = []
    if not isinstance(payload, list):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in payload if str(item).strip()))


def _require_currently_usable_angle(
    angle_id: int, db: Session, current_user: User
) -> AdvertisingAngle:
    angle = db.query(AdvertisingAngle).filter(
        AdvertisingAngle.id == angle_id,
        AdvertisingAngle.owner_user_id == current_user.id,
    ).first()
    if angle is None:
        raise _not_found("Không tìm thấy góc quảng cáo.")
    if angle.trust_action not in {"allow", "soften"} or not _evidence_ids(angle):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Góc quảng cáo này chưa đủ điều kiện bằng chứng để tạo brief.")

    report = db.query(TrendReport).filter(
        TrendReport.id == angle.trend_report_id,
        TrendReport.user_id == current_user.id,
    ).first()
    if report is None:
        raise _not_found("Không tìm thấy báo cáo xu hướng nguồn.")
    evaluation = evaluate_report_trust_details(report, db, current_user)
    assessment = next(
        (item for claim, item in evaluation.assessments if claim.claim_id == angle.source_claim_key),
        None,
    )
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Claim nguồn của góc quảng cáo không còn khả dụng.")
    current_action = str(getattr(assessment.recommended_action, "value", assessment.recommended_action))
    current_status = str(getattr(assessment.status, "value", assessment.status))
    current_evidence = {str(item) for item in assessment.evidence_ids}
    if (
        current_action not in {"allow", "soften"}
        or current_status != "evidence_supported"
        or not set(_evidence_ids(angle)).issubset(current_evidence)
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Góc quảng cáo không còn được đánh giá là đủ điều kiện theo Độ tin cậy sản phẩm hiện tại.")
    return angle


def create_brief_from_angle(
    angle_id: int, db: Session, current_user: User
) -> AdvertisingBrief:
    angle = _require_currently_usable_angle(angle_id, db, current_user)
    existing = db.query(AdvertisingBrief).filter(
        AdvertisingBrief.owner_user_id == current_user.id,
        AdvertisingBrief.advertising_angle_id == angle.id,
    ).first()
    if existing is not None:
        return existing

    brief = AdvertisingBrief(
        owner_user_id=current_user.id,
        advertising_angle_id=angle.id,
        title=angle.title,
        objective=None,
        target_audience=None,
        core_message=angle.wording,
        copy_direction="Dùng hướng triển khai này, không thêm dữ kiện chưa được bằng chứng hỗ trợ.",
        rationale=angle.rationale,
        status="draft",
    )
    db.add(brief)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        brief = db.query(AdvertisingBrief).filter(
            AdvertisingBrief.owner_user_id == current_user.id,
            AdvertisingBrief.advertising_angle_id == angle.id,
        ).one()
    else:
        db.refresh(brief)
    return brief


def create_campaign_from_brief(
    brief_id: int, db: Session, current_user: User
) -> Campaign:
    brief = get_owned_brief(brief_id, db, current_user)
    # Revalidate through the sole Product Trust contract before a campaign can
    # be created from an older brief after policies or evidence changed.
    angle = _require_currently_usable_angle(brief.advertising_angle_id, db, current_user)
    existing = db.query(Campaign).filter(
        Campaign.user_id == current_user.id,
        Campaign.advertising_brief_id == brief.id,
    ).first()
    if existing is not None:
        return existing

    campaign = Campaign(
        user_id=current_user.id,
        advertising_brief_id=brief.id,
        trend_report_id=angle.trend_report_id,
        name=brief.title[:160],
        description=brief.core_message,
        notes=brief.rationale,
        target_audience=brief.target_audience,
        objective=brief.objective,
        status="draft",
    )
    db.add(campaign)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        campaign = db.query(Campaign).filter(
            Campaign.user_id == current_user.id,
            Campaign.advertising_brief_id == brief.id,
        ).one()
    else:
        db.refresh(campaign)
    return campaign


def create_campaign_metric_snapshot(
    *,
    campaign_id: int,
    metric_payload: dict,
    db: Session,
    current_user: User,
    captured_at: datetime | None = None,
    metric_schema: str = "campaign_metrics_v1",
) -> CampaignMetricSnapshot:
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id,
    ).first()
    if campaign is None:
        raise _not_found("Không tìm thấy chiến dịch.")
    if not isinstance(metric_payload, dict) or not metric_payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hãy nhập ít nhất một chỉ số thực tế để lưu bản ghi.")
    when = captured_at or datetime.now(timezone.utc)
    if when.tzinfo is None or when.utcoffset() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Thời điểm ghi nhận phải có múi giờ.")
    schema = str(metric_schema).strip()
    if not schema:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Thiếu định dạng dữ liệu số liệu.")
    snapshot = CampaignMetricSnapshot(
        owner_user_id=current_user.id,
        campaign_id=campaign.id,
        advertising_brief_id=campaign.advertising_brief_id,
        captured_at=when,
        metric_schema=schema,
        payload_json=json.dumps(metric_payload, ensure_ascii=False, sort_keys=True),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_campaign_metric_snapshots(
    campaign_id: int, db: Session, current_user: User
) -> list[CampaignMetricSnapshot]:
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id,
    ).first()
    if campaign is None:
        raise _not_found("Không tìm thấy chiến dịch.")
    return db.query(CampaignMetricSnapshot).filter(
        CampaignMetricSnapshot.campaign_id == campaign.id,
        CampaignMetricSnapshot.owner_user_id == current_user.id,
    ).order_by(CampaignMetricSnapshot.captured_at.asc(), CampaignMetricSnapshot.id.asc()).all()
