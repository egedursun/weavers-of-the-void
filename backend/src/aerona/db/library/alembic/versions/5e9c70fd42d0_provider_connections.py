import sqlalchemy as sa
from alembic import op

import aerona.db.types

revision = "5e9c70fd42d0"
down_revision = "2fbe54b84142"
branch_labels = None
depends_on = None

KINDS = (
    "claude_subscription",
    "chatgpt_subscription",
    "gemini_subscription",
    "copilot_subscription",
    "openai",
    "anthropic",
    "gemini",
    "mistral",
    "groq",
    "deepseek",
    "xai",
    "openrouter",
    "cohere",
    "cerebras",
    "perplexity",
    "replicate",
    "huggingface",
    "local_server",
    "image_worker",
)
ROLES = ("world_agents", "writing", "conversation", "images")


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.Enum(*KINDS, name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=False),
        sa.Column("secret", sa.Text(), server_default="", nullable=False),
        sa.Column("secret_hint", sa.String(length=4), server_default="", nullable=False),
        sa.Column("base_url", sa.String(length=500), server_default="", nullable=False),
        sa.Column("logged_in_at", aerona.db.types.UtcDateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["accounts.id"], name=op.f("fk_provider_connections_created_by_accounts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_provider_connections_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_connections")),
    )
    with op.batch_alter_table("provider_connections", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_provider_connections_workspace_id"), ["workspace_id"], unique=False)

    op.create_table(
        "provider_chain_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.Enum(*ROLES, name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=200), server_default="", nullable=False),
        sa.Column("tools_work", sa.Boolean(), nullable=True),
        sa.Column("sees_images", sa.Boolean(), nullable=True),
        sa.Column("checked_at", aerona.db.types.UtcDateTime(timezone=True), nullable=True),
        sa.Column("check_note", sa.String(length=500), server_default="", nullable=False),
        sa.CheckConstraint("position >= 0", name=op.f("ck_provider_chain_entries_position_min")),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["provider_connections.id"], name=op.f("fk_provider_chain_entries_connection_id_provider_connections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_provider_chain_entries_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_chain_entries")),
    )
    with op.batch_alter_table("provider_chain_entries", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_provider_chain_entries_connection_id"), ["connection_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_provider_chain_entries_workspace_id"), ["workspace_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("provider_chain_entries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_provider_chain_entries_workspace_id"))
        batch_op.drop_index(batch_op.f("ix_provider_chain_entries_connection_id"))
    op.drop_table("provider_chain_entries")
    with op.batch_alter_table("provider_connections", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_provider_connections_workspace_id"))
    op.drop_table("provider_connections")
