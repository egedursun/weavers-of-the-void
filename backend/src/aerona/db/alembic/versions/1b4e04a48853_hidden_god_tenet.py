import sqlalchemy as sa
from alembic import op

revision = "1b4e04a48853"
down_revision = "8f56551e2761"
branch_labels = None
depends_on = None

TENETS_BEFORE = (
    "pacifism",
    "holy_war",
    "asceticism",
    "sacred_suffering",
    "purity_of_body",
    "ancestor_veneration",
    "human_sacrifice",
    "animal_sacrifice",
    "celibate_clergy",
    "proselytism",
    "exclusivity",
    "syncretic_openness",
    "monastic_learning",
    "anti_magic",
    "sanctified_magic",
    "judgement_by_deeds",
    "judgement_by_faith",
    "reincarnation",
    "martyrdom_glory",
    "divine_kingship",
    "dietary_law",
    "sacred_species",
    "pilgrimage_duty",
    "souls_rest",
    "void_communion",
    "feeding_the_hunger",
    "whispered_secrets",
)
TENETS_AFTER = (*TENETS_BEFORE, "hidden_god")
RENAMED = (
    ("the Blessed Fields of ", "the paradise of "),
    ("the Grey Plain of ", "the middle realm of "),
    ("the Pits of ", "the torment of "),
    ("the Forgetting of ", "the oblivion of "),
    ("the Hall of the Fallen of ", "the rest of warriors of "),
    ("the House of the Ancestors of ", "the rest of ancestors of "),
)


def rename(pairs: tuple[tuple[str, str], ...]) -> None:
    for old, new in pairs:
        op.execute(f"UPDATE afterlife_strata SET name = '{new}' || substr(name, {len(old) + 1}) WHERE name LIKE '{old}%'")


def widen(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table("cult_tenets", schema=None) as batch_op:
        batch_op.alter_column(
            "tenet",
            existing_type=sa.Enum(*before, name="tenet", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*after, name="tenet", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    widen(TENETS_BEFORE, TENETS_AFTER)
    rename(RENAMED)


def downgrade() -> None:
    rename(tuple((new, old) for old, new in RENAMED))
    op.execute("DELETE FROM cult_tenets WHERE tenet = 'hidden_god'")
    widen(TENETS_AFTER, TENETS_BEFORE)
