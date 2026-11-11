import sqlalchemy as sa
from alembic import op

revision = "3b8e51c7d2a4"
down_revision = "6f1e2c30010d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM norm_changes WHERE before = after"))
    with op.batch_alter_table("norm_changes", schema=None) as batch_op:
        batch_op.create_check_constraint("a_change", "before IS NULL OR before <> after")


def downgrade() -> None:
    with op.batch_alter_table("norm_changes", schema=None) as batch_op:
        batch_op.drop_constraint("a_change", type_="check")
