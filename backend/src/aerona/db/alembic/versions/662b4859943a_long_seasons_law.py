import sqlalchemy as sa
from alembic import op

revision = "662b4859943a"
down_revision = "88d61a5796a9"
branch_labels = None
depends_on = None

OLD_NATURAL_LAWS = (
    "none",
    "immortality",
    "short_life",
    "dead_return",
    "magic_price",
    "war_ban",
    "bounty",
    "drought",
    "sea_ban",
    "one_language",
    "disasters",
    "souls_reincarnate",
    "gift_flowering",
    "gift_withering",
    "no_iron",
    "eternal_night",
    "magic_requires_blood",
    "gravity_shift",
    "seasons_reversed",
    "dreams_are_real",
    "oaths_bind",
    "the_dead_speak",
    "metal_rusts_fast",
)
NEW_NATURAL_LAWS = (*OLD_NATURAL_LAWS, "long_seasons")
OLD_SEASON_CAUSES = ("orbit", "divine")
NEW_SEASON_CAUSES = ("orbit", "natural_law", "divine")
WIDENED = (
    ("entities", "natural_law", OLD_NATURAL_LAWS, NEW_NATURAL_LAWS, True),
    ("natural_law_profiles", "effect", OLD_NATURAL_LAWS, NEW_NATURAL_LAWS, False),
    ("irregular_seasons", "cause", OLD_SEASON_CAUSES, NEW_SEASON_CAUSES, False),
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


def downgrade() -> None:
    widen(False)
