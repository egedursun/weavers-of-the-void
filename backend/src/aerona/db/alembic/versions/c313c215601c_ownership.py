import sqlalchemy as sa
from alembic import op

revision = "c313c215601c"
down_revision = "7e3748499664"
branch_labels = None
depends_on = None

LEDGER = ("revenue", "inputs", "wages", "upkeep", "taxes", "invested")


def upgrade() -> None:
    op.create_table(
        "site_profits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("community_node_id", sa.Integer(), nullable=False),
        sa.Column("workshop_id", sa.Integer(), nullable=True),
        sa.Column("resource_node_id", sa.Integer(), nullable=True),
        sa.Column("site", sa.String(length=120), nullable=False),
        *(sa.Column(column, sa.Integer(), nullable=False) for column in LEDGER),
        sa.Column("profit", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_site_profits_epoch_min")),
        *(sa.CheckConstraint(f"{column} >= 0", name=op.f(f"ck_site_profits_{column}_min")) for column in LEDGER),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_site_profits_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["community_node_id"], ["nodes.id"], name=op.f("fk_site_profits_community_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workshop_id"], ["workshops.id"], name=op.f("fk_site_profits_workshop_id_workshops"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resource_node_id"], ["nodes.id"], name=op.f("fk_site_profits_resource_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_profits")),
    )
    with op.batch_alter_table("site_profits", schema=None) as batch_op:
        batch_op.create_index("ix_site_profits_owner", ["owner_node_id"], unique=False)
        batch_op.create_index("ix_site_profits_community", ["community_node_id"], unique=False)
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_node_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_workshops_owner_node_id"), ["owner_node_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_workshops_owner_node_id_nodes"), "nodes", ["owner_node_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.add_column(sa.Column("drink", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(batch_op.f("ck_community_industry_drink_range"), "drink BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_community_industry_drink_range"), type_="check")
        batch_op.drop_column("drink")
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_workshops_owner_node_id_nodes"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_workshops_owner_node_id"))
        batch_op.drop_column("owner_node_id")
    with op.batch_alter_table("site_profits", schema=None) as batch_op:
        batch_op.drop_index("ix_site_profits_community")
        batch_op.drop_index("ix_site_profits_owner")
    op.drop_table("site_profits")
