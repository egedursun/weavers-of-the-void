import sqlalchemy as sa
from alembic import op

revision = "5db9e4e79b01"
down_revision = "0fc1044d2f25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("arc_beats", schema=None) as batch_op:
        batch_op.add_column(sa.Column("line_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_arc_beats_line_id"), ["line_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_arc_beats_line_id_chronicle"), "chronicle", ["line_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("arc_beats", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_arc_beats_line_id_chronicle"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_arc_beats_line_id"))
        batch_op.drop_column("line_id")
