import sqlalchemy as sa
from alembic import op

revision = "3c7d9e21b4a6"
down_revision = "ea5f12047d6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dominions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trend", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("dominions", schema=None) as batch_op:
        batch_op.drop_column("trend")
