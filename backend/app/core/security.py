from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_utils import utc_now
from app.database.database import get_db
from app.models.user import User
from app.models.user_session import UserSession

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    data: dict,
):
    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = data.copy()

    payload.update(
        {
            "exp": expire,
        }
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(
    token: str,
):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        subject = payload.get("sub")

        if subject is None:
            return None

        return {
            "subject": str(subject),
            "token_version": payload.get("ver"),
            "session_id": payload.get("jti"),
        }

    except JWTError:
        return None


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    token_data = decode_access_token(
        token
    )

    if token_data is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    subject = token_data["subject"]
    user = (
        db.query(User).filter(User.id == int(subject)).first()
        if subject.isdigit()
        else db.query(User).filter(User.username == subject).first()
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    token_version = token_data.get("token_version")
    if (
        (token_version is None and user.token_version != 0)
        or (
            token_version is not None
            and token_version != user.token_version
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid",
        )

    session_id = token_data.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid",
        )
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == user.id,
        )
        .first()
    )
    now = utc_now()
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid",
        )
    if user.auth_provider == "local" and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "email": user.email,
                "message": "Email chưa được xác minh.",
            },
        )
    if session.last_active_at < now - timedelta(minutes=5):
        session.last_active_at = now
        db.commit()
    request.state.auth_session = session

    return user


def get_current_session(
    request: Request,
    _current_user: User = Depends(get_current_user),
) -> UserSession:
    session = getattr(request.state, "auth_session", None)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid",
        )
    return session
