import sqlalchemy as sa
from alembic import op

revision = "93404bcaf8cb"
down_revision = "fe81c6759526"
branch_labels = None
depends_on = None

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
)

NEW_PROCESSES = (*OLD_PROCESSES, "lighting")
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
)

NEW_METHODS = (*OLD_METHODS, "tallow_candles", "oil_lamps", "glow_moss", "magic_light")


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(table: str, column: str, old: tuple[str, ...], new: tuple[str, ...], *, nullable: bool = False) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum(old, column), type_=enum(new, column), existing_nullable=nullable)


def upgrade() -> None:
    retype("community_methods", "process", OLD_PROCESSES, NEW_PROCESSES)
    retype("community_methods", "method", OLD_METHODS, NEW_METHODS)
    retype("production_runs", "method", OLD_METHODS, NEW_METHODS, nullable=True)
    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.add_column(sa.Column("light", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(batch_op.f("ck_community_industry_light_range"), "light BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_community_industry_light_range"), type_="check")
        batch_op.drop_column("light")
    retype("production_runs", "method", NEW_METHODS, OLD_METHODS, nullable=True)
    retype("community_methods", "method", NEW_METHODS, OLD_METHODS)
    retype("community_methods", "process", NEW_PROCESSES, OLD_PROCESSES)
