from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.core.datetime_utils import utc_now
from app.database.database import Base


class ContentActivity(Base):
    __tablename__ = "content_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    saved_content_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_contents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )
