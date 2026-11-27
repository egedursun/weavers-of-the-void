import json

import sqlalchemy as sa
from alembic import op

revision = "f3a8c1d5e9b2"
down_revision = "e5b7c2d9a1f3"
branch_labels = None
depends_on = None

RULE_DEFAULTS = tuple(("passability", f"sea_{mode}_pct", 100.0, 0.0) for mode in ("on_foot", "mounted", "wheeled", "burrowing", "climbing"))


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
