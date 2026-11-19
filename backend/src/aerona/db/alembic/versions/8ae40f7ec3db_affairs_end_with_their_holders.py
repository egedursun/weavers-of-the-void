import sqlalchemy as sa
from alembic import op

revision = "8ae40f7ec3db"
down_revision = "c461b1635292"
branch_labels = None
depends_on = None

STATE_OLD = ("incubating", "internalised", "rejected")
STATE_NEW = (*STATE_OLD, "lapsed")


def enum_of(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="state", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("incubating_ideas", schema=None) as batch_op:
        batch_op.alter_column("state", existing_type=enum_of(STATE_OLD), type_=enum_of(STATE_NEW), existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE incubating_ideas SET state = 'rejected' WHERE state = 'lapsed'")
    with op.batch_alter_table("incubating_ideas", schema=None) as batch_op:
        batch_op.alter_column("state", existing_type=enum_of(STATE_NEW), type_=enum_of(STATE_OLD), existing_nullable=False)
