import sqlalchemy as sa
from alembic import op

import aerona.db.types

revision = "2fbe54b84142"
down_revision = "453400d797f6"
branch_labels = None
depends_on = None


OLD_KINDS = (
    "created",
    "adopted",
    "opened",
    "renamed",
    "edited",
    "exported",
    "imported",
    "duplicated",
    "archived",
    "restored",
    "deleted",
    "recovered",
    "purged",
)
ADDED_KINDS = (
    "moved",
    "account_created",
    "password_reset",
    "account_deactivated",
    "account_reactivated",
    "account_deleted",
    "workspace_created",
    "workspace_renamed",
    "workspace_deleted",
    "member_added",
    "member_role_changed",
    "member_removed",
    "access_changed",
    "canon_approval_changed",
)


def kinds(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="kind", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Enum("active", "deactivated", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("server_role", sa.Enum("owner", "admin", "member", name="server_role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "avatar_tone",
            sa.Enum(
                "gold", "verdigris", "info", "success", "warning", "danger", "muted", name="avatar_tone", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("last_sign_in_at", aerona.db.types.UtcDateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", aerona.db.types.UtcDateTime(timezone=True), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", aerona.db.types.UtcDateTime(timezone=True), nullable=True),
        sa.CheckConstraint("failed_attempts >= 0", name=op.f("ck_accounts_failed_attempts_min")),
        sa.ForeignKeyConstraint(["created_by"], ["accounts.id"], name=op.f("fk_accounts_created_by_accounts"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("email", name="uq_accounts_email"),
        sa.UniqueConstraint("username", name="uq_accounts_username"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=120), nullable=False),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", aerona.db.types.UtcDateTime(timezone=True), nullable=False),
        sa.Column("expires_at", aerona.db.types.UtcDateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=300), server_default="", nullable=False),
        sa.Column("address", sa.String(length=64), server_default="", nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_sessions_account_id_accounts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sessions_account_id"), ["account_id"], unique=False)

    op.create_table(
        "universe_overrides",
        sa.Column("universe_id", sa.String(length=12), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("admin", "editor", "viewer", "none", name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("set_by", sa.Integer(), nullable=True),
        sa.Column("set_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_universe_overrides_account_id_accounts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_by"], ["accounts.id"], name=op.f("fk_universe_overrides_set_by_accounts"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("universe_id", "account_id", name=op.f("pk_universe_overrides")),
    )
    with op.batch_alter_table("universe_overrides", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_universe_overrides_account_id"), ["account_id"], unique=False)

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.Enum("personal", "team", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("owner_account_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["accounts.id"], name=op.f("fk_workspaces_created_by_accounts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_account_id"], ["accounts.id"], name=op.f("fk_workspaces_owner_account_id_accounts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_workspaces_owner_account_id"), ["owner_account_id"], unique=False)

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("admin", "editor", "viewer", name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("added_by", sa.Integer(), nullable=True),
        sa.Column("added_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_workspace_members_account_id_accounts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["accounts.id"], name=op.f("fk_workspace_members_added_by_accounts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_workspace_members_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "account_id", name=op.f("pk_workspace_members")),
    )
    with op.batch_alter_table("workspace_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_workspace_members_account_id"), ["account_id"], unique=False)

    op.create_table(
        "universe_permissions",
        sa.Column("universe_id", sa.String(length=12), nullable=False),
        sa.Column("role", sa.Enum("editor", "viewer", name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "permission",
            sa.Enum(
                "view",
                "edit_world",
                "start_ages",
                "change_rules",
                "lock_canon",
                "alternative_histories",
                "undo_own",
                "undo_any",
                "generate_images",
                "export",
                "download_books",
                "divine_will_read",
                "presence_on_record",
                "manage_shelf",
                name="permission",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["universe_id"], ["universes.id"], name=op.f("fk_universe_permissions_universe_id_universes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("universe_id", "role", "permission", name=op.f("pk_universe_permissions")),
    )
    with op.batch_alter_table("library_events", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=kinds(OLD_KINDS), type_=kinds(OLD_KINDS + ADDED_KINDS), existing_nullable=False)
        batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("account_name", sa.String(length=80), server_default="", nullable=False))
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_library_events_account_id_accounts"), "accounts", ["account_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_library_events_workspace_id_workspaces"), "workspaces", ["workspace_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("universes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("legacy_author_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("legacy_author_name", sa.String(length=80), server_default="", nullable=False))
        batch_op.add_column(sa.Column("canon_approval", sa.Boolean(), server_default="0", nullable=False))
        batch_op.create_index(batch_op.f("ix_universes_workspace_id"), ["workspace_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_universes_workspace_id_workspaces"), "workspaces", ["workspace_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(
            batch_op.f("fk_universes_legacy_author_account_id_accounts"), "accounts", ["legacy_author_account_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("universes", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_universes_legacy_author_account_id_accounts"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_universes_workspace_id_workspaces"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_universes_workspace_id"))
        batch_op.drop_column("canon_approval")
        batch_op.drop_column("legacy_author_name")
        batch_op.drop_column("legacy_author_account_id")
        batch_op.drop_column("workspace_id")

    op.execute(sa.text("DELETE FROM library_events WHERE kind IN (" + ", ".join(f"'{kind}'" for kind in ADDED_KINDS) + ")"))
    with op.batch_alter_table("library_events", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=kinds(OLD_KINDS + ADDED_KINDS), type_=kinds(OLD_KINDS), existing_nullable=False)
        batch_op.drop_constraint(batch_op.f("fk_library_events_workspace_id_workspaces"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_library_events_account_id_accounts"), type_="foreignkey")
        batch_op.drop_column("workspace_id")
        batch_op.drop_column("account_name")
        batch_op.drop_column("account_id")

    op.drop_table("universe_permissions")
    with op.batch_alter_table("workspace_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workspace_members_account_id"))

    op.drop_table("workspace_members")
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workspaces_owner_account_id"))

    op.drop_table("workspaces")
    with op.batch_alter_table("universe_overrides", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_universe_overrides_account_id"))

    op.drop_table("universe_overrides")
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sessions_account_id"))

    op.drop_table("sessions")
    op.drop_table("accounts")
