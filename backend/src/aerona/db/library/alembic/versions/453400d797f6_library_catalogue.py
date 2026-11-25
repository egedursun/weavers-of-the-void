import sqlalchemy as sa
from alembic import op

import aerona.db.types

revision = "453400d797f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "library_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("universe_id", sa.String(length=12), nullable=False),
        sa.Column("universe_name", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.Text(), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_library_events")),
    )
    with op.batch_alter_table("library_events", schema=None) as batch_op:
        batch_op.create_index("ix_library_events_universe_id", ["universe_id"], unique=False)

    op.create_table(
        "universes",
        sa.Column("id", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("cover_path", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("active", "archived", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("opened_at", aerona.db.types.UtcDateTime(timezone=True), nullable=True),
        sa.Column("updated_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("population", sa.BigInteger(), nullable=False),
        sa.Column("sons", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("schema_revision", sa.String(length=120), server_default="", nullable=False),
        sa.Column("app_version", sa.String(length=120), server_default="", nullable=False),
        sa.Column(
            "origin",
            sa.Enum("created", "imported", "duplicated", "adopted", name="origin", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("origin_note", sa.Text(), server_default="", nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("media_prefix", sa.String(length=120), server_default="", nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_universes_epoch_min")),
        sa.CheckConstraint("population >= 0", name=op.f("ck_universes_population_min")),
        sa.CheckConstraint("size_bytes >= 0", name=op.f("ck_universes_size_bytes_min")),
        sa.CheckConstraint("sons >= 0", name=op.f("ck_universes_sons_min")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_universes")),
    )
    with op.batch_alter_table("universes", schema=None) as batch_op:
        batch_op.create_index("ix_universes_opened_at", ["opened_at"], unique=False)
        batch_op.create_index("ix_universes_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("universes", schema=None) as batch_op:
        batch_op.drop_index("ix_universes_status")
        batch_op.drop_index("ix_universes_opened_at")

    op.drop_table("universes")
    with op.batch_alter_table("library_events", schema=None) as batch_op:
        batch_op.drop_index("ix_library_events_universe_id")

    op.drop_table("library_events")
