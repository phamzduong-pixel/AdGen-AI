from collections.abc import Generator
import json

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.core.platforms import normalize_custom_platform_name
from app.core.platforms import is_legacy_platform
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.models.brand import BrandProfile
from app.schemas.message import MessageCreate
from app.schemas.message import MessageUpdate
from app.services.ai_service import ask_ai
from app.services.ai_service import stream_ai
from app.services.prompt_service import is_legacy_prompt_type
from app.services.prompt_service import is_supported_prompt_type
from app.services.prompt_service import normalize_prompt_type
from app.services.conversation_service import save_generated_conversation_title
from app.services.conversation_service import should_generate_conversation_title
from app.services.brand_prompt import build_brand_context
from app.services.context_engine.context_pruner import context_pruner
from app.services.context_engine.models import FollowUpIntentType
from app.services.context_engine.service import conversation_context_service
from app.services.product_aware.models import AudienceProfile, ProductAwareContext, ProductProfile
from app.services.product_aware.service import product_aware_engine


def validate_prompt_type(
    prompt_type: str | None,
    *,
    allow_legacy: bool = False,
) -> str | None:
    if prompt_type is None:
        return None

    normalized_type = normalize_prompt_type(prompt_type)

    if not is_supported_prompt_type(normalized_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Loại nền tảng '{prompt_type}' không được hỗ trợ",
        )

    if is_legacy_prompt_type(normalized_type) and not allow_legacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nền tảng này chỉ còn được giữ để mở dữ liệu cũ. "
                "Hãy chọn Facebook, TikTok, Instagram, Shopee, Google Ads hoặc Khác."
            ),
        )

    return normalized_type


def _requested_prompt_type(message: MessageCreate) -> str | None:
    if message.prompt_type:
        return message.prompt_type
    return message.ad_brief.platform if message.ad_brief else None


def _stored_platform_name(message: Message | None) -> str | None:
    if message is None:
        return None
    if message.platform_name:
        return normalize_custom_platform_name(message.platform_name)
    if not message.ad_brief_json:
        return None
    try:
        brief = json.loads(message.ad_brief_json)
    except (TypeError, ValueError):
        return None
    return normalize_custom_platform_name(brief.get("platform_name"))


def _resolve_custom_platform_name(
    message: MessageCreate | MessageUpdate,
    prompt_type: str | None,
    *,
    fallback: str | None = None,
) -> str | None:
    value = message.platform_name or fallback
    if isinstance(message, MessageCreate) and message.ad_brief:
        value = value or message.ad_brief.platform_name
    value = normalize_custom_platform_name(value)
    if prompt_type == "other" and not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cần nhập tên nền tảng hoặc nơi đăng nội dung khi chọn Khác.",
        )
    return value


def _serialize_ad_brief(
    message: MessageCreate,
    prompt_type: str | None,
    custom_platform_name: str | None,
) -> str | None:
    if not message.ad_brief:
        return None
    brief = message.ad_brief.model_dump()
    if prompt_type:
        brief["platform"] = prompt_type
    if custom_platform_name:
        brief["platform_name"] = custom_platform_name
    return json.dumps(brief, ensure_ascii=False)


def _conversation_has_legacy_platform(
    db: Session,
    conversation_id: int,
    prompt_type: str | None,
) -> bool:
    normalized = normalize_prompt_type(prompt_type)
    return bool(
        normalized
        and is_legacy_prompt_type(normalized)
        and db.query(Message.id)
        .filter(
            Message.conversation_id == conversation_id,
            Message.prompt_type == normalized,
        )
        .first()
    )

def get_user_conversation(
    db: Session,
    conversation_id: int,
    current_user: User,
) -> Conversation:
    """
    Lấy cuộc trò chuyện thuộc về người dùng hiện tại.
    """

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Cuộc trò chuyện không tồn tại "
                "hoặc bạn không có quyền truy cập"
            ),
        )

    return conversation


