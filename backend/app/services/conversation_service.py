from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.uploaded_file import UploadedFile
from app.models.brand import BrandProfile


DEFAULT_CONVERSATION_TITLES = {
    "",
    "New Chat",
    "Cuộc trò chuyện mới",
}


def generate_conversation_title(content: str) -> str:
    normalized_content = " ".join(content.split())
    words = normalized_content.split(" ")[:8]
    title = " ".join(words)

    if len(title) <= 50:
        return title or "Cuộc trò chuyện mới"

    shortened = title[:50].rstrip()
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]

    return shortened or title[:50].rstrip()


def should_generate_conversation_title(
    db: Session,
    conversation: Conversation,
) -> bool:
    if conversation.is_title_custom or conversation.has_generated_title:
        return False

    if (conversation.title or "").strip() not in DEFAULT_CONVERSATION_TITLES:
        return False

    assistant_message_count = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.role == "assistant",
        )
        .count()
    )

    return assistant_message_count == 0


def save_generated_conversation_title(
    conversation: Conversation,
    first_message_content: str,
) -> None:
    if conversation.is_title_custom or conversation.has_generated_title:
        return

    conversation.title = generate_conversation_title(first_message_content)
    conversation.has_generated_title = True


def create_conversation(
    db: Session,
    user_id: int,
    title: str,
    brand_id: int | None = None,
):
    if brand_id is not None and not db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.user_id == user_id,
    ).first():
        raise HTTPException(status_code=404, detail="Thương hiệu không tồn tại.")
    conversation = Conversation(
        title=title,
        user_id=user_id,
        brand_id=brand_id,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_all_conversations(
    db: Session,
    user_id: int,
):
    return (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id
        )
        .order_by(
            Conversation.is_pinned.desc(),
            Conversation.updated_at.desc()
        )
        .all()
    )


def get_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


def update_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
    title: str,
):
    conversation = get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    conversation.title = title
    conversation.is_title_custom = True

    db.commit()
    db.refresh(conversation)

    return conversation


def delete_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
):
    conversation = get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    deleted_id = conversation.id
    stored_paths = [
        item.filepath
        for item in db.query(UploadedFile)
        .filter(UploadedFile.conversation_id == conversation.id)
        .all()
    ]
    db.delete(conversation)
    db.commit()

    from pathlib import Path
    from app.services.upload_service import UPLOAD_DIRECTORY

    for stored_path in stored_paths:
        path = Path(stored_path)
        try:
            if path.resolve().parent == UPLOAD_DIRECTORY.resolve():
                path.unlink(missing_ok=True)
        except OSError:
            pass

    return {
        "message": "Conversation deleted successfully",
        "conversation_id": deleted_id,
    }


def toggle_pin_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
    is_pinned: bool | None = None,
):
    conversation = get_conversation(db, conversation_id, user_id)
    conversation.is_pinned = (
        not conversation.is_pinned if is_pinned is None else is_pinned
    )
    db.commit()
    db.refresh(conversation)
    return conversation


def update_conversation_brand(
    db: Session,
    conversation_id: int,
    user_id: int,
    brand_id: int | None,
):
    conversation = get_conversation(db, conversation_id, user_id)
    if brand_id is not None and not db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.user_id == user_id,
    ).first():
        raise HTTPException(status_code=404, detail="Thương hiệu không tồn tại.")
    conversation.brand_id = brand_id
    db.commit()
    db.refresh(conversation)
    return conversation
