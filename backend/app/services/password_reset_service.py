import hashlib
import hmac
import secrets
import threading
from collections import defaultdict
from collections import deque
from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.core.security import verify_password
from app.core.datetime_utils import utc_now
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.password_reset import ResetPasswordRequest
from app.services.email_service import EmailConfigurationError
from app.services.email_service import EmailDeliveryError
from app.services.email_service import email_provider


GENERIC_REQUEST_MESSAGE = (
    "Nếu email tồn tại trong hệ thống, mã xác minh đã được gửi."
)
INVALID_CODE_MESSAGE = "Mã xác minh không hợp lệ hoặc đã hết hạn."


def _utcnow() -> datetime:
    return utc_now()


def _secret_hash(value: str, purpose: str) -> str:
    payload = f"password-reset:{purpose}:{value}".encode()
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


class PasswordResetRateLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def consume(self, email: str, ip_address: str) -> None:
        now = _utcnow()
        hour_ago = now - timedelta(hours=1)
        email_key = f"email:{_secret_hash(email, 'rate')}"
        ip_key = f"ip:{_secret_hash(ip_address or 'unknown', 'rate')}"

        with self._lock:
            email_events = self._events[email_key]
            ip_events = self._events[ip_key]
            for events in (email_events, ip_events):
                while events and events[0] < hour_ago:
                    events.popleft()

            if email_events:
                retry_at = email_events[-1] + timedelta(
                    seconds=settings.PASSWORD_RESET_RESEND_SECONDS
                )
                if retry_at > now:
                    retry_after = max(1, int((retry_at - now).total_seconds()))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=(
                            "Vui lòng chờ trước khi yêu cầu mã xác minh mới."
                        ),
                        headers={"Retry-After": str(retry_after)},
                    )
            if (
                len(email_events)
                >= settings.PASSWORD_RESET_EMAIL_HOURLY_LIMIT
                or len(ip_events) >= settings.PASSWORD_RESET_IP_HOURLY_LIMIT
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Bạn đã yêu cầu quá nhiều mã. Vui lòng thử lại sau.",
                    headers={"Retry-After": "3600"},
                )

            email_events.append(now)
            ip_events.append(now)


password_reset_rate_limiter = PasswordResetRateLimiter()


def request_password_reset(
    db: Session,
    email: str,
    ip_address: str,
) -> dict:
    normalized_email = email.strip().lower()
    try:
        email_provider.ensure_configured()
    except EmailConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Dịch vụ gửi email chưa được cấu hình. "
                "Vui lòng liên hệ quản trị viên."
            ),
        ) from error

    password_reset_rate_limiter.consume(normalized_email, ip_address)
    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )
    expires_in = settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES * 60
    response = {
        "message": GENERIC_REQUEST_MESSAGE,
        "expires_in": expires_in,
        "resend_after": settings.PASSWORD_RESET_RESEND_SECONDS,
    }
    if user is None:
        return response

    now = _utcnow()
    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .update({PasswordResetToken.used_at: now}, synchronize_session=False)
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    reset_record = PasswordResetToken(
        user_id=user.id,
        otp_hash=_secret_hash(code, "otp"),
        expires_at=now
        + timedelta(minutes=settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES),
    )
    db.add(reset_record)
    try:
        email_provider.send_code(
            recipient=user.email,
            code=code,
            expires_minutes=settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES,
        )
        db.commit()
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể gửi email xác minh. Vui lòng thử lại sau.",
        ) from error
    return response


def verify_reset_code(db: Session, email: str, code: str) -> dict:
    normalized_email = email.strip().lower()
    record = (
        db.query(PasswordResetToken)
        .join(User, PasswordResetToken.user_id == User.id)
        .filter(
            func.lower(User.email) == normalized_email,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.verified_at.is_(None),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    now = _utcnow()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_CODE_MESSAGE,
        )
    if record.expires_at <= now:
        record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_CODE_MESSAGE,
        )

    submitted_hash = _secret_hash(code, "otp")
    if not hmac.compare_digest(submitted_hash, record.otp_hash):
        record.attempt_count += 1
        if record.attempt_count >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
            record.used_at = now
        db.commit()
        attempts_left = max(
            0,
            settings.PASSWORD_RESET_MAX_ATTEMPTS - record.attempt_count,
        )
        detail = (
            INVALID_CODE_MESSAGE
            if attempts_left == 0
            else f"Mã xác minh không đúng. Còn {attempts_left} lần thử."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    reset_token = secrets.token_urlsafe(48)
    record.verified_at = now
    record.reset_token_hash = _secret_hash(reset_token, "token")
    record.reset_token_expires_at = now + timedelta(
        minutes=settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES
    )
    db.commit()
    return {
        "reset_token": reset_token,
        "expires_in": settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES * 60,
    }


def reset_password(
    db: Session,
    data: ResetPasswordRequest,
) -> dict:
    token_hash = _secret_hash(data.reset_token, "token")
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.reset_token_hash == token_hash,
            PasswordResetToken.verified_at.is_not(None),
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    now = _utcnow()
    if (
        record is None
        or record.reset_token_expires_at is None
        or record.reset_token_expires_at <= now
        or not hmac.compare_digest(record.reset_token_hash, token_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiên đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
        )

    user = record.user
    if user.auth_provider == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Tài khoản này sử dụng đăng nhập Google. "
                "Vui lòng tiếp tục bằng Google."
            ),
        )
    if verify_password(data.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải khác mật khẩu hiện tại.",
        )

    user.hashed_password = hash_password(data.new_password)
    user.email_verified = True
    user.token_version += 1
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None),
    ).update(
        {UserSession.revoked_at: now},
        synchronize_session=False,
    )
    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .update({PasswordResetToken.used_at: now}, synchronize_session=False)
    )
    db.commit()
    return {"message": "Mật khẩu đã được cập nhật thành công."}
