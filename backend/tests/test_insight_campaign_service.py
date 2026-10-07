from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.insight_campaign import router as insight_campaign_router
from app.api.trend_report import router as trend_report_router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.advertising_angle import AdvertisingAngle
from app.models.advertising_brief import AdvertisingBrief, CampaignMetricSnapshot
from app.models.campaign import Campaign
from app.models.trend_report import TrendReport
from app.models.user import User
from app.schemas.product_trust import SourcePolicyUpsert
from app.services.advertising_angle_service import generate_advertising_angle
from app.services.insight_campaign_service import (
    create_brief_from_angle,
    create_campaign_from_brief,
    create_campaign_metric_snapshot,
    get_owned_brief,
    list_campaign_metric_snapshots,
)
from app.services.product_trust.report_service import upsert_source_policy


NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    owner = User(username="insight-owner", email="insight-owner@example.test", hashed_password="x")
    db.add(owner); db.commit()
    app = FastAPI(); app.include_router(trend_report_router); app.include_router(insight_campaign_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    return engine, db, owner, TestClient(app)


def _report(client):
    response = client.post("/trend-reports", json={
        "query": "insight campaign test",
        "claims": [{"claim_id": "claim-1", "claim_text": "Documented product feature", "claim_type": "product_fact", "evidence_ids": ["evidence-1"]}],
        "evidences": [{
            "evidence_id": "evidence-1", "title": "Evidence", "source_url": "https://official.example/product",
            "publisher": "Official", "retrieved_at": NOW.isoformat(), "excerpt": "Documented product feature.",
            "source_type": "manual_verified", "status": "verified", "metadata": {"verification_basis": "manual review"},
        }],
        "retrieved_at": NOW.isoformat(),
    })
    assert response.status_code == 201, response.text
    return response.json()["report_id"]


def _angle(db, owner, client):
    result = generate_advertising_angle(report_key=_report(client), claim_key="claim-1", db=db, current_user=owner)
    assert result.angle is not None
    return result.angle


def test_angle_to_brief_to_campaign_preserves_provenance_and_is_idempotent():
    engine, db, owner, client = _setup()
    try:
        angle = _angle(db, owner, client)
        brief = create_brief_from_angle(angle.id, db, owner)
        same_brief = create_brief_from_angle(angle.id, db, owner)
        campaign = create_campaign_from_brief(brief.id, db, owner)
        same_campaign = create_campaign_from_brief(brief.id, db, owner)
        assert same_brief.id == brief.id and same_campaign.id == campaign.id
        assert brief.advertising_angle_id == angle.id
        assert brief.title == angle.title and brief.core_message == angle.wording
        assert brief.objective is None and brief.target_audience is None
        assert campaign.advertising_brief_id == brief.id
        assert campaign.trend_report_id == angle.trend_report_id
        report = db.get(TrendReport, angle.trend_report_id)
        assert report is not None and report.claims[0].claim_key == angle.source_claim_key
        assert report.evidences[0].evidence_id in angle.source_evidence_ids_json
        assert db.query(AdvertisingBrief).count() == 1 and db.query(Campaign).count() == 1
    finally:
        client.close(); db.close(); engine.dispose()


def test_metric_snapshots_are_append_only_and_caller_supplied():
    engine, db, owner, client = _setup()
    try:
        campaign = create_campaign_from_brief(create_brief_from_angle(_angle(db, owner, client).id, db, owner).id, db, owner)
        first = create_campaign_metric_snapshot(campaign_id=campaign.id, metric_payload={"impressions": 12, "clicks": 2}, db=db, current_user=owner, captured_at=NOW)
        second = create_campaign_metric_snapshot(campaign_id=campaign.id, metric_payload={"impressions": 20, "clicks": 3}, db=db, current_user=owner, captured_at=NOW.replace(hour=13))
        snapshots = list_campaign_metric_snapshots(campaign.id, db, owner)
        assert [item.id for item in snapshots] == [first.id, second.id]
        assert first.advertising_brief_id == campaign.advertising_brief_id
        assert first.payload_json == '{"clicks": 2, "impressions": 12}'
        with pytest.raises(HTTPException) as error:
            create_campaign_metric_snapshot(campaign_id=campaign.id, metric_payload={}, db=db, current_user=owner)
        assert error.value.status_code == 422
        assert db.query(CampaignMetricSnapshot).count() == 2
    finally:
        client.close(); db.close(); engine.dispose()


def test_current_trust_policy_and_invalid_angle_block_definitive_artifacts():
    engine, db, owner, client = _setup()
    try:
        angle = _angle(db, owner, client)
        upsert_source_policy(SourcePolicyUpsert(host="official.example", decision="excluded"), db, owner)
        with pytest.raises(HTTPException) as stale_error:
            create_brief_from_angle(angle.id, db, owner)
        assert stale_error.value.status_code == 422

        report = db.get(TrendReport, angle.trend_report_id)
        for action in ("block", "ask_user"):
            invalid = AdvertisingAngle(owner_user_id=owner.id, trend_report_id=report.id, source_claim_key="claim-1", source_evidence_ids_json='["evidence-1"]', trust_status="contradicted", trust_risk_level="high", trust_action=action, angle_type="evidence_led", title=action, rationale="test", wording="test", source_key=f"invalid-{action}")
            db.add(invalid); db.commit()
            with pytest.raises(HTTPException) as invalid_error:
                create_brief_from_angle(invalid.id, db, owner)
            assert invalid_error.value.status_code == 422
        with pytest.raises(HTTPException) as absent_error:
            create_brief_from_angle(999999, db, owner)
        assert absent_error.value.status_code == 404
    finally:
        client.close(); db.close(); engine.dispose()


def test_owner_cannot_use_other_users_angle_brief_campaign_or_metrics():
    engine, db, owner, client = _setup()
    try:
        angle = _angle(db, owner, client)
        brief = create_brief_from_angle(angle.id, db, owner)
        campaign = create_campaign_from_brief(brief.id, db, owner)
        snapshot = create_campaign_metric_snapshot(campaign_id=campaign.id, metric_payload={"clicks": 1}, db=db, current_user=owner)
        other = User(username="insight-other", email="insight-other@example.test", hashed_password="x")
        db.add(other); db.commit()
        for operation in (
            lambda: create_brief_from_angle(angle.id, db, other),
            lambda: create_campaign_from_brief(brief.id, db, other),
            lambda: create_campaign_metric_snapshot(campaign_id=campaign.id, metric_payload={"clicks": 2}, db=db, current_user=other),
            lambda: get_owned_brief(brief.id, db, other),
        ):
            with pytest.raises(HTTPException) as error:
                operation()
            assert error.value.status_code == 404
        assert db.get(CampaignMetricSnapshot, snapshot.id).owner_user_id == owner.id
    finally:
        client.close(); db.close(); engine.dispose()


def test_minimal_api_converts_and_records_actual_metrics():
    engine, db, owner, client = _setup()
    try:
        angle = _angle(db, owner, client)
        brief = client.post(f"/insight-campaign/advertising-angles/{angle.id}/brief")
        assert brief.status_code == 201, brief.text
        campaign = client.post(f"/insight-campaign/briefs/{brief.json()['id']}/campaign")
        assert campaign.status_code == 201, campaign.text
        campaign_id = campaign.json()["id"]
        created = client.post(f"/insight-campaign/campaigns/{campaign_id}/metric-snapshots", json={"metric_payload": {"engagement": 4}, "captured_at": NOW.isoformat()})
        listed = client.get(f"/insight-campaign/campaigns/{campaign_id}/metric-snapshots")
        assert created.status_code == 201 and listed.status_code == 200
        assert listed.json()[0]["metric_payload"] == {"engagement": 4}
    finally:
        client.close(); db.close(); engine.dispose()