def build_history(
    db: Session,
    conversation_id: int,
) -> list[dict]:
    """
    Lấy toàn bộ lịch sử hội thoại theo thứ tự tăng dần.
    """

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id
        )
        .order_by(
            Message.created_at.asc(),
            Message.id.asc(),
        )
        .all()
    )

    history = []
    for message in messages:
        item = {"role": message.role, "content": message.content}
        if message.prompt_type:
            item["prompt_type"] = message.prompt_type
        if message.platform_name:
            item["platform_name"] = message.platform_name
        if message.ad_brief_json:
            try:
                item["ad_brief"] = json.loads(message.ad_brief_json)
            except (TypeError, ValueError):
                pass
        if message.role == "user" and message.attachments:
            item["attachments"] = [
                {
                    "filepath": attachment.filepath,
                    "content_type": attachment.content_type,
                    "filename": attachment.filename,
                }
                for attachment in message.attachments
            ]
        history.append(item)
    return history


def attach_files_to_message(
    db: Session,
    conversation_id: int,
    message_id: int,
    attachment_ids: list[int],
) -> None:
    if not attachment_ids:
        return

    unique_ids = list(dict.fromkeys(attachment_ids))
    attachments = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id.in_(unique_ids),
            UploadedFile.conversation_id == conversation_id,
            UploadedFile.message_id.is_(None),
        )
        .all()
    )

    if len(attachments) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Một hoặc nhiều tệp đính kèm không hợp lệ",
        )

    for attachment in attachments:
        attachment.message_id = message_id


from app.services.upload_service import determine_file_type


def serialize_message(message: Message) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "brand_id": message.brand_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
        "attachments": [
            {
                "id": attachment.id,
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "file_type": determine_file_type(attachment.content_type, attachment.filename),
                "size": attachment.size,
                "url": f"/uploads/file/{attachment.id}/download",
            }
            for attachment in message.attachments
        ],
        "ad_brief": (
            json.loads(message.ad_brief_json)
            if message.ad_brief_json
            else None
        ),
        "prompt_type": message.prompt_type,
        "platform_name": message.platform_name,
    }


def resolve_message_brand(
    message: MessageCreate,
    conversation: Conversation,
    db: Session,
    current_user: User,
) -> BrandProfile | None:
    if "brand_id" in message.model_fields_set:
        if message.brand_id is None:
            conversation.brand_id = None
            return None
        brand = db.query(BrandProfile).filter(
            BrandProfile.id == message.brand_id,
            BrandProfile.user_id == current_user.id,
        ).first()
        if brand is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thương hiệu không tồn tại hoặc không thuộc tài khoản.",
            )
        conversation.brand_id = brand.id
        return brand
    if conversation.brand_id is None:
        return None
    return db.query(BrandProfile).filter(
        BrandProfile.id == conversation.brand_id,
        BrandProfile.user_id == current_user.id,
    ).first()



AI_MAX_TURN_PAIRS = 6


def build_ai_context(
    history: list[dict],
    current_instruction: str,
    prompt_type: str | None,
    brand: BrandProfile | None,
) -> tuple[list[dict], str]:
    """Prune history while preserving the original brief and current attachments."""
    follow_up = conversation_context_service.resolve_conversation_context(
        user_message=current_instruction,
        history=history,
        current_prompt_type=prompt_type,
    )
    ai_history = context_pruner.prune_relevant_history(
        history,
        max_turn_pairs=AI_MAX_TURN_PAIRS,
    )
    instruction = conversation_context_service.format_follow_up_prompt_instruction(follow_up)
    if instruction:
        for index in range(len(ai_history) - 1, -1, -1):
            if ai_history[index].get("role") == "user":
                ai_history[index] = dict(ai_history[index])
                ai_history[index]["content"] = f"{ai_history[index].get('content', '')}\n\n{instruction}"
                break

    extracted = follow_up.extracted_product
    if extracted.is_empty():
        return ai_history, ""
    platform = follow_up.target_platform or prompt_type or extracted.platform or "other"
    product = ProductProfile(
        name=extracted.product_name or "Sản phẩm chưa đặt tên",
        description=extracted.description,
        usp=extracted.usp,
        price=extracted.price,
        offer=extracted.offer,
        key_features=extracted.key_features,
    )
    audience = AudienceProfile(demographics=extracted.target_audience)
    product_context = product_aware_engine.build_full_context(
        ProductAwareContext(
            product=product,
            platform=platform,
            audience=audience,
            brand_name=brand.name if brand else None,
            brand_voice=brand.default_tone if brand else None,
        ),
        include_trends=False,
    )
    return ai_history, product_context

