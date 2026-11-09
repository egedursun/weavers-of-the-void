import sqlalchemy as sa
from alembic import op

revision = "b7d41c9e2a15"
down_revision = "acc2e62332ed"
branch_labels = None
depends_on = None

TABLES = ("dimensions", "galaxy_clusters", "galaxies")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("depth", sa.JSON(), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("depth")
