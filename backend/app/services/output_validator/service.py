import re

from app.services.output_validator.models import (
    ValidationErrorType,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from app.services.output_validator.rules import OutputValidationRules


class OutputValidationService:
    """
    Dịch vụ thẩm định và bảo vệ chất lượng đầu ra của AI (Output Validation & Resilience Service):
    - Kiểm tra phản hồi rỗng, quá ngắn hoặc sai định dạng.
    - Kiểm tra các ràng buộc kỹ thuật của nền tảng (Google Ads, Email, TikTok).
    - Phát hiện và cảnh báo các cam kết cấm (Forbidden Claims).
    - Tự động sửa chữa nhẹ (loại bỏ markdown blocks hỏng, làm sạch khoảng trắng).
    - Cung cấp cơ chế Fallback an toàn khi AI API gặp sự cố hoặc timeout, ngăn chặn server bị crash.
    """

    @classmethod
    def validate_and_sanitize(
        cls,
        raw_text: str | None,
        platform: str | None = None,
        forbidden_claims: list[str] | None = None,
    ) -> ValidationResult:
        # 1. Non-empty check
        if not raw_text or not raw_text.strip():
            fallback = cls.generate_fallback_response(
                error_type=ValidationErrorType.EMPTY_RESPONSE,
                platform=platform,
            )
            return ValidationResult(
                is_valid=False,
                sanitized_content=fallback,
                issues=[
                    ValidationIssue(
                        error_type=ValidationErrorType.EMPTY_RESPONSE,
                        severity=ValidationSeverity.CRITICAL,
                        message="Phản hồi từ AI rỗng hoặc chỉ chứa khoảng trắng.",
                    )
                ],
                auto_repaired=True,
            )

        content = raw_text.strip()
        auto_repaired = False

        # 2. Auto-repair formatting (remove orphan code block fences if any)
        if content.count("```") % 2 != 0:
            content += "\n```"
            auto_repaired = True

        # 3. Check forbidden claims & platform constraints & length
        issues: list[ValidationIssue] = []
        issues.extend(OutputValidationRules.check_non_empty(content))
        issues.extend(OutputValidationRules.check_forbidden_claims(content, forbidden_claims))
        issues.extend(OutputValidationRules.check_platform_constraints(content, platform))

        has_critical = any(
            i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for i in issues
        )

        return ValidationResult(
            is_valid=not has_critical,
            sanitized_content=content,
            issues=issues,
            auto_repaired=auto_repaired,
        )

    @classmethod
    def generate_fallback_response(
        cls,
        error_type: ValidationErrorType,
        platform: str | None = None,
        user_prompt: str | None = None,
        custom_message: str | None = None,
    ) -> str:
        """
        Tạo nội dung phản hồi an toàn (Resilient Fallback) khi AI gặp sự cố kỹ thuật.
        Đảm bảo không bao giờ để server crash hoặc trả về 500 error không kiểm soát.
        """
        plat_label = (platform or "quảng cáo").upper()

        if error_type in [ValidationErrorType.API_ERROR, ValidationErrorType.TIMEOUT]:
            return (
                f"### ⚠️ THÔNG BÁO HỆ THỐNG - DỊCH VỤ AI ĐANG TẢI CAO\n\n"
                f"Hệ thống tạo nội dung cho nền tảng **{plat_label}** tạm thời gặp độ trễ từ dịch vụ AI.\n\n"
                f"**Khuyến nghị:**\n"
                f"1. Vui lòng bấm nút **Thử lại** hoặc gửi lại yêu cầu sau ít giây.\n"
                f"2. Bạn có thể bổ sung thêm mô tả chi tiết về sản phẩm để AI phản hồi nhanh và chính xác hơn."
            )

        if error_type == ValidationErrorType.EMPTY_RESPONSE:
            return (
                f"### ⚠️ NỘI DUNG CHƯA ĐỦ ĐỂ TẠO BÀI VIẾT CHO {plat_label}\n\n"
                f"Hệ thống chưa nhận đủ dữ liệu đầu vào hoặc AI chưa hoàn tất xử lý.\n\n"
                f"**Vui lòng cung cấp thêm:**\n"
                f"- Tên sản phẩm hoặc dịch vụ\n"
                f"- Lợi ích chính hoặc tính năng nổi bật\n"
                f"- Mục tiêu quảng cáo hoặc ưu đãi (nếu có)"
            )

        return (
            f"### ⚠️ YÊU CẦU ĐANG ĐƯỢC XỬ LÝ\n\n"
            f"{custom_message or 'Vui lòng kiểm tra lại thông tin và thử lại.'}"
        )


output_validation_service = OutputValidationService()
