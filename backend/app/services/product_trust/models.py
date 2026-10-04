"""Small, in-memory contracts for product claim assessment."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ProductClaimType(str, Enum):
    DESCRIPTION = "description"
    FEATURE = "feature"
    BENEFIT = "benefit"
    USP = "usp"
    PRICE = "price"
    OFFER = "offer"
    WARRANTY = "warranty"
    TECHNICAL_SPEC = "technical_spec"


class ClaimOrigin(str, Enum):
    USER_PROVIDED = "user_provided"
    EXTERNAL_EVIDENCE = "external_evidence"
    AI_INFERENCE = "ai_inference"


class ClaimAssessmentStatus(str, Enum):
    EVIDENCE_SUPPORTED = "evidence_supported"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ClaimRiskLevel(str, Enum):
    NORMAL = "normal"
    HIGH = "high"


class RecommendedAction(str, Enum):
    ALLOW = "allow"
    SOFTEN = "soften"
    ASK_USER = "ask_user"
    BLOCK = "block"


@dataclass(frozen=True)
class ProductClaim:
    claim_id: str
    claim_text: str
    claim_type: ProductClaimType | str
    origin: ClaimOrigin | str
    product_field: str

    def __post_init__(self) -> None:
        for field_name in ("claim_id", "claim_text", "product_field"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True)
class ClaimAssessment:
    claim_id: str
    status: ClaimAssessmentStatus | str
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""
    risk_level: ClaimRiskLevel | str = ClaimRiskLevel.NORMAL
    recommended_action: RecommendedAction | str = RecommendedAction.SOFTEN
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not isinstance(self.claim_id, str) or not self.claim_id.strip():
            raise ValueError("claim_id must be a non-empty string")
        if self.assessed_at.tzinfo is None or self.assessed_at.utcoffset() is None:
            raise ValueError("assessed_at must be timezone-aware")
