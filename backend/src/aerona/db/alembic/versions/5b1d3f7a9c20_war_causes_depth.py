import sqlalchemy as sa
from alembic import op

revision = "5b1d3f7a9c20"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None

OLD_WAR_CAUSES = (
    "hostility",
    "uprising",
    "tribute_revolt",
    "incited",
    "declared",
    "betrayal",
    "conquest_journey",
    "foreign_god",
    "independence",
    "vendetta",
    "grudge",
    "divine_grudge",
    "rivalry",
    "debt",
    "espionage",
    "sabotage",
    "envy",
    "schism",
    "beast",
    "resource",
    "ideology",
    "trade_route",
)
NEW_WAR_CAUSES = (*OLD_WAR_CAUSES, "claim", "holy_war", "succession", "raid", "liberation", "punitive")
WIDENED = (
    ("wars", "cause", OLD_WAR_CAUSES, NEW_WAR_CAUSES, False),
    ("bonds", "war_cause", OLD_WAR_CAUSES, NEW_WAR_CAUSES, True),
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
