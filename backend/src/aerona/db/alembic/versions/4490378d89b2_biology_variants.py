import sqlalchemy as sa
from alembic import op

revision = "4490378d89b2"
down_revision = "b0caad39c04d"
branch_labels = None
depends_on = None

OLD_BIASES = (
    "overconfidence",
    "sunk_cost",
    "loss_aversion",
    "confirmation",
    "recency",
    "groupthink",
    "hostile_attribution",
    "optimism",
    "status_quo",
    "availability",
    "anchoring",
    "in_group_favour",
    "authority_deference",
    "scarcity_panic",
    "fatalism",
    "risk_seeking",
    "planning_fallacy",
    "halo",
    "projection",
)
NEW_BIASES = (*OLD_BIASES, "literalism", "colony_risk_aversion")


def bias_type(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="bias", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    op.create_table(
        "biology_variants",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("food_need_pct", sa.Integer(), nullable=False),
        sa.Column("fertility_pct", sa.Integer(), nullable=False),
        sa.Column("death_pct", sa.Integer(), nullable=False),
        sa.Column("disease_pct", sa.Integer(), nullable=False),
        sa.Column("morale_loss_pct", sa.Integer(), nullable=False),
        sa.Column("fire_harm_pct", sa.Integer(), nullable=False),
        sa.Column("storm_harm_pct", sa.Integer(), nullable=False),
        sa.Column("breathes", sa.Boolean(), nullable=False),
        sa.Column("drinks", sa.Boolean(), nullable=False),
        sa.Column("ages", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("death_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_death_pct_range")),
        sa.CheckConstraint("disease_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_disease_pct_range")),
        sa.CheckConstraint("fertility_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_fertility_pct_range")),
        sa.CheckConstraint("fire_harm_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_fire_harm_pct_range")),
        sa.CheckConstraint("food_need_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_food_need_pct_range")),
        sa.CheckConstraint("morale_loss_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_morale_loss_pct_range")),
        sa.CheckConstraint("storm_harm_pct BETWEEN 0 AND 500", name=op.f("ck_biology_variants_storm_harm_pct_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_biology_variants_updated_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_biology_variants_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_biology_variants")),
    )
    with op.batch_alter_table("bias_weights", schema=None) as batch_op:
        batch_op.alter_column("bias", existing_type=bias_type(OLD_BIASES), type_=bias_type(NEW_BIASES), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("bias_weights", schema=None) as batch_op:
        batch_op.alter_column("bias", existing_type=bias_type(NEW_BIASES), type_=bias_type(OLD_BIASES), existing_nullable=False)
    op.drop_table("biology_variants")
