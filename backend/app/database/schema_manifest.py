"""Canonical application schema used by the read-only schema validator.

This module intentionally does not import SQLAlchemy models.  The manifest is
maintained as an independent description of the schema supported by the
application; the validator compares it with both the live database and the
models separately.
"""

from __future__ import annotations

from typing import Any


_UNSET = object()


def _column(
    type_name: str,
    *,
    nullable: bool = True,
    primary_key: bool = False,
    length: int | None = None,
    default: Any = _UNSET,
    server_default: Any = _UNSET,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "type": type_name,
        "nullable": nullable,
        "primary_key": primary_key,
    }
    if length is not None:
        value["length"] = length
    if default is not _UNSET:
        value["default"] = default
    if server_default is not _UNSET:
        value["server_default"] = server_default
    return value


def _fk(column: str, target: str, on_delete: str | None = None) -> dict[str, Any]:
    value = {"columns": [column], "target": target}
    if on_delete is not None:
        value["on_delete"] = on_delete
    return value


def _unique(name: str | None, columns: list[str]) -> dict[str, Any]:
    return {"name": name, "columns": columns}


def _index(
    name: str,
    columns: list[str],
    *,
    unique: bool = False,
    predicates: dict[str, str] | None = None,
) -> dict[str, Any]:
    value = {"name": name, "columns": columns, "unique": unique}
    if predicates:
        value["predicates"] = predicates
    return value


def _table(
    columns: dict[str, dict[str, Any]],
    *,
    foreign_keys: list[dict[str, Any]] | None = None,
    unique_constraints: list[dict[str, Any]] | None = None,
    indexes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "columns": columns,
        "foreign_keys": foreign_keys or [],
        "unique_constraints": unique_constraints or [],
        "indexes": indexes or [],
        "check_constraints": [],
    }


