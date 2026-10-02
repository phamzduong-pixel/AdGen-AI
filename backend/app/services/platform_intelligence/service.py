from app.services.platform_intelligence.models import (
    PlatformId,
    PlatformSpecification,
)
from app.services.platform_intelligence.registry import PLATFORM_SPECIFICATIONS


class PlatformIntelligenceService:
    """
    Dịch vụ Platform Intelligence: Cung cấp thông số, quy tắc,
    cấu trúc, hook, CTA và best practices chuyên sâu cho từng nền tảng.
    """

    @classmethod
    def get_specification(cls, platform_id: str | None) -> PlatformSpecification | None:
        if not platform_id:
            return None
        normalized = platform_id.strip().lower()
        try:
            enum_val = PlatformId(normalized)
            return PLATFORM_SPECIFICATIONS.get(enum_val)
        except ValueError:
            return None

    @classmethod
    def get_all_platforms(cls) -> list[PlatformSpecification]:
        return list(PLATFORM_SPECIFICATIONS.values())

    @classmethod
    def is_valid_platform(cls, platform_id: str | None) -> bool:
        if not platform_id:
            return False
        normalized = platform_id.strip().lower()
        try:
            PlatformId(normalized)
            return True
        except ValueError:
            return False

    @classmethod
    def format_platform_context(cls, platform_id: str | None) -> str:
        spec = cls.get_specification(platform_id)
        if spec is None:
            return ""

        sections_str = "\n".join(f"  - {s}" for s in spec.structure.primary_sections)
        tones_str = ", ".join(spec.recommended_tones)
        hook_types_str = ", ".join(spec.hook_guideline.recommended_types)
        cta_actions_str = ", ".join(spec.cta_guideline.primary_actions)
        constraints_str = "\n".join(f"  - {c}" for c in spec.constraints)
        best_practices_str = "\n".join(f"  - {b}" for b in spec.best_practices)
        policy_str = "\n".join(f"  - {p}" for p in spec.policy_guidelines)

        return (
            f"### QUY CHUẨN PLATFORM INTELLIGENCE: {spec.display_name.upper()}\n"
            f"1. **Mục tiêu nền tảng**: {spec.primary_objective}\n"
            f"2. **Hành vi người dùng**: {spec.audience_behavior}\n"
            f"3. **Giọng điệu đề xuất**: {tones_str}\n"
            f"4. **Cấu trúc bắt buộc**:\n{sections_str}\n"
            f"   * Hướng dẫn độ dài: {spec.structure.suggested_length_guide}\n"
            f"5. **Quy tắc Hook**: {spec.hook_guideline.time_or_line_constraint} | Dạng hook ưu tiên: {hook_types_str}\n"
            f"6. **Quy tắc CTA**: {spec.cta_guideline.tone_requirement} | Hành động hướng tới: {cta_actions_str}\n"
            f"7. **Ràng buộc kỹ thuật (Constraints)**:\n{constraints_str}\n"
            f"8. **Nguyên tắc tối ưu (Best Practices)**:\n{best_practices_str}\n"
            f"9. **Chính sách an toàn nền tảng**:\n{policy_str}"
        )


platform_intelligence_service = PlatformIntelligenceService()
