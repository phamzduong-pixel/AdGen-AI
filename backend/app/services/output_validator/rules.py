import re

from app.services.output_validator.models import (
    ValidationErrorType,
    ValidationIssue,
    ValidationSeverity,
)


class OutputValidationRules:
    """Các quy tắc kiểm tra tính hợp lệ và an toàn của nội dung AI sinh ra."""

    @classmethod
    def check_non_empty(cls, text: str | None) -> list[ValidationIssue]:
        if not text or not text.strip():
            return [
                ValidationIssue(
                    error_type=ValidationErrorType.EMPTY_RESPONSE,
                    severity=ValidationSeverity.CRITICAL,
                    message="Phản hồi từ AI rỗng hoặc chỉ chứa khoảng trắng.",
                )
            ]
        if len(text.strip().split()) < 10:
            return [
                ValidationIssue(
                    error_type=ValidationErrorType.TOO_SHORT,
                    severity=ValidationSeverity.WARNING,
                    message="Nội dung AI trả về quá ngắn (dưới 10 từ), có thể chưa hoàn chỉnh.",
                )
            ]
        return []

    @classmethod
    def check_forbidden_claims(
        cls,
        text: str,
        forbidden_claims: list[str] | None = None,
    ) -> list[ValidationIssue]:
        issues = []
        default_forbidden = [
            r"100%\s*(hết|khỏi|thành công|cam kết)",
            r"trị dứt điểm",
            r"tốt nhất thế giới",
            r"số 1 việt nam",
            r"chữa khỏi hoàn toàn",
        ]
        all_patterns = default_forbidden.copy()
        if forbidden_claims:
            for claim in forbidden_claims:
                all_patterns.append(re.escape(claim.strip()))

        text_lower = text.lower()
        for pattern in all_patterns:
            if re.search(pattern, text_lower):
                issues.append(
                    ValidationIssue(
                        error_type=ValidationErrorType.FORBIDDEN_CLAIM,
                        severity=ValidationSeverity.WARNING,
                        message=f"Nội dung chứa cụm từ nhạy cảm / cam kết sai chính sách ({pattern}).",
                        context=pattern,
                    )
                )
        return issues

    @classmethod
    def check_platform_constraints(
        cls,
        text: str,
        platform: str | None,
    ) -> list[ValidationIssue]:
        issues = []
        if not platform:
            return issues

        p_lower = platform.strip().lower()

        # 1. Google Ads Checks
        if p_lower == "google_ads":
            # Check headlines lines if structured
            for line in text.splitlines():
                if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "- ")) and len(line.strip()) > 35:
                    if "tiêu đề" in text.lower() or "headline" in text.lower():
                        issues.append(
                            ValidationIssue(
                                error_type=ValidationErrorType.PLATFORM_CONSTRAINT_VIOLATION,
                                severity=ValidationSeverity.INFO,
                                message="Phát hiện tiêu đề Google Ads có thể dài hơn 30 ký tự.",
                                context=line[:40],
                            )
                        )
                        break

        # 2. Email Checks
        elif p_lower == "email":
            if "p.s." not in text.lower() and "tái bút" not in text.lower():
                issues.append(
                    ValidationIssue(
                        error_type=ValidationErrorType.MISSING_REQUIRED_SECTION,
                        severity=ValidationSeverity.INFO,
                        message="Email marketing khuyến nghị nên có dòng P.S. (Tái bút).",
                    )
                )

        # 3. TikTok Checks
        elif p_lower == "tiktok":
            if "hook" not in text.lower() and "giây" not in text.lower() and "cảnh" not in text.lower():
                issues.append(
                    ValidationIssue(
                        error_type=ValidationErrorType.MISSING_REQUIRED_SECTION,
                        severity=ValidationSeverity.INFO,
                        message="Kịch bản TikTok nên có phân cảnh thời gian và hook mở đầu.",
                    )
                )

        return issues
