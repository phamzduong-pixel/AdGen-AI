"""Deterministic Advertising Angles guarded by live Product Trust evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.advertising_angle import AdvertisingAngle
from app.models.user import User
from app.services.product_trust.report_service import evaluate_report_trust_details
from app.services.trend_report_service import get_owned_trend_report


@dataclass(frozen=True)
class AdvertisingAngleResult:
    action: str
    angle: AdvertisingAngle | None
    message: str | None = None


def _value(item: object) -> str:
    return str(getattr(item, "value", item))


def _source_key(
    *, report_key: str, claim_key: str, evidence_ids: tuple[str, ...], action: str, angle_type: str
) -> str:
    payload = json.dumps(
        {
            "report_key": report_key,
            "claim_key": claim_key,
            "evidence_ids": sorted(evidence_ids),
            "action": action,
            "angle_type": angle_type,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_owned_advertising_angle(
    angle_id: int, db: Session, current_user: User
) -> AdvertisingAngle:
    angle = (
        db.query(AdvertisingAngle)
        .filter(
            AdvertisingAngle.id == angle_id,
            AdvertisingAngle.owner_user_id == current_user.id,
        )
        .first()
    )
    if angle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertising Angle not found.")
    return angle


def generate_advertising_angle(
    *,
    report_key: str,
    claim_key: str,
    db: Session,
    current_user: User,
    mode: str = "all_evidence",
    angle_type: str = "evidence_led",
) -> AdvertisingAngleResult:
    """Generate one traceable angle without an LLM or trust heuristics.

    The current report and source-policy state are evaluated for every call.
    ``ask_user`` and ``block`` never persist an angle. ``soften`` is persisted
    only when it retains explicit supporting/contradicting evidence references.
    """

    report = get_owned_trend_report(report_key, db, current_user)
    evaluation = evaluate_report_trust_details(report, db, current_user, mode=mode)
    match = next(
        ((claim, assessment) for claim, assessment in evaluation.assessments if claim.claim_id == claim_key),
        None,
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trend Report claim not found.")

    claim, assessment = match
    action = _value(assessment.recommended_action)
    trust_status = _value(assessment.status)
    risk_level = _value(assessment.risk_level)
    evidence_ids = tuple(dict.fromkeys(str(item) for item in assessment.evidence_ids if str(item)))

    if action == "block":
        return AdvertisingAngleResult("block", None, "This claim is blocked by Product Trust.")
    if action == "ask_user":
        return AdvertisingAngleResult("ask_user", None, "More evidence or clarification is required.")
    if not evidence_ids:
        return AdvertisingAngleResult(action, None, "No traceable evidence is available for an advertising angle.")

    source_key = _source_key(
        report_key=report.report_key,
        claim_key=claim.claim_id,
        evidence_ids=evidence_ids,
        action=action,
        angle_type=angle_type,
    )
    existing = (
        db.query(AdvertisingAngle)
        .filter(
            AdvertisingAngle.owner_user_id == current_user.id,
            AdvertisingAngle.source_key == source_key,
        )
        .first()
    )
    if existing is not None:
        return AdvertisingAngleResult(action, existing)

    if action == "soften":
        wording = f"Consider a cautious, evidence-led angle around: {claim.claim_text}"
        title = f"Cautious evidence-led angle: {claim.claim_text}"
    else:
        wording = f"Lead with the documented point: {claim.claim_text}"
        title = f"Evidence-led angle: {claim.claim_text}"

    angle = AdvertisingAngle(
        owner_user_id=current_user.id,
        trend_report_id=report.id,
        source_claim_key=claim.claim_id,
        source_evidence_ids_json=json.dumps(list(evidence_ids), ensure_ascii=False),
        trust_status=trust_status,
        trust_risk_level=risk_level,
        trust_action=action,
        angle_type=angle_type,
        title=title,
        rationale=assessment.rationale,
        wording=wording,
        source_key=source_key,
    )
    db.add(angle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        angle = (
            db.query(AdvertisingAngle)
            .filter(
                AdvertisingAngle.owner_user_id == current_user.id,
                AdvertisingAngle.source_key == source_key,
            )
            .one()
        )
    else:
        db.refresh(angle)
    return AdvertisingAngleResult(action, angle)
