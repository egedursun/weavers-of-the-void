import sqlalchemy as sa
from alembic import op

revision = "c1e5a9d3f7b2"
down_revision = "b9d4f1a7c3e6"
branch_labels = None
depends_on = None

HELD = ("language_intelligibility", "speaker_cohorts", "tradition_participation")
OLD_CAUSES = (
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
)
NEW_CAUSES = (*OLD_CAUSES, "ritual")
CAUSE_COLUMNS = (("injuries", "cause_kind"), ("conditions", "source"))


def causes(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    for table, column in CAUSE_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*old, name=column, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*new, name=column, native_enum=False, create_constraint=True, length=40),
                existing_nullable=False,
            )


def upgrade() -> None:
    for table in HELD:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    causes(OLD_CAUSES, NEW_CAUSES)


def downgrade() -> None:
    op.execute(sa.text("UPDATE injuries SET cause_kind = 'quest' WHERE cause_kind = 'ritual'"))
    op.execute(sa.text("UPDATE conditions SET source = 'quest' WHERE source = 'ritual'"))
    causes(NEW_CAUSES, OLD_CAUSES)
    for table in HELD:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("locked")
