import sqlalchemy as sa
from alembic import op

revision = "0fc1044d2f25"
down_revision = "c4e8a2d6f1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "record_keepers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("chronicler", "historian", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("scope_node_id", sa.Integer(), nullable=False),
        sa.Column("keeper_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_record_keepers_since_epoch_min")),
        sa.ForeignKeyConstraint(["keeper_entity_id"], ["entities.id"], name=op.f("fk_record_keepers_keeper_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scope_node_id"], ["nodes.id"], name=op.f("fk_record_keepers_scope_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_keepers")),
        sa.UniqueConstraint("kind", "scope_node_id", name="uq_record_keepers_kind_scope"),
    )
    with op.batch_alter_table("record_keepers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_record_keepers_keeper_entity_id"), ["keeper_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_record_keepers_scope_node_id"), ["scope_node_id"], unique=False)

    with op.batch_alter_table("epochs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chronicler_entity_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_epochs_chronicler_entity_id"), ["chronicler_entity_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_epochs_chronicler_entity_id_entities"), "entities", ["chronicler_entity_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("historian_views", schema=None) as batch_op:
        batch_op.add_column(sa.Column("historian_entity_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_historian_views_historian_entity_id"), ["historian_entity_id"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_historian_views_historian_entity_id_entities"), "entities", ["historian_entity_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("historian_views", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_historian_views_historian_entity_id_entities"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_historian_views_historian_entity_id"))
        batch_op.drop_column("historian_entity_id")

    with op.batch_alter_table("epochs", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_epochs_chronicler_entity_id_entities"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_epochs_chronicler_entity_id"))
        batch_op.drop_column("chronicler_entity_id")

    with op.batch_alter_table("record_keepers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_record_keepers_scope_node_id"))
        batch_op.drop_index(batch_op.f("ix_record_keepers_keeper_entity_id"))

    op.drop_table("record_keepers")
