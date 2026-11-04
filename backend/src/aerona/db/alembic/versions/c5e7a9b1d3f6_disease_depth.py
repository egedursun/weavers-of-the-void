import sqlalchemy as sa
from alembic import op

revision = "c5e7a9b1d3f6"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None

OLD_COHORT_CONDITIONS = ("none", "veteran", "sick", "enslaved", "captive")
NEW_COHORT_CONDITIONS = (*OLD_COHORT_CONDITIONS, "maimed")
OLD_INJURY_KINDS = (
    "bruise",
    "cut",
    "deep_cut",
    "puncture",
    "fracture",
    "crush",
    "burn",
    "frostbite",
    "bite",
    "venom",
    "severed",
    "gouged",
    "destroyed",
    "curse_wither",
    "void_touch",
    "divine_brand",
)
NEW_INJURY_KINDS = (*OLD_INJURY_KINDS, "sickness")
WIDENED = (
    ("community_cohorts", "condition", OLD_COHORT_CONDITIONS, NEW_COHORT_CONDITIONS, False),
    ("captive_cohorts", "condition", OLD_COHORT_CONDITIONS, NEW_COHORT_CONDITIONS, False),
    ("injuries", "kind", OLD_INJURY_KINDS, NEW_INJURY_KINDS, False),
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
    with op.batch_alter_table("outbreaks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    with op.batch_alter_table("immunities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("endemic_diseases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("endemic_diseases", schema=None) as batch_op:
        batch_op.drop_column("locked")
    with op.batch_alter_table("immunities", schema=None) as batch_op:
        batch_op.drop_column("locked")
    with op.batch_alter_table("outbreaks", schema=None) as batch_op:
        batch_op.drop_column("locked")
    op.execute("DELETE FROM community_cohorts WHERE condition = 'maimed'")
    op.execute("UPDATE captive_cohorts SET condition = 'captive' WHERE condition = 'maimed'")
    op.execute("UPDATE injuries SET kind = 'venom' WHERE kind = 'sickness'")
    widen(False)
