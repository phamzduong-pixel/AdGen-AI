from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardActivity
from app.schemas.dashboard import DashboardPlatformUsage
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import get_dashboard_activity_service
from app.services.dashboard_service import get_dashboard_summary_service
from app.services.dashboard_service import get_platform_usage_service


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard_summary_service(db, current_user)


@router.get("/activity", response_model=DashboardActivity)
def get_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard_activity_service(db, current_user)


@router.get("/platform-usage", response_model=DashboardPlatformUsage)
def get_platform_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_platform_usage_service(db, current_user)
