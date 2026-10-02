from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.datetime_utils import utc_now
from app.core.security import hash_password
from app.core.security import verify_password
from app.models.campaign import Campaign
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.user_session import UserSession
from app.schemas.user import ChangePasswordRequest
from app.schemas.user import UserProfileResponse
from app.schemas.user import UserSettingsResponse
from app.schemas.user import UserSettingsUpdate
from app.schemas.user import UserUpdate


def get_profile_service(
    db: Session,
    current_user: User,
) -> UserProfileResponse:
    total_conversations = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == current_user.id)
        .scalar()
    )
    total_saved = (
        db.query(func.count(SavedContent.id))
        .filter(SavedContent.user_id == current_user.id)
        .scalar()
    )
    total_campaigns = (
        db.query(func.count(Campaign.id))
        .filter(Campaign.user_id == current_user.id)
        .scalar()
    )
    top_platform_row = (
        db.query(Message.prompt_type, func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == current_user.id,
            Message.role == "user",
            Message.prompt_type.is_not(None),
        )
        .group_by(Message.prompt_type)
        .order_by(func.count(Message.id).desc())
        .first()
    )
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        email_verified=current_user.email_verified,
        total_conversations=int(total_conversations or 0),
        total_saved_contents=int(total_saved or 0),
        total_campaigns=int(total_campaigns or 0),
        top_platform=top_platform_row[0] if top_platform_row else None,
    )


def update_profile_service(
    data: UserUpdate,
    db: Session,
    current_user: User,
) -> UserProfileResponse:
    username = data.username.strip()
    email = str(data.email).strip().lower()
    duplicate = (
        db.query(User)
        .filter(
            User.id != current_user.id,
            (
                (func.lower(User.username) == username.lower())
                | (func.lower(User.email) == email)
            ),
        )
        .first()
    )
    if duplicate:
        detail = (
            "Username đã được sử dụng"
            if duplicate.username.lower() == username.lower()
            else "Email đã được sử dụng"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    current_user.username = username
    current_user.email = email
    current_user.email_verified = True
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username hoặc email đã được sử dụng",
        ) from error
    db.refresh(current_user)
    return get_profile_service(db, current_user)


def change_password_service(
    data: ChangePasswordRequest,
    db: Session,
    current_user: User,
) -> dict:
    if current_user.auth_provider == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản Google không sử dụng mật khẩu AdGen AI",
        )
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng",
        )
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải khác mật khẩu hiện tại",
        )
    current_user.hashed_password = hash_password(data.new_password)
    current_user.token_version += 1
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked_at.is_(None),
    ).update(
        {UserSession.revoked_at: utc_now()},
        synchronize_session=False,
    )
    db.commit()
    return {
        "message": (
            "Đổi mật khẩu thành công. Vui lòng đăng nhập lại để tiếp tục."
        )
    }


def get_settings_service(
    db: Session,
    current_user: User,
) -> UserSettingsResponse:
    settings = (
        db.query(UserSettings)
        .filter(UserSettings.user_id == current_user.id)
        .first()
    )
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return UserSettingsResponse.model_validate(settings, from_attributes=True)


def update_settings_service(
    data: UserSettingsUpdate,
    db: Session,
    current_user: User,
) -> UserSettingsResponse:
    settings = (
        db.query(UserSettings)
        .filter(UserSettings.user_id == current_user.id)
        .first()
    )
    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    for field, value in data.model_dump().items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return UserSettingsResponse.model_validate(settings, from_attributes=True)
