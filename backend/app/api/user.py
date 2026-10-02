from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import ChangePasswordRequest
from app.schemas.user import MessageResponse
from app.schemas.user import UserProfileResponse
from app.schemas.user import UserSettingsResponse
from app.schemas.user import UserSettingsUpdate
from app.schemas.user import UserUpdate
from app.services.user_service import change_password_service
from app.services.user_service import get_profile_service
from app.services.user_service import get_settings_service
from app.services.user_service import update_profile_service
from app.services.user_service import update_settings_service
from app.services.email_verification_service import send_verification_code
from fastapi import HTTPException


router = APIRouter(prefix="/users/me", tags=["User"])


@router.get("", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_profile_service(db, current_user)


@router.patch("", response_model=UserProfileResponse)
def update_profile(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    previous_email = current_user.email.lower()
    updated = update_profile_service(data, db, current_user)
    if previous_email != updated.email.lower():
        try:
            send_verification_code(
                db,
                updated.email,
                enforce_cooldown=False,
            )
        except HTTPException:
            pass
    return updated


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_password_service(data, db, current_user)


@router.get("/settings", response_model=UserSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_settings_service(db, current_user)


@router.put("/settings", response_model=UserSettingsResponse)
def update_settings(
    data: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_settings_service(data, db, current_user)
