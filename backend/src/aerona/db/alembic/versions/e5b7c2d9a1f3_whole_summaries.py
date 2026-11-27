import sqlalchemy as sa
from alembic import op

revision = "e5b7c2d9a1f3"
down_revision = "e7d2a9c4b6f1"
branch_labels = None
depends_on = None

SUMMARY_LENGTH = 220
COLUMNS = (("action_records", "summary"), ("creation_rewards", "reason"), ("ledger_entries", "input_summary"))


def retype(table: str, column: str, before: sa.types.TypeEngine[str], after: sa.types.TypeEngine[str]) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=before, type_=after, existing_nullable=True)


def upgrade() -> None:
    for table, column in COLUMNS:
        retype(table, column, sa.String(length=SUMMARY_LENGTH), sa.Text())


def downgrade() -> None:
    for table, column in COLUMNS:
        retype(table, column, sa.Text(), sa.String(length=SUMMARY_LENGTH))
