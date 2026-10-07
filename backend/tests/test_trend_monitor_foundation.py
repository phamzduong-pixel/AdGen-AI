import json
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.models
from app.database.database import Base
from app.models.user import User
from app.services.trend_monitor_service import TrendMonitorCollection, create_monitor, create_snapshot, get_owned_monitor, run_due_monitors, run_monitor, set_monitor_enabled

class FakeCollector:
    def __init__(self, payload=None, fails=False): self.payload, self.fails = payload, fails
    def collect(self, monitor):
        if self.fails: raise RuntimeError("secret token")
        return TrendMonitorCollection(payload=self.payload, provider="fake", freshness_status="fresh")

def test_monitor_schedule_snapshot_and_owner_isolation():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    owner = User(username="monitor-owner", email="monitor-owner@example.com", hashed_password="x")
    other = User(username="monitor-other", email="monitor-other@example.com", hashed_password="x")
    db.add_all([owner, other]); db.commit()
    due = datetime(2026, 10, 7, tzinfo=timezone.utc)
    monitor = create_monitor(report_key=None, query="running shoes", cadence_minutes=60, timezone="Asia/Saigon", next_run_at=due, db=db, current_user=owner)
    persisted_due = monitor.next_run_at.replace(tzinfo=timezone.utc)
    assert monitor.enabled and monitor.cadence_minutes == 60 and monitor.timezone == "Asia/Saigon" and persisted_due == due
    assert set_monitor_enabled(monitor.monitor_key, False, db, owner).enabled is False
    snapshot = create_snapshot(monitor_key=monitor.monitor_key, run_key="run-1", payload={"score": 3}, provider="test", freshness_status="fresh", error_message=None, db=db, current_user=owner)
    assert snapshot.monitor_id == monitor.id and json.loads(snapshot.payload_json) == {"score": 3}
    with pytest.raises(Exception): get_owned_monitor(monitor.monitor_key, db, other)
    with pytest.raises(IntegrityError): create_snapshot(monitor_key=monitor.monitor_key, run_key="run-1", payload={}, db=db, current_user=owner)

def test_manual_due_idempotency_and_error_states():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool); Base.metadata.create_all(engine); db = sessionmaker(bind=engine)()
    owner = User(username="run-owner", email="run-owner@example.com", hashed_password="x"); db.add(owner); db.commit()
    monitor = create_monitor(report_key=None, query="topic", cadence_minutes=5, next_run_at=datetime(2026, 10, 1, tzinfo=timezone.utc), db=db, current_user=owner)
    first = run_monitor(monitor_key=monitor.monitor_key, run_key="manual-1", collector=FakeCollector({"signal": 1}), db=db, current_user=owner)
    reused = run_monitor(monitor_key=monitor.monitor_key, run_key="manual-1", collector=FakeCollector({"signal": 2}), db=db, current_user=owner)
    assert first.snapshot.status == "success" and not first.reused and reused.reused and reused.snapshot.id == first.snapshot.id
    failed = run_monitor(monitor_key=monitor.monitor_key, run_key="manual-error", collector=FakeCollector(fails=True), db=db, current_user=owner)
    assert failed.snapshot.status == "error" and "secret" not in (failed.snapshot.error_message or "")
    set_monitor_enabled(monitor.monitor_key, False, db, owner)
    with pytest.raises(Exception): run_monitor(monitor_key=monitor.monitor_key, run_key="disabled", collector=FakeCollector({}), db=db, current_user=owner)
    future = create_monitor(report_key=None, query="future", next_run_at=datetime(2030, 1, 1, tzinfo=timezone.utc), db=db, current_user=owner)
    assert run_due_monitors(collector=FakeCollector({"due": True}), db=db, now=datetime(2026, 10, 2, tzinfo=timezone.utc)) == []
    set_monitor_enabled(monitor.monitor_key, True, db, owner); monitor.next_run_at = datetime(2026, 10, 1); db.commit()
    assert len(run_due_monitors(collector=FakeCollector({"due": True}), db=db, now=datetime(2026, 10, 2, tzinfo=timezone.utc))) == 1
