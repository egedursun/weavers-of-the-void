import sqlalchemy as sa
from alembic import op

revision = "f9b1d3e5a7c6"
down_revision = "e8a0c2d4f6b5"
branch_labels = None
depends_on = None

PACKAGES = (
    "snake_venom",
    "drink_dependence",
    "drug_dependence",
    "lycanthropy",
    "vampirism",
    "divine_blessing",
    "void_taint",
    "possession",
    "trauma",
    "hunger_curse",
)
OLD_MEMORIES = (
    "harmed_me",
    "killed_kin",
    "saved_me",
    "betrayed_me",
    "kept_oath",
    "broke_oath",
    "maimed_me",
    "humiliated_me",
    "gifted_me",
    "converted_me",
    "conquered_us",
    "freed_us",
    "famine_aid",
    "desecrated_holy",
    "married_into",
    "fought_us",
    "traded_with",
    "allied_with",
    "made_peace",
    "demanded_tribute",
    "cheated_us",
    "spied_on_us",
    "envied",
    "failed_to_heal",
    "taught_me",
    "held_captive",
    "lamented",
    "divine_will",
    "goodwill",
    "ill_will",
    "long_history",
)
NEW_MEMORIES = (*OLD_MEMORIES, "dreads")
TRANSMISSIONS = ("contact", "bite", "ingestion", "inhalation", "blood", "curse", "birth", "rite", "gaze", "experience")


def memories(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table("memories", schema=None) as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum(*old, name="kind", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name="kind", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    memories(OLD_MEMORIES, NEW_MEMORIES)
    op.create_table(
        "afflictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bearer_node_id", sa.Integer(), nullable=False),
        sa.Column("package", sa.Enum(*PACKAGES, name="package", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("stage_since_epoch", sa.Integer(), nullable=False),
        sa.Column("transmission", sa.Enum(*TRANSMISSIONS, name="transmission", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("cured_epoch", sa.Integer(), nullable=True),
        sa.Column("applied", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("stage >= 0", name=op.f("ck_afflictions_stage_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_afflictions_since_epoch_min")),
        sa.ForeignKeyConstraint(["bearer_node_id"], ["nodes.id"], name=op.f("fk_afflictions_bearer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_afflictions_source_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_afflictions")),
    )
    with op.batch_alter_table("afflictions", schema=None) as batch_op:
        batch_op.create_index("ix_afflictions_bearer", ["bearer_node_id"], unique=False)
        batch_op.create_index("ix_afflictions_package", ["package"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("afflictions", schema=None) as batch_op:
        batch_op.drop_index("ix_afflictions_package")
        batch_op.drop_index("ix_afflictions_bearer")
    op.drop_table("afflictions")
    memories(NEW_MEMORIES, OLD_MEMORIES)
