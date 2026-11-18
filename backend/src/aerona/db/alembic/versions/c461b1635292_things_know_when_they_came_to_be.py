import sqlalchemy as sa
from alembic import op

revision = "c461b1635292"
down_revision = "5db9e4e79b01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "node_births",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("day", sa.Integer(), nullable=True),
        sa.Column("hour", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_node_births_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_node_births")),
    )


def downgrade() -> None:
    op.drop_table("node_births")
