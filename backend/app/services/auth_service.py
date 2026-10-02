from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.core.security import hash_password
from app.core.security import verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from fastapi import Request
from app.services.session_service import create_user_session


def register_user(
    db: Session,
    user: UserCreate,
) -> User:
    """
    Đăng ký tài khoản mới.
    """

    username_exists = (
        db.query(User)
        .filter(
            func.lower(User.username) == user.username.lower()
        )
        .first()
    )



    if username_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username đã được sử dụng",
        )

    email_exists = (
        db.query(User)
        .filter(
            func.lower(User.email) == str(user.email).lower()
        )
        .first()
    )

    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng",
        )

    new_user = User(
        username=user.username,
        email=str(user.email).lower(),
        hashed_password=hash_password(
            user.password
        ),
        email_verified=True,
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username hoặc email đã được sử dụng",
        ) from error
    db.refresh(new_user)

    return new_user


def login_user(
    db: Session,
    identifier: str,
    password: str,
    request: Request,
) -> dict:
    """
    Kiểm tra tài khoản và tạo access token.
    """

    user = (
        db.query(User)
        .filter(
            (func.lower(User.username) == identifier.strip().lower())
            | (func.lower(User.email) == identifier.strip().lower())
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài khoản không tồn tại",
        )

    if user.auth_provider == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản này sử dụng đăng nhập bằng Google",
        )

    password_is_valid = verify_password(
        password,
        user.hashed_password,
    )

    if not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mật khẩu không chính xác",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    session = create_user_session(db, user, request)
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "ver": user.token_version,
            "jti": session.id,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def get_me(
    user: User,
) -> User:
    """
    Trả về thông tin người dùng hiện tại.
    """

    return user
