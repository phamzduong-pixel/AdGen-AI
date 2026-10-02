from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from app.core.config import settings
from app.database.database import Base
import app.models  # noqa: F401


config = context.config
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Ignore known, safe differences in databases created before Alembic."""

    if not settings.is_sqlite:
        return True

    table_name = getattr(getattr(object_, "table", None), "name", None)
    if (
        type_ == "index"
        and table_name == "saved_contents"
        and name == "ix_saved_contents_id"
    ):
        return False
    if type_ in {"foreign_key_constraint", "unique_constraint"}:
        parent_table = getattr(object_, "table", None)
        if getattr(parent_table, "name", None) == "saved_contents":
            return False
    if type_ == "column" and table_name:
        legacy_nullable_columns = {
            ("uploaded_files", "conversation_id"),
            ("users", "created_at"),
        }
        if (table_name, name) in legacy_nullable_columns:
            return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_object=include_object,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
            render_as_batch=settings.is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
