import hashlib
import hmac
import secrets
import threading
from collections import defaultdict
from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_utils import utc_now
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.services.email_service import EmailConfigurationError
from app.services.email_service import EmailDeliveryError
from app.services.email_service import email_provider


GENERIC_MESSAGE = (
    "Nếu tài khoản cần xác minh, mã xác minh đã được gửi đến email."
)
INVALID_CODE_MESSAGE = "Mã xác minh không hợp lệ hoặc đã hết hạn."


def _utcnow() -> datetime:
    return utc_now()


def _code_hash(code: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"email-verification:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


class VerificationRateLimiter:
    def __init__(self):
        self._last_sent = {}
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._last_sent.clear()

    def consume(self, email: str) -> None:
        key = hashlib.sha256(email.encode()).hexdigest()
        now = _utcnow()
        with self._lock:
            last_sent = self._last_sent.get(key)
            if last_sent:
                retry_at = last_sent + timedelta(
                    seconds=settings.EMAIL_VERIFICATION_RESEND_SECONDS
                )
                if retry_at > now:
                    retry_after = max(1, int((retry_at - now).total_seconds()))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Vui lòng chờ trước khi yêu cầu mã xác minh mới.",
                        headers={"Retry-After": str(retry_after)},
                    )
            self._last_sent[key] = now


verification_rate_limiter = VerificationRateLimiter()


def send_verification_code(
    db: Session,
    email: str,
    *,
    enforce_cooldown: bool = True,
) -> dict:
    normalized_email = email.strip().lower()
    if enforce_cooldown:
        verification_rate_limiter.consume(normalized_email)

    response = {
        "message": GENERIC_MESSAGE,
        "expires_in": settings.EMAIL_VERIFICATION_EXPIRE_MINUTES * 60,
        "resend_after": settings.EMAIL_VERIFICATION_RESEND_SECONDS,
    }
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

    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )
    if user is None or user.email_verified or user.auth_provider == "google":
        return response

    now = _utcnow()
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None),
    ).update(
        {EmailVerificationToken.used_at: now},
        synchronize_session=False,
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    record = EmailVerificationToken(
        user_id=user.id,
        code_hash=_code_hash(code),
        expires_at=now
        + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES),
    )
    db.add(record)
    try:
        email_provider.send_verification_code(
            recipient=user.email,
            code=code,
            expires_minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
        )
        db.commit()
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể gửi email xác minh. Vui lòng thử lại sau.",
        ) from error
    return response


def verify_email(db: Session, email: str, code: str) -> dict:
    normalized_email = email.strip().lower()
    record = (
        db.query(EmailVerificationToken)
        .join(User, EmailVerificationToken.user_id == User.id)
        .filter(
            func.lower(User.email) == normalized_email,
            EmailVerificationToken.used_at.is_(None),
        )
        .order_by(EmailVerificationToken.created_at.desc())
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
    if not hmac.compare_digest(_code_hash(code), record.code_hash):
        record.attempt_count += 1
        if record.attempt_count >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
            record.used_at = now
        db.commit()
        attempts_left = max(
            0,
            settings.EMAIL_VERIFICATION_MAX_ATTEMPTS - record.attempt_count,
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

    record.used_at = now
    record.user.email_verified = True
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == record.user_id,
        EmailVerificationToken.used_at.is_(None),
    ).update(
        {EmailVerificationToken.used_at: now},
        synchronize_session=False,
    )
    db.commit()
    return {"message": "Xác minh email thành công"}
