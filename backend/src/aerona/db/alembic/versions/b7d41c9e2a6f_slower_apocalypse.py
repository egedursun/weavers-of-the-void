import json

import sqlalchemy as sa
from alembic import op

revision = "b7d41c9e2a6f"
down_revision = "6fa247807812"
branch_labels = None
depends_on = None

RULE_DEFAULTS = (("balance", "apocalypse_speed", 100.0, 1.0),)


def reset_snapshots(forward: bool) -> None:
    bind = op.get_bind()
    swaps = {(namespace, key): (old, new) if forward else (new, old) for namespace, key, old, new in RULE_DEFAULTS}
    for cosmos_id, raw in bind.execute(sa.text("SELECT id, rules_snapshot FROM cosmos")).all():
        snapshot = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        changed = False
        for (namespace, key), (before, after) in swaps.items():
            table = snapshot.get(namespace)
            if isinstance(table, dict) and key in table and float(table[key]) == before:
                table[key] = after
                changed = True
        if changed:
            bind.execute(sa.text("UPDATE cosmos SET rules_snapshot = :snapshot WHERE id = :id"), {"snapshot": json.dumps(snapshot), "id": cosmos_id})


def upgrade() -> None:
    reset_snapshots(True)


def downgrade() -> None:
    reset_snapshots(False)
