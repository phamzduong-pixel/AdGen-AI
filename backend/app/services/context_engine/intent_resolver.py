import re

from app.services.context_engine.models import FollowUpIntentType
from app.services.prompt_service import normalize_prompt_type


class FollowUpIntentResolver:
    """
    Bộ nhận diện ý định follow-up của người dùng từ văn bản tự nhiên.
    Nhận diện các dạng:
    - "Viết ngắn hơn", "cô đọng lại", "rút gọn" -> SHORTEN
    - "Viết dài hơn", "chi tiết hơn", "mở rộng" -> EXPAND
    - "Đổi giọng văn hài hước/chuyên nghiệp", "đổi tone" -> CHANGE_TONE
    - "Thêm CTA", "thêm lời kêu gọi hành động", "đổi cta" -> ADD_CTA
    - "Viết lại", "tạo bản khác", "làm lại" -> REWRITE
    - "Cho tôi 5 phiên bản khác", "tạo 3 options", "thêm 4 phương án" -> MULTI_VARIATION
    - "Đổi sang TikTok", "chuyển qua Shopee", "viết cho Facebook" -> SWITCH_PLATFORM
    """

    PLATFORM_PATTERNS = {
        "facebook": r"\b(facebook|fb|face)\b",
        "instagram": r"\b(instagram|ig|insta)\b",
        "tiktok": r"\b(tiktok|tik tok)\b",
        "google_ads": r"\b(google ads|google ad|gads|google search)\b",
        "youtube": r"\b(youtube|yt|shorts|video dài)\b",
        "shopee": r"\b(shopee|sàn tmdt|tmdt|lazada|tiktok shop)\b",
        "email": r"\b(email|mail|newsletter|hộp thư)\b",
        "landing_page": r"\b(landing page|landingpage|trang đích|sales page)\b",
        "seo": r"\b(seo|bài viết seo|blog|bài blog)\b",
    }

    @classmethod
    def detect_platform_switch(cls, user_text: str) -> str | None:
        text_lower = user_text.lower()
        if re.search(r"\b(đổi sang|chuyển qua|chuyển sang|viết cho|đổi qua|nền tảng)\b", text_lower):
            for platform, pattern in cls.PLATFORM_PATTERNS.items():
                if re.search(pattern, text_lower):
                    return platform
        return None

    @classmethod
    def resolve_intent(cls, user_text: str) -> tuple[FollowUpIntentType, dict]:
        text_lower = user_text.strip().lower()
        metadata: dict = {}

        # 1. Switch Platform Check
        switched_platform = cls.detect_platform_switch(text_lower)
        if switched_platform:
            metadata["target_platform"] = switched_platform
            return FollowUpIntentType.SWITCH_PLATFORM, metadata

        # 2. Multi-variation Check
        var_match = re.search(r"(\d+)\s*(phiên bản|phương án|options|lựa chọn|mẫu|version)", text_lower)
        if var_match or "nhiều phiên bản" in text_lower or "thêm options" in text_lower:
            count = int(var_match.group(1)) if var_match else 3
            metadata["variation_count"] = count
            return FollowUpIntentType.MULTI_VARIATION, metadata

        # 2b. Voiceover / Audio Generation Check
        if re.search(r"\b(voiceover|lồng tiếng|đọc kịch bản|đọc nội dung|sinh audio|tạo audio|chuyển thành audio|chuyển thành giọng nói|đọc giúp tôi|nghe thử giọng)\b", text_lower):
            if "nam" in text_lower or "đàn ông" in text_lower:
                metadata["preferred_gender"] = "male"
            elif "nữ" in text_lower or "phụ nữ" in text_lower:
                metadata["preferred_gender"] = "female"
            return FollowUpIntentType.GENERATE_VOICEOVER, metadata

        # 3. Shorten Check
        if re.search(r"\b(ngắn hơn|ngắn gọn|rút gọn|cô đọng|thu gọn|ngắn lại|bớt dài)\b", text_lower):
            return FollowUpIntentType.SHORTEN, metadata

        # 4. Expand Check
        if re.search(r"\b(dài hơn|chi tiết hơn|mở rộng|viết sâu hơn|thêm ý)\b", text_lower):
            return FollowUpIntentType.EXPAND, metadata

        # 5. Add / Change CTA Check
        if re.search(r"\b(cta|kêu gọi hành động|call to action|lời kêu gọi)\b", text_lower) and any(w in text_lower for w in ["thêm", "đổi", "bổ sung", "tạo", "cho", "viết"]):
            return FollowUpIntentType.ADD_CTA, metadata

        # 6. Change Tone Check
        tone_match = re.search(
            r"\b(đổi giọng|đổi tone|giọng văn|phong cách|tone)\s*(hài hước|chuyên nghiệp|gần gũi|trẻ trung|sang trọng|năng động|cảm xúc|kịch tính)?",
            text_lower,
        )
        if tone_match or "hài hước hơn" in text_lower or "chuyên nghiệp hơn" in text_lower or "gần gũi hơn" in text_lower:
            if tone_match and tone_match.group(2):
                metadata["target_tone"] = tone_match.group(2)
            elif "hài hước" in text_lower:
                metadata["target_tone"] = "hài hước"
            elif "chuyên nghiệp" in text_lower:
                metadata["target_tone"] = "chuyên nghiệp"
            elif "gần gũi" in text_lower:
                metadata["target_tone"] = "gần gũi"
            return FollowUpIntentType.CHANGE_TONE, metadata

        # 7. Rewrite Check
        if re.search(r"\b(viết lại|làm lại|tạo lại|viết bản khác|chỉnh lại|thay đổi nội dung)\b", text_lower):
            return FollowUpIntentType.REWRITE, metadata

        # 8. If text is very short (< 10 words) and contains directive words, treat as general refinement
        if len(user_text.split()) <= 15 and any(w in text_lower for w in ["thêm", "bớt", "đổi", "sửa", "chỉnh", "nhấn mạnh", "bỏ"]):
            return FollowUpIntentType.GENERAL_REFINEMENT, metadata

        return FollowUpIntentType.NEW_REQUEST, metadata


intent_resolver = FollowUpIntentResolver()
