from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.models
from app.database.database import Base
from app.models.user import User
from app.services.trend_monitor_service import create_monitor, create_snapshot
from app.services.trend_alert_service import evaluate_snapshot

def test_new_active_resolve_retrigger_and_invalid_snapshots():
    engine=create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool); Base.metadata.create_all(engine); db=sessionmaker(bind=engine)()
    user=User(username="alert-life",email="alert-life@example.com",hashed_password="x"); db.add(user); db.commit()
    monitor=create_monitor(report_key=None,query="q",db=db,current_user=user)
    first=create_snapshot(monitor_key=monitor.monitor_key,run_key="1",payload={"trend_key":"a","score":10},db=db,current_user=user)
    alert=evaluate_snapshot(first.id,db,user)[0]; assert alert.status=="new"
    assert evaluate_snapshot(first.id,db,user)[0].status=="active"
    second=create_snapshot(monitor_key=monitor.monitor_key,run_key="2",payload={"trend_key":"b","score":10},db=db,current_user=user)
    evaluate_snapshot(second.id,db,user); db.refresh(alert); assert alert.status=="resolved" and alert.active_key is None and alert.resolved_at
    third=create_snapshot(monitor_key=monitor.monitor_key,run_key="3",payload={"trend_key":"a","score":10},db=db,current_user=user)
    retrigger=evaluate_snapshot(third.id,db,user)[0]; assert retrigger.id != alert.id and retrigger.status=="new"
    for key,status,payload in (("4","empty",{}),("5","error",{}),("6","success",{})):
        snap=create_snapshot(monitor_key=monitor.monitor_key,run_key=key,payload=payload,status_value=status,db=db,current_user=user); assert evaluate_snapshot(snap.id,db,user)==[]