def create_message_service(
    message: MessageCreate,
    db: Session,
    current_user: User,
):
    """
    Lưu tin nhắn người dùng, gọi Gemini không streaming
    và lưu câu trả lời của trợ lý.
    """

    conversation = get_user_conversation(
        db=db,
        conversation_id=message.conversation_id,
        current_user=current_user,
    )

    content = message.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung tin nhắn không được để trống",
        )

    requested_prompt_type = _requested_prompt_type(message)
    prompt_type = validate_prompt_type(
        requested_prompt_type,
        allow_legacy=_conversation_has_legacy_platform(
            db, conversation.id, requested_prompt_type
        ),
    )
    custom_platform_name = _resolve_custom_platform_name(message, prompt_type)
    brand = resolve_message_brand(message, conversation, db, current_user)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=content,
        ad_brief_json=(
            _serialize_ad_brief(message, prompt_type, custom_platform_name)
        ),
        prompt_type=prompt_type,
        platform_name=custom_platform_name,
        brand_id=brand.id if brand else None,
    )

    db.add(user_message)
    db.flush()
    attach_files_to_message(
        db=db,
        conversation_id=conversation.id,
        message_id=user_message.id,
        attachment_ids=message.attachment_ids,
    )
    db.commit()
    db.refresh(user_message)

    history = build_history(
        db=db,
        conversation_id=conversation.id,
    )
    ai_history, product_context = build_ai_context(
        history, content, prompt_type, brand
    )
    should_generate_title = should_generate_conversation_title(
        db=db,
        conversation=conversation,
    )

    try:
        assistant_content = ask_ai(
            history=ai_history,
            prompt_type=prompt_type,
            custom_platform_name=custom_platform_name,
            product_context=product_context,
            **(
                {"brand_context": build_brand_context(brand)}
                if brand
                else {}
            ),
        )

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
            prompt_type=prompt_type,
            platform_name=custom_platform_name,
            brand_id=brand.id if brand else None,
        )

        db.add(assistant_message)
        if should_generate_title:
            save_generated_conversation_title(
                conversation=conversation,
                first_message_content=content,
            )
        db.commit()
        db.refresh(assistant_message)

        return {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "prompt_type": prompt_type,
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không thể nhận phản hồi từ AI: {error}",
        ) from error


def get_messages_service(
    conversation_id: int,
    db: Session,
    current_user: User,
):
    """
    Lấy danh sách tin nhắn của một cuộc trò chuyện.
    """

    conversation = get_user_conversation(
        db=db,
        conversation_id=conversation_id,
        current_user=current_user,
    )

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id
        )
        .order_by(
            Message.created_at.asc(),
            Message.id.asc(),
        )
        .all()
    )
    return [serialize_message(message) for message in messages]


def get_message_service(
    message_id: int,
    db: Session,
    current_user: User,
) -> Message:
    """
    Lấy một tin nhắn thuộc cuộc trò chuyện của người dùng.
    """

    message = (
        db.query(Message)
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

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Tin nhắn không tồn tại "
                "hoặc bạn không có quyền truy cập"
            ),
        )

    return message


