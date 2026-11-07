import sqlalchemy as sa
from alembic import op

revision = "dd58ba3646ed"
down_revision = "93404bcaf8cb"
branch_labels = None
depends_on = None

OLD_COMMODITIES = (
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

NEW_COMMODITIES = (*OLD_COMMODITIES, "meat", "milk", "cheese", "fruit", "tubers", "coal", "peat", "dung")
OLD_PROCESSES = (
    "farming",
    "fishing",
    "logging",
    "mining",
    "milling",
    "weaving",
    "smelting",
    "tanning",
    "brewing",
    "distilling",
    "masonry",
    "charcoal",
    "preserving",
    "lighting",
)

NEW_PROCESSES = (*OLD_PROCESSES, "butchery", "dairy", "pressing")
OLD_METHODS = (
    "hand_sickle",
    "ox_plough",
    "irrigated_terraces",
    "crop_rotation",
    "divine_harvest",
    "line_and_net",
    "fish_weirs",
    "deep_sea_fleets",
    "axe_felling",
    "water_sawmill",
    "pick_and_shovel",
    "fire_setting",
    "pumped_shafts",
    "earth_shaping",
    "hand_quern",
    "watermill",
    "windmill",
    "hand_loom",
    "water_frame",
    "bloomery",
    "blast_furnace",
    "divine_forge",
    "pit_tanning",
    "oil_curing",
    "open_vat",
    "cellar_brewing",
    "herbal_still",
    "arcane_alembic",
    "hand_chisel",
    "water_saw",
    "clamp_kiln",
    "retort_kiln",
    "salting",
    "smoking",
    "drying",
    "icing",
    "magic_keeping",
    "tallow_candles",
    "oil_lamps",
    "glow_moss",
    "magic_light",
)

NEW_METHODS = (*OLD_METHODS, "home_slaughter", "shambles", "hand_churning", "cave_ageing", "treading", "screw_press")
COLUMNS = (
    ("community_methods", "process", False, "PROCESSES"),
    ("community_methods", "method", False, "METHODS"),
    ("speculations", "commodity", False, "COMMODITIES"),
    ("trade_policies", "commodity", True, "COMMODITIES"),
    ("structure_designs", "upkeep_commodity", True, "COMMODITIES"),
    ("community_needs", "commodity", False, "COMMODITIES"),
    ("goods_flows", "commodity", False, "COMMODITIES"),
    ("labour_reasons", "commodity", True, "COMMODITIES"),
    ("market_price_holds", "commodity", False, "COMMODITIES"),
    ("market_prices", "commodity", False, "COMMODITIES"),
    ("people_biology", "staple", False, "COMMODITIES"),
    ("production_runs", "output", False, "COMMODITIES"),
    ("production_runs", "bottleneck", True, "COMMODITIES"),
    ("production_runs", "method", True, "METHODS"),
    ("trade_flows", "commodity", False, "COMMODITIES"),
    ("trade_route_losses", "commodity", False, "COMMODITIES"),
    ("community_stocks", "commodity", False, "COMMODITIES"),
    ("resource_profiles", "commodity", False, "COMMODITIES"),
    ("species_yields", "commodity", True, "COMMODITIES"),
)


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def kinds(group: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return {
        "COMMODITIES": (OLD_COMMODITIES, NEW_COMMODITIES),
        "PROCESSES": (OLD_PROCESSES, NEW_PROCESSES),
        "METHODS": (OLD_METHODS, NEW_METHODS),
    }[group]


def retype(*, forward: bool) -> None:
    for table, column, nullable, group in COLUMNS:
        old, new = kinds(group)
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum(before, column), type_=enum(after, column), existing_nullable=nullable)


def upgrade() -> None:
    retype(forward=True)


def downgrade() -> None:
    retype(forward=False)
