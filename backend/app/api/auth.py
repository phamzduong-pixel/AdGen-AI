from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request

from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.schemas.user import (
    GoogleCredential,
    UserCreate,
    RegistrationResponse,
    UserResponse,
)

from app.schemas.token import Token
from app.schemas.password_reset import ForgotPasswordRequest
from app.schemas.password_reset import ForgotPasswordResponse
from app.schemas.password_reset import ResetPasswordRequest
from app.schemas.password_reset import VerifyResetCodeRequest
from app.schemas.password_reset import VerifyResetCodeResponse

from app.services.auth_service import (
    register_user,
    login_user,
)
from app.services.google_auth_service import GOOGLE_CLIENT_ID_PATTERN
from app.services.google_auth_service import login_with_google
from app.services.password_reset_service import request_password_reset
from app.services.password_reset_service import reset_password
from app.services.password_reset_service import verify_reset_code
from app.schemas.user import MessageResponse
from app.schemas.email_verification import EmailVerificationRequest
from app.schemas.email_verification import EmailVerificationResponse
from app.schemas.email_verification import VerifyEmailRequest
from app.schemas.email_verification import VerifyEmailResponse
from app.schemas.session import LogoutResponse
from app.schemas.session import SessionResponse
from app.services.email_verification_service import send_verification_code
from app.services.email_verification_service import verify_email
from app.services.session_service import list_user_sessions
from app.services.session_service import revoke_all_user_sessions
from app.services.session_service import revoke_user_session

from app.core.security import (
    get_current_session,
    get_current_user,
)
from app.core.config import settings
from app.models.user_session import UserSession

from app.models.user import User
from app.services.user_service import avatar_url_for_client


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegistrationResponse,
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):

    created_user = register_user(
        db,
        user,
    )
    return {
        "id": created_user.id,
        "username": created_user.username,
        "email": created_user.email,
        "created_at": created_user.created_at,
        "auth_provider": created_user.auth_provider,
        "avatar_url": created_user.avatar_url,
        "email_verified": created_user.email_verified,
        "verification_expires_in": 0,
        "resend_after": 0,
        "verification_sent": False,
    }


@router.post(
    "/login",
    response_model=Token,
)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    return login_user(
        db,
        form_data.username,
        form_data.password,
        request,
    )


@router.get("/google/config")
def google_config():
    """Expose only the public Google OAuth client id to the frontend."""
    client_id = settings.GOOGLE_CLIENT_ID
    return {
        "client_id": client_id if GOOGLE_CLIENT_ID_PATTERN.fullmatch(client_id) else None,
    }

@router.post(
    "/google",
    response_model=Token,
)
def google_login(
    data: GoogleCredential,
    request: Request,
    db: Session = Depends(get_db),
):
    return login_with_google(db, data.credential, request)


@router.post(
    "/send-verification-code",
    response_model=EmailVerificationResponse,
)
def request_email_verification(
    data: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    return send_verification_code(db, str(data.email))


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
)
def complete_email_verification(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    return verify_email(db, str(data.email), data.code)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
)
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip_address = request.client.host if request.client else "unknown"
    return request_password_reset(db, str(data.email), ip_address)


@router.post(
    "/verify-reset-code",
    response_model=VerifyResetCodeResponse,
)
def verify_password_reset_code(
    data: VerifyResetCodeRequest,
    db: Session = Depends(get_db),
):
    return verify_reset_code(db, str(data.email), data.code)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def complete_password_reset(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return reset_password(db, data)


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(
        get_current_user
    ),
):

    return UserResponse.model_validate(current_user).model_copy(
        update={"avatar_url": avatar_url_for_client(current_user)}
    )

@router.get("/sessions", response_model=list[SessionResponse])
def sessions(
    current_user: User = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return list_user_sessions(db, current_user, current_session)


@router.delete("/sessions/{session_id}", response_model=LogoutResponse)
def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_user_session(db, current_user, session_id)
    return {"message": "Đã đăng xuất khỏi thiết bị."}


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    revoke_user_session(db, current_user, current_session.id)
    return {"message": "Đã đăng xuất."}


@router.post("/logout-all", response_model=LogoutResponse)
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_all_user_sessions(db, current_user)
    return {"message": "Đã đăng xuất khỏi tất cả thiết bị."}
