import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.trend_monitor import TrendMonitor, TrendSnapshot
from app.models.user import User
from app.services.trend_report_service import get_owned_trend_report


@dataclass(frozen=True)
class TrendMonitorCollection:
    payload: dict | None
    provider: str | None = None
    freshness_status: str | None = None


class TrendMonitorCollector(Protocol):
    def collect(self, monitor: TrendMonitor) -> TrendMonitorCollection: ...


@dataclass(frozen=True)
class TrendMonitorRunResult:
    snapshot: TrendSnapshot
    reused: bool


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _existing_snapshot(monitor: TrendMonitor, run_key: str, db: Session) -> TrendSnapshot | None:
    return db.query(TrendSnapshot).filter(TrendSnapshot.monitor_id == monitor.id, TrendSnapshot.run_key == run_key).first()


def run_monitor(*, monitor_key: str, run_key: str, collector: TrendMonitorCollector, db: Session, current_user: User, allow_disabled: bool = False) -> TrendMonitorRunResult:
    monitor = get_owned_monitor(monitor_key, db, current_user)
    if not monitor.enabled and not allow_disabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trend Monitor is disabled.")
    existing = _existing_snapshot(monitor, run_key, db)
    if existing:
        return TrendMonitorRunResult(snapshot=existing, reused=True)
    try:
        collected = collector.collect(monitor)
        if collected.payload is None:
            snapshot = TrendSnapshot(monitor_id=monitor.id, run_key=run_key, status="empty", provider=collected.provider, freshness_status=collected.freshness_status, payload_json="{}")
        else:
            snapshot = TrendSnapshot(monitor_id=monitor.id, run_key=run_key, status="success", provider=collected.provider, freshness_status=collected.freshness_status, payload_json=json.dumps(collected.payload, ensure_ascii=False))
    except Exception:
        snapshot = TrendSnapshot(monitor_id=monitor.id, run_key=run_key, status="error", payload_json="{}", error_message="Trend collector failed.")
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _existing_snapshot(monitor, run_key, db)
        if existing:
            return TrendMonitorRunResult(snapshot=existing, reused=True)
        raise
    db.refresh(snapshot)
    # Alerts are best-effort post-persistence work. A failed evaluation must
    # never undo a valid collection snapshot or alter its status.
    try:
        from app.services.trend_alert_service import evaluate_snapshot
        evaluate_snapshot(snapshot.id, db, current_user)
    except Exception:
        db.rollback()
        db.refresh(snapshot)
    monitor.next_run_at = _utc(datetime.now(timezone.utc)) + timedelta(minutes=monitor.cadence_minutes)
    db.commit()
    return TrendMonitorRunResult(snapshot=snapshot, reused=False)


def run_due_monitors(*, collector: TrendMonitorCollector, db: Session, now: datetime | None = None) -> list[TrendMonitorRunResult]:
    due_at = _utc(now or datetime.now(timezone.utc))
    monitors = db.query(TrendMonitor).filter(TrendMonitor.enabled.is_(True), TrendMonitor.next_run_at.is_not(None), TrendMonitor.next_run_at <= due_at).all()
    results: list[TrendMonitorRunResult] = []
    for monitor in monitors:
        owner = db.get(User, monitor.user_id)
        if owner:
            results.append(run_monitor(monitor_key=monitor.monitor_key, run_key=f"due:{_utc(monitor.next_run_at).isoformat()}", collector=collector, db=db, current_user=owner))
    return results


def create_monitor(*, report_key: str | None, query: str | None, cadence_minutes: int = 1440, timezone: str = "UTC", next_run_at: datetime | None = None, db: Session, current_user: User) -> TrendMonitor:
    report = get_owned_trend_report(report_key, db, current_user) if report_key else None
    target_query = (query or (report.query if report else "")).strip()
    if not target_query or cadence_minutes < 1:
        raise ValueError("monitor requires a query and positive cadence_minutes")
    monitor = TrendMonitor(monitor_key=uuid.uuid4().hex, user_id=current_user.id, trend_report_id=report.id if report else None, query=target_query, cadence_minutes=cadence_minutes, timezone=timezone, next_run_at=next_run_at)
    db.add(monitor); db.commit(); db.refresh(monitor)
    return monitor


def get_owned_monitor(monitor_key: str, db: Session, current_user: User) -> TrendMonitor:
    monitor = db.query(TrendMonitor).filter(TrendMonitor.monitor_key == monitor_key, TrendMonitor.user_id == current_user.id).first()
    if monitor is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trend Monitor không tồn tại.")
    return monitor


def set_monitor_enabled(monitor_key: str, enabled: bool, db: Session, current_user: User) -> TrendMonitor:
    monitor = get_owned_monitor(monitor_key, db, current_user); monitor.enabled = enabled; db.commit(); db.refresh(monitor); return monitor


def create_snapshot(*, monitor_key: str, run_key: str, payload: dict, status_value: str = "success", provider: str | None = None, freshness_status: str | None = None, error_message: str | None = None, captured_at: datetime | None = None, db: Session, current_user: User) -> TrendSnapshot:
    monitor = get_owned_monitor(monitor_key, db, current_user)
    snapshot = TrendSnapshot(monitor_id=monitor.id, run_key=run_key, payload_json=json.dumps(payload, ensure_ascii=False), status=status_value, provider=provider, freshness_status=freshness_status, error_message=error_message, captured_at=captured_at)
    db.add(snapshot); db.commit(); db.refresh(snapshot); return snapshot
