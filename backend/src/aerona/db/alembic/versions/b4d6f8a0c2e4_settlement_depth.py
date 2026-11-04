import sqlalchemy as sa
from alembic import op

revision = "b4d6f8a0c2e4"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None

DISTRICT_KINDS = (
    "farmland",
    "market",
    "craft_quarter",
    "temple_quarter",
    "harbour",
    "citadel",
    "slums",
    "palace",
    "foreign_quarter",
    "necropolis",
)
DESIGN_PARAMETERS = (
    "housing",
    "food_store",
    "goods_store",
    "harbour",
    "order",
    "sanitation",
    "piety_floor",
    "admin_pct",
    "policing",
    "investment_pct",
    "tension_relief_pct",
)


def upgrade() -> None:
    op.create_table(
        "district_designs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_kind", sa.Enum(*DISTRICT_KINDS, name="base_kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        *(sa.Column(column, sa.Integer(), nullable=True) for column in DESIGN_PARAMETERS),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("created_by_son_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_son_id"], ["sons.id"], name=op.f("fk_district_designs_created_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_district_designs_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_district_designs")),
    )
    with op.batch_alter_table("district_designs", schema=None) as batch_op:
        batch_op.create_index("ix_district_designs_world", ["world_id"], unique=False)
    with op.batch_alter_table("settlement_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("admin_capacity", sa.Integer(), server_default=sa.text("50"), nullable=False))
        batch_op.create_check_constraint(op.f("ck_settlement_profiles_admin_capacity_range"), "admin_capacity BETWEEN 0 AND 300")
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
        batch_op.add_column(sa.Column("design_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_districts_design_id_district_designs"), "district_designs", ["design_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_districts_design_id_district_designs"), type_="foreignkey")
        batch_op.drop_column("design_id")
        batch_op.drop_column("locked")
    with op.batch_alter_table("settlement_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_settlement_profiles_admin_capacity_range"), type_="check")
        batch_op.drop_column("admin_capacity")
    with op.batch_alter_table("district_designs", schema=None) as batch_op:
        batch_op.drop_index("ix_district_designs_world")
    op.drop_table("district_designs")
