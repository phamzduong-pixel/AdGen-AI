from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    username = Column(
        String,
        unique=True,
        nullable=False,
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
    )

    hashed_password = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    token_version = Column(
        Integer,
        default=0,
        nullable=False,
    )

    auth_provider = Column(
        String(20),
        default="local",
        nullable=False,
    )

    google_sub = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    avatar_url = Column(
        String(500),
        nullable=True,
    )

    email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete",
    )

    settings = relationship(
        "UserSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    email_verification_tokens = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    brands = relationship(
        "BrandProfile",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# Register the related mapper even when this model is imported in isolation.
from app.models.user_settings import UserSettings  # noqa: E402,F401
from app.models.password_reset import PasswordResetToken  # noqa: E402,F401
from app.models.email_verification import EmailVerificationToken  # noqa: E402,F401
from app.models.user_session import UserSession  # noqa: E402,F401
from app.models.brand import BrandProfile  # noqa: E402,F401
