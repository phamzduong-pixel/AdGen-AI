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


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    user = relationship("User", back_populates="email_verification_tokens")

    __table_args__ = (
        Index(
            "ix_email_verification_user_active",
            "user_id",
            "used_at",
            "created_at",
        ),
    )
