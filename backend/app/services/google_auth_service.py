import re
import secrets

from fastapi import HTTPException
from fastapi import status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import Request

from app.core.config import settings
from app.core.security import create_access_token
from app.core.security import hash_password
from app.models.user import User
from app.services.session_service import create_user_session


GOOGLE_CLIENT_ID_PATTERN = re.compile(
    r"^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$"
)


def _verify_google_id_token(credential: str, audience: str) -> dict:
    return id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        audience,
    )


def _unique_username(db: Session, email: str, display_name: str = "") -> str:
    source = display_name.strip() or email.split("@", 1)[0]
    base = re.sub(r"[^A-Za-z0-9_.-]+", "-", source).strip("._-").lower()
    if len(base) < 3:
        base = f"user-{base or 'google'}"
    base = base[:28].rstrip("._-")

    candidate = base
    suffix = 2
    while (
        db.query(User)
        .filter(func.lower(User.username) == candidate.lower())
        .first()
    ):
        suffix_text = f"-{suffix}"
        candidate = f"{base[: 32 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def _adgen_token(db: Session, user: User, request: Request) -> dict:
    session = create_user_session(db, user, request)
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "ver": user.token_version,
            "jti": session.id,
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


def login_with_google(db: Session, credential: str, request: Request) -> dict:
    client_id = settings.GOOGLE_CLIENT_ID
    if not GOOGLE_CLIENT_ID_PATTERN.fullmatch(client_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Đăng nhập Google chưa được cấu hình hợp lệ",
        )

    try:
        claims = _verify_google_id_token(credential, client_id)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác minh tài khoản Google",
        ) from error

    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    if not subject or not email or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản Google chưa xác minh email",
        )

    user = db.query(User).filter(User.google_sub == subject).first()
    if user is not None:
        avatar_url = str(claims.get("picture") or "").strip() or None
        if avatar_url and avatar_url != user.avatar_url:
            user.avatar_url = avatar_url
        if not user.email_verified:
            user.email_verified = True
        if db.is_modified(user):
            db.commit()
        return _adgen_token(db, user, request)

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )
    if user is not None:
        google_is_authoritative = email.endswith("@gmail.com") or bool(
            claims.get("hd")
        )
        if not user.google_sub and not google_is_authoritative:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Hãy đăng nhập bằng mật khẩu để xác nhận liên kết Google "
                    "cho email này"
                ),
            )
        if user.google_sub and user.google_sub != subject:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email đã được liên kết với tài khoản Google khác",
            )
        user.google_sub = subject
        user.avatar_url = str(claims.get("picture") or "").strip() or None
        user.email_verified = True
    else:
        user = User(
            username=_unique_username(db, email, str(claims.get("name") or "")),
            email=email,
            # Keep the legacy NOT NULL column compatible. Local login is blocked
            # by auth_provider, and this random value is never exposed or reused.
            hashed_password=hash_password(secrets.token_urlsafe(48)),
            auth_provider="google",
            google_sub=subject,
            avatar_url=str(claims.get("picture") or "").strip() or None,
            email_verified=True,
        )
        db.add(user)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể liên kết tài khoản Google",
        ) from error
    db.refresh(user)
    return _adgen_token(db, user, request)
