import sqlalchemy as sa
from alembic import op

revision = "c29aa6af1502"
down_revision = "7d41c2b9e0a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ley_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_a_id", sa.Integer(), nullable=False),
        sa.Column("region_b_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("severed", sa.Boolean(), nullable=False),
        sa.Column("severed_until_epoch", sa.Integer(), nullable=True),
        sa.Column("severed_by_son_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("region_a_id < region_b_id", name=op.f("ck_ley_lines_ordered_pair")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_ley_lines_strength_range")),
        sa.ForeignKeyConstraint(["region_a_id"], ["entities.id"], name=op.f("fk_ley_lines_region_a_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_b_id"], ["entities.id"], name=op.f("fk_ley_lines_region_b_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["severed_by_son_id"], ["sons.id"], name=op.f("fk_ley_lines_severed_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_ley_lines_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ley_lines")),
        sa.UniqueConstraint("region_a_id", "region_b_id", name="one_line_per_pair"),
    )
    with op.batch_alter_table("ley_lines", schema=None) as batch_op:
        batch_op.create_index("ix_ley_lines_world", ["world_id"], unique=False)

    with op.batch_alter_table("place_environment", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nexus", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("place_environment", schema=None) as batch_op:
        batch_op.drop_column("nexus")

    with op.batch_alter_table("ley_lines", schema=None) as batch_op:
        batch_op.drop_index("ix_ley_lines_world")

    op.drop_table("ley_lines")
