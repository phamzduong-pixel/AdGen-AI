import threading

from app.services.knowledge_base.models import (
    KnowledgeBundle,
    KnowledgeDomain,
    KnowledgeEntry,
)


class KnowledgeService:
    """
    Nền tảng Knowledge Base mở rộng cho:
    - Platform Knowledge
    - Marketing Knowledge
    - Product Knowledge
    - Brand Knowledge
    - Trend Knowledge

    Được thiết kế mở, sẵn sàng tích hợp Vector/RAG trong tương lai mà không làm phức tạp hóa hệ thống hiện tại.
    """

    def __init__(self):
        self._entries: dict[str, KnowledgeEntry] = {}
        self._lock = threading.Lock()
        self._seed_default_knowledge()

    def _seed_default_knowledge(self) -> None:
        default_items = [
            # 1. Marketing Knowledge
            KnowledgeEntry(
                id="mkt-aida",
                domain=KnowledgeDomain.MARKETING,
                title="Mô hình AIDA trong Copywriting",
                summary="Framework 4 bước kinh điển: Attention, Interest, Desire, Action.",
                content=(
                    "- Attention: Gây chú ý ngay từ câu đầu tiên bằng nỗi đau, sự thật bất ngờ hoặc câu hỏi.\n"
                    "- Interest: Duy trì hứng thú bằng cách phân tích thực trạng và cách tiếp cận mới.\n"
                    "- Desire: Kích thích khao khát bằng lợi ích chuyển đổi cụ thể và hình ảnh tương lai tích cực.\n"
                    "- Action: Lời kêu gọi hành động dứt khoát, dễ thực hiện."
                ),
                tags=["framework", "copywriting", "aida"],
                verified_source="AdGen Marketing Standard",
            ),
            KnowledgeEntry(
                id="mkt-pas",
                domain=KnowledgeDomain.MARKETING,
                title="Mô hình PAS (Problem - Agitate - Solution)",
                summary="Framework đánh trúng tâm lý nỗi đau và đưa ra giải pháp cứu cánh.",
                content=(
                    "- Problem: Gọi tên chính xác vấn đề/khó khăn người dùng đang gặp phải.\n"
                    "- Agitate: Xoáy sâu vào hệ quả nếu không giải quyết vấn đề kịp thời (mất thời gian, mất tiền, mệt mỏi).\n"
                    "- Solution: Giới thiệu sản phẩm như một giải pháp cứu tinh dễ dàng và hiệu quả."
                ),
                tags=["framework", "copywriting", "pas", "pain_point"],
                verified_source="AdGen Marketing Standard",
            ),
            KnowledgeEntry(
                id="mkt-fab",
                domain=KnowledgeDomain.MARKETING,
                title="Mô hình FAB (Feature - Advantage - Benefit)",
                summary="Chuyển đổi đặc điểm kỹ thuật thành giá trị thực tế cho người dùng.",
                content=(
                    "- Feature: Đặc điểm hoặc thông số của sản phẩm (Ví dụ: Chống ồn chủ động ANC 45dB).\n"
                    "- Advantage: Điểm vượt trội so với giải pháp thông thường (Loại bỏ tạp âm xung quanh hiệu quả).\n"
                    "- Benefit: Lợi ích đời sống/công việc khách hàng nhận được (Giúp bạn tập trung làm việc tuyệt đối ở quán cafe ồn ào)."
                ),
                tags=["framework", "fab", "product_positioning"],
                verified_source="AdGen Marketing Standard",
            ),
            # 2. Platform Knowledge
            KnowledgeEntry(
                id="plat-google-rsa",
                domain=KnowledgeDomain.PLATFORM,
                title="Tiêu chuẩn kỹ thuật Google Responsive Search Ads",
                summary="Giới hạn ký tự và quy định viết mẫu quảng cáo tìm kiếm Google.",
                content=(
                    "- Tiêu đề (Headline): Tối đa 30 ký tự (bao gồm khoảng trắng và ký tự tiếng Việt).\n"
                    "- Mô tả (Description): Tối đa 90 ký tự.\n"
                    "- Nghiêm cấm dấu chấm than (!) trong tiêu đề.\n"
                    "- Mỗi quảng cáo cần cung cấp từ 5-15 tiêu đề và 3-4 đoạn mô tả để thuật toán Google tối ưu hiển thị."
                ),
                tags=["google_ads", "rsa", "character_limit"],
                verified_source="Google Ads Official Policy",
            ),
            KnowledgeEntry(
                id="plat-tiktok-retention",
                domain=KnowledgeDomain.PLATFORM,
                title="Quy tắc giữ chân người xem video TikTok",
                summary="Nguyên tắc 3 giây đầu và nhịp độ video ngắn.",
                content=(
                    "- 3 giây đầu quyết định 80% tỷ lệ xem tiếp của người dùng TikTok.\n"
                    "- Cần kết hợp đồng thời 3 yếu tố trong 3s đầu: Hình ảnh chuyển động + Giọng nói/Âm thanh + Chữ to trên màn hình (On-screen text).\n"
                    "- Nhịp dựng video (Cut pacing) nên thay đổi góc nhìn/hình ảnh mỗi 2-3 giây."
                ),
                tags=["tiktok", "video_script", "retention"],
                verified_source="TikTok Creator Portal",
            ),
            KnowledgeEntry(
                id="plat-shopee-seo",
                domain=KnowledgeDomain.PLATFORM,
                title="Công thức đặt tiêu đề chuẩn SEO sàn TMĐT Shopee",
                summary="Cấu trúc tiêu đề tối đa hóa lượt tìm kiếm và tỷ lệ nhấp chuột.",
                content=(
                    "- Cấu trúc vàng: [Thương hiệu] + [Tên sản phẩm] + [Đặc điểm nổi bật/Model] + [Công dụng hoặc Phân loại] + [Mã bảo hành/Cam kết].\n"
                    "- Đặt các từ khóa có lượng tìm kiếm cao nhất lên 50 ký tự đầu tiên của tiêu đề.\n"
                    "- Mô tả sản phẩm phải chia rõ ràng thành các mục: Đặc điểm nổi bật, Bảng thông số, Hướng dẫn sử dụng, Chính sách đổi trả."
                ),
                tags=["shopee", "ecommerce", "seo_title"],
                verified_source="Shopee Seller Education Hub",
            ),
            KnowledgeEntry(
                id="plat-youtube-retention",
                domain=KnowledgeDomain.PLATFORM,
                title="Nguyên tắc tối ưu Video SEO và tỷ lệ xem hết trên YouTube",
                summary="Chiến lược giữ chân 5s đầu, cấu trúc Chapters và Call-To-Action cho YouTube.",
                content=(
                    "- 5 đến 15 giây đầu tiên là giai đoạn vàng quyết định Retention Curve của YouTube.\n"
                    "- Tiêu đề dưới 70 ký tự để hiển thị trọn vẹn trên Mobile.\n"
                    "- Mô tả cần chứa từ khóa SEO, danh sách Timestamps (Chapters) và link tài nguyên hữu ích.\n"
                    "- CTA đăng ký kênh nên lồng ghép tự nhiên sau khi đã trao giá trị cốt lõi."
                ),
                tags=["youtube", "video_seo", "retention", "timestamps"],
                verified_source="YouTube Creator Academy",
            ),
            KnowledgeEntry(
                id="plat-facebook-performance",
                domain=KnowledgeDomain.PLATFORM,
                title="Quy chuẩn tối ưu hóa chuyển đổi Facebook Ads",
                summary="Hành vi đọc lướt 3 dòng đầu và chuyển hóa tính năng thành lợi ích.",
                content=(
                    "- 3 dòng đầu tiên của caption phải giữ chân người đọc trước nút 'Xem thêm'.\n"
                    "- Phân bổ rõ ràng: Hook -> Nỗi đau/Lợi ích -> Ưu đãi -> CTA nhắn tin hoặc mua hàng.\n"
                    "- Đề xuất tiêu đề ngắn gọn cho banner hình ảnh đi kèm."
                ),
                tags=["facebook", "facebook_ads", "performance_marketing"],
                verified_source="Meta Business Blueprint",
            ),
            KnowledgeEntry(
                id="plat-email-openrate",
                domain=KnowledgeDomain.PLATFORM,
                title="Chiến lược tối ưu tỷ lệ mở và nhấp chuột Email Marketing",
                summary="Tiêu đề dưới 50 ký tự, pre-header và 1 CTA trọng tâm.",
                content=(
                    "- Tiêu đề Subject Line dưới 50 ký tự để không bị cắt trên smartphone.\n"
                    "- Luôn có Preview Text bổ trợ và phần Tái bút (P.S.) nhấn mạnh ưu đãi.\n"
                    "- Mỗi email chỉ tập trung vào 1 hành động chuyển đổi duy nhất (Single focused CTA)."
                ),
                tags=["email", "newsletter", "subject_line"],
                verified_source="Email Marketing Association Standard",
            ),
        ]
        for item in default_items:
            self._entries[item.id] = item

    def register_entry(self, entry: KnowledgeEntry) -> None:
        with self._lock:
            self._entries[entry.id] = entry

    def query_knowledge(
        self,
        domain: KnowledgeDomain | None = None,
        tags: list[str] | None = None,
        query: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeEntry]:
        with self._lock:
            results = []
            q_str = query.lower() if query else None
            tags_lower = [t.lower() for t in tags] if tags else []

            for entry in self._entries.values():
                if domain and entry.domain != domain:
                    continue
                if tags_lower:
                    entry_tags = [t.lower() for t in entry.tags]
                    if not any(t in entry_tags for t in tags_lower):
                        continue
                if q_str:
                    matched = (
                        q_str in entry.title.lower()
                        or q_str in entry.summary.lower()
                        or q_str in entry.content.lower()
                    )
                    if not matched:
                        continue
                results.append(entry)

            return results[:limit]

    def format_knowledge_context(
        self,
        domain: KnowledgeDomain | None = None,
        platform_name: str | None = None,
        product_context: str | None = None,
        brand_context: str | None = None,
    ) -> str:
        """
        Định dạng ngữ cảnh tri thức chuẩn xác cho Prompt Engine.
        Áp đặt quy tắc GROUNDING tuyệt đối: Không bịa đặt số liệu hoặc chính sách.
        """
        entries = self.query_knowledge(
            domain=domain,
            query=platform_name,
            limit=4,
        )

        parts = []
        if entries:
            parts.append("### NỀN TẢNG TRI THỨC ĐÃ KIỂM CHỨNG (VERIFIED KNOWLEDGE)")
            for e in entries:
                parts.append(
                    f"**[{e.domain.value.upper()}] {e.title}** (Nguồn: {e.verified_source or 'Hệ thống'}):\n{e.content}"
                )

        if product_context and product_context.strip():
            parts.append(f"**[PRODUCT KNOWLEDGE] Thông tin sản phẩm xác thực:**\n{product_context.strip()}")

        if brand_context and brand_context.strip():
            parts.append(f"**[BRAND KNOWLEDGE] Quy chuẩn thương hiệu:**\n{brand_context.strip()}")

        grounding_rule = (
            "### NGUYÊN TẮC TRUNG THỰC & CHÍNH XÁC DỮ LIỆU (GROUNDING POLICY):\n"
            "- CHỈ sử dụng các đặc điểm, công dụng, giá bán hoặc chính sách được cung cấp trong dữ liệu.\n"
            "- TUYỆT ĐỐI KHÔNG tự bịa đặt: Số liệu thị trường, phần trăm khuyến mãi, giải thưởng, chứng nhận hoặc chính sách nền tảng không có căn cứ.\n"
            "- Nếu thông tin chưa có, hãy yêu cầu người dùng bổ sung hoặc tạo nội dung ở dạng khung đề xuất trung thực."
        )
        parts.append(grounding_rule)

        return "\n\n".join(parts)


knowledge_service = KnowledgeService()
