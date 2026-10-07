import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.models.trend_monitor import TrendMonitor, TrendSnapshot
from app.models.trend_alert import TrendAlert
from app.models.advertising_angle import AdvertisingAngle
from app.models.advertising_brief import AdvertisingBrief
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignListResponse
from app.schemas.insight_campaign import (
    AdvertisingBriefResponse,
    CampaignMetricSnapshotCreate,
    CampaignMetricSnapshotResponse,
)
from app.services.campaign_service import _campaign_base
from app.services.insight_campaign_service import (
    create_brief_from_angle,
    create_campaign_from_brief,
    create_campaign_metric_snapshot,
    list_campaign_metric_snapshots,
)


router = APIRouter(prefix="/insight-campaign", tags=["Insight Campaign"])


def _campaign_response(campaign):
    return CampaignListResponse(**_campaign_base(campaign, 0))


def _snapshot_response(snapshot):
    try:
        payload = json.loads(snapshot.payload_json)
    except (TypeError, ValueError):
        payload = {}
    return CampaignMetricSnapshotResponse(
        id=snapshot.id,
        owner_user_id=snapshot.owner_user_id,
        campaign_id=snapshot.campaign_id,
        advertising_brief_id=snapshot.advertising_brief_id,
        captured_at=snapshot.captured_at,
        metric_schema=snapshot.metric_schema,
        metric_payload=payload if isinstance(payload, dict) else {},
        created_at=snapshot.created_at,
    )


def _json(value, fallback):
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


@router.get("/overview")
def get_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Owner-scoped read model for the existing Stage 4 workflow UI."""
    monitors = db.query(TrendMonitor).filter(TrendMonitor.user_id == current_user.id).order_by(TrendMonitor.updated_at.desc()).all()
    monitor_ids = [item.id for item in monitors]
    snapshots = db.query(TrendSnapshot).filter(TrendSnapshot.monitor_id.in_(monitor_ids)).order_by(TrendSnapshot.captured_at.desc()).all() if monitor_ids else []
    alerts = db.query(TrendAlert).filter(TrendAlert.user_id == current_user.id).order_by(TrendAlert.created_at.desc()).all()
    angles = db.query(AdvertisingAngle).filter(AdvertisingAngle.owner_user_id == current_user.id).order_by(AdvertisingAngle.created_at.desc()).all()
    briefs = db.query(AdvertisingBrief).filter(AdvertisingBrief.owner_user_id == current_user.id).order_by(AdvertisingBrief.created_at.desc()).all()
    campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id, Campaign.advertising_brief_id.is_not(None)).order_by(Campaign.updated_at.desc()).all()
    return {
        "monitors": [{"monitor_key": item.monitor_key, "query": item.query, "enabled": item.enabled, "cadence_minutes": item.cadence_minutes, "timezone": item.timezone, "next_run_at": item.next_run_at} for item in monitors],
        "snapshots": [{"monitor_id": item.monitor_id, "captured_at": item.captured_at, "status": item.status, "provider": item.provider, "freshness_status": item.freshness_status, "payload": _json(item.payload_json, {}), "error_message": item.error_message} for item in snapshots],
        "alerts": [{"severity": item.severity, "title": item.title, "message": item.message, "status": item.status, "created_at": item.created_at, "resolved_at": item.resolved_at} for item in alerts],
        "angles": [{"id": item.id, "angle_type": item.angle_type, "title": item.title, "wording": item.wording, "rationale": item.rationale, "trust_status": item.trust_status, "trust_action": item.trust_action, "created_at": item.created_at} for item in angles],
        "briefs": [{"id": item.id, "advertising_angle_id": item.advertising_angle_id, "title": item.title, "objective": item.objective, "target_audience": item.target_audience, "core_message": item.core_message, "copy_direction": item.copy_direction, "rationale": item.rationale, "status": item.status, "created_at": item.created_at} for item in briefs],
        "campaigns": [{"id": item.id, "advertising_brief_id": item.advertising_brief_id, "name": item.name, "description": item.description, "status": item.status, "created_at": item.created_at, "updated_at": item.updated_at} for item in campaigns],
    }


@router.post("/advertising-angles/{angle_id}/brief", response_model=AdvertisingBriefResponse, status_code=status.HTTP_201_CREATED)
def create_brief(angle_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_brief_from_angle(angle_id, db, current_user)


@router.post("/briefs/{brief_id}/campaign", response_model=CampaignListResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(brief_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _campaign_response(create_campaign_from_brief(brief_id, db, current_user))


@router.get("/campaigns/{campaign_id}/metric-snapshots", response_model=list[CampaignMetricSnapshotResponse])
def list_metric_snapshots(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [_snapshot_response(item) for item in list_campaign_metric_snapshots(campaign_id, db, current_user)]


@router.post("/campaigns/{campaign_id}/metric-snapshots", response_model=CampaignMetricSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_metric_snapshot(campaign_id: int, data: CampaignMetricSnapshotCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _snapshot_response(create_campaign_metric_snapshot(campaign_id=campaign_id, metric_payload=data.metric_payload, captured_at=data.captured_at, metric_schema=data.metric_schema, db=db, current_user=current_user))
