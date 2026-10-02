from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    otp_hash = Column(String(64), nullable=False)
    reset_token_hash = Column(String(64), nullable=True, unique=True)
    expires_at = Column(DateTime, nullable=False)
    reset_token_expires_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    verified_at = Column(DateTime, nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    user = relationship("User", back_populates="password_reset_tokens")

    __table_args__ = (
        Index(
            "ix_password_reset_user_active",
            "user_id",
            "used_at",
            "created_at",
        ),
    )
