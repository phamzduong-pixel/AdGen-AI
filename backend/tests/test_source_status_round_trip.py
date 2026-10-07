import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.conversation import Conversation
from app.models.trend_report import TrendReport
from app.models.user import User
from app.schemas.trend_report import TrendReportCreate
from app.services.trend_report_service import create_trend_report_service, get_trend_report_service


def test_multiple_source_statuses_round_trip():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        owner = User(username="status-owner", email="status-owner@example.com", hashed_password="unused")
        session.add(owner)
        session.commit()
        conversation = Conversation(user_id=owner.id, title="Status round trip")
        session.add(conversation)
        session.commit()
        statuses = [
            {"source": "youtube", "status": "success", "retrieved_at": "2026-10-05T12:00:00Z", "evidence_count": 2},
            {"source": "meta", "status": "timeout", "retrieved_at": None, "evidence_count": 0, "error": "provider timeout"},
        ]
        data = TrendReportCreate(
            query="status round trip",
            conversation_id=conversation.id,
            source_statuses=statuses,
            retrieved_at=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
        )
        assert data.source_statuses == statuses
        created = create_trend_report_service(data, session, owner)
        stored = session.query(TrendReport).filter_by(report_key=created.report_id).one()
        assert json.loads(stored.source_statuses_json) == statuses
        loaded = get_trend_report_service(created.report_id, session, owner)
        assert loaded.source_statuses == statuses
        assert [item["source"] for item in loaded.source_statuses] == ["youtube", "meta"]
        assert loaded.source_statuses[0]["evidence_count"] == 2
        assert loaded.source_statuses[1]["status"] == "timeout"
    finally:
        session.close()
        engine.dispose()