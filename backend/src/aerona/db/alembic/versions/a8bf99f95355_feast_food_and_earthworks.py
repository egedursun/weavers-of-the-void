import sqlalchemy as sa
from alembic import op

revision = "a8bf99f95355"
down_revision = "959c964d1a42"
branch_labels = None
depends_on = None

OLD_FEATURES = ("mass_grave", "salvage_field")
NEW_FEATURES = (*OLD_FEATURES, "earthworks")


def features(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table("battlefield_features", schema=None) as batch_op:
        batch_op.alter_column(
            "feature",
            existing_type=sa.Enum(*old, name="feature", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name="feature", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    features(OLD_FEATURES, NEW_FEATURES)
    with op.batch_alter_table("gatherings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("food", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(op.f("ck_gatherings_food_min"), "food >= 0")


def downgrade() -> None:
    with op.batch_alter_table("gatherings", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_gatherings_food_min"), type_="check")
        batch_op.drop_column("food")
    features(NEW_FEATURES, OLD_FEATURES)
