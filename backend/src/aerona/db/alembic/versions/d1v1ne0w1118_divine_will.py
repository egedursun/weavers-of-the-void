import sqlalchemy as sa
from alembic import op

revision = "d1v1ne0w1118"
down_revision = "e52b7c4d9a10"
branch_labels = None
depends_on = None


OLD_JOB_KINDS = (
    "epoch",
    "genesis",
    "deepen",
    "summon",
    "image",
    "backup",
    "book",
    "import",
    "simulation",
    "son_turn",
    "naming",
    "completion",
    "revelation",
    "world_creation",
    "awakening",
    "content",
    "maintenance",
    "retry",
    "prehistory",
    "deep_time",
)
NEW_JOB_KINDS = (
    "epoch",
    "genesis",
    "deepen",
    "summon",
    "image",
    "backup",
    "book",
    "import",
    "simulation",
    "son_turn",
    "naming",
    "completion",
    "revelation",
    "world_creation",
    "awakening",
    "content",
    "maintenance",
    "retry",
    "prehistory",
    "deep_time",
    "divine_will",
    "divine_will_plan",
    "divine_will_forecast",
    "divine_will_index",
)


def job_kinds(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="kind", native_enum=False, create_constraint=True, length=40)


def retype_jobs(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=job_kinds(before), type_=job_kinds(after), existing_nullable=False)


