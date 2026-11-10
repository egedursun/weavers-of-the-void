import sqlalchemy as sa
from alembic import op

revision = "c2e4a6b8d0f1"
down_revision = "fb3043d02ad2"
branch_labels = None
depends_on = None


NEW_COUNTERS = (
    "season_order",
    "weather_shaping",
    "sibling_messages",
    "narrative_bonds",
    "prayers",
    "free_living_creation",
    "free_land_creation",
    "anchor_chosen",
    "words_coined",
    "gifts",
    "holy_world",
    "leak_stitched",
    "take_life",
    "intrigue",
    "outer_bargain",
    "harvests",
    "discoveries",
    "claims",
    "worship_changes",
    "learning",
    "prophecies",
    "commander_appointments",
    "adoptions",
    "explorations",
    "resurrection_rites",
    "languages_founded",
    "cultures_created",
    "land_rewards",
    "laws_enacted",
    "officers_appointed",
    "taxes_set",
    "treaties_proposed",
    "oaths_sworn",
    "faction_acts",
)
OLD_COUNTERS = (*NEW_COUNTERS, "repeated_creations")
NEW_STEPS = (
    "completion",
    "backup",
    "distribution",
    "naming",
    "fate_judgment",
    "chronicle",
    "voices",
    "council",
    "epoch_words",
    "local_gods",
    "transition",
    "world_birth",
    "network_repair",
    "prune",
    "images",
    "localisation",
    "background",
)
OLD_STEPS = (*NEW_STEPS, "horizon_intuitions")
CATEGORIES = ("imagery", "material", "color", "sound", "creature", "place", "theme", "phrase")


def kinds(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    op.execute("DELETE FROM turn_counters WHERE counter = 'repeated_creations'")
    op.execute("DELETE FROM epoch_steps WHERE step = 'horizon_intuitions'")
    with op.batch_alter_table("turn_counters", schema=None) as batch_op:
        batch_op.alter_column("counter", existing_type=kinds(OLD_COUNTERS, "counter"), type_=kinds(NEW_COUNTERS, "counter"), existing_nullable=False)
    with op.batch_alter_table("epoch_steps", schema=None) as batch_op:
        batch_op.alter_column("step", existing_type=kinds(OLD_STEPS, "step"), type_=kinds(NEW_STEPS, "step"), existing_nullable=False)
    with op.batch_alter_table("creation_motifs", schema=None) as batch_op:
        batch_op.drop_constraint("category", type_="check")
        batch_op.drop_column("category")


def downgrade() -> None:
    with op.batch_alter_table("creation_motifs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", kinds(CATEGORIES, "category"), nullable=True))
    with op.batch_alter_table("epoch_steps", schema=None) as batch_op:
        batch_op.alter_column("step", existing_type=kinds(NEW_STEPS, "step"), type_=kinds(OLD_STEPS, "step"), existing_nullable=False)
    with op.batch_alter_table("turn_counters", schema=None) as batch_op:
        batch_op.alter_column("counter", existing_type=kinds(NEW_COUNTERS, "counter"), type_=kinds(OLD_COUNTERS, "counter"), existing_nullable=False)
