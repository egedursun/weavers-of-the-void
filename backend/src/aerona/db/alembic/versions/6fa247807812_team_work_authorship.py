import sqlalchemy as sa
from alembic import op

revision = "6fa247807812"
down_revision = "p7e5e11ce119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "rebellion",
                "death",
                "birth",
                "prophecy",
                "apocalypse",
                "horror",
                "war",
                "prayer",
                "cosmos",
                "ascension",
                "disaster",
                "epoch",
                "achievement",
                "society",
                "reputation",
                "error",
                "note",
                "work",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("account_id", "category", name=op.f("pk_notification_preferences")),
    )

    op.create_table(
        "canon_proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column("touches", sa.JSON(), nullable=False),
        sa.Column("held_node_ids", sa.JSON(), nullable=False),
        sa.Column("author_account_id", sa.Integer(), nullable=True),
        sa.Column("author_name", sa.String(length=80), nullable=True),
        sa.Column("proposed_epoch", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", "withdrawn", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("decided_by_account_id", sa.Integer(), nullable=True),
        sa.Column("decided_by_name", sa.String(length=80), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("plan_ordinal", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("proposed_epoch >= 0", name=op.f("ck_canon_proposals_proposed_epoch_min")),
        sa.ForeignKeyConstraint(
            ["ledger_entry_id"], ["ledger_entries.id"], name=op.f("fk_canon_proposals_ledger_entry_id_ledger_entries"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["divine_will_plans.id"], name=op.f("fk_canon_proposals_plan_id_divine_will_plans"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canon_proposals")),
    )
    with op.batch_alter_table("canon_proposals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_canon_proposals_author_account_id"), ["author_account_id"], unique=False)
        batch_op.create_index("ix_canon_proposals_status", ["status", "id"], unique=False)

    op.create_table(
        "queued_acts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("lever", "undo", "rules", "divine_will", "presence", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("expected_revision", sa.Integer(), nullable=True),
        sa.Column("author_account_id", sa.Integer(), nullable=True),
        sa.Column("author_name", sa.String(length=80), nullable=True),
        sa.Column("speaker_node_id", sa.Integer(), nullable=True),
        sa.Column("presence_session_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("plan_ordinal", sa.Integer(), nullable=True),
        sa.Column("queued_epoch", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "applied", "proposed", "failed", "cancelled", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("cancelled_by_account_id", sa.Integer(), nullable=True),
        sa.Column("cancelled_by_name", sa.String(length=80), nullable=True),
        sa.Column("conflict", sa.JSON(), nullable=False),
        sa.Column("proposal_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("queued_epoch >= 0", name=op.f("ck_queued_acts_queued_epoch_min")),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"], name=op.f("fk_queued_acts_ledger_entry_id_ledger_entries"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["divine_will_plans.id"], name=op.f("fk_queued_acts_plan_id_divine_will_plans"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["presence_session_id"], ["presence_sessions.id"], name=op.f("fk_queued_acts_presence_session_id_presence_sessions"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["speaker_node_id"], ["nodes.id"], name=op.f("fk_queued_acts_speaker_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["canon_proposals.id"], name=op.f("fk_queued_acts_proposal_id_canon_proposals"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queued_acts")),
    )
    with op.batch_alter_table("queued_acts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_queued_acts_author_account_id"), ["author_account_id"], unique=False)
        batch_op.create_index("ix_queued_acts_status", ["status", "id"], unique=False)

    op.create_table(
        "notification_reads",
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["notifications.id"], name=op.f("fk_notification_reads_notification_id_notifications"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("notification_id", "account_id", name=op.f("pk_notification_reads")),
    )
    with op.batch_alter_table("notification_reads", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_notification_reads_account_id"), ["account_id"], unique=False)

    with op.batch_alter_table("action_records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))

    with op.batch_alter_table("chronicle", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))

    with op.batch_alter_table("divine_will_artifacts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("shared", sa.Boolean(), server_default="0", nullable=False))

    with op.batch_alter_table("divine_will_forecasts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("shared", sa.Boolean(), server_default="0", nullable=False))

    with op.batch_alter_table("divine_will_plans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("shared", sa.Boolean(), server_default="0", nullable=False))

    with op.batch_alter_table("divine_will_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("shared", sa.Boolean(), server_default="0", nullable=False))

    with op.batch_alter_table("epoch_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("started_by_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("started_by_name", sa.String(length=80), nullable=True))

    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("undone_by_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("undone_by_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("recipient_account_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_notifications_recipient_account_id"), ["recipient_account_id"], unique=False)

    with op.batch_alter_table("presence_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("shared", sa.Boolean(), server_default="0", nullable=False))

    with op.batch_alter_table("state_changes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("map_notes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("author_name", sa.String(length=80), nullable=True))

    with op.batch_alter_table("entities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("note_author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("note_author_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_table("notification_preferences")
    with op.batch_alter_table("entities", schema=None) as batch_op:
        batch_op.drop_column("note_author_name")
        batch_op.drop_column("note_author_account_id")

    with op.batch_alter_table("map_notes", schema=None) as batch_op:
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("state_changes", schema=None) as batch_op:
        batch_op.drop_column("changed_at")
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("presence_sessions", schema=None) as batch_op:
        batch_op.drop_column("shared")
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notifications_recipient_account_id"))
        batch_op.drop_column("recipient_account_id")

    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")
        batch_op.drop_column("undone_by_name")
        batch_op.drop_column("undone_by_account_id")
        batch_op.drop_column("reason")

    with op.batch_alter_table("epoch_runs", schema=None) as batch_op:
        batch_op.drop_column("started_by_name")
        batch_op.drop_column("started_by_account_id")

    with op.batch_alter_table("divine_will_sessions", schema=None) as batch_op:
        batch_op.drop_column("shared")
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("divine_will_plans", schema=None) as batch_op:
        batch_op.drop_column("shared")
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("divine_will_forecasts", schema=None) as batch_op:
        batch_op.drop_column("shared")
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("divine_will_artifacts", schema=None) as batch_op:
        batch_op.drop_column("shared")
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("chronicle", schema=None) as batch_op:
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")

    with op.batch_alter_table("action_records", schema=None) as batch_op:
        batch_op.drop_column("author_name")
        batch_op.drop_column("author_account_id")
        batch_op.drop_column("reason")

    with op.batch_alter_table("notification_reads", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notification_reads_account_id"))

    op.drop_table("notification_reads")
    with op.batch_alter_table("queued_acts", schema=None) as batch_op:
        batch_op.drop_index("ix_queued_acts_status")
        batch_op.drop_index(batch_op.f("ix_queued_acts_author_account_id"))

    op.drop_table("queued_acts")
    with op.batch_alter_table("canon_proposals", schema=None) as batch_op:
        batch_op.drop_index("ix_canon_proposals_status")
        batch_op.drop_index(batch_op.f("ix_canon_proposals_author_account_id"))

    op.drop_table("canon_proposals")
