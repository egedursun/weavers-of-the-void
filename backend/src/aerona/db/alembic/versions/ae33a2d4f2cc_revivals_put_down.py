import sqlalchemy as sa
from alembic import op

revision = "ae33a2d4f2cc"
down_revision = "020685008952"
branch_labels = None
depends_on = None

STAGES_BEFORE = ("steady", "stress", "distortion", "revitalisation", "new_steady")
STAGES_AFTER = (*STAGES_BEFORE, "suppressed")


def stages(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table("revivals", schema=None) as batch_op:
        batch_op.alter_column(
            "stage",
            existing_type=sa.Enum(*before, name="stage", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*after, name="stage", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    stages(STAGES_BEFORE, STAGES_AFTER)


def downgrade() -> None:
    op.execute("UPDATE revivals SET stage = 'distortion' WHERE stage = 'suppressed'")
    stages(STAGES_AFTER, STAGES_BEFORE)
