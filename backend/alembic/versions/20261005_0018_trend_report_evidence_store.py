"""Add Stage 1 Trend Radar report and evidence snapshots."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261005_0018"
down_revision: str | None = "20261003_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trend_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("provider_status", sa.String(length=40), nullable=False),
        sa.Column("caveat", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "report_key", name="uq_trend_reports_user_key"),
    )
    op.create_index("ix_trend_reports_report_key", "trend_reports", ["report_key"])
    op.create_index("ix_trend_reports_user_id", "trend_reports", ["user_id"])
    op.create_index("ix_trend_reports_conversation_id", "trend_reports", ["conversation_id"])
    op.create_index("ix_trend_reports_source_message_id", "trend_reports", ["source_message_id"])
    op.create_index(
        "ix_trend_reports_user_source_message",
        "trend_reports",
        ["user_id", "source_message_id"],
    )

    op.create_table(
        "trend_report_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.String(length=160), nullable=False),
        sa.Column("citation_id", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("publisher", sa.String(length=300), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("verification_status", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["report_id"], ["trend_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "citation_id", name="uq_trend_report_evidence_citation"),
        sa.UniqueConstraint("report_id", "evidence_id", name="uq_trend_report_evidence_id"),
    )
    op.create_index("ix_trend_report_evidence_report_id", "trend_report_evidence", ["report_id"])

    op.create_table(
        "trend_report_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("claim_key", sa.String(length=160), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=40), nullable=False),
        sa.Column("caveat", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["trend_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "claim_key", name="uq_trend_report_claim_key"),
    )
    op.create_index("ix_trend_report_claims_report_id", "trend_report_claims", ["report_id"])

    op.create_table(
        "trend_report_claim_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["trend_report_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["trend_report_evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", "evidence_id", name="uq_trend_report_claim_evidence"),
    )
    op.create_index("ix_trend_report_claim_evidence_claim_id", "trend_report_claim_evidence", ["claim_id"])
    op.create_index("ix_trend_report_claim_evidence_evidence_id", "trend_report_claim_evidence", ["evidence_id"])

    with op.batch_alter_table("saved_contents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trend_report_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_saved_contents_trend_report_id",
            "trend_reports",
            ["trend_report_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_saved_contents_trend_report_id", "saved_contents", ["trend_report_id"])

    with op.batch_alter_table("content_documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trend_report_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_content_documents_trend_report_id",
            "trend_reports",
            ["trend_report_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_content_documents_trend_report_id", "content_documents", ["trend_report_id"])
    op.create_index(
        "uq_content_documents_user_trend_report",
        "content_documents",
        ["user_id", "trend_report_id"],
        unique=True,
    )

    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trend_report_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_campaigns_trend_report_id",
            "trend_reports",
            ["trend_report_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_campaigns_trend_report_id", "campaigns", ["trend_report_id"])


def downgrade() -> None:
    op.drop_index("ix_campaigns_trend_report_id", table_name="campaigns")
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.drop_constraint("fk_campaigns_trend_report_id", type_="foreignkey")
        batch_op.drop_column("trend_report_id")

    op.drop_index("uq_content_documents_user_trend_report", table_name="content_documents")
    op.drop_index("ix_content_documents_trend_report_id", table_name="content_documents")
    with op.batch_alter_table("content_documents", schema=None) as batch_op:
        batch_op.drop_constraint("fk_content_documents_trend_report_id", type_="foreignkey")
        batch_op.drop_column("trend_report_id")

    op.drop_index("ix_saved_contents_trend_report_id", table_name="saved_contents")
    with op.batch_alter_table("saved_contents", schema=None) as batch_op:
        batch_op.drop_constraint("fk_saved_contents_trend_report_id", type_="foreignkey")
        batch_op.drop_column("trend_report_id")

    op.drop_index("ix_trend_report_claim_evidence_evidence_id", table_name="trend_report_claim_evidence")
    op.drop_index("ix_trend_report_claim_evidence_claim_id", table_name="trend_report_claim_evidence")
    op.drop_table("trend_report_claim_evidence")

    op.drop_index("ix_trend_report_claims_report_id", table_name="trend_report_claims")
    op.drop_table("trend_report_claims")

    op.drop_index("ix_trend_report_evidence_report_id", table_name="trend_report_evidence")
    op.drop_table("trend_report_evidence")

    op.drop_index("ix_trend_reports_user_source_message", table_name="trend_reports")
    op.drop_index("ix_trend_reports_source_message_id", table_name="trend_reports")
    op.drop_index("ix_trend_reports_conversation_id", table_name="trend_reports")
    op.drop_index("ix_trend_reports_user_id", table_name="trend_reports")
    op.drop_index("ix_trend_reports_report_key", table_name="trend_reports")
    op.drop_table("trend_reports")
