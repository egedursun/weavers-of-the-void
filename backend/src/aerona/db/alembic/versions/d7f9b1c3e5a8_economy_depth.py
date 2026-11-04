import sqlalchemy as sa
from alembic import op

revision = "d7f9b1c3e5a8"
down_revision = "b9d1f3a5c7e2"
branch_labels = None
depends_on = None

OLD_ORIGINS = ("catalog", "god_remains", "dead_star", "beast", "leak_crystal", "research")
NEW_ORIGINS = (*OLD_ORIGINS, "divine")
OLD_TREASURY_ENTRIES = ("tax", "tolls", "investment", "garrison", "walls", "building", "festival", "alms", "fire", "plunder", "grant")
NEW_TREASURY_ENTRIES = (*OLD_TREASURY_ENTRIES, "loan")
WIDENED = (
    ("world_materials", "origin", OLD_ORIGINS, NEW_ORIGINS, False),
    ("polity_treasury", "entry", OLD_TREASURY_ENTRIES, NEW_TREASURY_ENTRIES, False),
    ("settlement_treasury", "entry", OLD_TREASURY_ENTRIES, NEW_TREASURY_ENTRIES, False),
)
NAME_LENGTH = 200
WORKSHOP_KINDS = (
    "market",
    "granary",
    "warehouse",
    "mine",
    "lumber_camp",
    "fishery",
    "charcoal_kiln",
    "forge",
    "tannery",
    "mill",
    "brewery",
    "weavery",
    "stable",
    "mason_yard",
    "shipyard",
    "siege_yard",
    "alchemist",
    "shrine_workshop",
    "mint",
)
HELD_TABLES = ("world_materials", "node_materials", "community_stocks", "workshops", "resource_profiles", "resource_workers", "currencies", "loans")
COMMODITIES = (
    "grain",
    "livestock",
    "fish",
    "fodder",
    "timber",
    "fuel",
    "bread",
    "ore",
    "stone",
    "cloth",
    "tools",
    "weapons",
    "armour",
    "mounts",
    "siege_materiel",
    "medicine",
    "luxuries",
    "incense",
    "sacred_goods",
    "magical_reagents",
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    for table in HELD_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("held", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.drop_column("material")
    op.create_table(
        "workshop_designs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("base_kind", enum_of("base_kind", WORKSHOP_KINDS), nullable=False),
        sa.Column("name", sa.String(length=NAME_LENGTH), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("output_pct", sa.Integer(), nullable=False),
        sa.Column("capacity_pct", sa.Integer(), nullable=False),
        sa.Column("store_pct", sa.Integer(), nullable=False),
        sa.Column("quality_bonus", sa.Integer(), nullable=False),
        sa.Column("held", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("output_pct BETWEEN 0 AND 500", name=op.f("ck_workshop_designs_output_pct_range")),
        sa.CheckConstraint("capacity_pct BETWEEN 0 AND 500", name=op.f("ck_workshop_designs_capacity_pct_range")),
        sa.CheckConstraint("store_pct BETWEEN 0 AND 500", name=op.f("ck_workshop_designs_store_pct_range")),
        sa.CheckConstraint("quality_bonus BETWEEN 0 AND 100", name=op.f("ck_workshop_designs_quality_bonus_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_workshop_designs_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workshop_designs")),
    )
    with op.batch_alter_table("workshop_designs", schema=None) as batch_op:
        batch_op.create_index("ix_workshop_designs_world", ["world_id"], unique=False)
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.add_column(sa.Column("design_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_workshops_design_id_workshop_designs"), "workshop_designs", ["design_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "market_price_holds",
        sa.Column("market_entity_id", sa.Integer(), nullable=False),
        sa.Column("commodity", enum_of("commodity", COMMODITIES), nullable=False),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("supply", sa.Integer(), nullable=True),
        sa.Column("set_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("price >= 0", name=op.f("ck_market_price_holds_price_min")),
        sa.CheckConstraint("supply >= 0", name=op.f("ck_market_price_holds_supply_min")),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_market_price_holds_market_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("market_entity_id", "commodity", name=op.f("pk_market_price_holds")),
    )


def downgrade() -> None:
    op.drop_table("market_price_holds")
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_workshops_design_id_workshop_designs"), type_="foreignkey")
        batch_op.drop_column("design_id")
    op.drop_table("workshop_designs")
    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("material", sa.String(length=120), nullable=True))
    for table in HELD_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("held")
    widen(False)
