import sqlalchemy as sa
from alembic import op

revision = "4f7b9c2e8a61"
down_revision = "8c4e2a6f1d93"
branch_labels = None
depends_on = None

MANDATES = ("produce", "export_ban", "build", "famine_relief", "curfew", "slum_clearance")
WIDER = (*MANDATES, "prepare", "enclosure")


def enum_of(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="kind", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("mandates", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of(MANDATES), type_=enum_of(WIDER), existing_nullable=False)


def downgrade() -> None:
    op.execute("DELETE FROM mandates WHERE kind IN ('prepare', 'enclosure')")
    with op.batch_alter_table("mandates", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of(WIDER), type_=enum_of(MANDATES), existing_nullable=False)
