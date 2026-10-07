from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


ReportClaimType = Literal[
    "evidence_backed",
    "product_fact",
    "ai_inference",
    "insufficient_evidence",
]


class TrendReportEvidenceCreate(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=500)
    source_url: AnyHttpUrl
    publisher: str = Field(min_length=1, max_length=300)
    retrieved_at: datetime
    published_at: datetime | None = None
    excerpt: str = Field(min_length=1, max_length=20_000)
    source_type: str = Field(min_length=1, max_length=80)
    status: str = Field(default="unverified", min_length=1, max_length=40)
    confidence: float | None = Field(default=None, ge=0, le=1)
    content_hash: str | None = Field(default=None, max_length=128)
    metadata: dict = Field(default_factory=dict)

    @field_validator("evidence_id", "title", "publisher", "excerpt", "source_type", "status")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split()) if value != value.strip() else value


class TrendReportClaimCreate(BaseModel):
    claim_id: str = Field(min_length=1, max_length=160)
    claim_text: str = Field(min_length=1, max_length=20_000)
    claim_type: ReportClaimType
    evidence_ids: list[str] = Field(default_factory=list)
    caveat: str | None = Field(default=None, max_length=5_000)

    @model_validator(mode="after")
    def require_explicit_support(self):
        if self.claim_type in {"evidence_backed", "product_fact"} and not self.evidence_ids:
            raise ValueError(
                "Evidence-backed/product-fact claim pháº£i tham chiáº¿u evidence_ids rÃµ rÃ ng"
            )
        if self.claim_type in {"ai_inference", "insufficient_evidence"} and self.evidence_ids:
            raise ValueError(
                "AI inference/insufficient evidence claim khÃ´ng Ä‘Æ°á»£c gáº¯n evidence nhÆ° factual support"
            )
        return self


class TrendReportCreate(BaseModel):
    request_id: str | None = Field(default=None, max_length=160)
    query: str = Field(min_length=1, max_length=20_000)
    summary: str | None = Field(default=None, max_length=50_000)
    summary_claim_ids: list[str] = Field(default_factory=list)
    conversation_id: int | None = Field(default=None, gt=0)
    source_message_id: int | None = Field(default=None, gt=0)
    generated_at: datetime | None = None
    retrieved_at: datetime | None = None
    provider_status: str = Field(default="success", min_length=1, max_length=40)
    caveat: str | None = Field(default=None, max_length=10_000)
    source_statuses: list[dict] = Field(default_factory=list)
    evidences: list[TrendReportEvidenceCreate] = Field(default_factory=list)
    claims: list[TrendReportClaimCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_explicit_summary_claim_contract(self):
        if self.summary and not self.summary_claim_ids:
            raise ValueError(
                "summary requires explicit summary_claim_ids; factual claims must be declared"
            )
        if not self.summary and self.summary_claim_ids:
            raise ValueError("summary_claim_ids requires a summary")
        claim_ids = [claim.claim_id for claim in self.claims]
        if self.summary and set(self.summary_claim_ids) != set(claim_ids):
            raise ValueError(
                "summary_claim_ids must declare every structured claim in the summary contract"
            )
        if len(self.summary_claim_ids) != len(set(self.summary_claim_ids)):
            raise ValueError("summary_claim_ids must not contain duplicates")
        return self


class TrendReportRetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    request_id: str | None = Field(default=None, max_length=160)
    conversation_id: int | None = Field(default=None, gt=0)
    source_message_id: int | None = Field(default=None, gt=0)
    refresh: bool = False
    max_age_days: int = Field(default=30, ge=0, le=3_650)


class TrendReportEvidenceResponse(BaseModel):
    evidence_id: str
    citation_id: str
    title: str
    source_url: str
    publisher: str
    retrieved_at: datetime
    published_at: datetime | None
    excerpt: str
    source_type: str
    status: str
    confidence: float | None
    content_hash: str | None
    metadata: dict
    model_config = {"from_attributes": True}


class TrendReportClaimResponse(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: ReportClaimType
    caveat: str | None
    evidence: list[TrendReportEvidenceResponse]


class TrendReportResponse(BaseModel):
    product_trust: dict | None = None
    report_id: str
    request_id: str
    user_id: int
    conversation_id: int | None
    source_message_id: int | None
    query: str
    summary: str | None
    summary_claim_ids: list[str]
    generated_at: datetime
    retrieved_at: datetime
    provider_status: str
    caveat: str | None
    source_statuses: list[dict]
    evidences: list[TrendReportEvidenceResponse]
    claims: list[TrendReportClaimResponse]


class TrendReportListResponse(BaseModel):
    reports: list[TrendReportResponse]
