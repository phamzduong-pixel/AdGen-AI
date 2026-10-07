from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.trend_report import router as trend_report_router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.user import User
from app.schemas.product_trust import SourcePolicyUpsert
from app.schemas.message import MessageCreate
from app.services.product_trust.report_service import list_source_policies, upsert_source_policy
from app.services.message_service import _trend_trust_gate


NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def make_app(db, owner):
    app = FastAPI()
    app.include_router(trend_report_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    return app


def make_client():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = session_factory()
    owner = User(
        username='trust-report-owner',
        email='trust-report-owner@example.com',
        hashed_password='unused',
        email_verified=True,
    )
    db.add(owner)
    db.commit()
    return engine, db, TestClient(make_app(db, owner))


def verified_evidence(host='official.example', status='verified', **metadata):
    return {
        'evidence_id': 'evidence-1',
        'title': 'Official product document',
        'source_url': f'https://{host}/product',
        'publisher': 'Official publisher',
        'retrieved_at': NOW.isoformat(),
        'excerpt': 'The product has a documented feature.',
        'source_type': 'manual_verified',
        'status': status,
        'metadata': {'verification_basis': 'manual review', **metadata},
    }


def create_report(client, *, claim_text='Documented feature', evidence=None):
    return client.post(
        '/trend-reports',
        json={
            'query': 'product trust test',
            'claims': [
                {
                    'claim_id': 'claim-1',
                    'claim_text': claim_text,
                    'claim_type': 'product_fact',
                    'evidence_ids': ['evidence-1'],
                }
            ],
            'summary': claim_text,
            'summary_claim_ids': ['claim-1'],
            'evidences': [evidence or verified_evidence()],
            'retrieved_at': NOW.isoformat(),
        },
    )


def test_product_trust_summary_accepts_verified_evidence_with_basis():
    engine, db, client = make_client()
    try:
        created = create_report(client)
        assert created.status_code == 201, created.text
        report_id = created.json()['report_id']

        response = client.get(f'/trend-reports/{report_id}/trust')

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['can_use_for_generation'] is True
        assert body['requires_review'] is False
        assert body['claims'][0]['status'] == 'evidence_supported'
        assert body['claims'][0]['recommended_action'] == 'allow'
        assert created.json()['product_trust']['mode'] == 'all_evidence'

        loaded = client.get(f'/trend-reports/{report_id}')
        assert loaded.status_code == 200
        assert loaded.json()['product_trust']['mode'] == 'all_evidence'
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_verified_only_mode_filters_non_verified_evidence():
    engine, db, client = make_client()
    try:
        evidence = verified_evidence(status='partial')
        created = create_report(client, evidence=evidence)
        assert created.status_code == 201, created.text
        report_id = created.json()['report_id']

        response = client.get(
            f'/trend-reports/{report_id}/trust',
            params={'mode': 'verified_only'},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['mode'] == 'verified_only'
        assert body['claims'][0]['status'] == 'insufficient_evidence'
        assert body['requires_review'] is True
        assert body['can_use_for_generation'] is True

        trusted_policy = client.put(
            '/trend-reports/source-policies',
            json={'host': 'official.example', 'decision': 'trusted'},
        )
        assert trusted_policy.status_code == 200, trusted_policy.text
        trusted_response = client.get(
            f'/trend-reports/{report_id}/trust',
            params={'mode': 'verified_only'},
        )
        assert trusted_response.status_code == 200, trusted_response.text
        trusted_body = trusted_response.json()
        assert trusted_body['trusted_source_hosts'] == ['official.example']
        assert trusted_body['claims'][0]['status'] == 'insufficient_evidence'
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_excluded_source_is_removed_without_becoming_verified():
    engine, db, client = make_client()
    try:
        created = create_report(client)
        assert created.status_code == 201, created.text
        report_id = created.json()['report_id']

        policy = client.put(
            '/trend-reports/source-policies',
            json={'host': 'https://official.example/', 'decision': 'excluded'},
        )
        assert policy.status_code == 200, policy.text
        assert policy.json()['host'] == 'official.example'
        assert client.get(f'/trend-reports/{report_id}').json()['product_trust'] is None

        response = client.get(f'/trend-reports/{report_id}/trust')

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['excluded_evidence_ids'] == ['evidence-1']
        assert body['claims'][0]['status'] == 'insufficient_evidence'
        assert body['claims'][0]['evidence_ids'] == []
        assert any('Excluded source policies' in item for item in body['caveats'])
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_high_risk_contradiction_blocks_generation():
    engine, db, client = make_client()
    try:
        evidence = verified_evidence(
            contradicts_claim_ids=['claim-1'],
        )
        created = create_report(
            client,
            claim_text='Cure 100% chronic disease',
            evidence=evidence,
        )
        assert created.status_code == 201, created.text
        report_id = created.json()['report_id']

        response = client.get(f'/trend-reports/{report_id}/trust')

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['can_use_for_generation'] is False
        assert body['blocking_claim_ids'] == ['claim-1']
        assert body['claims'][0]['status'] == 'contradicted'
        assert body['claims'][0]['risk_level'] == 'high'
        assert body['claims'][0]['recommended_action'] == 'block'
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_source_policies_are_isolated_by_user():
    engine, db, client = make_client()
    try:
        owner = db.query(User).filter(User.username == 'trust-report-owner').one()
        other = User(
            username='trust-report-other',
            email='trust-report-other@example.com',
            hashed_password='unused',
            email_verified=True,
        )
        db.add(other)
        db.commit()

        upsert_source_policy(
            SourcePolicyUpsert(host='owner.example', decision='trusted'),
            db,
            owner,
        )
        assert [item.host for item in list_source_policies(db, other)] == []

        upsert_source_policy(
            SourcePolicyUpsert(host='other.example', decision='excluded'),
            db,
            other,
        )
        assert [item.host for item in list_source_policies(db, owner)] == ['owner.example']
        assert [item.host for item in list_source_policies(db, other)] == ['other.example']
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_generation_gate_uses_live_verified_only_policy_and_owner_scope():
    engine, db, client = make_client()
    try:
        created = create_report(client)
        assert created.status_code == 201, created.text
        report_id = created.json()['report_id']
        owner = db.query(User).filter(User.username == 'trust-report-owner').one()
        request = MessageCreate(
            conversation_id=1,
            content='Write an ad',
            trend_report_key=report_id,
            trend_trust_mode='verified_only',
        )

        gate = _trend_trust_gate(request, db, owner)
        assert gate is not None
        assert gate.action.value == 'allow'
        assert 'Documented feature' in gate.context

        upsert_source_policy(
            SourcePolicyUpsert(host='official.example', decision='excluded'), db, owner
        )
        excluded_gate = _trend_trust_gate(request, db, owner)
        assert excluded_gate is not None
        assert excluded_gate.action.value == 'soften'
        assert 'Only the following claims are approved for factual use: none' in excluded_gate.context

        other = User(username='gate-other', email='gate-other@example.com', hashed_password='unused')
        db.add(other)
        db.commit()
        try:
            _trend_trust_gate(request, db, other)
            assert False, 'other user must not access the owner report'
        except HTTPException as error:
            assert error.status_code == 404
    finally:
        client.close()
        db.close()
        engine.dispose()
