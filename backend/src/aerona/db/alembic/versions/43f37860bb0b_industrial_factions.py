import sqlalchemy as sa
from alembic import op

revision = "43f37860bb0b"
down_revision = "ae33a2d4f2cc"
branch_labels = None
depends_on = None

KINDS_BEFORE = (
    "merchant_guild",
    "craft_guild",
    "priesthood",
    "warrior_order",
    "noble_council",
    "peasant_league",
    "rebels",
    "bandits",
    "pirates",
    "assassins",
    "scholars_academy",
    "secret_society",
    "mercenary_company",
    "interworld_federation",
    "wandering_market",
    "void_pirates",
    "social_circle",
    "mage_order",
    "estate",
    "party",
    "movement",
    "chartered_company",
    "holy_order",
    "crime_family",
    "thieves_guild",
    "smuggling_ring",
    "pirate_confederacy",
    "art_movement",
    "club",
    "league",
)
KINDS_AFTER = (*KINDS_BEFORE, "workers_union", "engineers_society", "financiers")


def kinds(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table("faction_profiles", schema=None) as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum(*before, name="kind", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*after, name="kind", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    kinds(KINDS_BEFORE, KINDS_AFTER)


def downgrade() -> None:
    op.execute("UPDATE faction_profiles SET kind = 'craft_guild' WHERE kind = 'workers_union'")
    op.execute("UPDATE faction_profiles SET kind = 'scholars_academy' WHERE kind = 'engineers_society'")
    op.execute("UPDATE faction_profiles SET kind = 'merchant_guild' WHERE kind = 'financiers'")
    kinds(KINDS_AFTER, KINDS_BEFORE)
