import sqlalchemy as sa
from alembic import op

revision = "a4c6e8b0d2f1"
down_revision = "f1b3d5e7a9c4"
branch_labels = None
depends_on = None

IMAGE_STYLES = ("photoreal", "painting", "ink", "watercolor", "anime", "custom")


def upgrade() -> None:
    with op.batch_alter_table("cosmos", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "image_style",
                sa.Enum(*IMAGE_STYLES, name="image_style", native_enum=False, create_constraint=True, length=40),
                server_default="photoreal",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("image_style_custom", sa.Text(), server_default="", nullable=False))
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.add_column(sa.Column("style", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.drop_column("style")
    with op.batch_alter_table("cosmos", schema=None) as batch_op:
        batch_op.drop_column("image_style_custom")
        batch_op.drop_column("image_style")
