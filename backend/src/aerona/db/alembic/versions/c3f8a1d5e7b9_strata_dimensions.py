import sqlalchemy as sa
from alembic import op

revision = "c3f8a1d5e7b9"
down_revision = "b7d41c9e2a15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.add_column(sa.Column("dimension_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_afterlife_strata_dimension_id"), ["dimension_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_afterlife_strata_dimension_id_dimensions"), "dimensions", ["dimension_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_afterlife_strata_dimension_id_dimensions"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_afterlife_strata_dimension_id"))
        batch_op.drop_column("dimension_id")
