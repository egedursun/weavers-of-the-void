import sqlalchemy as sa
from alembic import op

revision = "a2b4c6d8e0f1"
down_revision = "f9b1d3e5a7c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("addictions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), server_default="[]", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("addictions", schema=None) as batch_op:
        batch_op.drop_column("locked")
