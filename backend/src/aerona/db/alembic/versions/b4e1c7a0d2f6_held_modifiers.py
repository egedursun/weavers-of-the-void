import sqlalchemy as sa
from alembic import op

revision = "b4e1c7a0d2f6"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("modifiers") as batch_op:
        batch_op.add_column(sa.Column("held", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("modifiers") as batch_op:
        batch_op.drop_column("held")
