import json

from fastapi import HTTPException
from fastapi import status
from pydantic import BaseModel
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.platforms import normalize_custom_platform_name
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.user import User
from app.schemas.content_tools import ContentSourceRequest
from app.services.ai_service import generate_structured_content
from app.services.message_service import get_message_service


def resolve_content_source(
    data: ContentSourceRequest,
    db: Session,
    current_user: User,
) -> tuple[str, str | None, str | None, str | None, str | None, int | None]:
    if data.saved_content_id is not None:
        saved_content = (
            db.query(SavedContent)
            .filter(
                SavedContent.id == data.saved_content_id,
                SavedContent.user_id == current_user.id,
            )
            .first()
        )
        if saved_content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Nội dung đã lưu không tồn tại hoặc bạn không có quyền truy cập"
                ),
            )
        return (
            saved_content.content,
            data.platform or saved_content.platform,
            data.platform_name or saved_content.platform_name,
            data.target_audience,
            data.tone,
            saved_content.id,
        )

    if data.message_id is None:
        return (
            data.content or "",
            data.platform,
            data.platform_name,
            data.target_audience,
            data.tone,
            None,
        )

    message = get_message_service(
        message_id=data.message_id,
        db=db,
        current_user=current_user,
    )
    if message.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể xử lý phản hồi do AI tạo",
        )

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

    platform = data.platform
    platform_name = data.platform_name
    target_audience = data.target_audience
    tone = data.tone
    if source_message:
        platform = platform or source_message.prompt_type
        platform_name = platform_name or source_message.platform_name
        if source_message.ad_brief_json:
            try:
                brief = json.loads(source_message.ad_brief_json)
                platform = platform or brief.get("platform")
                platform_name = platform_name or brief.get("platform_name")
                target_audience = target_audience or brief.get("target_audience")
                tone = tone or brief.get("tone")
            except (TypeError, ValueError):
                pass

    return message.content, platform, normalize_custom_platform_name(platform_name), target_audience, tone, None


def request_structured_ai(
    *,
    system_instruction: str,
    payload: dict,
    response_model: type[BaseModel],
) -> BaseModel:
    try:
        raw_response = generate_structured_content(
            system_instruction=system_instruction,
            payload=payload,
        )
    except Exception as error:
        error_text = str(error).lower()
        if any(marker in error_text for marker in ("quota", "429", "rate limit")):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Gemini đã hết hạn mức hoặc đang quá tải. "
                    "Vui lòng thử lại sau."
                ),
            ) from error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini không phản hồi. Vui lòng thử lại sau.",
        ) from error

    try:
        return response_model.model_validate_json(raw_response)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini trả về dữ liệu không đúng cấu trúc yêu cầu.",
        ) from error
