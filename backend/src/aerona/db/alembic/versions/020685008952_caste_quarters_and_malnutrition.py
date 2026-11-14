import sqlalchemy as sa
from alembic import op

revision = "020685008952"
down_revision = "c4b0365489e0"
branch_labels = None
depends_on = None

CONDITIONS_BEFORE = (
    "chronic_illness",
    "paranoia",
    "visions",
    "rage",
    "melancholy",
    "addiction",
    "age_blindness",
    "age_deafness",
    "withered_limb",
    "endless_hunger",
    "possession",
    "void_taint",
    "chosen_mark",
    "divine_brand",
    "nightmares",
    "comatose",
    "cognitive_decline",
)
CONDITIONS_AFTER = (*CONDITIONS_BEFORE, "malnutrition")


def kinds(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table("conditions", schema=None) as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum(*before, name="kind", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*after, name="kind", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    kinds(CONDITIONS_BEFORE, CONDITIONS_AFTER)
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("purity_rank_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_districts_purity_rank_id"), ["purity_rank_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_districts_purity_rank_id_purity_ranks"), "purity_ranks", ["purity_rank_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_districts_purity_rank_id_purity_ranks"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_districts_purity_rank_id"))
        batch_op.drop_column("purity_rank_id")
    op.execute("DELETE FROM conditions WHERE kind = 'malnutrition'")
    kinds(CONDITIONS_AFTER, CONDITIONS_BEFORE)
