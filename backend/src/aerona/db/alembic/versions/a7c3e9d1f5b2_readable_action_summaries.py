import sqlalchemy as sa
from alembic import op

from aerona.core.action_text import readable_summary

revision = "a7c3e9d1f5b2"
down_revision = "f2a6c8e0b4d7"
branch_labels = None
depends_on = None

SUMMARY_LIMIT = 220
COLUMNS = (("action_records", "summary"), ("ledger_entries", "input_summary"))


def upgrade() -> None:
    bind = op.get_bind()
    for table, column in COLUMNS:
        rows = bind.execute(sa.text(f"SELECT id, {column} FROM {table} WHERE {column} LIKE '{{%'")).all()
        for row_id, text in rows:
            readable = readable_summary(text, SUMMARY_LIMIT)
            if readable != text:
                bind.execute(sa.text(f"UPDATE {table} SET {column} = :text WHERE id = :id"), {"text": readable, "id": row_id})


def downgrade() -> None:
    pass
