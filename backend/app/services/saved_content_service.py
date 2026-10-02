import json

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.user import User
from app.models.brand import BrandProfile
from app.schemas.saved_content import SavedContentCreate
from app.services.message_service import get_user_conversation


def _get_owned_assistant_message(
    db: Session,
    message_id: int,
    current_user: User,
) -> tuple[Message, Conversation]:
    result = (
        db.query(Message, Conversation)
        .join(
            Conversation,
            Message.conversation_id == Conversation.id,
        )
        .filter(
            Message.id == message_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nội dung không tồn tại hoặc bạn không có quyền truy cập",
        )

    message, conversation = result
    if message.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể lưu phản hồi do AI tạo",
        )

    return message, conversation


def _build_title(
    requested_title: str | None,
    conversation: Conversation,
    content: str,
) -> str:
    title = (requested_title or conversation.title or "").strip()
    if not title or title in {"New Chat", "Cuộc trò chuyện mới"}:
        title = next(
            (line.strip("# *-") for line in content.splitlines() if line.strip()),
            "Nội dung quảng cáo",
        )
    return " ".join(title.split())[:160] or "Nội dung quảng cáo"


def _find_platform(
    db: Session,
    message: Message,
) -> str | None:
    source_message = (
        db.query(Message)
        .filter(
            Message.conversation_id == message.conversation_id,
            Message.role == "user",
            Message.id < message.id,
        )
        .order_by(Message.id.desc())
        .first()
    )
    return source_message.prompt_type if source_message else None


def _find_platform_name(
    db: Session,
    message: Message,
) -> str | None:
    source_message = (
        db.query(Message)
        .filter(
            Message.conversation_id == message.conversation_id,
            Message.role == "user",
            Message.id < message.id,
        )
        .order_by(Message.id.desc())
        .first()
    )
    if source_message is None:
        return message.platform_name
    if source_message.platform_name:
        return source_message.platform_name
    if source_message.ad_brief_json:
        try:
            return json.loads(source_message.ad_brief_json).get("platform_name")
        except (TypeError, ValueError):
            pass
    return None

def save_content_service(
    data: SavedContentCreate,
    db: Session,
    current_user: User,
) -> SavedContent:
    if data.message_id is not None:
        message, conversation = _get_owned_assistant_message(
            db=db,
            message_id=data.message_id,
            current_user=current_user,
        )

        existing = (
            db.query(SavedContent)
            .filter(
                SavedContent.user_id == current_user.id,
                SavedContent.message_id == message.id,
            )
            .first()
        )
        if existing is not None:
            return existing
        content = message.content
        message_id = message.id
        platform = _find_platform(db, message)
        platform_name = _find_platform_name(db, message)
        brand_id = message.brand_id
    else:
        conversation = get_user_conversation(
            db=db,
            conversation_id=data.conversation_id,
            current_user=current_user,
        )
        content = data.content or ""
        message_id = None
        platform = data.platform
        platform_name = data.platform_name
        brand_id = data.brand_id if "brand_id" in data.model_fields_set else conversation.brand_id
        if brand_id is not None and not db.query(BrandProfile).filter(
            BrandProfile.id == brand_id,
            BrandProfile.user_id == current_user.id,
        ).first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thương hiệu không tồn tại.",
            )
        existing = (
            db.query(SavedContent)
            .filter(
                SavedContent.user_id == current_user.id,
                SavedContent.content == content,
            )
            .first()
        )
        if existing is not None:
            return existing

    saved_content = SavedContent(
        user_id=current_user.id,
        conversation_id=conversation.id,
        message_id=message_id,
        title=_build_title(data.title, conversation, content),
        content=content,
        platform=platform,
        platform_name=platform_name,
        brand_id=brand_id,
    )
    db.add(saved_content)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate_query = db.query(SavedContent).filter(
            SavedContent.user_id == current_user.id,
        )
        existing = (
            duplicate_query.filter(SavedContent.message_id == message_id).first()
            if message_id is not None
            else duplicate_query.filter(SavedContent.content == content).first()
        )
        if existing is not None:
            return existing
        raise
    db.refresh(saved_content)
    return saved_content


def list_saved_contents_service(
    db: Session,
    current_user: User,
) -> list[SavedContent]:
    return (
        db.query(SavedContent)
        .filter(SavedContent.user_id == current_user.id)
        .order_by(
            SavedContent.created_at.desc(),
            SavedContent.id.desc(),
        )
        .all()
    )


def _delete_saved_content(
    saved_content: SavedContent | None,
    db: Session,
) -> dict:
    if saved_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nội dung đã lưu không tồn tại",
        )

    response = {
        "message": "Đã bỏ lưu nội dung",
        "id": saved_content.id,
        "message_id": saved_content.message_id,
    }
    db.delete(saved_content)
    db.commit()
    return response


def delete_saved_content_service(
    saved_content_id: int,
    db: Session,
    current_user: User,
) -> dict:
    saved_content = (
        db.query(SavedContent)
        .filter(
            SavedContent.id == saved_content_id,
            SavedContent.user_id == current_user.id,
        )
        .first()
    )
    return _delete_saved_content(saved_content, db)


def unsave_message_service(
    message_id: int,
    db: Session,
    current_user: User,
) -> dict:
    saved_content = (
        db.query(SavedContent)
        .filter(
            SavedContent.message_id == message_id,
            SavedContent.user_id == current_user.id,
        )
        .first()
    )
    return _delete_saved_content(saved_content, db)
