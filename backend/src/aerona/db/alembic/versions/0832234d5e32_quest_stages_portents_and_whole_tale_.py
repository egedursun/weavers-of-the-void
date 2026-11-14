import sqlalchemy as sa
from alembic import op

revision = "0832234d5e32"
down_revision = "809d03497de7"
branch_labels = None
depends_on = None

STAGES_BEFORE = ("inciting", "rising", "crisis", "climax", "resolution")
QUEST_STAGES = ("call", "refusal", "mentor", "threshold", "ordeal", "return")
STAGES_AFTER = (*STAGES_BEFORE[:4], *QUEST_STAGES, "resolution")
SETUPS_BEFORE = ("prophecy", "omen", "dream", "foresight", "thread")
SETUPS_AFTER = (*SETUPS_BEFORE, "portent")
STAGED = ("arcs", "arc_beats")


def kind_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen_stages(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    for table in STAGED:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column("stage", existing_type=kind_of(before, "stage"), type_=kind_of(after, "stage"), existing_nullable=False)


def widen_setups(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table("setups", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=kind_of(before, "kind"), type_=kind_of(after, "kind"), existing_nullable=False)


def upgrade() -> None:
    widen_stages(STAGES_BEFORE, STAGES_AFTER)
    widen_setups(SETUPS_BEFORE, SETUPS_AFTER)
    with op.batch_alter_table("arc_beats", schema=None) as batch_op:
        batch_op.alter_column("text", existing_type=sa.VARCHAR(length=480), type_=sa.Text(), existing_nullable=False)
    with op.batch_alter_table("setups", schema=None) as batch_op:
        batch_op.alter_column("payoff_text", existing_type=sa.VARCHAR(length=480), type_=sa.Text(), existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE setups SET kind = 'omen' WHERE kind = 'portent'")
    quest = ", ".join(f"'{stage}'" for stage in QUEST_STAGES)
    for table in STAGED:
        op.execute(f"UPDATE {table} SET stage = 'rising' WHERE stage IN ({quest})")
    op.execute("UPDATE arc_beats SET text = substr(text, 1, 480)")
    op.execute("UPDATE setups SET payoff_text = substr(payoff_text, 1, 480)")
    with op.batch_alter_table("setups", schema=None) as batch_op:
        batch_op.alter_column("payoff_text", existing_type=sa.Text(), type_=sa.VARCHAR(length=480), existing_nullable=False)
    with op.batch_alter_table("arc_beats", schema=None) as batch_op:
        batch_op.alter_column("text", existing_type=sa.Text(), type_=sa.VARCHAR(length=480), existing_nullable=False)
    widen_setups(SETUPS_AFTER, SETUPS_BEFORE)
    widen_stages(STAGES_AFTER, STAGES_BEFORE)
