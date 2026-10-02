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


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_name = Column(String(100), nullable=False, default="Thiết bị không xác định")
    browser = Column(String(80), nullable=False, default="Trình duyệt không xác định")
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    last_active_at = Column(DateTime, nullable=False, default=utc_now)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_user_sessions_user_revoked", "user_id", "revoked_at"),
    )
