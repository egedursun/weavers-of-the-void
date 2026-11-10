import sqlalchemy as sa
from alembic import op

revision = "fb3043d02ad2"
down_revision = "a67800447482"
branch_labels = None
depends_on = None


OLD_FEATURES = ("asteroid_field", "wormhole", "periodic_comet", "rogue_world", "gravity_well")
NEW_FEATURES = (*OLD_FEATURES, "wandering_star")


def feature_kinds(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="kind", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("cosmic_features", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=feature_kinds(OLD_FEATURES), type_=feature_kinds(NEW_FEATURES), existing_nullable=False)


def downgrade() -> None:
    op.execute("DELETE FROM cosmic_features WHERE kind = 'wandering_star'")
    with op.batch_alter_table("cosmic_features", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=feature_kinds(NEW_FEATURES), type_=feature_kinds(OLD_FEATURES), existing_nullable=False)