def update_message_service(
    message_id: int,
    message_data: MessageUpdate,
    db: Session,
    current_user: User,
):
    """
    Chỉ cập nhật nội dung tin nhắn, chưa gọi lại AI.
    """

    message = get_message_service(
        message_id=message_id,
        db=db,
        current_user=current_user,
    )

    if message.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể chỉnh sửa tin nhắn người dùng",
        )

    content = message_data.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung tin nhắn không được để trống",
        )

    prompt_type = validate_prompt_type(
        message_data.prompt_type or message.prompt_type,
        allow_legacy=is_legacy_prompt_type(message.prompt_type),
    )
    custom_platform_name = _resolve_custom_platform_name(
        message_data,
        prompt_type,
        fallback=_stored_platform_name(message),
    )
    message.content = content
    message.prompt_type = prompt_type
    message.platform_name = custom_platform_name

    db.commit()
    db.refresh(message)

    return message


def delete_message_service(
    message_id: int,
    db: Session,
    current_user: User,
):
    """
    Xóa một tin nhắn thuộc cuộc trò chuyện của người dùng.
    """

    message = get_message_service(
        message_id=message_id,
        db=db,
        current_user=current_user,
    )

    db.delete(message)
    db.commit()

    return {
        "message": "Xóa tin nhắn thành công"
    }


def stream_message_service(
    message: MessageCreate,
    db: Session,
    current_user: User,
) -> Generator[str, None, None]:
    """
    Lưu tin nhắn người dùng, stream phản hồi Gemini
    và lưu câu trả lời đầy đủ sau khi stream hoàn tất.
    """

    conversation = get_user_conversation(
        db=db,
        conversation_id=message.conversation_id,
        current_user=current_user,
    )

    content = message.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung tin nhắn không được để trống",
        )

    requested_prompt_type = _requested_prompt_type(message)
    prompt_type = validate_prompt_type(
        requested_prompt_type,
        allow_legacy=_conversation_has_legacy_platform(
            db, conversation.id, requested_prompt_type
        ),
    )
    custom_platform_name = _resolve_custom_platform_name(message, prompt_type)
    brand = resolve_message_brand(message, conversation, db, current_user)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=content,
        ad_brief_json=(
            _serialize_ad_brief(message, prompt_type, custom_platform_name)
        ),
        prompt_type=prompt_type,
        platform_name=custom_platform_name,
        brand_id=brand.id if brand else None,
    )

    db.add(user_message)
    db.flush()
    attach_files_to_message(
        db=db,
        conversation_id=conversation.id,
        message_id=user_message.id,
        attachment_ids=message.attachment_ids,
    )
    db.commit()
    db.refresh(user_message)

    history = build_history(
        db=db,
        conversation_id=conversation.id,
    )
    ai_history, product_context = build_ai_context(
        history, content, prompt_type, brand
    )
    should_generate_title = should_generate_conversation_title(
        db=db,
        conversation=conversation,
    )

    def generate() -> Generator[str, None, None]:
        full_response = ""
        stream_completed = False
        stream_cancelled = False

        try:
            for chunk in stream_ai(
                history=ai_history,
                prompt_type=prompt_type,
                custom_platform_name=custom_platform_name,
                product_context=product_context,
                **(
                    {"brand_context": build_brand_context(brand)}
                    if brand
                    else {}
                ),
            ):
                full_response += chunk

                yield chunk
            stream_completed = True
        except GeneratorExit:
            stream_cancelled = True
            raise
        except Exception as error:
            db.rollback()
            error_text = str(error).lower()
            marker = (
                "[ADGEN_QUOTA_ERROR]"
                if "quota" in error_text or "429" in error_text
                else "[ADGEN_STREAM_ERROR]"
            )
            yield f"\n{marker}\n"
        finally:
            if full_response.strip() and (stream_completed or stream_cancelled):
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_response.strip(),
                    prompt_type=prompt_type,
                    platform_name=custom_platform_name,
                    brand_id=brand.id if brand else None,
                )

                db.add(assistant_message)
                if should_generate_title:
                    save_generated_conversation_title(
                        conversation=conversation,
                        first_message_content=content,
                    )
                db.commit()

    return generate()


