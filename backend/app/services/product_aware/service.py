from app.services.knowledge_base.service import knowledge_service
from app.services.platform_intelligence.service import platform_intelligence_service
from app.services.product_aware.models import (
    AudienceProfile,
    CampaignObjectiveType,
    ProductAwareContext,
    ProductProfile,
)
from app.services.external_retrieval.evidence import Evidence
from app.services.product_trust.service import format_product_trust_context
from app.services.trend_intelligence.service import trend_intelligence_service


class ProductAwareEngine:
    """
    Engine sinh nội dung định hướng sản phẩm (Product-Aware Generation Engine).
    Hợp nhất 7 yếu tố cốt lõi:
    1. Product (Thông số, tính năng, lợi ích, giá, ưu đãi)
    2. Target Audience (Chân dung, nỗi đau, kỳ vọng)
    3. Campaign Objective (Mục tiêu chiến dịch)
    4. Platform (Facebook, Instagram, TikTok, Google Ads, YouTube, Shopee, Email, Landing Page, SEO)
    5. Platform Knowledge (Quy chuẩn kỹ thuật, hook, CTA của nền tảng)
    6. Marketing Knowledge (Framework AIDA, PAS, FAB, BAB)
    7. Relevant Current Information (Xu hướng thực tế đã thẩm định)
    """

    @classmethod
    def format_product_section(cls, product: ProductProfile) -> str:
        lines = [f"- **Tên sản phẩm**: {product.name}"]
        if product.category:
            lines.append(f"- **Ngành hàng**: {product.category}")
        if product.description:
            lines.append(f"- **Mô tả**: {product.description}")
        if product.key_features:
            lines.append(f"- **Tính năng nổi bật**: {', '.join(product.key_features)}")
        if product.key_benefits:
            lines.append(f"- **Lợi ích cốt lõi**: {', '.join(product.key_benefits)}")
        if product.usp:
            lines.append(f"- **Điểm khác biệt độc quyền (USP)**: {product.usp}")
        if product.price:
            lines.append(f"- **Giá bán**: {product.price}")
        if product.offer:
            lines.append(f"- **Chương trình ưu đãi**: {product.offer}")
        if product.warranty:
            lines.append(f"- **Bảo hành & Cam kết**: {product.warranty}")
        if product.technical_specs:
            specs_str = "; ".join(f"{k}: {v}" for k, v in product.technical_specs.items())
            lines.append(f"- **Thông số kỹ thuật**: {specs_str}")
        if product.forbidden_claims:
            lines.append(
                f"- **Cam kết cấm sử dụng (Forbidden Claims)**: {', '.join(product.forbidden_claims)}"
            )
        return "\n".join(lines)

    @classmethod
    def format_audience_section(cls, audience: AudienceProfile | None) -> str:
        if not audience:
            return "- Khách hàng mục tiêu chung theo ngữ cảnh sản phẩm."

        lines = []
        if audience.persona_name:
            lines.append(f"- **Chân dung khách hàng**: {audience.persona_name}")
        if audience.demographics:
            lines.append(f"- **Đặc điểm nhân khẩu học**: {audience.demographics}")
        if audience.pain_points:
            lines.append(f"- **Nỗi đau / Vấn đề gặp phải**: {', '.join(audience.pain_points)}")
        if audience.desires:
            lines.append(f"- **Mong muốn / Kỳ vọng**: {', '.join(audience.desires)}")
        if audience.common_objections:
            lines.append(f"- **Rào cản / Từ chối thường gặp**: {', '.join(audience.common_objections)}")
        return "\n".join(lines) if lines else "- Đối tượng khách hàng đại chúng."

    @classmethod
    def build_full_context(
        cls,
        context: ProductAwareContext,
        include_trends: bool = True,
        product_evidence: tuple[Evidence, ...] | None = None,
    ) -> str:
        """
        Tổng hợp toàn bộ 7 yếu tố thành cấu trúc hướng dẫn hoàn chỉnh cho Prompt Engine.
        """
        parts = []

        # 1. Product Section
        parts.append("### 1. THÔNG TIN SẢN PHẨM DO NGƯỜI DÙNG CUNG CẤP (PRODUCT REFERENCE)")
        parts.append(cls.format_product_section(context.product))

        trust_context = format_product_trust_context(
            context.product,
            product_evidence,
        )
        if trust_context:
            parts.append(trust_context)

        # 2. Audience Section
        parts.append("### 2. KHÁCH HÀNG MỤC TIÊU (TARGET AUDIENCE)")
        parts.append(cls.format_audience_section(context.audience))

        # 3. Campaign Objective
        objective_labels = {
            CampaignObjectiveType.AWARENESS: "Gia tăng nhận diện thương hiệu",
            CampaignObjectiveType.ENGAGEMENT: "Thúc đẩy tương tác (Like, Comment, Share)",
            CampaignObjectiveType.TRAFFIC: "Kéo lưu lượng truy cập về website/gian hàng",
            CampaignObjectiveType.MESSAGES: "Kích thích khách hàng nhắn tin tư vấn (Messenger / Direct)",
            CampaignObjectiveType.LEAD_GENERATION: "Thu thập khách hàng tiềm năng (Lead Generation)",
            CampaignObjectiveType.CONVERSION: "Chuyển đổi bán hàng / Chốt đơn trực tiếp",
            CampaignObjectiveType.RETENTION: "Chăm sóc và giữ chân khách hàng cũ",
            CampaignObjectiveType.EVENT_PROMOTION: "Quảng bá sự kiện / Ra mắt sản phẩm mới",
        }
        obj_text = objective_labels.get(context.objective, context.objective.value)
        parts.append(f"### 3. MỤC TIÊU CHIẾN DỊCH (CAMPAIGN OBJECTIVE)\n- {obj_text}")

        # 4 & 5. Platform & Platform Knowledge
        platform_info = platform_intelligence_service.format_platform_context(context.platform)
        if platform_info:
            parts.append(platform_info)

        # 6. Marketing Knowledge & Frameworks
        brand_ctx = ""
        if context.brand_name:
            brand_ctx = f"Thương hiệu: {context.brand_name}"
            if context.brand_voice:
                brand_ctx += f" | Tone of voice: {context.brand_voice}"

        mkt_knowledge = knowledge_service.format_knowledge_context(
            platform_name=context.platform,
            brand_context=brand_ctx,
        )
        if mkt_knowledge:
            parts.append(mkt_knowledge)

        # 7. Relevant Current Information
        if include_trends:
            trend_ctx = trend_intelligence_service.format_trend_context(
                query=context.product.category or context.product.name,
                platform=context.platform,
            )
            if trend_ctx:
                parts.append(trend_ctx)

        # Grounding Rule Enforcement
        parts.append(
            "### QUY TẮC RÀNG BUỘC SẢN PHẨM (STRICT GROUNDING):\n"
            "- Tuyệt đối KHÔNG tự ý đưa ra mức giá, chương trình giảm giá hoặc quà tặng khác ngoài những gì đã nêu trong mục 1.\n"
            "- Nếu thiếu thông tin cần thiết, hãy đặt câu hỏi gợi mở cho người dùng thay vì tự bịa số liệu."
        )

        return "\n\n".join(parts)


product_aware_engine = ProductAwareEngine()
