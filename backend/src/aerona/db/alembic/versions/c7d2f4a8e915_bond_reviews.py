import sqlalchemy as sa
from alembic import op

revision = "c7d2f4a8e915"
down_revision = "b3c1e7a9d204"
branch_labels = None
depends_on = None

TABLE = "bond_reviews"


def upgrade() -> None:
    if TABLE in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        TABLE,
        sa.Column("bond_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["bond_id"], ["bonds.id"], name=op.f("fk_bond_reviews_bond_id_bonds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("bond_id", name=op.f("pk_bond_reviews")),
    )


def downgrade() -> None:
    op.drop_table(TABLE)