def edit_message_stream_service(
    message_id: int,
    message_data: MessageUpdate,
    db: Session,
    current_user: User,
) -> Generator[str, None, None]:
    """
    Sửa tin nhắn người dùng, xóa các tin nhắn phía sau
    và stream lại câu trả lời mới.
    """

    existing_message = get_message_service(
        message_id=message_id,
        db=db,
        current_user=current_user,
    )

    if existing_message.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể chỉnh sửa tin nhắn người dùng",
        )

    content = message_data.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung tin nhắn không được để trống",
        )

    requested_prompt_type = message_data.prompt_type or existing_message.prompt_type
    prompt_type = validate_prompt_type(
        requested_prompt_type,
        allow_legacy=is_legacy_prompt_type(existing_message.prompt_type),
    )
    custom_platform_name = _resolve_custom_platform_name(
        message_data,
        prompt_type,
        fallback=_stored_platform_name(existing_message),
    )
    conversation_id = existing_message.conversation_id
    conversation = get_user_conversation(db, conversation_id, current_user)
    brand = (
        db.query(BrandProfile)
        .filter(
            BrandProfile.id == conversation.brand_id,
            BrandProfile.user_id == current_user.id,
        )
        .first()
        if conversation.brand_id
        else None
    )

    existing_message.content = content
    existing_message.prompt_type = prompt_type
    existing_message.platform_name = custom_platform_name
    existing_message.brand_id = brand.id if brand else None

    (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.id > existing_message.id,
        )
        .delete(
            synchronize_session=False
        )
    )

    db.commit()
    db.refresh(existing_message)

    history = build_history(
        db=db,
        conversation_id=conversation_id,
    )
    ai_history, product_context = build_ai_context(
        history, content, prompt_type, brand
    )

    def generate() -> Generator[str, None, None]:
        full_response = ""
        stream_completed = False
        stream_cancelled = False

        try:
            for chunk in stream_ai(
                history=ai_history,
                prompt_type=prompt_type,
                custom_platform_name=custom_platform_name,
                product_context=product_context,
                **(
                    {"brand_context": build_brand_context(brand)}
                    if brand
                    else {}
                ),
            ):
                full_response += chunk

                yield chunk
            stream_completed = True
        except GeneratorExit:
            stream_cancelled = True
            raise
        except Exception as error:
            db.rollback()
            error_text = str(error).lower()
            marker = (
                "[ADGEN_QUOTA_ERROR]"
                if "quota" in error_text or "429" in error_text
                else "[ADGEN_STREAM_ERROR]"
            )
            yield f"\n{marker}\n"
        finally:
            if full_response.strip() and (stream_completed or stream_cancelled):
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response.strip(),
                    prompt_type=prompt_type,
                    platform_name=custom_platform_name,
                    brand_id=brand.id if brand else None,
                )

                db.add(assistant_message)
                db.commit()

    return generate()


def clear_conversation_messages_service(
    conversation_id: int,
    db: Session,
    current_user: User,
):
    conversation = get_user_conversation(
        db=db,
        conversation_id=conversation_id,
        current_user=current_user,
    )
    stored_paths = [
        item.filepath
        for item in db.query(UploadedFile)
        .filter(UploadedFile.conversation_id == conversation.id)
        .all()
    ]

    db.query(UploadedFile).filter(
        UploadedFile.conversation_id == conversation.id
    ).delete(synchronize_session=False)
    db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).delete(synchronize_session=False)

    if not conversation.is_title_custom:
        conversation.title = "Cuộc trò chuyện mới"
        conversation.has_generated_title = False

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

    return {"message": "Đã xóa toàn bộ tin nhắn", "conversation_id": conversation.id}
