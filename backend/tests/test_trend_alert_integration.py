from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.models
from app.database.database import Base
from app.models.trend_alert import TrendAlert
from app.models.trend_monitor import TrendSnapshot
from app.models.user import User
from app.services.trend_monitor_service import TrendMonitorCollection, create_monitor, run_monitor

class Collector:
    def collect(self, monitor): return TrendMonitorCollection(payload={"trend_key":"signal","score":10})

def _setup():
    engine=create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool); Base.metadata.create_all(engine); db=sessionmaker(bind=engine)()
    user=User(username="alert-run",email="alert-run@example.com",hashed_password="x"); db.add(user); db.commit()
    return db,user,create_monitor(report_key=None,query="q",db=db,current_user=user)

def test_run_monitor_persists_snapshot_before_alert():
    db,user,monitor=_setup(); result=run_monitor(monitor_key=monitor.monitor_key,run_key="ok",collector=Collector(),db=db,current_user=user)
    assert result.snapshot.status == "success" and db.query(TrendAlert).filter_by(snapshot_id=result.snapshot.id).count() == 1

def test_alert_failure_preserves_success_snapshot():
    db,user,monitor=_setup()
    with patch("app.services.trend_alert_service.evaluate_snapshot", side_effect=RuntimeError("unexpected")):
        result=run_monitor(monitor_key=monitor.monitor_key,run_key="fail",collector=Collector(),db=db,current_user=user)
    stored=db.get(TrendSnapshot,result.snapshot.id)
    assert stored is not None and stored.status == "success" and stored.payload_json == '{"trend_key": "signal", "score": 10}'
