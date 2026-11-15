import sqlalchemy as sa
from alembic import op

revision = "c6bde0bacf5d"
down_revision = "a0be25fe960c"
branch_labels = None
depends_on = None


SPECIAL_KINDS = {
    "living": "living",
    "dead": "souls",
    "dream": "dreamt",
    "mirror": "mirrored",
    "gods_palace": "palace",
    "generation_ship": "voyage",
    "void_pocket": "phenomenon",
    "corpse_world": "corpse",
}
CASES = " ".join(f"WHEN '{world_type}' THEN '{kind}'" for world_type, kind in SPECIAL_KINDS.items())
KINDS_BY_TYPE = (
    "UPDATE world_type_profiles SET prehistory_kind = COALESCE("
    f"(SELECT CASE worlds.world_type {CASES} ELSE 'full' END FROM worlds WHERE worlds.id = world_type_profiles.world_id), 'full')"
)


def upgrade() -> None:
    op.create_table(
        "deep_time_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epochs", sa.Integer(), nullable=False),
        sa.Column("ran", sa.Integer(), nullable=False),
        sa.Column("from_epoch", sa.Integer(), nullable=False),
        sa.Column("to_epoch", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum("running", "done", "stopped", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("sons_simulated", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epochs >= 1", name=op.f("ck_deep_time_runs_epochs_min")),
        sa.CheckConstraint("from_epoch >= 0", name=op.f("ck_deep_time_runs_from_epoch_min")),
        sa.CheckConstraint("ran >= 0", name=op.f("ck_deep_time_runs_ran_min")),
        sa.CheckConstraint("sons_simulated >= 0", name=op.f("ck_deep_time_runs_sons_simulated_min")),
        sa.CheckConstraint("to_epoch >= 0", name=op.f("ck_deep_time_runs_to_epoch_min")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deep_time_runs")),
    )
    op.create_table(
        "prehistories",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "full",
                "living",
                "souls",
                "dreamt",
                "mirrored",
                "palace",
                "voyage",
                "phenomenon",
                "corpse",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "state", sa.Enum("planned", "running", "done", "aborted", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "source",
            sa.Enum("simulated", "backfilled", "mirrored", "dreamt", "derived", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("epochs", sa.Integer(), nullable=False),
        sa.Column("resolution", sa.Integer(), nullable=False),
        sa.Column("rounds_done", sa.Integer(), nullable=False),
        sa.Column("birth_epoch", sa.Integer(), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("slow_rounds", sa.Integer(), nullable=False),
        sa.Column("source_world_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("birth_epoch >= 0", name=op.f("ck_prehistories_birth_epoch_min")),
        sa.CheckConstraint("epochs BETWEEN 0 AND 1000", name=op.f("ck_prehistories_epochs_range")),
        sa.CheckConstraint("resolution BETWEEN 1 AND 20", name=op.f("ck_prehistories_resolution_range")),
        sa.CheckConstraint("rounds_done >= 0", name=op.f("ck_prehistories_rounds_done_min")),
        sa.CheckConstraint("seconds >= 0", name=op.f("ck_prehistories_seconds_min")),
        sa.CheckConstraint("slow_rounds >= 0", name=op.f("ck_prehistories_slow_rounds_min")),
        sa.ForeignKeyConstraint(["source_world_id"], ["worlds.id"], name=op.f("fk_prehistories_source_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_prehistories_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_prehistories")),
    )
    op.create_table(
        "deep_time_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_deep_time_events_epoch_min")),
        sa.CheckConstraint("magnitude BETWEEN 0 AND 100", name=op.f("ck_deep_time_events_magnitude_range")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_deep_time_events_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["deep_time_runs.id"], name=op.f("fk_deep_time_events_run_id_deep_time_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deep_time_events")),
    )
    with op.batch_alter_table("deep_time_events", schema=None) as batch_op:
        batch_op.create_index("ix_deep_time_events_run", ["run_id"], unique=False)

    op.create_table(
        "prehistory_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("simulated", "backfilled", "mirrored", "dreamt", "derived", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("source_world_id", sa.Integer(), nullable=True),
        sa.Column("mirrored", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("magnitude BETWEEN 0 AND 100", name=op.f("ck_prehistory_events_magnitude_range")),
        sa.CheckConstraint("round >= 0", name=op.f("ck_prehistory_events_round_min")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_prehistory_events_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_world_id"], ["worlds.id"], name=op.f("fk_prehistory_events_source_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_prehistory_events_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_prehistory_events_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prehistory_events")),
    )
    with op.batch_alter_table("prehistory_events", schema=None) as batch_op:
        batch_op.create_index("ix_prehistory_events_world", ["world_id"], unique=False)

    with op.batch_alter_table("world_type_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "prehistory_kind",
                sa.Enum(
                    "full",
                    "living",
                    "souls",
                    "dreamt",
                    "mirrored",
                    "palace",
                    "voyage",
                    "phenomenon",
                    "corpse",
                    name="prehistory_kind",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=False,
                server_default="full",
            )
        )
    op.execute(KINDS_BY_TYPE)


def downgrade() -> None:
    with op.batch_alter_table("world_type_profiles", schema=None) as batch_op:
        batch_op.drop_column("prehistory_kind")

    with op.batch_alter_table("prehistory_events", schema=None) as batch_op:
        batch_op.drop_index("ix_prehistory_events_world")

    op.drop_table("prehistory_events")
    with op.batch_alter_table("deep_time_events", schema=None) as batch_op:
        batch_op.drop_index("ix_deep_time_events_run")

    op.drop_table("deep_time_events")
    op.drop_table("prehistories")
    op.drop_table("deep_time_runs")
