import sqlalchemy as sa
from alembic import op

revision = "d7f9b1c3e5a8"
down_revision = "a7c3e9d1f5b2"
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
    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("material", sa.String(length=120), nullable=True))
    for table in HELD_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("held")
    widen(False)
