import sqlalchemy as sa
from alembic import op

revision = "e7d2a9c4b6f1"
down_revision = "c0a1d9e4f7b2"
branch_labels = None
depends_on = None

SOURCES = (
    "entity",
    "typed_section",
    "chronicle",
    "incident",
    "son",
    "foreign_god",
    "world",
    "star",
    "creator",
    "word",
    "epoch",
    "note",
    "message",
    "council",
    "artifact",
    "attachment",
)


def upgrade() -> None:
    with op.batch_alter_table("divine_will_chunks", schema=None) as batch_op:
        batch_op.drop_index("ix_divine_will_chunks_source")
        batch_op.drop_index(batch_op.f("ix_divine_will_chunks_node_id"))
        batch_op.drop_index(batch_op.f("ix_divine_will_chunks_cycle_id"))
    op.drop_table("divine_will_chunks")


def downgrade() -> None:
    op.create_table(
        "divine_will_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum(*SOURCES, name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=True),
        sa.Column("cycle_id", sa.Integer(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("digest", sa.String(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name=op.f("ck_divine_will_chunks_ordinal_min")),
        sa.CheckConstraint("tokens >= 0", name=op.f("ck_divine_will_chunks_tokens_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_divine_will_chunks_updated_epoch_min")),
        sa.ForeignKeyConstraint(["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_chunks_cycle_id_divine_will_cycles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_divine_will_chunks_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_chunks")),
    )
    with op.batch_alter_table("divine_will_chunks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_chunks_cycle_id"), ["cycle_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_divine_will_chunks_node_id"), ["node_id"], unique=False)
        batch_op.create_index("ix_divine_will_chunks_source", ["source", "source_id"], unique=False)
