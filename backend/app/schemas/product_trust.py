from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


SourcePolicyDecision = Literal["trusted", "excluded"]
TrustEvaluationMode = Literal["all_evidence", "verified_only"]


class SourcePolicyUpsert(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    decision: SourcePolicyDecision
    note: str | None = Field(default=None, max_length=2_000)

    @field_validator("host")
    @classmethod
    def normalize_host(cls, value: str) -> str:
        return value.strip().lower().rstrip(".")

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SourcePolicyResponse(BaseModel):
    host: str
    decision: SourcePolicyDecision
    note: str | None
    created_at: datetime
    updated_at: datetime


class ProductTrustClaimResponse(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str
    status: str
    evidence_ids: list[str]
    risk_level: str
    recommended_action: str
    rationale: str


class ProductTrustSummaryResponse(BaseModel):
    report_id: str
    mode: TrustEvaluationMode
    evaluated_at: datetime
    can_use_for_generation: bool
    requires_review: bool
    blocking_claim_ids: list[str]
    excluded_evidence_ids: list[str]
    trusted_source_hosts: list[str]
    claim_counts: dict[str, int]
    claims: list[ProductTrustClaimResponse]
    caveats: list[str]
