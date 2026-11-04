import sqlalchemy as sa
from alembic import op

revision = "e7c3a1f5b9d2"
down_revision = "d4a8c2e6f0b3"
branch_labels = None
depends_on = None

KIN_BONDS = (
    "inside",
    "lives_in",
    "worships",
    "enemy",
    "ally",
    "descends_from",
    "protects",
    "rules",
    "owns",
    "beat",
    "killed",
    "cursed",
    "blessed",
    "source_of",
    "tells_of",
    "destroyed",
    "loves",
    "fears",
    "hunts",
    "trades_with",
    "prophesies",
    "caused",
    "celebrates",
    "forbids",
    "speaks",
    "produced",
    "built",
    "migrated_to",
    "discovered",
    "soul_descended_to",
    "party_to",
    "member_of",
    "knows",
    "pays_tribute",
    "related",
    "holds_captive",
    "spy_network",
    "pursues",
    "companion",
    "rival",
    "apprentice_of",
    "commands",
    "part_of",
    "passenger_of",
    "captain_of",
    "tamed",
    "truce",
    "owes",
    "treated_by",
    "parent_of",
    "spouse_of",
    "betrothed_to",
    "concubine_of",
    "fostered_by",
    "sworn_kin",
)
ALL_BONDS = (*KIN_BONDS, "tells", "fixed_in", "adherent_of", "practises")
EXPOSED_CAUSES = (
    "battle",
    "duel",
    "punishment",
    "torture",
    "accident",
    "monster",
    "disaster",
    "curse",
    "magic_backlash",
    "god",
    "poison",
    "quest",
    "escape",
    "sacrifice",
    "age",
    "player",
    "exposure",
)
ALL_CAUSES = (*EXPOSED_CAUSES, "ritual")
CAUSE_COLUMNS = (("injuries", "cause_kind"), ("conditions", "source"))


def named_enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def bond_indexes() -> list[tuple[str, str]]:
    rows = op.get_bind().execute(sa.text("SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'bonds' AND sql IS NOT NULL"))
    return [(row[0], row[1]) for row in rows]


def upgrade() -> None:
    indexes = bond_indexes()
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=named_enum("kind", KIN_BONDS), type_=named_enum("kind", ALL_BONDS), existing_nullable=False)
    for name, sql in indexes:
        op.execute(sa.text(f'DROP INDEX IF EXISTS "{name}"'))
        op.execute(sa.text(sql))
    for table, column in CAUSE_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=named_enum(column, EXPOSED_CAUSES), type_=named_enum(column, ALL_CAUSES), existing_nullable=False)


def downgrade() -> None:
    return None
