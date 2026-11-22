import sqlalchemy as sa
from alembic import op

revision = "9c9860da5822"
down_revision = "3a2b122e454a"
branch_labels = None
depends_on = None

CYCLES = ("carbon", "water", "nutrients")


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    op.rename_table("world_cycles", "world_cycles_columns")
    op.create_table(
        "world_cycles",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("cycle", enum_of("cycle", CYCLES), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("inflow", sa.Integer(), nullable=False),
        sa.Column("outflow", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("stock BETWEEN 0 AND 100", name=op.f("ck_world_cycles_stock_range")),
        sa.CheckConstraint("inflow >= 0", name=op.f("ck_world_cycles_inflow_min")),
        sa.CheckConstraint("outflow >= 0", name=op.f("ck_world_cycles_outflow_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_world_cycles_updated_epoch_min")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_cycles_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", "cycle", name=op.f("pk_world_cycles")),
    )
    for cycle in CYCLES:
        op.execute(
            f"INSERT INTO world_cycles (world_id, cycle, stock, inflow, outflow, updated_epoch, locked) "
            f"SELECT world_id, '{cycle}', {cycle}, MAX({cycle}_in, 0), MAX({cycle}_out, 0), MAX(updated_epoch, 0), "
            f"CASE WHEN EXISTS (SELECT 1 FROM json_each(world_cycles_columns.locked) WHERE value = '{cycle}') THEN '[\"stock\"]' ELSE '[]' END "
            f"FROM world_cycles_columns"
        )
    op.drop_table("world_cycles_columns")


def downgrade() -> None:
    op.rename_table("world_cycles", "world_cycles_rows")
    op.create_table(
        "world_cycles",
        sa.Column("world_id", sa.Integer(), nullable=False),
        *(sa.Column(cycle, sa.Integer(), nullable=False, server_default="50") for cycle in CYCLES),
        *(sa.Column(f"{cycle}_{side}", sa.Integer(), nullable=False, server_default="0") for cycle in CYCLES for side in ("in", "out")),
        sa.Column("updated_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"),
        *(sa.CheckConstraint(f"{cycle} BETWEEN 0 AND 100", name=op.f(f"ck_world_cycles_{cycle}_range")) for cycle in CYCLES),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_cycles_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_cycles")),
    )
    op.execute("INSERT INTO world_cycles (world_id) SELECT DISTINCT world_id FROM world_cycles_rows")
    for cycle in CYCLES:
        op.execute(
            f"UPDATE world_cycles SET ({cycle}, {cycle}_in, {cycle}_out) = "
            f"(SELECT stock, inflow, outflow FROM world_cycles_rows WHERE world_cycles_rows.world_id = world_cycles.world_id AND cycle = '{cycle}') "
            f"WHERE EXISTS (SELECT 1 FROM world_cycles_rows WHERE world_cycles_rows.world_id = world_cycles.world_id AND cycle = '{cycle}')"
        )
    op.drop_table("world_cycles_rows")
