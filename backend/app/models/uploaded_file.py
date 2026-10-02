from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from app.database.database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    filename = Column(
        String,
        nullable=False,
    )

    filepath = Column(
        String,
        nullable=False,
    )

    content_type = Column(String, nullable=False, default="application/octet-stream")
    size = Column(Integer, nullable=False, default=0)

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False,
    )

    message_id = Column(
        Integer,
        ForeignKey("messages.id"),
        nullable=True,
    )

    conversation = relationship(
        "Conversation",
        back_populates="uploaded_files",
    )

    message = relationship(
        "Message",
        back_populates="attachments",
    )
