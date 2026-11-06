import sqlalchemy as sa
from alembic import op

revision = "b3d5f7a9c1e2"
down_revision = "a2b4c6d8e0f1"
branch_labels = None
depends_on = None

HANDEDNESS = ("right", "left", "both")


def upgrade() -> None:
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("lost_digits", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(
            sa.Column(
                "handedness",
                sa.Enum(*HANDEDNESS, name="handedness", native_enum=False, create_constraint=True, length=40),
                server_default="right",
                nullable=False,
            )
        )
    with op.batch_alter_table("injuries", schema=None) as batch_op:
        batch_op.add_column(sa.Column("digits", sa.JSON(), server_default="[]", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("injuries", schema=None) as batch_op:
        batch_op.drop_column("digits")
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        batch_op.drop_column("handedness")
        batch_op.drop_column("lost_digits")
