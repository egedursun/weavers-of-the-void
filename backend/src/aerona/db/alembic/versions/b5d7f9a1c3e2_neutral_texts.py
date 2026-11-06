import sqlalchemy as sa
from alembic import op

revision = "b5d7f9a1c3e2"
down_revision = "a4c6e8b0d2f1"
branch_labels = None
depends_on = None

BOND_TEXTS = (
    ("sacred to him", "sacred to this god"),
    ("his remains", "the remains of this god"),
    ("the world he birthed", "the world they birthed"),
)
TOOL_NAMES = (("pray_to_father", "pray_to_creator"),)


def _rename(pairs: tuple[tuple[str, str], ...], statement: str) -> None:
    for old, new in pairs:
        op.execute(sa.text(statement).bindparams(old=old, new=new))


def upgrade() -> None:
    _rename(BOND_TEXTS, "UPDATE bonds SET description = :new, description_key = :new WHERE description = :old")
    _rename(TOOL_NAMES, "UPDATE ledger_entries SET tool = :new WHERE tool = :old")


def downgrade() -> None:
    _rename(tuple((new, old) for old, new in BOND_TEXTS), "UPDATE bonds SET description = :new, description_key = :new WHERE description = :old")
    _rename(tuple((new, old) for old, new in TOOL_NAMES), "UPDATE ledger_entries SET tool = :new WHERE tool = :old")
