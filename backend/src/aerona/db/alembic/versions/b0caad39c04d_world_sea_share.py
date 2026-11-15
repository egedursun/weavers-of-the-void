import sqlalchemy as sa
from alembic import op

revision = "b0caad39c04d"
down_revision = "39ded63f7c3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("world_type_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sea_pct", sa.Integer(), nullable=False, server_default="25"))
        batch_op.create_check_constraint(op.f("ck_world_type_profiles_sea_pct_range"), "sea_pct BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("world_type_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_world_type_profiles_sea_pct_range"), type_="check")
        batch_op.drop_column("sea_pct")
