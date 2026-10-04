"""Provider-neutral contracts for optional external retrieval."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from app.services.external_retrieval.evidence import Evidence


class SearchProviderStatus(str, Enum):
    SUCCESS = "success"
    EMPTY = "empty"
    NOT_CONFIGURED = "not_configured"
    INVALID_REQUEST = "invalid_request"
    AUTHENTICATION_ERROR = "authentication_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    HTTP_ERROR = "http_error"
    INVALID_RESPONSE = "invalid_response"


@dataclass(frozen=True)
class SearchProviderResult:
    """Safe, provider-neutral result returned before AI integration exists."""

    status: SearchProviderStatus
    evidences: tuple[Evidence, ...] = ()
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return self.status not in {SearchProviderStatus.SUCCESS, SearchProviderStatus.EMPTY}


class SearchProvider(Protocol):
    """Minimal adapter interface; providers do not decide retrieval intent."""

    def search(self, query: str, *, limit: int | None = None) -> SearchProviderResult:
        """Return normalized Evidence or a safe provider status."""