def upgrade() -> None:
    retype_jobs(OLD_JOB_KINDS, NEW_JOB_KINDS)
    op.create_table(
        "divine_will_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_divine_will_sessions_opened_epoch_min")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_sessions")),
    )
    op.create_table(
        "divine_will_cycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "mode",
            sa.Enum(
                "command",
                "plan",
                "ask_lore",
                "creative_work",
                "mechanics_guide",
                "foresight",
                name="mode",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "awaiting_confirmation", "done", "failed", "cancelled", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("player_text", sa.Text(), nullable=False),
        sa.Column("final_text", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_divine_will_cycles_epoch_min")),
        sa.CheckConstraint("input_tokens >= 0", name=op.f("ck_divine_will_cycles_input_tokens_min")),
        sa.CheckConstraint("ordinal >= 1", name=op.f("ck_divine_will_cycles_ordinal_min")),
        sa.CheckConstraint("output_tokens >= 0", name=op.f("ck_divine_will_cycles_output_tokens_min")),
        sa.CheckConstraint("steps >= 0", name=op.f("ck_divine_will_cycles_steps_min")),
        sa.ForeignKeyConstraint(
            ["session_id"], ["divine_will_sessions.id"], name=op.f("fk_divine_will_cycles_session_id_divine_will_sessions"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_cycles")),
        sa.UniqueConstraint("session_id", "ordinal", name="uq_divine_will_cycles_ordinal"),
    )
    with op.batch_alter_table("divine_will_cycles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_cycles_session_id"), ["session_id"], unique=False)

    op.create_table(
        "divine_will_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "story",
                "chapter",
                "novel",
                "screenplay",
                "poem",
                "chronicle",
                "encyclopedia",
                "outline",
                "notes",
                "report",
                "plan",
                "forecast",
                "html_page",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("format", sa.Enum("markdown", "fountain", "html", name="format", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("status", sa.Enum("draft", "final", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column(
            "mode",
            sa.Enum(
                "command",
                "plan",
                "ask_lore",
                "creative_work",
                "mechanics_guide",
                "foresight",
                name="mode",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_cycle_id", sa.Integer(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("current_version >= 1", name=op.f("ck_divine_will_artifacts_current_version_min")),
        sa.ForeignKeyConstraint(
            ["created_cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_artifacts_created_cycle_id_divine_will_cycles"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_artifacts")),
    )
    op.create_table(
        "divine_will_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.Enum("image", "document", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("mime", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("media_key", sa.String(), nullable=False),
        sa.Column("markdown_key", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("stored", "converted", "indexed", "unreadable", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("seen_by_model", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("size >= 0", name=op.f("ck_divine_will_attachments_size_min")),
        sa.ForeignKeyConstraint(
            ["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_attachments_cycle_id_divine_will_cycles"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_attachments")),
    )
    with op.batch_alter_table("divine_will_attachments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_attachments_cycle_id"), ["cycle_id"], unique=False)

    op.create_table(
        "divine_will_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
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
                name="source",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
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

    op.create_table(
        "divine_will_confirmations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("action_id", sa.String(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Enum("destructive", "costly", "both", name="reason", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column(
            "status", sa.Enum("pending", "approved", "declined", "expired", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(
            ["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_confirmations_cycle_id_divine_will_cycles"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ledger_entry_id"], ["ledger_entries.id"], name=op.f("fk_divine_will_confirmations_ledger_entry_id_ledger_entries"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_confirmations")),
    )
    with op.batch_alter_table("divine_will_confirmations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_confirmations_cycle_id"), ["cycle_id"], unique=False)

    op.create_table(
        "divine_will_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "player",
                "thought",
                "text",
                "tool_call",
                "tool_result",
                "confirmation_request",
                "confirmation_reply",
                "notice",
                "retry",
                "error",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("handle", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("ordinal >= 1", name=op.f("ck_divine_will_events_ordinal_min")),
        sa.ForeignKeyConstraint(["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_events_cycle_id_divine_will_cycles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_events")),
        sa.UniqueConstraint("cycle_id", "ordinal", name="uq_divine_will_events_ordinal"),
    )
    with op.batch_alter_table("divine_will_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_events_cycle_id"), ["cycle_id"], unique=False)

    op.create_table(
        "divine_will_forecasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=True),
        sa.Column("epochs", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "done", "failed", "cancelled", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("eta_seconds", sa.Integer(), nullable=False),
        sa.Column("interventions", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("epochs >= 1", name=op.f("ck_divine_will_forecasts_epochs_min")),
        sa.CheckConstraint("eta_seconds >= 0", name=op.f("ck_divine_will_forecasts_eta_seconds_min")),
        sa.ForeignKeyConstraint(
            ["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_forecasts_cycle_id_divine_will_cycles"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_forecasts")),
    )
    with op.batch_alter_table("divine_will_forecasts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_forecasts_cycle_id"), ["cycle_id"], unique=False)

    op.create_table(
        "divine_will_handles",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("query", sa.JSON(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("total >= 0", name=op.f("ck_divine_will_handles_total_min")),
        sa.ForeignKeyConstraint(["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_handles_cycle_id_divine_will_cycles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_divine_will_handles")),
    )
    with op.batch_alter_table("divine_will_handles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_handles_cycle_id"), ["cycle_id"], unique=False)

    op.create_table(
        "divine_will_artifact_nodes",
        sa.Column("artifact_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["divine_will_artifacts.id"], name=op.f("fk_divine_will_artifact_nodes_artifact_id_divine_will_artifacts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_divine_will_artifact_nodes_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id", "node_id", name=op.f("pk_divine_will_artifact_nodes")),
    )
    with op.batch_alter_table("divine_will_artifact_nodes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_artifact_nodes_node_id"), ["node_id"], unique=False)

    op.create_table(
        "divine_will_artifact_versions",
        sa.Column("artifact_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("ck_divine_will_artifact_versions_version_min")),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["divine_will_artifacts.id"], name=op.f("fk_divine_will_artifact_versions_artifact_id_divine_will_artifacts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_artifact_versions_cycle_id_divine_will_cycles"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("artifact_id", "version", name=op.f("pk_divine_will_artifact_versions")),
    )
    op.create_table(
        "divine_will_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=True),
        sa.Column("artifact_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "approved", "running", "paused", "done", "failed", "abandoned", name="status", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["divine_will_artifacts.id"], name=op.f("fk_divine_will_plans_artifact_id_divine_will_artifacts"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["cycle_id"], ["divine_will_cycles.id"], name=op.f("fk_divine_will_plans_cycle_id_divine_will_cycles"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_will_plans")),
    )
    with op.batch_alter_table("divine_will_plans", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_will_plans_cycle_id"), ["cycle_id"], unique=False)

    op.create_table(
        "divine_will_plan_steps",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("action_id", sa.String(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.Column(
            "declared_impact",
            sa.Enum("safe", "costly", "destructive", name="declared_impact", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("estimated_essence", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "skipped", "failed", "undone", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("result_text", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.CheckConstraint("estimated_essence >= 0", name=op.f("ck_divine_will_plan_steps_estimated_essence_min")),
        sa.CheckConstraint("ordinal >= 1", name=op.f("ck_divine_will_plan_steps_ordinal_min")),
        sa.ForeignKeyConstraint(
            ["ledger_entry_id"], ["ledger_entries.id"], name=op.f("fk_divine_will_plan_steps_ledger_entry_id_ledger_entries"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["divine_will_plans.id"], name=op.f("fk_divine_will_plan_steps_plan_id_divine_will_plans"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", "ordinal", name=op.f("pk_divine_will_plan_steps")),
    )


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind IN ('divine_will', 'divine_will_plan', 'divine_will_forecast', 'divine_will_index')")
    retype_jobs(NEW_JOB_KINDS, OLD_JOB_KINDS)
    op.drop_table("divine_will_plan_steps")
    with op.batch_alter_table("divine_will_plans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_plans_cycle_id"))

    op.drop_table("divine_will_plans")
    op.drop_table("divine_will_artifact_versions")
    with op.batch_alter_table("divine_will_artifact_nodes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_artifact_nodes_node_id"))

    op.drop_table("divine_will_artifact_nodes")
    with op.batch_alter_table("divine_will_handles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_handles_cycle_id"))

    op.drop_table("divine_will_handles")
    with op.batch_alter_table("divine_will_forecasts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_forecasts_cycle_id"))

    op.drop_table("divine_will_forecasts")
    with op.batch_alter_table("divine_will_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_events_cycle_id"))

    op.drop_table("divine_will_events")
    with op.batch_alter_table("divine_will_confirmations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_confirmations_cycle_id"))

    op.drop_table("divine_will_confirmations")
    with op.batch_alter_table("divine_will_chunks", schema=None) as batch_op:
        batch_op.drop_index("ix_divine_will_chunks_source")
        batch_op.drop_index(batch_op.f("ix_divine_will_chunks_node_id"))
        batch_op.drop_index(batch_op.f("ix_divine_will_chunks_cycle_id"))

    op.drop_table("divine_will_chunks")
    with op.batch_alter_table("divine_will_attachments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_attachments_cycle_id"))

    op.drop_table("divine_will_attachments")
    op.drop_table("divine_will_artifacts")
    with op.batch_alter_table("divine_will_cycles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_will_cycles_session_id"))

    op.drop_table("divine_will_cycles")
    op.drop_table("divine_will_sessions")
