from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


class TrendReport(Base):
    __tablename__ = "trend_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "report_key", name="uq_trend_reports_user_key"),
        Index("ix_trend_reports_user_source_message", "user_id", "source_message_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_id: Mapped[str] = mapped_column(String(160), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    provider_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="not_requested"
    )
    caveat: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_trust_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    source_statuses_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # History cleanup must retain evidence provenance and all downstream insight
    # artifacts, so reports are hidden rather than physically deleted.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    evidences = relationship(
        "TrendReportEvidence",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="TrendReportEvidence.citation_id",
    )
    claims = relationship(
        "TrendReportClaim",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="TrendReportClaim.id",
    )


class TrendReportEvidence(Base):
    __tablename__ = "trend_report_evidence"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "citation_id", name="uq_trend_report_evidence_citation"
        ),
        UniqueConstraint(
            "report_id", "evidence_id", name="uq_trend_report_evidence_id"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("trend_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(String(160), nullable=False)
    citation_id: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    publisher: Mapped[str] = mapped_column(String(300), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    report = relationship("TrendReport", back_populates="evidences")
    claim_links = relationship(
        "TrendReportClaimEvidence",
        back_populates="evidence",
        cascade="all, delete-orphan",
    )


class TrendReportClaim(Base):
    __tablename__ = "trend_report_claims"
    __table_args__ = (
        UniqueConstraint("report_id", "claim_key", name="uq_trend_report_claim_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("trend_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_key: Mapped[str] = mapped_column(String(160), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(40), nullable=False)
    caveat: Mapped[str | None] = mapped_column(Text, nullable=True)

    report = relationship("TrendReport", back_populates="claims")
    evidence_links = relationship(
        "TrendReportClaimEvidence",
        back_populates="claim",
        cascade="all, delete-orphan",
    )


class TrendReportClaimEvidence(Base):
    __tablename__ = "trend_report_claim_evidence"
    __table_args__ = (
        UniqueConstraint(
            "claim_id", "evidence_id", name="uq_trend_report_claim_evidence"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("trend_report_claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("trend_report_evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )

    claim = relationship("TrendReportClaim", back_populates="evidence_links")
    evidence = relationship("TrendReportEvidence", back_populates="claim_links")