def _c(**kwargs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return kwargs


CANONICAL_SCHEMA_MANIFEST: dict[str, Any] = {
    "schema_id": "adgen-ai",
    "manifest_version": "2026-10-02.1",
    "supported_dialects": ["sqlite", "postgresql"],
    # Alembic's control table is allowed in a managed database but is not an
    # application table described below.
    "allowed_control_tables": ["alembic_version"],
    "tables": {
        "ad_templates": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer"),
                system_key=_column("string", length=80),
                title=_column("string", nullable=False, length=160),
                description=_column("string", nullable=False, length=500),
                platform=_column("string", nullable=False, length=50),
                platform_name=_column("string", length=80),
                category=_column("string", nullable=False, length=80),
                prompt_template=_column("text", nullable=False),
                default_tone=_column("string", nullable=False, length=100),
                default_length=_column("string", nullable=False, length=50),
                suggested_cta=_column("string", nullable=False, length=300),
                is_system=_column("boolean", nullable=False, default=False, server_default="0"),
                is_popular=_column("boolean", nullable=False, default=False, server_default="0"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[_fk("user_id", "users.id", "CASCADE")],
            unique_constraints=[_unique(None, ["system_key"])],
            indexes=[
                _index("ix_ad_templates_id", ["id"]),
                _index("ix_ad_templates_user_id", ["user_id"]),
                _index("ix_ad_templates_platform", ["platform"]),
                _index("ix_ad_templates_category", ["category"]),
                _index("ix_ad_templates_is_system", ["is_system"]),
            ],
        ),
        "brand_assets": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                brand_id=_column("integer", nullable=False),
                file_name=_column("string", nullable=False, length=255),
                stored_name=_column("string", nullable=False, length=255),
                file_type=_column("string", nullable=False, length=120),
                file_url=_column("string", nullable=False, length=500),
                size=_column("integer", nullable=False),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[_fk("brand_id", "brand_profiles.id", "CASCADE")],
            indexes=[_index("ix_brand_assets_brand_id", ["brand_id"])],
        ),
        "brand_content_checks": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                brand_id=_column("integer", nullable=False),
                user_id=_column("integer", nullable=False),
                score=_column("integer", nullable=False),
                platform=_column("string", length=50),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("brand_id", "brand_profiles.id", "CASCADE"),
                _fk("user_id", "users.id", "CASCADE"),
            ],
            indexes=[
                _index("ix_brand_content_checks_brand_id", ["brand_id"]),
                _index("ix_brand_content_checks_user_id", ["user_id"]),
            ],
        ),
        "brand_profiles": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                name=_column("string", nullable=False, length=160),
                description=_column("text"),
                industry=_column("string", length=160),
                website=_column("string", length=500),
                slogan=_column("string", length=500),
                mission=_column("text"),
                target_audience=_column("text"),
                brand_personality=_column("string", length=500),
                default_tone=_column("string", length=100),
                default_language=_column("string", length=100),
                primary_color=_column("string", length=7),
                secondary_color=_column("string", length=7),
                keywords_json=_column("text", nullable=False, default="[]"),
                forbidden_words_json=_column("text", nullable=False, default="[]"),
                preferred_cta=_column("string", length=500),
                writing_guidelines=_column("text"),
                is_default=_column("boolean", nullable=False, default=False, server_default="0"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                updated_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[_fk("user_id", "users.id", "CASCADE")],
            indexes=[
                _index("ix_brand_profiles_user_id", ["user_id"]),
                _index("ix_brand_profiles_user_name", ["user_id", "name"]),
                _index(
                    "uq_brand_profiles_one_default",
                    ["user_id"],
                    unique=True,
                    predicates={"sqlite": "is_default = 1", "postgresql": "is_default"},
                ),
            ],
        ),
        "campaign_contents": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                campaign_id=_column("integer", nullable=False),
                saved_content_id=_column("integer", nullable=False),
                is_primary=_column("boolean", nullable=False, default=False, server_default="0"),
                added_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("campaign_id", "campaigns.id", "CASCADE"),
                _fk("saved_content_id", "saved_contents.id", "CASCADE"),
            ],
            unique_constraints=[_unique("uq_campaign_saved_content", ["campaign_id", "saved_content_id"])],
            indexes=[
                _index("ix_campaign_contents_campaign_id", ["campaign_id"]),
                _index("ix_campaign_contents_saved_content_id", ["saved_content_id"]),
            ],
        ),
        "campaigns": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                brand_id=_column("integer"),
                name=_column("string", nullable=False, length=160),
                description=_column("text"),
                notes=_column("text"),
                product_name=_column("string", length=200),
                target_audience=_column("text"),
                objective=_column("string", length=500),
                platform=_column("string", length=50),
                platform_name=_column("string", length=80),
                status=_column("string", nullable=False, length=20, default="draft", server_default="draft"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                updated_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("brand_id", "brand_profiles.id", "SET NULL"),
            ],
            indexes=[
                _index("ix_campaigns_id", ["id"]),
                _index("ix_campaigns_user_id", ["user_id"]),
                _index("ix_campaigns_brand_id", ["brand_id"]),
            ],
        ),
        "content_activities": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                saved_content_id=_column("integer"),
                action_type=_column("string", nullable=False, length=30),
                quantity=_column("integer", nullable=False, default=1),
                score=_column("float"),
                platform=_column("string", length=50),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("saved_content_id", "saved_contents.id", "CASCADE"),
            ],
            indexes=[
                _index("ix_content_activities_user_id", ["user_id"]),
                _index("ix_content_activities_saved_content_id", ["saved_content_id"]),
                _index("ix_content_activities_action_type", ["action_type"]),
                _index("ix_content_activities_created_at", ["created_at"]),
            ],
        ),
        "content_documents": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                source_message_id=_column("integer"),
                source_saved_content_id=_column("integer"),
                source_conversation_id=_column("integer"),
                brand_id=_column("integer"),
                campaign_id=_column("integer"),
                title=_column("string", nullable=False, length=160),
                content=_column("text", nullable=False),
                cta=_column("string", length=1000),
                hashtags=_column("text"),
                internal_notes=_column("text"),
                platform=_column("string", length=50),
                platform_name=_column("string", length=80),
                status=_column("string", nullable=False, length=20, default="draft", server_default="draft"),
                current_version=_column("integer", nullable=False, default=1, server_default="1"),
                is_campaign_primary=_column("boolean", nullable=False, default=False, server_default="0"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                updated_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("source_message_id", "messages.id", "SET NULL"),
                _fk("source_saved_content_id", "saved_contents.id", "SET NULL"),
                _fk("source_conversation_id", "conversations.id", "SET NULL"),
                _fk("brand_id", "brand_profiles.id", "SET NULL"),
                _fk("campaign_id", "campaigns.id", "SET NULL"),
            ],
            unique_constraints=[
                _unique("uq_content_documents_user_message", ["user_id", "source_message_id"]),
                _unique("uq_content_documents_user_saved_content", ["user_id", "source_saved_content_id"]),
            ],
            indexes=[
                _index("ix_content_documents_user_id", ["user_id"]),
                _index("ix_content_documents_source_message_id", ["source_message_id"]),
                _index("ix_content_documents_source_saved_content_id", ["source_saved_content_id"]),
                _index("ix_content_documents_source_conversation_id", ["source_conversation_id"]),
                _index("ix_content_documents_brand_id", ["brand_id"]),
                _index("ix_content_documents_campaign_id", ["campaign_id"]),
                _index(
                    "uq_content_documents_campaign_primary",
                    ["campaign_id"],
                    unique=True,
                    predicates={
                        "sqlite": "is_campaign_primary = 1 AND campaign_id IS NOT NULL",
                        "postgresql": "is_campaign_primary AND campaign_id IS NOT NULL",
                    },
                ),
            ],
        ),
        "content_versions": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                content_id=_column("integer", nullable=False),
                version_number=_column("integer", nullable=False),
                title=_column("string", nullable=False, length=160),
                content=_column("text", nullable=False),
                cta=_column("string", length=1000),
                hashtags=_column("text"),
                internal_notes=_column("text"),
                change_summary=_column("string", nullable=False, length=500),
                created_by=_column("string", nullable=False, length=20, default="user", server_default="user"),
                created_by_user_id=_column("integer"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("content_id", "content_documents.id", "CASCADE"),
                _fk("created_by_user_id", "users.id", "SET NULL"),
            ],
            unique_constraints=[_unique("uq_content_versions_number", ["content_id", "version_number"])],
            indexes=[
                _index("ix_content_versions_content_id", ["content_id"]),
                _index("ix_content_versions_created_by_user_id", ["created_by_user_id"]),
            ],
        ),
        "conversations": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                title=_column("string", nullable=False, default="Cuộc trò chuyện mới"),
                user_id=_column("integer", nullable=False),
                brand_id=_column("integer"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                updated_at=_column("datetime", nullable=False, default="utc_now"),
                is_pinned=_column("boolean", nullable=False, default=False, server_default="0"),
                is_title_custom=_column("boolean", nullable=False, default=False, server_default="0"),
                has_generated_title=_column("boolean", nullable=False, default=False, server_default="0"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id"),
                _fk("brand_id", "brand_profiles.id", "SET NULL"),
            ],
            indexes=[_index("ix_conversations_id", ["id"]), _index("ix_conversations_brand_id", ["brand_id"])],
        ),
        "email_verification_tokens": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                code_hash=_column("string", nullable=False, length=64),
                expires_at=_column("datetime", nullable=False),
                used_at=_column("datetime"),
                attempt_count=_column("integer", nullable=False, default=0),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[_fk("user_id", "users.id", "CASCADE")],
            indexes=[
                _index("ix_email_verification_tokens_user_id", ["user_id"]),
                _index("ix_email_verification_user_active", ["user_id", "used_at", "created_at"]),
            ],
        ),
        "voiceover_audios": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                audio_id=_column("string", nullable=False, length=36),
                filename=_column("string", nullable=False, length=255),
                user_id=_column("integer", nullable=False),
                message_id=_column("integer"),
                file_size_bytes=_column("integer", nullable=False, default=0, server_default="0"),
                duration_seconds=_column("float", nullable=False, default=0.0, server_default="0"),
                voice_id=_column("string", nullable=False, length=120),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("message_id", "messages.id", "SET NULL"),
            ],
            unique_constraints=[
                _unique(None, ["audio_id"]),
                _unique(None, ["filename"]),
            ],
            indexes=[
                _index("ix_voiceover_audios_id", ["id"]),
                _index("ix_voiceover_audios_user_id", ["user_id"]),
                _index("ix_voiceover_audios_message_id", ["message_id"]),
            ],
        ),        "media_assets": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                conversation_id=_column("integer", nullable=False),
                parent_asset_id=_column("integer"),
                root_asset_id=_column("integer"),
                source_uploaded_file_id=_column("integer"),
                version_number=_column("integer", nullable=False, default=1),
                kind=_column("string", nullable=False, length=20, default="image"),
                operation=_column("string", nullable=False, length=20, default="generate"),
                status=_column("string", nullable=False, length=20, default="processing"),
                prompt=_column("text", nullable=False),
                aspect_ratio=_column("string", length=10),
                provider=_column("string", length=50),
                model=_column("string", length=100),
                filename=_column("string", length=255),
                filepath=_column("string", length=1000),
                content_type=_column("string", length=100),
                size=_column("integer", nullable=False, default=0),
                error_message=_column("text"),
                operation_params=_column("json"),
                duration_seconds=_column("float"),
                width=_column("integer"),
                height=_column("integer"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("conversation_id", "conversations.id", "CASCADE"),
                _fk("parent_asset_id", "media_assets.id", "SET NULL"),
                _fk("root_asset_id", "media_assets.id", "SET NULL"),
                _fk("source_uploaded_file_id", "uploaded_files.id", "SET NULL"),
            ],
            unique_constraints=[
                _unique(
                    "uq_media_assets_lineage_version",
                    ["user_id", "conversation_id", "kind", "root_asset_id", "version_number"],
                )
            ],
            indexes=[
                _index("ix_media_assets_id", ["id"]),
                _index("ix_media_assets_user_id", ["user_id"]),
                _index("ix_media_assets_conversation_id", ["conversation_id"]),
                _index("ix_media_assets_parent_asset_id", ["parent_asset_id"]),
                _index("ix_media_assets_root_asset_id", ["root_asset_id"]),
            ],
        ),
        "media_edit_requests": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                conversation_id=_column("integer", nullable=False),
                source_asset_id=_column("integer"),
                idempotency_key=_column("string", nullable=False, length=200),
                payload_hash=_column("string", nullable=False, length=64),
                status=_column("string", nullable=False, length=30, default="processing"),
                created_asset_ids=_column("json"),
                failed_operation_index=_column("integer"),
                failed_operation=_column("string", length=50),
                output_asset_id=_column("integer"),
                error_message=_column("text"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                updated_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("conversation_id", "conversations.id", "CASCADE"),
                _fk("source_asset_id", "media_assets.id", "SET NULL"),
                _fk("output_asset_id", "media_assets.id", "SET NULL"),
            ],
            unique_constraints=[
                _unique("uq_media_edit_requests_scope_key", ["user_id", "conversation_id", "idempotency_key"])
            ],
            indexes=[
                _index("ix_media_edit_requests_id", ["id"]),
                _index("ix_media_edit_requests_user_id", ["user_id"]),
                _index("ix_media_edit_requests_conversation_id", ["conversation_id"]),
            ],
        ),
        "media_jobs": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                conversation_id=_column("integer", nullable=False),
                prompt=_column("text", nullable=False),
                aspect_ratio=_column("string", nullable=False, length=10),
                duration_seconds=_column("float"),
                source_asset_ids=_column("json"),
                provider=_column("string", nullable=False, length=50),
                provider_model=_column("string", length=100),
                provider_job_id=_column("string", length=255),
                status=_column("string", nullable=False, length=20, default="queued"),
                error_message=_column("text"),
                output_asset_id=_column("integer"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                updated_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("conversation_id", "conversations.id", "CASCADE"),
                _fk("output_asset_id", "media_assets.id", "SET NULL"),
            ],
            indexes=[
                _index("ix_media_jobs_id", ["id"]),
                _index("ix_media_jobs_user_id", ["user_id"]),
                _index("ix_media_jobs_conversation_id", ["conversation_id"]),
                _index("ix_media_jobs_provider_job_id", ["provider_job_id"]),
            ],
        ),
        "messages": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                conversation_id=_column("integer", nullable=False),
                brand_id=_column("integer"),
                role=_column("string", nullable=False, length=20),
                content=_column("text", nullable=False),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                ad_brief_json=_column("text"),
                prompt_type=_column("string", length=50),
                platform_name=_column("string", length=80),
            ),
            foreign_keys=[
                _fk("conversation_id", "conversations.id"),
                _fk("brand_id", "brand_profiles.id", "SET NULL"),
            ],
            indexes=[_index("ix_messages_id", ["id"]), _index("ix_messages_brand_id", ["brand_id"])],
        ),
        "password_reset_tokens": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                otp_hash=_column("string", nullable=False, length=64),
                reset_token_hash=_column("string", length=64),
                expires_at=_column("datetime", nullable=False),
                reset_token_expires_at=_column("datetime"),
                attempt_count=_column("integer", nullable=False, default=0),
                verified_at=_column("datetime"),
                used_at=_column("datetime"),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[_fk("user_id", "users.id", "CASCADE")],
            unique_constraints=[_unique(None, ["reset_token_hash"])],
            indexes=[
                _index("ix_password_reset_tokens_user_id", ["user_id"]),
                _index("ix_password_reset_user_active", ["user_id", "used_at", "created_at"]),
            ],
        ),
        "saved_contents": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                conversation_id=_column("integer", nullable=False),
                brand_id=_column("integer"),
                message_id=_column("integer"),
                title=_column("string", nullable=False, length=160),
                content=_column("text", nullable=False),
                platform=_column("string", length=50),
                platform_name=_column("string", length=80),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("conversation_id", "conversations.id", "CASCADE"),
                _fk("brand_id", "brand_profiles.id", "SET NULL"),
                _fk("message_id", "messages.id", "CASCADE"),
            ],
            unique_constraints=[_unique("uq_saved_contents_user_message", ["user_id", "message_id"])],
            indexes=[
                _index("ix_saved_contents_id", ["id"]),
                _index("ix_saved_contents_user_id", ["user_id"]),
                _index("ix_saved_contents_conversation_id", ["conversation_id"]),
                _index("ix_saved_contents_brand_id", ["brand_id"]),
                _index("ix_saved_contents_message_id", ["message_id"]),
            ],
        ),
        "template_favorites": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                template_id=_column("integer", nullable=False),
                created_at=_column("datetime", nullable=False, default="utc_now"),
            ),
            foreign_keys=[
                _fk("user_id", "users.id", "CASCADE"),
                _fk("template_id", "ad_templates.id", "CASCADE"),
            ],
            unique_constraints=[_unique("uq_template_favorite_user_template", ["user_id", "template_id"])],
            indexes=[
                _index("ix_template_favorites_user_id", ["user_id"]),
                _index("ix_template_favorites_template_id", ["template_id"]),
            ],
        ),
        "uploaded_files": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                filename=_column("string", nullable=False),
                filepath=_column("string", nullable=False),
                content_type=_column("string", nullable=False, default="application/octet-stream"),
                size=_column("integer", nullable=False, default=0),
                conversation_id=_column("integer", nullable=False),
                message_id=_column("integer"),
            ),
            foreign_keys=[
                _fk("conversation_id", "conversations.id"),
                _fk("message_id", "messages.id"),
            ],
            indexes=[_index("ix_uploaded_files_id", ["id"])],
        ),
        "user_sessions": _table(
            _c(
                id=_column("string", nullable=False, primary_key=True, length=36),
                user_id=_column("integer", nullable=False),
                device_name=_column("string", nullable=False, length=100, default="Thiết bị không xác định"),
                browser=_column("string", nullable=False, length=80, default="Trình duyệt không xác định"),
                ip_address=_column("string", length=64),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                last_active_at=_column("datetime", nullable=False, default="utc_now"),
                expires_at=_column("datetime", nullable=False),
                revoked_at=_column("datetime"),
            ),
            foreign_keys=[_fk("user_id", "users.id", "CASCADE")],
            indexes=[
                _index("ix_user_sessions_user_id", ["user_id"]),
                _index("ix_user_sessions_user_revoked", ["user_id", "revoked_at"]),
            ],
        ),
        "user_settings": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                user_id=_column("integer", nullable=False),
                default_platform=_column("string", nullable=False, length=50, default="facebook"),
                default_platform_name=_column("string", length=80),
                default_tone=_column("string", nullable=False, length=100, default="professional"),
                default_language=_column("string", nullable=False, length=50, default="vi"),
                default_length=_column("string", nullable=False, length=30, default="medium"),
                default_export_format=_column("string", nullable=False, length=20, default="markdown"),
                include_timestamps=_column("boolean", nullable=False, default=True),
            ),
            foreign_keys=[_fk("user_id", "users.id", "CASCADE")],
            indexes=[_index("ix_user_settings_user_id", ["user_id"], unique=True)],
        ),
        "users": _table(
            _c(
                id=_column("integer", nullable=False, primary_key=True),
                username=_column("string", nullable=False),
                email=_column("string", nullable=False),
                hashed_password=_column("string", nullable=False),
                created_at=_column("datetime", nullable=False, default="utc_now"),
                token_version=_column("integer", nullable=False, default=0),
                auth_provider=_column("string", nullable=False, length=20, default="local"),
                google_sub=_column("string", length=255),
                avatar_url=_column("string", length=500),
                email_verified=_column("boolean", nullable=False, default=False),
            ),
            unique_constraints=[
                _unique(None, ["username"]),
                _unique(None, ["email"]),
            ],
            indexes=[
                _index("ix_users_id", ["id"]),
                _index("ix_users_google_sub", ["google_sub"], unique=True),
            ],
        ),
    },
}
