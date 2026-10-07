from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.trend_report import router as trend_report_router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.advertising_angle import AdvertisingAngle
from app.models.user import User
from app.schemas.product_trust import SourcePolicyUpsert
from app.services.advertising_angle_service import (
    generate_advertising_angle,
    get_owned_advertising_angle,
)
from app.services.product_trust.report_service import upsert_source_policy


NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)
    owner = User(username="angle-owner", email="angle-owner@example.test", hashed_password="x")
    db.add(owner)
    db.commit()
    app = FastAPI()
    app.include_router(trend_report_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    return engine, db, owner, TestClient(app)


def _report(client, *, claim_text="Documented product feature", contradicts=False):
    metadata = {"verification_basis": "manual review"}
    if contradicts:
        metadata["contradicts_claim_ids"] = ["claim-1"]
    response = client.post(
        "/trend-reports",
        json={
            "query": "angle test",
            "claims": [{"claim_id": "claim-1", "claim_text": claim_text, "claim_type": "product_fact", "evidence_ids": ["evidence-1"]}],
            "evidences": [{
                "evidence_id": "evidence-1", "title": "Evidence", "source_url": "https://official.example/product",
                "publisher": "Official", "retrieved_at": NOW.isoformat(), "excerpt": "Documented feature.",
                "source_type": "manual_verified", "status": "verified", "metadata": metadata,
            }],
            "retrieved_at": NOW.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["report_id"]


def test_allow_angle_is_traceable_and_idempotent():
    engine, db, owner, client = _setup()
    try:
        report_key = _report(client)
        first = generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=owner)
        second = generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=owner)
        assert first.action == "allow" and first.angle is not None
        assert second.angle is not None and second.angle.id == first.angle.id
        assert first.angle.source_claim_key == "claim-1"
        assert first.angle.source_evidence_ids_json == '["evidence-1"]'
        assert first.angle.trust_action == "allow"
        assert db.query(AdvertisingAngle).count() == 1
    finally:
        client.close(); db.close(); engine.dispose()


def test_live_excluded_policy_prevents_persisting_a_new_angle():
    engine, db, owner, client = _setup()
    try:
        report_key = _report(client)
        allowed = generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=owner)
        assert allowed.angle is not None
        upsert_source_policy(SourcePolicyUpsert(host="official.example", decision="excluded"), db, owner)
        result = generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=owner)
        assert result.action == "soften" and result.angle is None
        assert db.query(AdvertisingAngle).count() == 1
    finally:
        client.close(); db.close(); engine.dispose()


def test_soften_persists_only_a_cautious_traceable_angle():
    engine, db, owner, client = _setup()
    try:
        report_key = _report(client, claim_text="Feature is contradicted", contradicts=True)
        result = generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=owner)
        assert result.action == "soften" and result.angle is not None
        assert result.angle.trust_status == "contradicted"
        assert result.angle.trust_action == "soften"
        assert "cautious" in result.angle.wording.lower()
        assert result.angle.source_evidence_ids_json == '["evidence-1"]'
    finally:
        client.close(); db.close(); engine.dispose()


def test_block_and_ask_user_never_persist_angles():
    engine, db, owner, client = _setup()
    try:
        blocked_report = _report(client, claim_text="Cure 100% chronic disease", contradicts=True)
        blocked = generate_advertising_angle(report_key=blocked_report, claim_key="claim-1", db=db, current_user=owner)
        assert blocked.action == "block" and blocked.angle is None

        ask_report = _report(client, claim_text="Cure 100% chronic disease")
        upsert_source_policy(SourcePolicyUpsert(host="official.example", decision="excluded"), db, owner)
        ask_user = generate_advertising_angle(report_key=ask_report, claim_key="claim-1", db=db, current_user=owner)
        assert ask_user.action == "ask_user" and ask_user.angle is None
        assert db.query(AdvertisingAngle).count() == 0
    finally:
        client.close(); db.close(); engine.dispose()


def test_angle_and_report_ownership_are_owner_scoped():
    engine, db, owner, client = _setup()
    try:
        report_key = _report(client)
        result = generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=owner)
        other = User(username="angle-other", email="angle-other@example.test", hashed_password="x")
        db.add(other); db.commit()
        with pytest.raises(HTTPException) as report_error:
            generate_advertising_angle(report_key=report_key, claim_key="claim-1", db=db, current_user=other)
        with pytest.raises(HTTPException) as angle_error:
            get_owned_advertising_angle(result.angle.id, db, other)
        assert report_error.value.status_code == 404
        assert angle_error.value.status_code == 404
    finally:
        client.close(); db.close(); engine.dispose()
