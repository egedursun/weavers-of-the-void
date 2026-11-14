import json

import sqlalchemy as sa
from alembic import op

revision = "809d03497de7"
down_revision = "1b4e04a48853"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, kinds FROM relationships WHERE kinds LIKE '%childhood%'")).all()
    for row_id, kinds in rows:
        kept = [kind for kind in json.loads(kinds or "[]") if kind != "childhood"]
        connection.execute(sa.text("UPDATE relationships SET kinds = :kinds WHERE id = :id"), {"kinds": json.dumps(kept), "id": row_id})


def downgrade() -> None:
    pass
