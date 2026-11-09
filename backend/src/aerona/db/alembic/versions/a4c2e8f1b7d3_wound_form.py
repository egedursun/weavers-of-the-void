import sqlalchemy as sa
from alembic import op

revision = "a4c2e8f1b7d3"
down_revision = "de91a61293c4"
branch_labels = None
depends_on = None

MODES = ("concrete", "semi_concrete", "conceptual", "reflection", "scattered")


def upgrade() -> None:
    with op.batch_alter_table("divine_wounds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("prior_mode", sa.Enum(*MODES, name="prior_mode", native_enum=False, create_constraint=True, length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("divine_wounds", schema=None) as batch_op:
        batch_op.drop_column("prior_mode")
