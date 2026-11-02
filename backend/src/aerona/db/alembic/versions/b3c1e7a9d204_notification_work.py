import sqlalchemy as sa
from alembic import op

revision = "b3c1e7a9d204"
down_revision = "81ed863309b2"
branch_labels = None
depends_on = None

CATEGORIES_BEFORE = (
    "rebellion",
    "death",
    "birth",
    "prophecy",
    "apocalypse",
    "horror",
    "war",
    "prayer",
    "cosmos",
    "ascension",
    "disaster",
    "epoch",
    "achievement",
    "society",
    "reputation",
    "error",
    "note",
)
CATEGORIES_AFTER = (*CATEGORIES_BEFORE, "work")
CONSTRAINT = "category"


def _condition(values: tuple[str, ...]) -> str:
    listed = ", ".join(f"'{value}'" for value in values)
    return f"category IN ({listed})"


def upgrade() -> None:
    with op.batch_alter_table("notifications", recreate="always") as batch:
        batch.add_column(sa.Column("job_id", sa.String(length=36), nullable=True))
        batch.drop_constraint(CONSTRAINT, type_="check")
        batch.create_check_constraint(CONSTRAINT, _condition(CATEGORIES_AFTER))


def downgrade() -> None:
    op.execute("DELETE FROM notifications WHERE category = 'work'")
    with op.batch_alter_table("notifications", recreate="always") as batch:
        batch.drop_constraint(CONSTRAINT, type_="check")
        batch.create_check_constraint(CONSTRAINT, _condition(CATEGORIES_BEFORE))
        batch.drop_column("job_id")
