import sqlalchemy as sa
from alembic import op

revision = "327eda9835ce"
down_revision = "10f7d9846da8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    districts = sa.table("districts", sa.column("hex_q", sa.Integer()), sa.column("hex_r", sa.Integer()), sa.column("locked", sa.JSON()))
    op.execute(districts.update().where(sa.not_(sa.cast(districts.c.locked, sa.String()).like('%"hex"%'))).values(hex_q=None, hex_r=None))


def downgrade() -> None:
    op.execute(sa.text("SELECT 1"))
