import uuid
from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_utils import utc_now
from app.models.user import User
from app.models.user_session import UserSession


def _browser_name(user_agent: str) -> str:
    value = user_agent.lower()
    if "edg/" in value:
        return "Microsoft Edge"
    if "opr/" in value or "opera" in value:
        return "Opera"
    if "chrome/" in value:
        return "Google Chrome"
    if "firefox/" in value:
        return "Mozilla Firefox"
    if "safari/" in value:
        return "Safari"
    return "Trình duyệt không xác định"


def _device_name(user_agent: str) -> str:
    value = user_agent.lower()
    if "iphone" in value:
        return "iPhone"
    if "ipad" in value:
        return "iPad"
    if "android" in value:
        return "Thiết bị Android"
    if "windows" in value:
        return "Máy tính Windows"
    if "macintosh" in value or "mac os" in value:
        return "Máy Mac"
    if "linux" in value:
        return "Máy tính Linux"
    return "Thiết bị không xác định"


def create_user_session(
    db: Session,
    user: User,
    request: Request,
) -> UserSession:
    now = utc_now()
    user_agent = request.headers.get("user-agent", "")[:500]
    session = UserSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        device_name=_device_name(user_agent),
        browser=_browser_name(user_agent),
        ip_address=request.client.host if request.client else None,
        created_at=now,
        last_active_at=now,
        expires_at=now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _masked_ip(value: str | None) -> str | None:
    if not value:
        return None
    if ":" in value:
        parts = value.split(":")
        return ":".join(parts[:3]) + ":…"
    parts = value.split(".")
    if len(parts) == 4:
        return ".".join(parts[:2] + ["xxx", "xxx"])
    return "Đã ẩn"


def list_user_sessions(
    db: Session,
    user: User,
    current_session: UserSession,
) -> list[dict]:
    now = utc_now()
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_active_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "device_name": s.device_name,
            "browser": s.browser,
            "ip_address": _masked_ip(s.ip_address),
            "created_at": s.created_at,
            "last_active_at": s.last_active_at,
            "expires_at": s.expires_at,
            "is_current": s.id == current_session.id,
        }
        for s in sessions
    ]


def revoke_user_session(
    db: Session,
    user: User,
    session_id: str,
) -> UserSession:
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên đăng nhập.",
        )
    session.revoked_at = utc_now()
    db.commit()
    return session


def revoke_all_user_sessions(db: Session, user: User) -> None:
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None),
    ).update(
        {UserSession.revoked_at: utc_now()},
        synchronize_session=False,
    )
    db.commit()
