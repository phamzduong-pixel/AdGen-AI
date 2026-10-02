"""Add optional custom name for the default platform."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260727_0010"
down_revision: Union[str, None] = "20260727_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("default_platform_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.drop_column("default_platform_name")