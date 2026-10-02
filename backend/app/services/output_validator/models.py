from dataclasses import dataclass, field
from enum import Enum


class ValidationErrorType(str, Enum):
    EMPTY_RESPONSE = "empty_response"
    TOO_SHORT = "too_short"
    PLATFORM_CONSTRAINT_VIOLATION = "platform_constraint_violation"
    FORBIDDEN_CLAIM = "forbidden_claim"
    MISSING_REQUIRED_SECTION = "missing_required_section"
    UNGROUNDED_DATA = "ungrounded_data"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    PARSING_ERROR = "parsing_error"


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    error_type: ValidationErrorType
    severity: ValidationSeverity
    message: str
    context: str | None = None


@dataclass
class ValidationResult:
    is_valid: bool
    sanitized_content: str
    issues: list[ValidationIssue] = field(default_factory=list)
    auto_repaired: bool = False

    @property
    def has_critical_error(self) -> bool:
        return any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in self.issues
        )
