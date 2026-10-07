"""Deterministic Trend Alert evaluation; no providers or LLM calls."""
import json
from dataclasses import dataclass
from app.core.datetime_utils import utc_now
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.trend_alert import TrendAlert
from app.models.trend_monitor import TrendMonitor, TrendSnapshot
from app.models.user import User
from app.services.trend_monitor_service import get_owned_monitor

MIN_SIGNAL_VALUE = 10.0
SPIKE_GROWTH_FACTOR = 1.5

@dataclass(frozen=True)
class Signal:
    trend_key: str
    value: float | None
    title: str

def normalize_signal(snapshot: TrendSnapshot) -> Signal | None:
    if snapshot.status != "success": return None
    try: data = json.loads(snapshot.payload_json)
    except (TypeError, ValueError): return None
    if not isinstance(data, dict) or not isinstance(data.get("trend_key"), str) or not data["trend_key"].strip(): return None
    raw = data.get("score", data.get("volume")); value = float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
    return Signal(data["trend_key"].strip(), value, str(data.get("title") or data["trend_key"]))

def evaluate_snapshot(snapshot_id: int, db: Session, current_user: User) -> list[TrendAlert]:
    snapshot = db.get(TrendSnapshot, snapshot_id)
    if snapshot is None: return []
    monitor = get_owned_monitor(db.get(TrendMonitor, snapshot.monitor_id).monitor_key, db, current_user)
    signal = normalize_signal(snapshot)
    if signal is None: return []
    previous = db.query(TrendSnapshot).filter(TrendSnapshot.monitor_id == monitor.id, TrendSnapshot.status == "success", TrendSnapshot.id != snapshot.id).order_by(TrendSnapshot.captured_at.desc()).first()
    prior = normalize_signal(previous) if previous else None
    alert_type = "trend_new" if prior is None or prior.trend_key != signal.trend_key else ("trend_spike" if signal.value is not None and prior.value is not None and signal.value >= MIN_SIGNAL_VALUE and signal.value >= prior.value * SPIKE_GROWTH_FACTOR else None)
    if not alert_type:
        # A valid successful comparable signal proves this trend no longer
        # qualifies for a spike; it never resolves another alert type/key.
        key_prefix = f"{monitor.id}:{signal.trend_key}:trend_spike"
        db.query(TrendAlert).filter(TrendAlert.monitor_id == monitor.id, TrendAlert.active_key == key_prefix).update({TrendAlert.status: "resolved", TrendAlert.active_key: None, TrendAlert.resolved_at: utc_now()}, synchronize_session=False)
        db.commit()
        return []
    key = f"{monitor.id}:{signal.trend_key}:{alert_type}"; existing = db.query(TrendAlert).filter(TrendAlert.active_key == key).first()
    if alert_type == "trend_new":
        db.query(TrendAlert).filter(TrendAlert.monitor_id == monitor.id, TrendAlert.alert_type == "trend_new", TrendAlert.active_key.is_not(None), TrendAlert.active_key != key).update({TrendAlert.status: "resolved", TrendAlert.active_key: None, TrendAlert.resolved_at: utc_now()}, synchronize_session=False)
        db.commit()
    if existing:
        existing.status = "active"; existing.snapshot_id = snapshot.id; db.commit(); return [existing]
    alert = TrendAlert(user_id=current_user.id, monitor_id=monitor.id, snapshot_id=snapshot.id, alert_key=key, active_key=key, alert_type=alert_type, status="new", severity="medium", title=signal.title, message=f"Đã phát hiện xu hướng: {signal.trend_key}.", payload_json=json.dumps({"trend_key": signal.trend_key, "value": signal.value}))
    db.add(alert)
    try: db.commit()
    except IntegrityError:
        db.rollback(); return [db.query(TrendAlert).filter(TrendAlert.active_key == key).one()]
    return [alert]
