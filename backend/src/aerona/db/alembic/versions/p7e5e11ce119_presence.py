import sqlalchemy as sa
from alembic import op

revision = "p7e5e11ce119"
down_revision = "d1v1ne0w1118"
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
    "divine_will",
    "divine_will_plan",
    "divine_will_forecast",
    "divine_will_index",
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
    "presence",
)
OLD_MEMORY_KINDS = (
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
    "dreads",
    "formative",
    "stole_faithful",
    "aided_chosen",
    "memory_gap",
    "compelled_me",
    "healed_me",
    "sheltered_me",
    "abandoned_me",
    "survived_with",
    "apologised_to_me",
    "judged_me",
)
NEW_MEMORY_KINDS = (
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
    "dreads",
    "formative",
    "stole_faithful",
    "aided_chosen",
    "memory_gap",
    "compelled_me",
    "healed_me",
    "sheltered_me",
    "abandoned_me",
    "survived_with",
    "apologised_to_me",
    "judged_me",
    "audience",
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(table: str, column: str, before: tuple[str, ...], after: tuple[str, ...]) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum_of(before, column), type_=enum_of(after, column), existing_nullable=False)


def upgrade() -> None:
    retype("jobs", "kind", OLD_JOB_KINDS, NEW_JOB_KINDS)
    retype("memories", "kind", OLD_MEMORY_KINDS, NEW_MEMORY_KINDS)
    op.create_table(
        "presence_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "guise",
            sa.Enum("creator", "unnamed_power", "dream_voice", "ordinary", name="guise", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("record", sa.Enum("on_record", "off_record", name="record", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("status", sa.Enum("open", "closed", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("dead_when_summoned", sa.Boolean(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_presence_sessions_opened_epoch_min")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_presence_sessions_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_presence_sessions")),
    )
    with op.batch_alter_table("presence_sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_presence_sessions_node_id"), ["node_id"], unique=False)

    op.create_table(
        "presence_exchanges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("player_text", sa.Text(), nullable=False),
        sa.Column("reply_text", sa.Text(), nullable=False),
        sa.Column("remember_text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "done", "failed", "cancelled", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_presence_exchanges_epoch_min")),
        sa.CheckConstraint("input_tokens >= 0", name=op.f("ck_presence_exchanges_input_tokens_min")),
        sa.CheckConstraint("ordinal >= 1", name=op.f("ck_presence_exchanges_ordinal_min")),
        sa.CheckConstraint("output_tokens >= 0", name=op.f("ck_presence_exchanges_output_tokens_min")),
        sa.CheckConstraint("steps >= 0", name=op.f("ck_presence_exchanges_steps_min")),
        sa.ForeignKeyConstraint(["session_id"], ["presence_sessions.id"], name=op.f("fk_presence_exchanges_session_id_presence_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_presence_exchanges")),
        sa.UniqueConstraint("session_id", "ordinal", name="uq_presence_exchanges_ordinal"),
    )
    with op.batch_alter_table("presence_exchanges", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_presence_exchanges_session_id"), ["session_id"], unique=False)

    op.create_table(
        "presence_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("text", "thought", "tool_call", "tool_result", "error", "retry", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("ordinal >= 1", name=op.f("ck_presence_events_ordinal_min")),
        sa.ForeignKeyConstraint(["exchange_id"], ["presence_exchanges.id"], name=op.f("fk_presence_events_exchange_id_presence_exchanges"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_presence_events")),
        sa.UniqueConstraint("exchange_id", "ordinal", name="uq_presence_events_ordinal"),
    )
    with op.batch_alter_table("presence_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_presence_events_exchange_id"), ["exchange_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("presence_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_presence_events_exchange_id"))

    op.drop_table("presence_events")
    with op.batch_alter_table("presence_exchanges", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_presence_exchanges_session_id"))

    op.drop_table("presence_exchanges")
    with op.batch_alter_table("presence_sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_presence_sessions_node_id"))

    op.drop_table("presence_sessions")
    op.execute("DELETE FROM memories WHERE kind = 'audience'")
    retype("memories", "kind", NEW_MEMORY_KINDS, OLD_MEMORY_KINDS)
    op.execute("DELETE FROM jobs WHERE kind = 'presence'")
    retype("jobs", "kind", NEW_JOB_KINDS, OLD_JOB_KINDS)
