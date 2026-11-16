import sqlalchemy as sa
from alembic import op

revision = "f19c2a7d4e60"
down_revision = "eb2a138f5f58"
branch_labels = None
depends_on = None

REASON_OLD = ("spy", "blood_curse", "exile", "impostor")
REASON_NEW = (*REASON_OLD, "hidden_power")


def enum_of(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="reason", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("identities", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=enum_of(REASON_OLD), type_=enum_of(REASON_NEW), existing_nullable=False)


def downgrade() -> None:
    op.execute("DELETE FROM identities WHERE reason = 'hidden_power'")
    with op.batch_alter_table("identities", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=enum_of(REASON_NEW), type_=enum_of(REASON_OLD), existing_nullable=False)
