import sqlalchemy as sa
from alembic import op

revision = "a7d2e9c4b1f6"
down_revision = "b4d8cd9d30e3"
branch_labels = None
depends_on = None

MERGED_KEYS = ("gods.mood.wrath", "gods.mood.grace", "gods.mood.silence", "gods.mood.loneliness", "gods.power.drain")
KEY_COLUMNS = (("chronicle", "template_key"), ("incidents", "kind"))


def upgrade() -> None:
    for key in MERGED_KEYS:
        for table, column in KEY_COLUMNS:
            op.execute(sa.text(f'UPDATE "{table}" SET "{column}" = :key WHERE "{column}" LIKE :variants').bindparams(key=key, variants=f"{key}.%"))


def downgrade() -> None:
    for key in MERGED_KEYS:
        for table, column in KEY_COLUMNS:
            op.execute(sa.text(f'UPDATE "{table}" SET "{column}" = :variant WHERE "{column}" = :key').bindparams(key=key, variant=f"{key}.1"))
