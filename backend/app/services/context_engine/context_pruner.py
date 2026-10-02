from typing import Any

from app.services.context_engine.models import ExtractedProductContext


class ContextPruner:
    """
    Bộ tối ưu hóa và trích xuất ngữ cảnh liên quan từ lịch sử hội thoại.
    Nhiệm vụ:
    - Tìm và trích xuất dữ liệu sản phẩm / AdBrief từ các tin nhắn trước đó.
    - Tìm câu trả lời gần nhất của Assistant để làm cơ sở tinh chỉnh (Refinement basis).
    - Cắt tỉa các tin nhắn dư thừa để tránh tràn token context window.
    """

    @classmethod
    def extract_product_from_history(cls, history: list[dict]) -> ExtractedProductContext:
        extracted = ExtractedProductContext()

        # Quét ngược từ tin nhắn mới nhất về trước để lấy AdBrief hoặc thông tin sản phẩm mới nhất
        for message in reversed(history):
            if message.get("ad_brief"):
                brief = message["ad_brief"]
                if isinstance(brief, dict):
                    extracted.product_name = brief.get("product_name") or extracted.product_name
                    extracted.description = brief.get("description") or extracted.description
                    extracted.target_audience = brief.get("target_audience") or extracted.target_audience
                    extracted.platform = brief.get("platform") or extracted.platform
                    extracted.price = brief.get("price") or extracted.price
                    extracted.offer = brief.get("offer") or extracted.offer
                    extracted.usp = brief.get("usp") or extracted.usp
                    extracted.raw_brief = brief
                    break

        return extracted

    @classmethod
    def get_last_assistant_message(cls, history: list[dict]) -> str | None:
        for message in reversed(history):
            if message.get("role") == "assistant" or message.get("role") == "model":
                content = message.get("content", "").strip()
                if content:
                    return content
        return None

    @classmethod
    def prune_relevant_history(
        cls,
        history: list[dict],
        max_turn_pairs: int = 3,
    ) -> list[dict]:
        """
        Chỉ giữ lại tối đa N cặp hội thoại gần nhất để tập trung vào mục tiêu của người dùng
        thay vì gửi toàn bộ lịch sử dài vô tận.
        """
        if len(history) <= (max_turn_pairs * 2):
            return history

        # Luôn giữ lại tin nhắn đầu tiên (chứa brief gốc nếu có) + N tin nhắn gần nhất
        first_message = history[0]
        recent_messages = history[-(max_turn_pairs * 2):]

        if first_message not in recent_messages:
            return [first_message] + recent_messages
        return recent_messages


context_pruner = ContextPruner()
