import unittest

from app.services.output_validator.models import (
    ValidationErrorType,
    ValidationSeverity,
)
from app.services.output_validator.rules import OutputValidationRules
from app.services.output_validator.service import (
    OutputValidationService,
    output_validation_service,
)


class OutputValidatorTest(unittest.TestCase):
    def test_empty_response_handling_and_fallback(self):
        res = output_validation_service.validate_and_sanitize(
            raw_text="",
            platform="facebook",
        )
        self.assertFalse(res.is_valid)
        self.assertTrue(res.auto_repaired)
        self.assertIn("NỘI DUNG CHƯA ĐỦ", res.sanitized_content)

    def test_forbidden_claims_detection(self):
        raw = "Sản phẩm này cam kết trị dứt điểm mụn 100% thành công sau 3 ngày dùng!"
        issues = OutputValidationRules.check_forbidden_claims(
            text=raw,
            forbidden_claims=["cam kết trị dứt điểm"],
        )
        self.assertTrue(len(issues) > 0)
        self.assertEqual(issues[0].error_type, ValidationErrorType.FORBIDDEN_CLAIM)

    def test_auto_repair_markdown_blocks(self):
        raw_broken = "### Tiêu đề\n```python\nprint('Hello world')"
        res = output_validation_service.validate_and_sanitize(raw_broken)
        self.assertTrue(res.sanitized_content.endswith("```"))
        self.assertTrue(res.auto_repaired)

    def test_resilient_fallback_on_api_error(self):
        fallback = output_validation_service.generate_fallback_response(
            error_type=ValidationErrorType.API_ERROR,
            platform="google_ads",
        )
        self.assertIn("THÔNG BÁO HỆ THỐNG", fallback)
        self.assertIn("GOOGLE_ADS", fallback)
        self.assertIn("Thử lại", fallback)


if __name__ == "__main__":
    unittest.main()
