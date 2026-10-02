from app.services.context_engine.context_pruner import context_pruner
from app.services.context_engine.intent_resolver import intent_resolver
from app.services.context_engine.models import (
    ExtractedProductContext,
    FollowUpContext,
    FollowUpIntentType,
)


class ConversationContextService:
    """
    Dịch vụ quản lý ngữ cảnh hội thoại thông minh (Conversation Context Service):
    - Tự động phát hiện follow-up request ("Viết ngắn hơn", "Đổi giọng văn", "Thêm CTA", "Viết lại", "5 phiên bản khác", "Đổi sang TikTok").
    - Kế thừa thông tin sản phẩm từ các lượt trò chuyện trước mà không bắt người dùng nhập lại.
    - Cắt tỉa lịch sử tối ưu cho Prompt Engine.
    """

    @classmethod
    def resolve_conversation_context(
        cls,
        user_message: str,
        history: list[dict],
        current_prompt_type: str | None = None,
    ) -> FollowUpContext:
        intent, metadata = intent_resolver.resolve_intent(user_message)
        extracted_product = context_pruner.extract_product_from_history(history)
        last_assistant_content = context_pruner.get_last_assistant_message(history)

        target_platform = metadata.get("target_platform")
        if not target_platform:
            target_platform = current_prompt_type or extracted_product.platform

        return FollowUpContext(
            intent=intent,
            target_platform=target_platform,
            target_tone=metadata.get("target_tone"),
            variation_count=metadata.get("variation_count"),
            specific_instruction=user_message.strip(),
            extracted_product=extracted_product,
            last_assistant_content=last_assistant_content,
        )

    @classmethod
    def format_follow_up_prompt_instruction(cls, follow_up: FollowUpContext) -> str:
        """
        Định dạng chỉ dẫn rõ ràng cho AI Core khi xử lý yêu cầu tinh chỉnh nối tiếp.
        """
        if follow_up.intent == FollowUpIntentType.NEW_REQUEST:
            return ""

        instructions = [
            "### YÊU CẦU ĐIỀU CHỈNH / TINH CHỈNH TIẾP TỤC (FOLLOW-UP REFINEMENT):",
            f"- **Loại yêu cầu**: {follow_up.intent.value.upper()}",
            f"- **Chỉ dẫn cụ thể của người dùng**: \"{follow_up.specific_instruction}\"",
        ]

        if follow_up.intent == FollowUpIntentType.SHORTEN:
            instructions.append(
                "- Hãy rút gọn nội dung, cô đọng các ý chính, loại bỏ câu từ thừa nhưng vẫn giữ trọn vẹn USP và CTA."
            )
        elif follow_up.intent == FollowUpIntentType.EXPAND:
            instructions.append(
                "- Hãy mở rộng nội dung, giải thích sâu hơn về lợi ích, kịch bản hoặc phân cảnh chi tiết."
            )
        elif follow_up.intent == FollowUpIntentType.CHANGE_TONE:
            instructions.append(
                f"- Hãy viết lại toàn bộ nội dung theo giọng điệu / phong cách mới: {follow_up.target_tone or 'như yêu cầu'}."
            )
        elif follow_up.intent == FollowUpIntentType.ADD_CTA:
            instructions.append(
                "- Hãy bổ sung hoặc tối ưu lại các phương án Call to Action mạnh mẽ, rõ ràng và hấp dẫn hơn."
            )
        elif follow_up.intent == FollowUpIntentType.MULTI_VARIATION:
            count = follow_up.variation_count or 3
            instructions.append(
                f"- Hãy tạo đúng {count} phiên bản nội dung độc lập với các góc tiếp cận (angles) khác nhau."
            )
        elif follow_up.intent == FollowUpIntentType.SWITCH_PLATFORM:
            instructions.append(
                f"- Người dùng muốn chuyển đổi nội dung sang nền tảng mới: {follow_up.target_platform.upper()}.\n"
                f"  Hãy sử dụng thông tin sản phẩm đã có và viết lại hoàn toàn theo đúng quy chuẩn kỹ thuật, hook, cấu trúc và CTA của {follow_up.target_platform.upper()}."
            )

        instructions.append(
            "- Giữ nguyên toàn bộ thông tin xác thực về sản phẩm (tên, giá, ưu đãi, tính năng). Tuyệt đối không tự bịa thông tin mới."
        )

        return "\n".join(instructions)


conversation_context_service = ConversationContextService()
