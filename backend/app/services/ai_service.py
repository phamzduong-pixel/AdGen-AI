from collections.abc import Generator
import json
from pathlib import Path

from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types

from app.core.config import settings
from app.services.prompt_service import build_system_prompt
from app.prompts.ad_brief import format_ad_brief
from app.services.output_validator.service import output_validation_service
from app.services.learning_dataset.models import LearningDatasetRecord
from app.services.learning_dataset.service import learning_dataset_service


MODEL_NAME = "gemini-2.5-flash"


if False and not settings.GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY chưa được cấu hình trong file .env"
    )


client = (
    genai.Client(api_key=settings.GEMINI_API_KEY)
    if settings.GEMINI_API_KEY
    else None
)


def _gemini_client():
    if client is None:
        raise RuntimeError("GEMINI_API_KEY chua duoc cau hinh")
    return client


def generate_structured_content(
    *,
    system_instruction: str,
    payload: dict,
) -> str:
    """Generate a JSON response while keeping user content out of the system prompt."""

    try:
        response = _gemini_client().models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=json.dumps(payload, ensure_ascii=False)
                        )
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        response_text = response.text
        if not response_text:
            raise ValueError("Gemini không trả về nội dung")
        return response_text.strip()
    except Exception as error:
        raise RuntimeError(
            f"Không thể nhận dữ liệu có cấu trúc từ Gemini: {error}"
        ) from error


def format_history(
    history: list[dict],
) -> list[types.Content]:
    """
    Chuyển lịch sử hội thoại trong database
    sang định dạng của Google Gen AI SDK.

    Database:
        assistant -> Gemini:
        model
    """

    contents: list[types.Content] = []

    for message in history:
        role = message.get("role")
        content = message.get("content", "").strip()

        if not content:
            continue

        gemini_role = (
            "user"
            if role == "user"
            else "model"
        )

        if message.get("ad_brief"):
            content = (
                f"{content}\n\n"
                f"{format_ad_brief(message['ad_brief'])}"
            )

        parts = [types.Part.from_text(text=content)]

        if gemini_role == "user":
            for attachment in message.get("attachments", []):
                path = Path(attachment["filepath"])
                mime_type = attachment.get("content_type", "")
                if not path.is_file():
                    continue
                if (
                    mime_type.startswith("image/")
                    or mime_type.startswith("video/")
                    or mime_type == "application/pdf"
                ):
                    parts.append(
                        types.Part.from_bytes(
                            data=path.read_bytes(),
                            mime_type=mime_type,
                        )
                    )
                elif mime_type == "text/plain":
                    text_content = path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )[:50_000]
                    parts.append(
                        types.Part.from_text(
                            text=(
                                f"Nội dung tệp {attachment['filename']}:\n"
                                f"{text_content}"
                            )
                        )
                    )
                else:
                    parts.append(
                        types.Part.from_text(
                            text=(
                                f"Tệp {attachment['filename']} đã được lưu, "
                                "nhưng định dạng này chưa được đọc."
                            )
                        )
                    )

        contents.append(types.Content(role=gemini_role, parts=parts))

    return contents


def create_config(
    prompt_type: str | None = None,
    custom_platform_name: str | None = None,
    brand_context: str = "",
    product_context: str = "",
    trend_query: str | None = None,
    enable_intelligence: bool = True,
) -> types.GenerateContentConfig:
    """
    Tạo cấu hình Gemini với system prompt phù hợp, kết hợp Platform Intelligence,
    Knowledge Base và Trend Intelligence.
    """

    system_instruction = build_system_prompt(
        prompt_type=prompt_type,
        custom_platform_name=custom_platform_name,
        brand_context=brand_context,
        product_context=product_context,
        trend_query=trend_query,
        enable_intelligence=enable_intelligence,
    )

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
    )


def ask_ai(
    history: list[dict],
    prompt_type: str | None = None,
    custom_platform_name: str | None = None,
    brand_context: str = "",
    product_context: str = "",
    trend_query: str | None = None,
    enable_intelligence: bool = True,
) -> str:
    """
    Gửi toàn bộ lịch sử hội thoại đến Gemini
    và nhận câu trả lời hoàn chỉnh.
    """

    contents = format_history(history)

    if not contents:
        raise ValueError(
            "Không có nội dung hợp lệ để gửi tới Gemini"
        )

    config = create_config(
        prompt_type=prompt_type,
        custom_platform_name=custom_platform_name,
        brand_context=brand_context,
        product_context=product_context,
        trend_query=trend_query,
        enable_intelligence=enable_intelligence,
    )

    try:
        response = _gemini_client().models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )

        response_text = response.text

        # 1. Output Validation & Sanitization
        validation_result = output_validation_service.validate_and_sanitize(
            raw_text=response_text,
            platform=prompt_type,
        )

        final_content = validation_result.sanitized_content

        # 2. AI Learning Dataset Logging
        try:
            record = LearningDatasetRecord(
                prompt_knowledge={"prompt_type": prompt_type, "model": MODEL_NAME},
                input_context={
                    "platform": prompt_type,
                    "brand_context": brand_context,
                    "product_context": product_context,
                },
                generated_content=final_content,
                tags=[prompt_type] if prompt_type else [],
            )
            learning_dataset_service.log_generation(record)
        except Exception:
            pass

        return final_content

    except Exception as error:
        raise RuntimeError(
            f"Không thể nhận phản hồi từ Gemini: {error}"
        ) from error


def generate_response(
    prompt: str,
    prompt_type: str | None = None,
    custom_platform_name: str | None = None,
    brand_context: str = "",
    product_context: str = "",
    trend_query: str | None = None,
) -> str:
    """
    Hàm tương thích dành cho luồng chỉ truyền
    một prompt thay vì toàn bộ lịch sử hội thoại.
    """

    if not isinstance(prompt, str):
        raise ValueError(
            "Prompt phải là chuỗi"
        )

    content = prompt.strip()

    if not content:
        raise ValueError(
            "Prompt không được để trống"
        )

    return ask_ai(
        history=[
            {
                "role": "user",
                "content": content,
            }
        ],
        prompt_type=prompt_type,
        custom_platform_name=custom_platform_name,
        brand_context=brand_context,
        product_context=product_context,
        trend_query=trend_query,
    )


def stream_ai(
    history: list[dict],
    prompt_type: str | None = None,
    custom_platform_name: str | None = None,
    brand_context: str = "",
    product_context: str = "",
    trend_query: str | None = None,
    enable_intelligence: bool = True,
) -> Generator[str, None, None]:
    """
    Gửi lịch sử hội thoại đến Gemini
    và trả phản hồi theo từng phần.
    """

    contents = format_history(history)

    if not contents:
        raise ValueError(
            "Không có nội dung hợp lệ để gửi tới Gemini"
        )

    config = create_config(
        prompt_type=prompt_type,
        custom_platform_name=custom_platform_name,
        brand_context=brand_context,
        product_context=product_context,
        trend_query=trend_query,
        enable_intelligence=enable_intelligence,
    )

    try:
        response_stream = (
            _gemini_client().models.generate_content_stream(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
        )

        for chunk in response_stream:
            chunk_text = chunk.text

            if chunk_text:
                yield chunk_text

    except Exception as error:
        raise RuntimeError(
            f"Không thể stream phản hồi từ Gemini: {error}"
        ) from error
