import types
import unittest
from unittest.mock import patch

from app.services import ai_service
from app.services.output_validator.models import (
    ValidationErrorType,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class FakeModels:
    def generate_content(self, **kwargs):
        return types.SimpleNamespace(text="generated response")

    def generate_content_stream(self, **kwargs):
        return [types.SimpleNamespace(text="generated "), types.SimpleNamespace(text="response")]


class AiServiceContractTest(unittest.TestCase):
    def valid_result(self, content="generated response", issues=None):
        return ValidationResult(
            is_valid=True,
            sanitized_content=content,
            issues=issues or [],
        )

    def test_non_stream_and_stream_share_validation_and_generation_logging(self):
        validator = self.valid_result(
            issues=[
                ValidationIssue(
                    error_type=ValidationErrorType.FORBIDDEN_CLAIM,
                    severity=ValidationSeverity.WARNING,
                    message="warning only",
                )
            ]
        )
        with patch.object(ai_service, "client", types.SimpleNamespace(models=FakeModels())), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=validator,
        ) as validate, patch.object(
            ai_service.learning_dataset_service,
            "log_generation",
        ) as log_generation:
            normal = ai_service.ask_ai([{"role": "user", "content": "hello"}], prompt_type="facebook")
            streamed = "".join(ai_service.stream_ai([{"role": "user", "content": "hello"}], prompt_type="facebook"))

        self.assertEqual(normal, "generated response")
        self.assertEqual(streamed, "generated response")
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(log_generation.call_count, 2)

    def test_error_validation_rejects_output_and_does_not_log(self):
        invalid = ValidationResult(
            is_valid=False,
            sanitized_content="fallback",
            issues=[
                ValidationIssue(
                    error_type=ValidationErrorType.FORBIDDEN_CLAIM,
                    severity=ValidationSeverity.ERROR,
                    message="blocked",
                )
            ],
        )
        with patch.object(ai_service, "client", types.SimpleNamespace(models=FakeModels())), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=invalid,
        ), patch.object(ai_service.learning_dataset_service, "log_generation") as log_generation:
            with self.assertRaises(RuntimeError):
                ai_service.ask_ai([{"role": "user", "content": "hello"}])
            with self.assertRaises(RuntimeError):
                list(ai_service.stream_ai([{"role": "user", "content": "hello"}]))

        log_generation.assert_not_called()

    def test_reference_data_is_not_put_in_system_instruction(self):
        config = ai_service.create_config(
            prompt_type="other",
            custom_platform_name="Private channel name",
            brand_context="BRAND_REFERENCE_SECRET",
            product_context="PRODUCT_REFERENCE_SECRET",
        )

        self.assertNotIn("Private channel name", config.system_instruction)
        self.assertNotIn("BRAND_REFERENCE_SECRET", config.system_instruction)
        self.assertNotIn("PRODUCT_REFERENCE_SECRET", config.system_instruction)


if __name__ == "__main__":
    unittest.main()