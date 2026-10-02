"""Store custom platform names on campaigns."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260727_0011"
down_revision: Union[str, None] = "20260727_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.add_column(sa.Column("platform_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.drop_column("platform_name")