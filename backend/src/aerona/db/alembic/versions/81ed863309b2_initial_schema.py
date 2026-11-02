import sqlalchemy as sa
from alembic import op

revision = "81ed863309b2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "achievements",
        sa.Column(
            "key",
            sa.Enum(
                "second_sky",
                "constellation",
                "prophecy_fulfilled",
                "return_from_death",
                "fathers_hand",
                "babel",
                "crowded_world",
                "first_prayer",
                "creators_cult",
                "interstellar_traveller",
                "saga_completed",
                "god_of_epochs",
                "ancient",
                "crowded_pantheon",
                "first_explorers",
                "sensed_world",
                "weapons_silent",
                name="key",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_achievements")),
    )
    op.create_table(
        "applied_fixups",
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_applied_fixups")),
    )
    op.create_table(
        "cosmos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rng_seed", sa.BigInteger(), nullable=False),
        sa.Column("lore_language", sa.Enum("english", "turkish", name="lore_language", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("seed_idea", sa.Text(), nullable=False),
        sa.Column("cosmology", sa.Text(), nullable=False),
        sa.Column("tone", sa.Text(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("epoch_start_year", sa.Integer(), nullable=False),
        sa.Column("doom_clock", sa.Integer(), nullable=False),
        sa.Column("doom_fraction", sa.Float(), nullable=False),
        sa.Column("fate_mode", sa.Enum("auto", "off", name="fate_mode", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("son_distribution", sa.Enum("auto", "manual", name="son_distribution", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("council_every_epochs", sa.Integer(), nullable=True),
        sa.Column("mortal_agents_per_epoch", sa.Integer(), nullable=True),
        sa.Column("mortal_agent_parallelism", sa.Integer(), nullable=True),
        sa.Column("fate_debt_epoch", sa.Integer(), nullable=True),
        sa.Column("alignment_until_epoch", sa.Integer(), nullable=True),
        sa.Column("map_version", sa.Integer(), nullable=False),
        sa.Column("primary_world_id", sa.Integer(), nullable=True),
        sa.Column("travel_resource", sa.JSON(), nullable=True),
        sa.Column("genesis_settings", sa.JSON(), nullable=True),
        sa.Column("notification_prefs", sa.JSON(), nullable=False),
        sa.Column("rules_snapshot", sa.JSON(), nullable=False),
        sa.Column("rules_snapshot_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("council_every_epochs IS NULL OR council_every_epochs >= 0", name=op.f("ck_cosmos_council_every_epochs_min")),
        sa.CheckConstraint("doom_clock >= 0", name=op.f("ck_cosmos_doom_clock_min")),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_cosmos_epoch_min")),
        sa.CheckConstraint("epoch_start_year >= 0", name=op.f("ck_cosmos_epoch_start_year_min")),
        sa.CheckConstraint("id = 1", name=op.f("ck_cosmos_singleton")),
        sa.CheckConstraint("map_version >= 1", name=op.f("ck_cosmos_map_version_min")),
        sa.CheckConstraint("mortal_agent_parallelism IS NULL OR mortal_agent_parallelism >= 1", name=op.f("ck_cosmos_mortal_agent_parallelism_min")),
        sa.CheckConstraint("mortal_agents_per_epoch IS NULL OR mortal_agents_per_epoch >= 0", name=op.f("ck_cosmos_mortal_agents_per_epoch_min")),
        sa.ForeignKeyConstraint(["primary_world_id"], ["worlds.id"], name=op.f("fk_cosmos_primary_world_id_worlds"), ondelete="SET NULL", use_alter=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cosmos")),
    )
    op.create_table(
        "councils",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("minutes", sa.JSON(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_councils")),
    )
    with op.batch_alter_table("councils", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_councils_epoch"), ["epoch"], unique=False)

    op.create_table(
        "creator_mood_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "axis", sa.Enum("contentment", "anger", "interest", "loneliness", name="axis", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("item", sa.String(length=120), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creator_mood_inputs")),
    )
    with op.batch_alter_table("creator_mood_inputs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_creator_mood_inputs_epoch"), ["epoch"], unique=False)

    op.create_table(
        "epoch_runs",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("started", sa.Boolean(), nullable=False),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("engine_notes", sa.JSON(), nullable=False),
        sa.Column("resumed", sa.Boolean(), nullable=False),
        sa.Column("engine_since_chronicle_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("phase BETWEEN 0 AND 5", name=op.f("ck_epoch_runs_phase_range")),
        sa.PrimaryKeyConstraint("epoch", name=op.f("pk_epoch_runs")),
    )
    op.create_table(
        "epoch_stats",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("epoch", name=op.f("pk_epoch_stats")),
    )
    op.create_table(
        "epoch_year_cursors",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("last_year", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("epoch", name=op.f("pk_epoch_year_cursors")),
    )
    op.create_table(
        "epochs",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("year_start", sa.Integer(), nullable=True),
        sa.Column("year_end", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chronicler_name", sa.String(length=200), nullable=True),
        sa.Column("chronicler_identity", sa.String(length=300), nullable=True),
        sa.Column("audit", sa.JSON(), nullable=True),
        sa.CheckConstraint("year_end IS NULL OR year_start IS NULL OR year_end >= year_start", name=op.f("ck_epochs_years_ordered")),
        sa.PrimaryKeyConstraint("epoch", name=op.f("pk_epochs")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("exclusive_group", sa.String(length=32), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("stage", sa.String(length=200), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_jobs_kind"), ["kind"], unique=False)
        batch_op.create_index(batch_op.f("ix_jobs_status"), ["status"], unique=False)

    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("entity", "son", "creator", "foreign_god", "world", "star", name="node_kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nodes")),
    )
    with op.batch_alter_table("nodes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_nodes_kind"), ["kind"], unique=False)
        batch_op.create_index("ix_nodes_kind_name", ["kind", "name"], unique=False)

    op.create_table(
        "rule_overrides",
        sa.Column("namespace", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("namespace", "key", name=op.f("pk_rule_overrides")),
    )
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "key",
            sa.Enum(
                "doom_far",
                "one_faith",
                "lost_star",
                "many_worlds",
                "long_peace",
                "cosmic_power",
                "loyal_pantheon",
                "new_horizons",
                name="key",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("running", "completed", "failed", "abandoned", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("start_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column("counter", sa.Integer(), nullable=False),
        sa.Column("baseline_entity_id", sa.Integer(), nullable=True),
        sa.Column("baseline_chronicle_id", sa.Integer(), nullable=True),
        sa.Column("baseline_count", sa.Integer(), nullable=True),
        sa.Column("baseline_rebel_ids", sa.JSON(), nullable=False),
        sa.Column("points_awarded", sa.Boolean(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.CheckConstraint("status = 'running' OR end_epoch IS NOT NULL", name=op.f("ck_scenarios_finished_has_epoch")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenarios")),
    )
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.create_index("ux_scenarios_running_key", ["key"], unique=True, sqlite_where=sa.text("status = 'running'"))

    op.create_table(
        "scores",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("epoch", name=op.f("pk_scores")),
    )
    op.create_table(
        "threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("open", "closed", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("closing_text", sa.Text(), nullable=True),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("status <> 'closed' OR closed_epoch IS NOT NULL", name=op.f("ck_threads_closed_has_epoch")),
        sa.CheckConstraint("progress >= 0", name=op.f("ck_threads_progress_min")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_threads")),
    )
    with op.batch_alter_table("threads", schema=None) as batch_op:
        batch_op.create_index("ix_threads_status", ["status"], unique=False)

    op.create_table(
        "agent_turns",
        sa.Column("agent_node_id", sa.Integer(), nullable=False),
        sa.Column("agent_kind", sa.Enum("son", "mortal", name="agent_kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("action_points_left", sa.Integer(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("action_points_left IS NULL OR action_points_left >= 0", name=op.f("ck_agent_turns_action_points_left_min")),
        sa.ForeignKeyConstraint(["agent_node_id"], ["nodes.id"], name=op.f("fk_agent_turns_agent_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("agent_node_id", name=op.f("pk_agent_turns")),
    )
    with op.batch_alter_table("agent_turns", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_agent_turns_epoch"), ["epoch"], unique=False)

    op.create_table(
        "creator",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("appearance", sa.Text(), nullable=True),
        sa.Column("temperament", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("essence", sa.Integer(), nullable=False),
        sa.Column("mood_contentment", sa.Integer(), nullable=False),
        sa.Column("mood_anger", sa.Integer(), nullable=False),
        sa.Column("mood_interest", sa.Integer(), nullable=False),
        sa.Column("mood_loneliness", sa.Integer(), nullable=False),
        sa.Column("mood_temperament", sa.Integer(), nullable=False),
        sa.Column("passions", sa.JSON(), nullable=False),
        sa.Column("passions_automatic", sa.Boolean(), nullable=False),
        sa.Column("depth", sa.JSON(), nullable=True),
        sa.Column("epic", sa.JSON(), nullable=True),
        sa.CheckConstraint("essence >= 0", name=op.f("ck_creator_essence_min")),
        sa.CheckConstraint("mood_anger BETWEEN 0 AND 100", name=op.f("ck_creator_mood_anger_range")),
        sa.CheckConstraint("mood_contentment BETWEEN 0 AND 100", name=op.f("ck_creator_mood_contentment_range")),
        sa.CheckConstraint("mood_interest BETWEEN 0 AND 100", name=op.f("ck_creator_mood_interest_range")),
        sa.CheckConstraint("mood_loneliness BETWEEN 0 AND 100", name=op.f("ck_creator_mood_loneliness_range")),
        sa.CheckConstraint("mood_temperament BETWEEN -100 AND 100", name=op.f("ck_creator_mood_temperament_range")),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_creator_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creator")),
    )
    op.create_table(
        "epoch_engine_phases",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "stage", sa.Enum("tick", "transition", "after_transition", name="stage", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("phase", sa.String(length=300), nullable=False),
        sa.Column("seconds", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["epoch"], ["epoch_runs.epoch"], name=op.f("fk_epoch_engine_phases_epoch_epoch_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("epoch", "stage", "phase", name=op.f("pk_epoch_engine_phases")),
    )
    op.create_table(
        "epoch_phase_timings",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("started_offset_seconds", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.CheckConstraint("phase BETWEEN 1 AND 5", name=op.f("ck_epoch_phase_timings_phase_range")),
        sa.ForeignKeyConstraint(["epoch"], ["epoch_runs.epoch"], name=op.f("fk_epoch_phase_timings_epoch_epoch_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("epoch", "phase", name=op.f("pk_epoch_phase_timings")),
    )
    op.create_table(
        "epoch_steps",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "step",
            sa.Enum(
                "completion",
                "backup",
                "distribution",
                "naming",
                "fate_judgment",
                "chronicle",
                "voices",
                "council",
                "epoch_words",
                "local_gods",
                "transition",
                "horizon_intuitions",
                "world_birth",
                "network_repair",
                "prune",
                "images",
                "localisation",
                "background",
                name="step",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", "skipped", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["epoch"], ["epoch_runs.epoch"], name=op.f("fk_epoch_steps_epoch_epoch_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("epoch", "step", name=op.f("pk_epoch_steps")),
    )
    op.create_table(
        "god_conflicts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("attacker_node_id", sa.Integer(), nullable=False),
        sa.Column("defender_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "outcome", sa.Enum("attacker_won", "defender_won", "draw", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("attacker_score", sa.Integer(), nullable=False),
        sa.Column("defender_score", sa.Integer(), nullable=False),
        sa.Column("duel", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("attacker_node_id <> defender_node_id", name=op.f("ck_god_conflicts_distinct_sides")),
        sa.ForeignKeyConstraint(["attacker_node_id"], ["nodes.id"], name=op.f("fk_god_conflicts_attacker_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["defender_node_id"], ["nodes.id"], name=op.f("fk_god_conflicts_defender_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_god_conflicts")),
    )
    with op.batch_alter_table("god_conflicts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_god_conflicts_attacker_node_id"), ["attacker_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_god_conflicts_defender_node_id"), ["defender_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_god_conflicts_epoch"), ["epoch"], unique=False)

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=200), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime", sa.Enum("image/png", "image/jpeg", "image/webp", name="mime", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("origin", sa.Enum("generated", "uploaded", name="origin", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("caption", sa.String(length=200), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("is_cover", sa.Boolean(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("file_name NOT LIKE '%/%' AND file_name NOT LIKE '%..%' AND file_name NOT LIKE '.%'", name=op.f("ck_images_safe_file_name")),
        sa.CheckConstraint("object_key LIKE 'originals/%' AND object_key NOT LIKE '%..%'", name=op.f("ck_images_original_object_key")),
        sa.CheckConstraint("length(sha256) = 64", name=op.f("ck_images_sha256_length")),
        sa.CheckConstraint("size_bytes >= 0", name=op.f("ck_images_size_bytes_min")),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_images_target_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_images")),
        sa.UniqueConstraint("file_name", name=op.f("uq_images_file_name")),
    )
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.create_index("ix_images_object_key", ["object_key"], unique=False)
        batch_op.create_index("ix_images_sha256", ["sha256"], unique=False)
        batch_op.create_index("ix_images_target", ["target_node_id", "is_cover", "id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "actor_kind",
            sa.Enum(
                "creator", "son", "mortal", "foreign_god", "fate", "engine", "system", name="actor_kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("actor_node_id", sa.Integer(), nullable=True),
        sa.Column("actor_name", sa.String(length=200), nullable=False),
        sa.Column("tool", sa.String(length=120), nullable=False),
        sa.Column(
            "action_kind",
            sa.Enum(
                "create_entity",
                "revelation",
                "summon_son",
                "bear_child",
                "command",
                "absolute_command",
                "bless_essence",
                "bless_hp",
                "bless_stat",
                "bless_existence",
                "add_star",
                "ascend",
                "lightning",
                "chain",
                "exile_son",
                "suppress_rebellion",
                "suppress_failed",
                "forgive",
                "answer_prayer",
                "chat",
                "resurrect_son",
                "kill_son",
                "take_life",
                "resurrect_mortal",
                "deify",
                "demote",
                "grant_power",
                "choose_prophet",
                "manifestation",
                "lineage_curse",
                "lift_lineage_curse",
                "convert",
                "wrath",
                "world_wrath",
                "drain_essence",
                "devour",
                "harvest_community",
                "kill_foreign_god",
                "canon_restore",
                "canon_strike",
                "edit_record",
                "edit_creator",
                "merge_records",
                "archive_record",
                "create_world",
                "birth_world",
                "forget_world",
                "remember_world",
                "exile_entity",
                "pardon",
                "ignite_star",
                "hang_star",
                "extinguish_star",
                "rekindle_star",
                "seal_gate",
                "sever_route",
                "stitch_route",
                "reveal_route",
                "recall_journey",
                "cleanse_leak",
                "sky_event",
                "spirit_cloak",
                "legendary_quest",
                "miracle",
                "disaster",
                "teach_knowledge",
                "advance_knowledge",
                "set_knowledge_level",
                "assign_mechanics",
                "syncretize_faith",
                "birth_creole",
                "curse",
                "dream",
                "influence",
                "declare_chosen",
                "incite_war",
                "transform",
                "destroy",
                "covenant",
                "change_anchor",
                "challenge",
                "speak_to_sibling",
                "weave_bond",
                "pray_to_creator",
                "harvest_resource",
                "gift",
                "holy_world",
                "interworld_treaty",
                "foreign_god_war",
                "open_cosmic_bed",
                "stitch_leak",
                "outer_bargain",
                "rebel",
                "convene_council",
                "awaken_peoples",
                "set_passions",
                "push_reputation",
                "found_language",
                "coin_words",
                "produce",
                "build",
                "create_culture",
                "discover_resource",
                "claim",
                "found_settlement",
                "establish_trade",
                "declare_war",
                "worship",
                "develop_knowledge",
                "learn",
                "diplomacy",
                "adventure",
                "discover_route",
                "explore_land",
                "resurrection_rite",
                "build_ship",
                "set_out",
                "tame",
                "weave_chimera",
                "bind_spirit",
                "search_ruins",
                "sabotage",
                "preach",
                "defy_god",
                "deny_god",
                "prophesy",
                "escape",
                "pay_ransom",
                "rescue_captive",
                "raise_army",
                "appoint_commander",
                "build_spy_network",
                "barter",
                "lend",
                "repay",
                "adopt",
                "network_repair",
                "ledger_undo",
                "sibling_scheme",
                "scatter_bones",
                "move_to_world",
                "foreign_god_talk",
                "write_plan",
                "abandon_settlement",
                "apocalypse",
                "awaken_species",
                "betrayal",
                "bless_army",
                "cosmic_archive",
                "cosmic_plague",
                "creator_sign",
                "crown_ruler",
                "cultural_contact",
                "designate_heir",
                "disband_army",
                "dissolve_faction",
                "end_blood_feud",
                "epoch_star",
                "ethnogenesis",
                "evaluate_goals",
                "force_battle",
                "foreign_god_land",
                "forget_legend",
                "forgive_debt",
                "forgive_tribute",
                "found_faction",
                "found_market",
                "fulfil_prophecy",
                "golden_age",
                "grant_independence",
                "grant_victory",
                "horror_event",
                "hunt",
                "impose_tribute",
                "incite_uprising",
                "introduce_species",
                "lay_spirit_to_rest",
                "megafauna_trail",
                "mint_coin",
                "mirror_birth",
                "mutate_species",
                "order_exodus",
                "order_feeding",
                "outer_cult",
                "planet_act",
                "pour_essence",
                "raise_hero",
                "raise_notable",
                "recall_hero",
                "reclaim_colony",
                "regenerate_map",
                "resettle_ruin",
                "reveal_previous_creation",
                "revive_legend",
                "set_doom_clock",
                "set_immortal",
                "set_route_danger",
                "set_sanity",
                "set_son_relation",
                "set_tier",
                "shape_society",
                "shelter_from_ruin",
                "soul_descent",
                "soul_harvest",
                "spare_prey",
                "spawn_pirates",
                "split_people",
                "summon_outer_being",
                "time_echo",
                "train_apprentice",
                "wake_foreign_god",
                "edit_language",
                "regenerate_signature",
                "add_epoch_words",
                "discard_intuition",
                "rejudge_fate",
                "retry_fate",
                "override_verdict",
                "retry_voices",
                "audit_chronicle",
                "retry_births",
                "edit_historian_view",
                "delete_historian_view",
                "maintenance",
                "dissolve_community",
                "raze_structure",
                "write_fate",
                "commemorate",
                "revive_world",
                "appoint_guardian",
                "set_abundance",
                "seed_place",
                "declare_pilgrimage_site",
                "order_end",
                "other",
                name="action_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("input_summary", sa.String(length=220), nullable=True),
        sa.Column("undone", sa.Boolean(), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied", sa.JSON(), nullable=False),
        sa.Column("conflicts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["actor_node_id"], ["nodes.id"], name=op.f("fk_ledger_entries_actor_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
    )
    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.create_index("ix_ledger_entries_actor", ["actor_node_id", "epoch"], unique=False)
        batch_op.create_index("ix_ledger_entries_epoch", ["epoch", "id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("sender_node_id", sa.Integer(), nullable=False),
        sa.Column("recipient_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "intent",
            sa.Enum(
                "friendship",
                "alliance",
                "love",
                "threat",
                "mockery",
                "warning",
                "bargain",
                "prayer",
                "answer",
                "chat",
                "dream",
                "command",
                name="intent",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "request",
            sa.Enum(
                "essence",
                "blessing",
                "permission",
                "vengeance",
                "forgiveness",
                "none",
                "wish",
                name="request",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("wish", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("answered", sa.Boolean(), nullable=False),
        sa.Column("answered_epoch", sa.Integer(), nullable=True),
        sa.Column("answer_essence", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("request IS NULL OR intent = 'prayer'", name=op.f("ck_messages_request_on_prayer")),
        sa.ForeignKeyConstraint(["recipient_node_id"], ["nodes.id"], name=op.f("fk_messages_recipient_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_node_id"], ["nodes.id"], name=op.f("fk_messages_sender_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.create_index("ix_messages_recipient", ["recipient_node_id", "answered"], unique=False)
        batch_op.create_index("ix_messages_sender", ["sender_node_id", "epoch"], unique=False)

    op.create_table(
        "name_registry",
        sa.Column("normalized", sa.String(length=200), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("display", sa.String(length=200), nullable=False),
        sa.Column("single_word", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_name_registry_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("normalized", name=op.f("pk_name_registry")),
        sa.UniqueConstraint("node_id", name=op.f("uq_name_registry_node_id")),
    )
    op.create_table(
        "stars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "star_type",
            sa.Enum(
                "yellow_dwarf",
                "red_giant",
                "blue_giant",
                "binary",
                "white_dwarf",
                "dead_star",
                "black_sun",
                "broken_star",
                "pulsar",
                "star_remnant",
                "reborn_star",
                name="star_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("brightness", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("depth", sa.JSON(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("brightness BETWEEN 0 AND 100", name=op.f("ck_stars_brightness_range")),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_stars_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stars")),
    )
    op.create_table(
        "turn_counters",
        sa.Column("agent_node_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "counter",
            sa.Enum(
                "sibling_messages",
                "narrative_bonds",
                "prayers",
                "free_living_creation",
                "free_land_creation",
                "anchor_chosen",
                "words_coined",
                "gifts",
                "holy_world",
                "leak_stitched",
                "take_life",
                "intrigue",
                "outer_bargain",
                "harvests",
                "discoveries",
                "claims",
                "worship_changes",
                "learning",
                "prophecies",
                "commander_appointments",
                "adoptions",
                "explorations",
                "repeated_creations",
                "resurrection_rites",
                "languages_founded",
                "cultures_created",
                "land_rewards",
                name="counter",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value >= 0", name=op.f("ck_turn_counters_value_min")),
        sa.ForeignKeyConstraint(["agent_node_id"], ["nodes.id"], name=op.f("fk_turn_counters_agent_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("agent_node_id", "epoch", "counter", name=op.f("pk_turn_counters")),
    )
    op.create_table(
        "action_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "actor_kind",
            sa.Enum(
                "creator", "son", "mortal", "foreign_god", "fate", "engine", "system", name="actor_kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("actor_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "create_entity",
                "revelation",
                "summon_son",
                "bear_child",
                "command",
                "absolute_command",
                "bless_essence",
                "bless_hp",
                "bless_stat",
                "bless_existence",
                "add_star",
                "ascend",
                "lightning",
                "chain",
                "exile_son",
                "suppress_rebellion",
                "suppress_failed",
                "forgive",
                "answer_prayer",
                "chat",
                "resurrect_son",
                "kill_son",
                "take_life",
                "resurrect_mortal",
                "deify",
                "demote",
                "grant_power",
                "choose_prophet",
                "manifestation",
                "lineage_curse",
                "lift_lineage_curse",
                "convert",
                "wrath",
                "world_wrath",
                "drain_essence",
                "devour",
                "harvest_community",
                "kill_foreign_god",
                "canon_restore",
                "canon_strike",
                "edit_record",
                "edit_creator",
                "merge_records",
                "archive_record",
                "create_world",
                "birth_world",
                "forget_world",
                "remember_world",
                "exile_entity",
                "pardon",
                "ignite_star",
                "hang_star",
                "extinguish_star",
                "rekindle_star",
                "seal_gate",
                "sever_route",
                "stitch_route",
                "reveal_route",
                "recall_journey",
                "cleanse_leak",
                "sky_event",
                "spirit_cloak",
                "legendary_quest",
                "miracle",
                "disaster",
                "teach_knowledge",
                "advance_knowledge",
                "set_knowledge_level",
                "assign_mechanics",
                "syncretize_faith",
                "birth_creole",
                "curse",
                "dream",
                "influence",
                "declare_chosen",
                "incite_war",
                "transform",
                "destroy",
                "covenant",
                "change_anchor",
                "challenge",
                "speak_to_sibling",
                "weave_bond",
                "pray_to_creator",
                "harvest_resource",
                "gift",
                "holy_world",
                "interworld_treaty",
                "foreign_god_war",
                "open_cosmic_bed",
                "stitch_leak",
                "outer_bargain",
                "rebel",
                "convene_council",
                "awaken_peoples",
                "set_passions",
                "push_reputation",
                "found_language",
                "coin_words",
                "produce",
                "build",
                "create_culture",
                "discover_resource",
                "claim",
                "found_settlement",
                "establish_trade",
                "declare_war",
                "worship",
                "develop_knowledge",
                "learn",
                "diplomacy",
                "adventure",
                "discover_route",
                "explore_land",
                "resurrection_rite",
                "build_ship",
                "set_out",
                "tame",
                "weave_chimera",
                "bind_spirit",
                "search_ruins",
                "sabotage",
                "preach",
                "defy_god",
                "deny_god",
                "prophesy",
                "escape",
                "pay_ransom",
                "rescue_captive",
                "raise_army",
                "appoint_commander",
                "build_spy_network",
                "barter",
                "lend",
                "repay",
                "adopt",
                "network_repair",
                "ledger_undo",
                "sibling_scheme",
                "scatter_bones",
                "move_to_world",
                "foreign_god_talk",
                "write_plan",
                "abandon_settlement",
                "apocalypse",
                "awaken_species",
                "betrayal",
                "bless_army",
                "cosmic_archive",
                "cosmic_plague",
                "creator_sign",
                "crown_ruler",
                "cultural_contact",
                "designate_heir",
                "disband_army",
                "dissolve_faction",
                "end_blood_feud",
                "epoch_star",
                "ethnogenesis",
                "evaluate_goals",
                "force_battle",
                "foreign_god_land",
                "forget_legend",
                "forgive_debt",
                "forgive_tribute",
                "found_faction",
                "found_market",
                "fulfil_prophecy",
                "golden_age",
                "grant_independence",
                "grant_victory",
                "horror_event",
                "hunt",
                "impose_tribute",
                "incite_uprising",
                "introduce_species",
                "lay_spirit_to_rest",
                "megafauna_trail",
                "mint_coin",
                "mirror_birth",
                "mutate_species",
                "order_exodus",
                "order_feeding",
                "outer_cult",
                "planet_act",
                "pour_essence",
                "raise_hero",
                "raise_notable",
                "recall_hero",
                "reclaim_colony",
                "regenerate_map",
                "resettle_ruin",
                "reveal_previous_creation",
                "revive_legend",
                "set_doom_clock",
                "set_immortal",
                "set_route_danger",
                "set_sanity",
                "set_son_relation",
                "set_tier",
                "shape_society",
                "shelter_from_ruin",
                "soul_descent",
                "soul_harvest",
                "spare_prey",
                "spawn_pirates",
                "split_people",
                "summon_outer_being",
                "time_echo",
                "train_apprentice",
                "wake_foreign_god",
                "edit_language",
                "regenerate_signature",
                "add_epoch_words",
                "discard_intuition",
                "rejudge_fate",
                "retry_fate",
                "override_verdict",
                "retry_voices",
                "audit_chronicle",
                "retry_births",
                "edit_historian_view",
                "delete_historian_view",
                "maintenance",
                "dissolve_community",
                "raze_structure",
                "write_fate",
                "commemorate",
                "revive_world",
                "appoint_guardian",
                "set_abundance",
                "seed_place",
                "declare_pilgrimage_site",
                "order_end",
                "other",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("essence_spent", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=220), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["actor_node_id"], ["nodes.id"], name=op.f("fk_action_records_actor_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"], name=op.f("fk_action_records_ledger_entry_id_ledger_entries"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_action_records_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_records")),
    )
    with op.batch_alter_table("action_records", schema=None) as batch_op:
        batch_op.create_index("ix_action_records_actor_epoch", ["actor_node_id", "epoch"], unique=False)
        batch_op.create_index("ix_action_records_kind_epoch", ["kind", "epoch"], unique=False)
        batch_op.create_index("ix_action_records_target", ["target_node_id", "epoch"], unique=False)

    op.create_table(
        "ledger_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("table_name", sa.String(length=120), nullable=False),
        sa.Column("row_key", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.Enum("insert", "update", "delete", name="operation", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["entry_id"], ["ledger_entries.id"], name=op.f("fk_ledger_changes_entry_id_ledger_entries"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_changes")),
    )
    with op.batch_alter_table("ledger_changes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ledger_changes_entry_id"), ["entry_id"], unique=False)
        batch_op.create_index("ix_ledger_changes_row", ["table_name", "row_key"], unique=False)

    op.create_table(
        "worlds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "world_type",
            sa.Enum(
                "ordinary",
                "ocean",
                "sand",
                "ice",
                "lava",
                "crystal",
                "living",
                "dead",
                "dream",
                "mirror",
                "gas",
                "ringed",
                "asteroid_belt",
                "tidally_locked",
                "void_pocket",
                "gods_palace",
                "generation_ship",
                "corpse_world",
                name="world_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("star_id", sa.Integer(), nullable=True),
        sa.Column("parent_world_id", sa.Integer(), nullable=True),
        sa.Column("orbit", sa.Float(), nullable=False),
        sa.Column("gravity", sa.Enum("low", "normal", "high", name="gravity", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "atmosphere",
            sa.Enum("none", "thin", "normal", "dense", "toxic", name="atmosphere", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("time_factor", sa.Float(), nullable=False),
        sa.Column("terrain_seed", sa.String(length=120), nullable=False),
        sa.Column("terrain_sea", sa.Float(), nullable=False),
        sa.Column("terrain_mountains", sa.Float(), nullable=False),
        sa.Column("terrain_humidity", sa.Float(), nullable=False),
        sa.Column(
            "discovery",
            sa.Enum("known", "legend", "unknown", "forgotten", name="discovery", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("danger", sa.Integer(), nullable=False),
        sa.Column("leakage", sa.Integer(), nullable=False),
        sa.Column("cosmology", sa.Text(), nullable=True),
        sa.Column("phonology", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("depth", sa.JSON(), nullable=True),
        sa.Column("creator_son_id", sa.Integer(), nullable=True),
        sa.Column("patron_son_id", sa.Integer(), nullable=True),
        sa.Column("patron_automatic", sa.Boolean(), nullable=False),
        sa.Column("epoch_star_entity_id", sa.Integer(), nullable=True),
        sa.Column("mirror_twin_id", sa.Integer(), nullable=True),
        sa.Column("mortal_agents", sa.Integer(), nullable=True),
        sa.Column(
            "climate_era",
            sa.Enum("temperate", "drought", "rain", "ice_age", "scorching", name="climate_era", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("climate_epochs_left", sa.Integer(), nullable=True),
        sa.Column("climate_since_epoch", sa.Integer(), nullable=True),
        sa.Column("climate_imposed_by_son_id", sa.Integer(), nullable=True),
        sa.Column("consciousness_closed", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("climate_epochs_left IS NULL OR climate_epochs_left >= 0", name=op.f("ck_worlds_climate_epochs_left_min")),
        sa.CheckConstraint("danger BETWEEN 0 AND 100", name=op.f("ck_worlds_danger_range")),
        sa.CheckConstraint("leakage BETWEEN 0 AND 100", name=op.f("ck_worlds_leakage_range")),
        sa.CheckConstraint("mirror_twin_id IS NULL OR mirror_twin_id <> id", name=op.f("ck_worlds_not_own_twin")),
        sa.CheckConstraint("mortal_agents IS NULL OR mortal_agents >= 0", name=op.f("ck_worlds_mortal_agents_min")),
        sa.CheckConstraint("orbit > 0", name=op.f("ck_worlds_orbit_positive")),
        sa.CheckConstraint("parent_world_id IS NULL OR parent_world_id <> id", name=op.f("ck_worlds_not_own_moon")),
        sa.CheckConstraint("terrain_humidity BETWEEN -1 AND 1", name=op.f("ck_worlds_terrain_humidity_range")),
        sa.CheckConstraint("terrain_mountains >= 0", name=op.f("ck_worlds_terrain_mountains_min")),
        sa.CheckConstraint("terrain_sea BETWEEN 0 AND 1", name=op.f("ck_worlds_terrain_sea_range")),
        sa.CheckConstraint("time_factor > 0", name=op.f("ck_worlds_time_factor_positive")),
        sa.ForeignKeyConstraint(
            ["climate_imposed_by_son_id"], ["sons.id"], name=op.f("fk_worlds_climate_imposed_by_son_id_sons"), ondelete="SET NULL", use_alter=True
        ),
        sa.ForeignKeyConstraint(["creator_son_id"], ["sons.id"], name=op.f("fk_worlds_creator_son_id_sons"), ondelete="SET NULL", use_alter=True),
        sa.ForeignKeyConstraint(
            ["epoch_star_entity_id"], ["entities.id"], name=op.f("fk_worlds_epoch_star_entity_id_entities"), ondelete="SET NULL", use_alter=True
        ),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_worlds_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mirror_twin_id"], ["worlds.id"], name=op.f("fk_worlds_mirror_twin_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_world_id"], ["worlds.id"], name=op.f("fk_worlds_parent_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patron_son_id"], ["sons.id"], name=op.f("fk_worlds_patron_son_id_sons"), ondelete="SET NULL", use_alter=True),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_worlds_star_id_stars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worlds")),
    )
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_worlds_creator_son_id"), ["creator_son_id"], unique=False)
        batch_op.create_index("ix_worlds_discovery", ["discovery"], unique=False)
        batch_op.create_index(batch_op.f("ix_worlds_parent_world_id"), ["parent_world_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_worlds_patron_son_id"), ["patron_son_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_worlds_star_id"), ["star_id"], unique=False)

    op.create_table(
        "deferred_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("world_birth", "council", "sensed_world", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "status", sa.Enum("pending", "running", "done", "failed", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("requested_by_node_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result_world_id", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_node_id"], ["nodes.id"], name=op.f("fk_deferred_steps_requested_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["result_world_id"], ["worlds.id"], name=op.f("fk_deferred_steps_result_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deferred_steps")),
    )
    with op.batch_alter_table("deferred_steps", schema=None) as batch_op:
        batch_op.create_index("ix_deferred_steps_status", ["status", "epoch"], unique=False)

    op.create_table(
        "epoch_world_narratives",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_epoch_world_narratives_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("epoch", "world_id", name=op.f("pk_epoch_world_narratives")),
    )
    op.create_table(
        "foreign_gods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "domain_primary",
            sa.Enum(
                "sea",
                "fire",
                "earth",
                "sky",
                "storm",
                "death",
                "life",
                "dream",
                "time",
                "light",
                "shadow",
                "war",
                "craft",
                "knowledge",
                "love",
                "trickery",
                "hunt",
                "plants",
                "bone",
                "blood",
                "sound",
                "stone",
                "ice",
                "madness",
                "trade",
                "road",
                "plague",
                "harvest",
                "moon",
                "sun",
                "star",
                "lies",
                "oath",
                "memory",
                "hunger",
                "glass",
                "salt",
                "ash",
                "border",
                "sleep",
                name="domain_primary",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "domain_secondary",
            sa.Enum(
                "sea",
                "fire",
                "earth",
                "sky",
                "storm",
                "death",
                "life",
                "dream",
                "time",
                "light",
                "shadow",
                "war",
                "craft",
                "knowledge",
                "love",
                "trickery",
                "hunt",
                "plants",
                "bone",
                "blood",
                "sound",
                "stone",
                "ice",
                "madness",
                "trade",
                "road",
                "plague",
                "harvest",
                "moon",
                "sun",
                "star",
                "lies",
                "oath",
                "memory",
                "hunger",
                "glass",
                "salt",
                "ash",
                "border",
                "sleep",
                name="domain_secondary",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("power", sa.Integer(), nullable=False),
        sa.Column("faith", sa.Integer(), nullable=False),
        sa.Column("stance", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum("awake", "asleep", "defeated", "dead", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("contacted", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("personality", sa.JSON(), nullable=True),
        sa.Column("existence_profile", sa.JSON(), nullable=True),
        sa.Column("depth", sa.JSON(), nullable=True),
        sa.Column("awakening_pressure", sa.Integer(), nullable=False),
        sa.Column("awakening_average", sa.Float(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("defeated_epoch", sa.Integer(), nullable=True),
        sa.Column("death_epoch", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("endurance", sa.Integer(), nullable=False),
        sa.Column("agility", sa.Integer(), nullable=False),
        sa.Column("wisdom", sa.Integer(), nullable=False),
        sa.Column("cunning", sa.Integer(), nullable=False),
        sa.Column("will", sa.Integer(), nullable=False),
        sa.Column("creativity", sa.Integer(), nullable=False),
        sa.Column("charisma", sa.Integer(), nullable=False),
        sa.Column("might", sa.Integer(), nullable=False),
        sa.Column("sanity", sa.Integer(), nullable=True),
        sa.CheckConstraint("status <> 'dead' OR death_epoch IS NOT NULL", name=op.f("ck_foreign_gods_dead_has_epoch")),
        sa.CheckConstraint("agility BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_agility_range")),
        sa.CheckConstraint("awakening_pressure >= 0", name=op.f("ck_foreign_gods_awakening_pressure_min")),
        sa.CheckConstraint("charisma BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_charisma_range")),
        sa.CheckConstraint("creativity BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_creativity_range")),
        sa.CheckConstraint("cunning BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_cunning_range")),
        sa.CheckConstraint("endurance BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_endurance_range")),
        sa.CheckConstraint("faith >= 0", name=op.f("ck_foreign_gods_faith_min")),
        sa.CheckConstraint("might BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_might_range")),
        sa.CheckConstraint("power BETWEEN 0 AND 100", name=op.f("ck_foreign_gods_power_range")),
        sa.CheckConstraint("sanity IS NULL OR sanity BETWEEN 0 AND 100", name=op.f("ck_foreign_gods_sanity_range")),
        sa.CheckConstraint("stance BETWEEN -100 AND 100", name=op.f("ck_foreign_gods_stance_range")),
        sa.CheckConstraint("strength BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_strength_range")),
        sa.CheckConstraint("will BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_will_range")),
        sa.CheckConstraint("wisdom BETWEEN 1 AND 100", name=op.f("ck_foreign_gods_wisdom_range")),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_foreign_gods_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_foreign_gods_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_foreign_gods")),
    )
    with op.batch_alter_table("foreign_gods", schema=None) as batch_op:
        batch_op.create_index("ix_foreign_gods_world_status", ["world_id", "status"], unique=False)

    op.create_table(
        "map_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("x", sa.Double(), nullable=False),
        sa.Column("y", sa.Double(), nullable=False),
        sa.Column("text", sa.String(length=400), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("text IS NULL OR length(text) <= 400", name=op.f("ck_map_notes_text_length")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_map_notes_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_map_notes")),
    )
    with op.batch_alter_table("map_notes", schema=None) as batch_op:
        batch_op.create_index("ix_map_notes_world", ["world_id"], unique=False)

    op.create_table(
        "map_snapshots",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_map_snapshots_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("epoch", "world_id", name=op.f("pk_map_snapshots")),
    )
    op.create_table(
        "motif_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("motif", sa.String(length=120), nullable=False),
        sa.Column("mode", sa.Enum("pinned", "allowed", name="mode", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_motif_overrides_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_motif_overrides")),
        sa.UniqueConstraint("world_id", "motif", name="uq_motif_overrides_world_motif"),
    )
    with op.batch_alter_table("motif_overrides", schema=None) as batch_op:
        batch_op.create_index("ix_motif_overrides_world", ["world_id"], unique=False)

    op.create_table(
        "sons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "rarity",
            sa.Enum("common", "uncommon", "rare", "epic", "legendary", "mythic", name="rarity", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column(
            "domain_primary",
            sa.Enum(
                "sea",
                "fire",
                "earth",
                "sky",
                "storm",
                "death",
                "life",
                "dream",
                "time",
                "light",
                "shadow",
                "war",
                "craft",
                "knowledge",
                "love",
                "trickery",
                "hunt",
                "plants",
                "bone",
                "blood",
                "sound",
                "stone",
                "ice",
                "madness",
                "trade",
                "road",
                "plague",
                "harvest",
                "moon",
                "sun",
                "star",
                "lies",
                "oath",
                "memory",
                "hunger",
                "glass",
                "salt",
                "ash",
                "border",
                "sleep",
                name="domain_primary",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "domain_secondary",
            sa.Enum(
                "sea",
                "fire",
                "earth",
                "sky",
                "storm",
                "death",
                "life",
                "dream",
                "time",
                "light",
                "shadow",
                "war",
                "craft",
                "knowledge",
                "love",
                "trickery",
                "hunt",
                "plants",
                "bone",
                "blood",
                "sound",
                "stone",
                "ice",
                "madness",
                "trade",
                "road",
                "plague",
                "harvest",
                "moon",
                "sun",
                "star",
                "lies",
                "oath",
                "memory",
                "hunger",
                "glass",
                "salt",
                "ash",
                "border",
                "sleep",
                name="domain_secondary",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("personality", sa.JSON(), nullable=False),
        sa.Column("existence_profile", sa.JSON(), nullable=True),
        sa.Column("existence", sa.Integer(), nullable=False),
        sa.Column("fading_epochs", sa.Integer(), nullable=False),
        sa.Column("hp", sa.Integer(), nullable=False),
        sa.Column("essence", sa.Integer(), nullable=False),
        sa.Column("faith", sa.Integer(), nullable=False),
        sa.Column("fame", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("active", "asleep", "exiled", "dead", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("sleep_epochs_left", sa.Integer(), nullable=False),
        sa.Column("chained", sa.Boolean(), nullable=False),
        sa.Column("rebel", sa.Boolean(), nullable=False),
        sa.Column("outer_bargain_forbidden", sa.Boolean(), nullable=False),
        sa.Column("standing_order", sa.Text(), nullable=True),
        sa.Column("order_absolute", sa.Boolean(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("plan_epoch", sa.Integer(), nullable=True),
        sa.Column("epic", sa.JSON(), nullable=True),
        sa.Column("anchor_entity_id", sa.Integer(), nullable=True),
        sa.Column("corpse_entity_id", sa.Integer(), nullable=True),
        sa.Column("parent_son_id", sa.Integer(), nullable=True),
        sa.Column("co_parent_son_id", sa.Integer(), nullable=True),
        sa.Column("current_world_id", sa.Integer(), nullable=True),
        sa.Column("manually_assigned_epoch", sa.Integer(), nullable=True),
        sa.Column("birth_epoch", sa.Integer(), nullable=False),
        sa.Column("death_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "death_cause",
            sa.Enum(
                "fading",
                "killed_by_sibling",
                "killed_by_creator",
                "devoured",
                "foreign_god",
                "cosmic_horror",
                "other",
                name="death_cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("last_acted_epoch", sa.Integer(), nullable=False),
        sa.Column("turn_rank", sa.Integer(), nullable=True),
        sa.Column("reputation_love", sa.Integer(), nullable=True),
        sa.Column("reputation_fear", sa.Integer(), nullable=True),
        sa.Column("reputation_forgotten", sa.Integer(), nullable=True),
        sa.Column("reputation_unanswered", sa.Integer(), nullable=True),
        sa.Column("reputation_last_contact_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "reputation_label",
            sa.Enum(
                "forgotten",
                "hated",
                "respected",
                "feared",
                "loved",
                "distant",
                "acknowledged",
                name="reputation_label",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("reputation_epoch", sa.Integer(), nullable=True),
        sa.Column("manual_love", sa.Integer(), nullable=False),
        sa.Column("manual_fear", sa.Integer(), nullable=False),
        sa.Column("manual_forgotten", sa.Integer(), nullable=False),
        sa.Column("trace_love", sa.Integer(), nullable=False),
        sa.Column("trace_fear", sa.Integer(), nullable=False),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("endurance", sa.Integer(), nullable=False),
        sa.Column("agility", sa.Integer(), nullable=False),
        sa.Column("wisdom", sa.Integer(), nullable=False),
        sa.Column("cunning", sa.Integer(), nullable=False),
        sa.Column("will", sa.Integer(), nullable=False),
        sa.Column("creativity", sa.Integer(), nullable=False),
        sa.Column("charisma", sa.Integer(), nullable=False),
        sa.Column("might", sa.Integer(), nullable=False),
        sa.Column("sanity", sa.Integer(), nullable=True),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("ambition", sa.Integer(), nullable=False),
        sa.Column("wrath", sa.Integer(), nullable=False),
        sa.Column("mercy", sa.Integer(), nullable=False),
        sa.CheckConstraint("status <> 'dead' OR death_epoch IS NOT NULL", name=op.f("ck_sons_dead_has_epoch")),
        sa.CheckConstraint("agility BETWEEN 1 AND 100", name=op.f("ck_sons_agility_range")),
        sa.CheckConstraint("ambition BETWEEN 0 AND 100", name=op.f("ck_sons_ambition_range")),
        sa.CheckConstraint("charisma BETWEEN 1 AND 100", name=op.f("ck_sons_charisma_range")),
        sa.CheckConstraint("creativity BETWEEN 1 AND 100", name=op.f("ck_sons_creativity_range")),
        sa.CheckConstraint("cunning BETWEEN 1 AND 100", name=op.f("ck_sons_cunning_range")),
        sa.CheckConstraint("domain_primary <> domain_secondary", name=op.f("ck_sons_distinct_domains")),
        sa.CheckConstraint("endurance BETWEEN 1 AND 100", name=op.f("ck_sons_endurance_range")),
        sa.CheckConstraint("essence >= 0", name=op.f("ck_sons_essence_min")),
        sa.CheckConstraint("existence BETWEEN 0 AND 100", name=op.f("ck_sons_existence_range")),
        sa.CheckConstraint("fading_epochs >= 0", name=op.f("ck_sons_fading_epochs_min")),
        sa.CheckConstraint("faith >= 0", name=op.f("ck_sons_faith_min")),
        sa.CheckConstraint("fame >= 0", name=op.f("ck_sons_fame_min")),
        sa.CheckConstraint("hp >= 0", name=op.f("ck_sons_hp_min")),
        sa.CheckConstraint("level >= 1", name=op.f("ck_sons_level_min")),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_sons_loyalty_range")),
        sa.CheckConstraint("mercy BETWEEN 0 AND 100", name=op.f("ck_sons_mercy_range")),
        sa.CheckConstraint("might BETWEEN 1 AND 100", name=op.f("ck_sons_might_range")),
        sa.CheckConstraint("parent_son_id IS NULL OR parent_son_id <> id", name=op.f("ck_sons_not_own_parent")),
        sa.CheckConstraint("sanity IS NULL OR sanity BETWEEN 0 AND 100", name=op.f("ck_sons_sanity_range")),
        sa.CheckConstraint("sleep_epochs_left >= 0", name=op.f("ck_sons_sleep_epochs_left_min")),
        sa.CheckConstraint("stars BETWEEN 1 AND 5", name=op.f("ck_sons_stars_range")),
        sa.CheckConstraint("strength BETWEEN 1 AND 100", name=op.f("ck_sons_strength_range")),
        sa.CheckConstraint("turn_rank IS NULL OR turn_rank >= 1", name=op.f("ck_sons_turn_rank_min")),
        sa.CheckConstraint("will BETWEEN 1 AND 100", name=op.f("ck_sons_will_range")),
        sa.CheckConstraint("wisdom BETWEEN 1 AND 100", name=op.f("ck_sons_wisdom_range")),
        sa.CheckConstraint("wrath BETWEEN 0 AND 100", name=op.f("ck_sons_wrath_range")),
        sa.CheckConstraint("xp >= 0", name=op.f("ck_sons_xp_min")),
        sa.ForeignKeyConstraint(["anchor_entity_id"], ["entities.id"], name=op.f("fk_sons_anchor_entity_id_entities"), ondelete="SET NULL", use_alter=True),
        sa.ForeignKeyConstraint(["co_parent_son_id"], ["sons.id"], name=op.f("fk_sons_co_parent_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["corpse_entity_id"], ["entities.id"], name=op.f("fk_sons_corpse_entity_id_entities"), ondelete="SET NULL", use_alter=True),
        sa.ForeignKeyConstraint(["current_world_id"], ["worlds.id"], name=op.f("fk_sons_current_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_sons_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_son_id"], ["sons.id"], name=op.f("fk_sons_parent_son_id_sons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sons")),
    )
    with op.batch_alter_table("sons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sons_current_world_id"), ["current_world_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sons_parent_son_id"), ["parent_son_id"], unique=False)
        batch_op.create_index("ix_sons_status", ["status"], unique=False)

    op.create_table(
        "world_leak_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("item", sa.String(length=120), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_leak_items_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_leak_items")),
    )
    with op.batch_alter_table("world_leak_items", schema=None) as batch_op:
        batch_op.create_index("ix_world_leak_items_epoch_world", ["epoch", "world_id"], unique=False)

    op.create_table(
        "world_maps",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("generator_version", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("signature", sa.String(length=120), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_maps_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_maps")),
    )
    op.create_table(
        "chronicle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "creation",
                "speech",
                "challenge",
                "prayer",
                "order",
                "fate",
                "death",
                "birth",
                "system",
                "message",
                "creator_hand",
                "world",
                "engine_raw",
                "knowledge",
                "resource",
                "culture",
                "trade",
                "exploration",
                "diplomacy",
                "production",
                "language",
                "miracle",
                "civilization",
                "creator_reputation",
                "construction",
                "existence",
                "dream",
                "star",
                "divine_sign",
                "climate",
                "cosmic",
                "debt",
                "foreign_god",
                "world_age",
                "council",
                "previous_creation",
                "sky",
                "gift",
                "worship",
                "world_birth",
                "prophecy",
                "covenant",
                "army",
                "ascension",
                "migration",
                "legendary_quest",
                "war",
                "war_of_gods",
                "cosmic_law",
                "horror",
                "outer_being",
                "immortality",
                "rebellion",
                "apocalypse",
                "resurrection",
                "lineage",
                "disaster",
                "adventure",
                "intrigue",
                "rescue",
                "chimera",
                "escape",
                "domestication",
                "age_change",
                "expedition",
                "spirit",
                "curse",
                "denial",
                "ransom",
                "prohibition",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column(
            "feed_category",
            sa.Enum(
                "voyage",
                "gate",
                "leak",
                "war",
                "disaster",
                "sky",
                "life",
                "civilization",
                "world",
                name="feed_category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("template_key", sa.String(length=120), nullable=True),
        sa.Column("son_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("hidden_as_duplicate", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_chronicle_epoch_min")),
        sa.CheckConstraint("year IS NULL OR year >= 0", name=op.f("ck_chronicle_year_min")),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_chronicle_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_chronicle_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chronicle")),
    )
    with op.batch_alter_table("chronicle", schema=None) as batch_op:
        batch_op.create_index("ix_chronicle_epoch", ["epoch", "id"], unique=False)
        batch_op.create_index("ix_chronicle_kind_epoch", ["kind", "epoch"], unique=False)
        batch_op.create_index("ix_chronicle_son", ["son_id"], unique=False)
        batch_op.create_index("ix_chronicle_world_epoch", ["world_id", "epoch"], unique=False)

    op.create_table(
        "climate_orders",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "era",
            sa.Enum("temperate", "drought", "rain", "ice_age", "scorching", name="era", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("ordered_epoch", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("ordered_epoch >= 1", name=op.f("ck_climate_orders_ordered_epoch_min")),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_climate_orders_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_climate_orders_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_climate_orders")),
    )
    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "entity_type",
            sa.Enum(
                "region",
                "place",
                "resource",
                "settlement",
                "species",
                "people",
                "mortal",
                "item",
                "structure",
                "language",
                "legend",
                "tradition",
                "cult",
                "faction",
                "celestial",
                "artwork",
                "law",
                "spirit",
                "knowledge",
                "prophecy",
                "event",
                "vessel",
                "outer_being",
                "army",
                "natural_law",
                name="entity_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subtype", sa.String(length=120), nullable=True),
        sa.Column(
            "engine_kind",
            sa.Enum(
                "war",
                "battle",
                "siege",
                "magic_storm",
                "earthquake",
                "flood",
                "plague",
                "drought",
                "storm",
                "famine",
                "uprising",
                "migration",
                "temple",
                "wall",
                "library",
                "school",
                "observatory",
                "cosmic_archive",
                "wonder",
                "rebels",
                "merchant_guild",
                "priests_council",
                "warrior_band",
                "interworld_federation",
                "wandering_market",
                "void_pirates",
                "peoples_army",
                "holy_guard",
                "mercenary_army",
                "dialect",
                "primitive_language",
                "currency",
                "eclipse_prophecy",
                "cosmic_travel_resource",
                "golem",
                "chimera",
                "descended_soul",
                "mirror_birth",
                "apprentice",
                "comet",
                "ascension_myth",
                "god_corpse",
                "god_shade",
                "resurrection_order",
                "ghost_ship",
                "colony",
                name="engine_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "mortal_role",
            sa.Enum(
                "ruler",
                "hero",
                "warrior",
                "knight",
                "hunter",
                "chosen",
                "seer",
                "priest",
                "sage",
                "healer",
                "artisan",
                "merchant",
                "scribe",
                "farmer",
                "explorer",
                "captain",
                "bandit",
                "saint",
                "apprentice",
                "commoner",
                name="mortal_role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("power_level", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "sea",
                "fire",
                "earth",
                "sky",
                "storm",
                "death",
                "life",
                "dream",
                "time",
                "light",
                "shadow",
                "war",
                "craft",
                "knowledge",
                "love",
                "trickery",
                "hunt",
                "plants",
                "bone",
                "blood",
                "sound",
                "stone",
                "ice",
                "madness",
                "trade",
                "road",
                "plague",
                "harvest",
                "moon",
                "sun",
                "star",
                "lies",
                "oath",
                "memory",
                "hunger",
                "glass",
                "salt",
                "ash",
                "border",
                "sleep",
                name="domain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "origin",
            sa.Enum("son", "creator", "engine", "mortal", "cosmos", name="origin", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("creator_son_id", sa.Integer(), nullable=True),
        sa.Column("maker_entity_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("canon", "rejected", "destroyed", "dead", "fulfilled", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("pending_name", sa.Boolean(), nullable=False),
        sa.Column("naming_attempts", sa.Integer(), nullable=False),
        sa.Column("fate_note", sa.Text(), nullable=True),
        sa.Column("depth", sa.JSON(), nullable=True),
        sa.Column("birth_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column("last_acted_epoch", sa.Integer(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=True),
        sa.Column(
            "archive_override", sa.Enum("history", "atlas", name="archive_override", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("private_note", sa.Text(), nullable=True),
        sa.Column("map_x", sa.Float(), nullable=True),
        sa.Column("map_y", sa.Float(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("civ_tier", sa.Integer(), nullable=True),
        sa.Column("civ_tier_epoch", sa.Integer(), nullable=True),
        sa.Column("civ_tier_previous", sa.Integer(), nullable=True),
        sa.Column("sanity", sa.Integer(), nullable=True),
        sa.Column(
            "knowledge_branch",
            sa.Enum(
                "agriculture",
                "metallurgy",
                "seafaring",
                "writing",
                "architecture",
                "medicine",
                "magic",
                "warfare",
                "astronomy",
                "trade",
                "sky_navigation",
                "shipbuilding",
                "gate_lore",
                "pathfinding",
                "void_living",
                "immortality",
                "biomancy",
                "forbidden",
                name="knowledge_branch",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "natural_law",
            sa.Enum(
                "none",
                "immortality",
                "short_life",
                "dead_return",
                "magic_price",
                "war_ban",
                "bounty",
                "drought",
                "sea_ban",
                "one_language",
                "disasters",
                name="natural_law",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "resource_mechanic",
            sa.Enum(
                "decaying",
                "addictive",
                "sentient",
                "depletion_price",
                "fixed",
                "sacred",
                name="resource_mechanic",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("sacred_to_son_id", sa.Integer(), nullable=True),
        sa.Column(
            "prophecy_reading",
            sa.Enum("true", "misread", "self_fulfilling", name="prophecy_reading", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column(
            "legend_category",
            sa.Enum("creature", "spirit", "resource", "relic", name="legend_category", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column(
            "social_class",
            sa.Enum("farmer", "artisan", "merchant", "priest", "warrior", "scribe", name="social_class", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("affiliated_entity_id", sa.Integer(), nullable=True),
        sa.Column("death_event_entity_id", sa.Integer(), nullable=True),
        sa.Column("is_underworld", sa.Boolean(), nullable=False),
        sa.Column("is_water", sa.Boolean(), nullable=False),
        sa.Column("fold_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("death_event_entity_id IS NULL OR entity_type = 'mortal'", name=op.f("ck_entities_death_event_on_mortal")),
        sa.CheckConstraint("knowledge_branch IS NULL OR entity_type = 'knowledge'", name=op.f("ck_entities_branch_on_knowledge")),
        sa.CheckConstraint("legend_category IS NULL OR entity_type = 'legend'", name=op.f("ck_entities_category_on_legend")),
        sa.CheckConstraint("mortal_role IS NULL OR entity_type = 'mortal'", name=op.f("ck_entities_role_on_mortal")),
        sa.CheckConstraint("natural_law IS NULL OR entity_type = 'natural_law'", name=op.f("ck_entities_law_on_natural_law")),
        sa.CheckConstraint("origin <> 'mortal' OR maker_entity_id IS NOT NULL", name=op.f("ck_entities_mortal_origin_has_maker")),
        sa.CheckConstraint("prophecy_reading IS NULL OR entity_type = 'prophecy'", name=op.f("ck_entities_reading_on_prophecy")),
        sa.CheckConstraint("resource_mechanic IS NULL OR entity_type = 'resource'", name=op.f("ck_entities_mechanic_on_resource")),
        sa.CheckConstraint("sacred_to_son_id IS NULL OR resource_mechanic = 'sacred'", name=op.f("ck_entities_sacred_owner_on_sacred")),
        sa.CheckConstraint("status NOT IN ('dead', 'destroyed') OR end_epoch IS NOT NULL", name=op.f("ck_entities_ended_has_epoch")),
        sa.CheckConstraint("civ_tier IS NULL OR civ_tier BETWEEN 0 AND 5", name=op.f("ck_entities_civ_tier_range")),
        sa.CheckConstraint("civ_tier_previous IS NULL OR civ_tier_previous BETWEEN 0 AND 5", name=op.f("ck_entities_civ_tier_previous_range")),
        sa.CheckConstraint("fold_count >= 0", name=op.f("ck_entities_fold_count_min")),
        sa.CheckConstraint("last_acted_epoch >= 0", name=op.f("ck_entities_last_acted_epoch_min")),
        sa.CheckConstraint("location_id IS NULL OR location_id <> id", name=op.f("ck_entities_not_own_location")),
        sa.CheckConstraint("maker_entity_id IS NULL OR maker_entity_id <> id", name=op.f("ck_entities_not_own_maker")),
        sa.CheckConstraint("power_level >= 1", name=op.f("ck_entities_power_level_min")),
        sa.CheckConstraint("private_note IS NULL OR length(private_note) <= 4000", name=op.f("ck_entities_private_note_length")),
        sa.CheckConstraint("sanity IS NULL OR sanity BETWEEN 0 AND 100", name=op.f("ck_entities_sanity_range")),
        sa.ForeignKeyConstraint(["affiliated_entity_id"], ["entities.id"], name=op.f("fk_entities_affiliated_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_son_id"], ["sons.id"], name=op.f("fk_entities_creator_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["death_event_entity_id"], ["entities.id"], name=op.f("fk_entities_death_event_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_entities_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["entities.id"], name=op.f("fk_entities_location_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["maker_entity_id"], ["entities.id"], name=op.f("fk_entities_maker_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sacred_to_son_id"], ["sons.id"], name=op.f("fk_entities_sacred_to_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_entities_world_id_worlds"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
    )
    with op.batch_alter_table("entities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_entities_creator_son_id"), ["creator_son_id"], unique=False)
        batch_op.create_index("ix_entities_engine_kind_status", ["engine_kind", "status"], unique=False)
        batch_op.create_index(batch_op.f("ix_entities_importance"), ["importance"], unique=False)
        batch_op.create_index(batch_op.f("ix_entities_location_id"), ["location_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_entities_maker_entity_id"), ["maker_entity_id"], unique=False)
        batch_op.create_index("ix_entities_pending", ["pending_name"], unique=False, sqlite_where=sa.text("pending_name = 1"))
        batch_op.create_index("ix_entities_type_status", ["entity_type", "status"], unique=False)
        batch_op.create_index(batch_op.f("ix_entities_world_id"), ["world_id"], unique=False)
        batch_op.create_index("ix_entities_world_type_status", ["world_id", "entity_type", "status"], unique=False)

    op.create_table(
        "fate_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("fame", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("fame >= 0", name=op.f("ck_fate_rewards_fame_min")),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_fate_rewards_son_id_sons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fate_rewards")),
    )
    with op.batch_alter_table("fate_rewards", schema=None) as batch_op:
        batch_op.create_index("ix_fate_rewards_son_epoch", ["son_id", "epoch"], unique=False)

    op.create_table(
        "foreign_god_powers",
        sa.Column("god_id", sa.Integer(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "effect",
            sa.Enum(
                "shield",
                "caller",
                "thief",
                "destroyer",
                "fertile",
                "reviving",
                "deathless",
                "sharp_tongued",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["god_id"], ["foreign_gods.id"], name=op.f("fk_foreign_god_powers_god_id_foreign_gods"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("god_id", "slot", name=op.f("pk_foreign_god_powers")),
    )
    op.create_table(
        "son_powers",
        sa.Column("son_id", sa.Integer(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "effect",
            sa.Enum(
                "cheap_creation",
                "duel_master",
                "essence_spring",
                "worshipped",
                "tireless",
                "untouchable",
                "dream_whisper",
                "war_father",
                "harvester",
                "seer",
                "reviving",
                "bounty_giver",
                "curser",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "param_entity_type",
            sa.Enum(
                "region",
                "place",
                "resource",
                "settlement",
                "species",
                "people",
                "mortal",
                "item",
                "structure",
                "language",
                "legend",
                "tradition",
                "cult",
                "faction",
                "celestial",
                "artwork",
                "law",
                "spirit",
                "knowledge",
                "prophecy",
                "event",
                "vessel",
                "outer_being",
                "army",
                "natural_law",
                name="param_entity_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "param_stat",
            sa.Enum(
                "strength",
                "endurance",
                "agility",
                "wisdom",
                "cunning",
                "will",
                "creativity",
                "charisma",
                "might",
                name="param_stat",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.CheckConstraint("param_entity_type IS NULL OR param_stat IS NULL", name=op.f("ck_son_powers_single_param")),
        sa.CheckConstraint("slot BETWEEN 0 AND 2", name=op.f("ck_son_powers_slot_range")),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_son_powers_son_id_sons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("son_id", "slot", name=op.f("pk_son_powers")),
    )
    with op.batch_alter_table("son_powers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_son_powers_effect"), ["effect"], unique=False)

    op.create_table(
        "son_relations",
        sa.Column("son_a_id", sa.Integer(), nullable=False),
        sa.Column("son_b_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("son_a_id < son_b_id", name=op.f("ck_son_relations_ordered_pair")),
        sa.CheckConstraint("value BETWEEN -100 AND 100", name=op.f("ck_son_relations_value_range")),
        sa.ForeignKeyConstraint(["son_a_id"], ["sons.id"], name=op.f("fk_son_relations_son_a_id_sons"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["son_b_id"], ["sons.id"], name=op.f("fk_son_relations_son_b_id_sons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("son_a_id", "son_b_id", name=op.f("pk_son_relations")),
        sa.UniqueConstraint("son_b_id", "son_a_id", name="uq_son_relations_reverse"),
    )
    op.create_table(
        "addiction_immunities",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("resource_entity_id", sa.Integer(), nullable=False),
        sa.Column("recovered_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("recovered_epoch >= 0", name=op.f("ck_addiction_immunities_recovered_epoch_min")),
        sa.ForeignKeyConstraint(
            ["community_entity_id"], ["entities.id"], name=op.f("fk_addiction_immunities_community_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_addiction_immunities_resource_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "resource_entity_id", name=op.f("pk_addiction_immunities")),
    )
    op.create_table(
        "addictions",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("resource_entity_id", sa.Integer(), nullable=False),
        sa.Column("owned_epochs", sa.Integer(), nullable=False),
        sa.Column("addicted_since_epoch", sa.Integer(), nullable=True),
        sa.Column("withdrawal_since_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("owned_epochs >= 0", name=op.f("ck_addictions_owned_epochs_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_addictions_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_addictions_resource_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "resource_entity_id", name=op.f("pk_addictions")),
    )
    op.create_table(
        "archive_holdings",
        sa.Column("archive_entity_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_entity_id", sa.Integer(), nullable=False),
        sa.Column("reader_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["archive_entity_id"], ["entities.id"], name=op.f("fk_archive_holdings_archive_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_entity_id"], ["entities.id"], name=op.f("fk_archive_holdings_knowledge_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reader_entity_id"], ["entities.id"], name=op.f("fk_archive_holdings_reader_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("archive_entity_id", "knowledge_entity_id", name=op.f("pk_archive_holdings")),
    )
    op.create_table(
        "canon_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_entity_id", sa.Integer(), nullable=False),
        sa.Column("predicate", sa.String(length=120), nullable=False),
        sa.Column("object_entity_id", sa.Integer(), nullable=True),
        sa.Column("object_text", sa.String(length=200), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("source_entity_id", sa.Integer(), nullable=True),
        sa.Column("deterministic", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("object_entity_id IS NOT NULL OR object_text IS NOT NULL", name=op.f("ck_canon_facts_has_object")),
        sa.ForeignKeyConstraint(["object_entity_id"], ["entities.id"], name=op.f("fk_canon_facts_object_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], name=op.f("fk_canon_facts_source_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"], name=op.f("fk_canon_facts_subject_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canon_facts")),
    )
    with op.batch_alter_table("canon_facts", schema=None) as batch_op:
        batch_op.create_index("ix_canon_facts_object", ["object_entity_id"], unique=False)
        batch_op.create_index("ix_canon_facts_subject", ["subject_entity_id", "active"], unique=False)

    op.create_table(
        "chronicle_entities",
        sa.Column("chronicle_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["chronicle_id"], ["chronicle.id"], name=op.f("fk_chronicle_entities_chronicle_id_chronicle"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_chronicle_entities_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chronicle_id", "entity_id", name=op.f("pk_chronicle_entities")),
        sa.UniqueConstraint("chronicle_id", "position", name="uq_chronicle_entities_position"),
    )
    with op.batch_alter_table("chronicle_entities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_chronicle_entities_entity_id"), ["entity_id"], unique=False)

    op.create_table(
        "civilization_tier_locks",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("tier BETWEEN 0 AND 5", name=op.f("ck_civilization_tier_locks_tier_range")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_civilization_tier_locks_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_civilization_tier_locks")),
    )
    op.create_table(
        "community_relation_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_a_id", sa.Integer(), nullable=False),
        sa.Column("entity_b_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=120), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["entity_a_id"], ["entities.id"], name=op.f("fk_community_relation_events_entity_a_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_b_id"], ["entities.id"], name=op.f("fk_community_relation_events_entity_b_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_relation_events")),
    )
    with op.batch_alter_table("community_relation_events", schema=None) as batch_op:
        batch_op.create_index("ix_community_relation_events_pair", ["entity_a_id", "entity_b_id", "epoch"], unique=False)

    op.create_table(
        "community_relations",
        sa.Column("entity_a_id", sa.Integer(), nullable=False),
        sa.Column("entity_b_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("blood_feud_since_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("entity_a_id < entity_b_id", name=op.f("ck_community_relations_ordered_pair")),
        sa.CheckConstraint("value BETWEEN -100 AND 100", name=op.f("ck_community_relations_value_range")),
        sa.ForeignKeyConstraint(["entity_a_id"], ["entities.id"], name=op.f("fk_community_relations_entity_a_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_b_id"], ["entities.id"], name=op.f("fk_community_relations_entity_b_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_a_id", "entity_b_id", name=op.f("pk_community_relations")),
    )
    with op.batch_alter_table("community_relations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_community_relations_entity_b_id"), ["entity_b_id"], unique=False)

    op.create_table(
        "community_societies",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("share_farmer", sa.Float(), nullable=False),
        sa.Column("share_artisan", sa.Float(), nullable=False),
        sa.Column("share_merchant", sa.Float(), nullable=False),
        sa.Column("share_priest", sa.Float(), nullable=False),
        sa.Column("share_warrior", sa.Float(), nullable=False),
        sa.Column("share_scribe", sa.Float(), nullable=False),
        sa.Column("satisfaction_farmer", sa.Integer(), nullable=False),
        sa.Column("satisfaction_artisan", sa.Integer(), nullable=False),
        sa.Column("satisfaction_merchant", sa.Integer(), nullable=False),
        sa.Column("satisfaction_priest", sa.Integer(), nullable=False),
        sa.Column("satisfaction_warrior", sa.Integer(), nullable=False),
        sa.Column("satisfaction_scribe", sa.Integer(), nullable=False),
        sa.Column("stock_food", sa.Integer(), nullable=False),
        sa.Column("stock_ore", sa.Integer(), nullable=False),
        sa.Column("stock_goods", sa.Integer(), nullable=False),
        sa.Column("price_food", sa.Integer(), nullable=False),
        sa.Column("price_ore", sa.Integer(), nullable=False),
        sa.Column("price_goods", sa.Integer(), nullable=False),
        sa.Column("golden_age_since_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("price_food >= 0", name=op.f("ck_community_societies_price_food_min")),
        sa.CheckConstraint("price_goods >= 0", name=op.f("ck_community_societies_price_goods_min")),
        sa.CheckConstraint("price_ore >= 0", name=op.f("ck_community_societies_price_ore_min")),
        sa.CheckConstraint("satisfaction_artisan BETWEEN 0 AND 100", name=op.f("ck_community_societies_satisfaction_artisan_range")),
        sa.CheckConstraint("satisfaction_farmer BETWEEN 0 AND 100", name=op.f("ck_community_societies_satisfaction_farmer_range")),
        sa.CheckConstraint("satisfaction_merchant BETWEEN 0 AND 100", name=op.f("ck_community_societies_satisfaction_merchant_range")),
        sa.CheckConstraint("satisfaction_priest BETWEEN 0 AND 100", name=op.f("ck_community_societies_satisfaction_priest_range")),
        sa.CheckConstraint("satisfaction_scribe BETWEEN 0 AND 100", name=op.f("ck_community_societies_satisfaction_scribe_range")),
        sa.CheckConstraint("satisfaction_warrior BETWEEN 0 AND 100", name=op.f("ck_community_societies_satisfaction_warrior_range")),
        sa.CheckConstraint("share_artisan BETWEEN 0 AND 100", name=op.f("ck_community_societies_share_artisan_range")),
        sa.CheckConstraint("share_farmer BETWEEN 0 AND 100", name=op.f("ck_community_societies_share_farmer_range")),
        sa.CheckConstraint("share_merchant BETWEEN 0 AND 100", name=op.f("ck_community_societies_share_merchant_range")),
        sa.CheckConstraint("share_priest BETWEEN 0 AND 100", name=op.f("ck_community_societies_share_priest_range")),
        sa.CheckConstraint("share_scribe BETWEEN 0 AND 100", name=op.f("ck_community_societies_share_scribe_range")),
        sa.CheckConstraint("share_warrior BETWEEN 0 AND 100", name=op.f("ck_community_societies_share_warrior_range")),
        sa.CheckConstraint("stock_food >= 0", name=op.f("ck_community_societies_stock_food_min")),
        sa.CheckConstraint("stock_goods >= 0", name=op.f("ck_community_societies_stock_goods_min")),
        sa.CheckConstraint("stock_ore >= 0", name=op.f("ck_community_societies_stock_ore_min")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_community_societies_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_community_societies")),
    )
    op.create_table(
        "creation_motifs",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("motif", sa.String(length=120), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "imagery",
                "material",
                "color",
                "sound",
                "creature",
                "place",
                "theme",
                "phrase",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_creation_motifs_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_creation_motifs_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", "motif", name=op.f("pk_creation_motifs")),
    )
    with op.batch_alter_table("creation_motifs", schema=None) as batch_op:
        batch_op.create_index("ix_creation_motifs_motif_epoch", ["motif", "epoch"], unique=False)

    op.create_table(
        "creation_rewards",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("renown", sa.Integer(), nullable=False),
        sa.Column("essence", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("land", sa.Boolean(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("thread_reverted", sa.Boolean(), nullable=False),
        sa.Column("fade_pct", sa.Integer(), nullable=False),
        sa.Column("repeats", sa.Integer(), nullable=False),
        sa.Column("partner_son_id", sa.Integer(), nullable=True),
        sa.Column("partner_xp", sa.Integer(), nullable=False),
        sa.Column("partner_renown", sa.Integer(), nullable=False),
        sa.Column("partner_cost", sa.Integer(), nullable=False),
        sa.Column("taken_back_pct", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=220), nullable=True),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_creation_rewards_cost_min")),
        sa.CheckConstraint("essence >= 0", name=op.f("ck_creation_rewards_essence_min")),
        sa.CheckConstraint("renown >= 0", name=op.f("ck_creation_rewards_renown_min")),
        sa.CheckConstraint("taken_back_pct BETWEEN 0 AND 100", name=op.f("ck_creation_rewards_taken_back_range")),
        sa.CheckConstraint("xp >= 0", name=op.f("ck_creation_rewards_xp_min")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_creation_rewards_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_son_id"], ["sons.id"], name=op.f("fk_creation_rewards_partner_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_creation_rewards_son_id_sons"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], name=op.f("fk_creation_rewards_thread_id_threads"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_creation_rewards")),
    )
    with op.batch_alter_table("creation_rewards", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_creation_rewards_son_id"), ["son_id"], unique=False)

    op.create_table(
        "creation_verdicts",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "verdict",
            sa.Enum("unjudged", "accepted", "fixed", "rejected", "limbo", name="verdict", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("judged_epoch", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_creation_verdicts_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_creation_verdicts")),
    )
    with op.batch_alter_table("creation_verdicts", schema=None) as batch_op:
        batch_op.create_index("ix_creation_verdicts_epoch_verdict", ["epoch", "verdict"], unique=False)

    op.create_table(
        "designated_heirs",
        sa.Column("ruler_entity_id", sa.Integer(), nullable=False),
        sa.Column("heir_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("ruler_entity_id <> heir_entity_id", name=op.f("ck_designated_heirs_not_own_heir")),
        sa.ForeignKeyConstraint(["heir_entity_id"], ["entities.id"], name=op.f("fk_designated_heirs_heir_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ruler_entity_id"], ["entities.id"], name=op.f("fk_designated_heirs_ruler_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ruler_entity_id", name=op.f("pk_designated_heirs")),
    )
    with op.batch_alter_table("designated_heirs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_designated_heirs_heir_entity_id"), ["heir_entity_id"], unique=False)

    op.create_table(
        "entity_flags",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "flag",
            sa.Enum(
                "disaster",
                "lost",
                "dead_language",
                "decipherable",
                "previous_creation",
                "ruin",
                "rebuilt",
                "remnant",
                "void",
                "cursed",
                "godless",
                "seeking_god",
                "empire",
                "federation",
                "independent",
                "colony",
                "pioneer",
                "golden_age",
                "immortal",
                "chimera",
                "mutation",
                "mutant",
                "mutated",
                "discovery",
                "native",
                "revelation",
                "soul_descended",
                "soul_bound",
                "soul_harvester",
                "crossed_to_the_dead",
                "wonder",
                "chosen",
                "manifested",
                "born_of_belief",
                "corrupted_memory",
                "fairy_tale",
                "name_from_language",
                "species_became_people",
                "original_resource",
                "cosmic_monopoly",
                "outer_cult",
                "whisper_source",
                "nameless",
                "escaped",
                "megafauna",
                "invasive",
                "worships_planet",
                "planet_closed",
                "burned",
                "cosmic_plague",
                "mirror",
                "mirror_born",
                "oathbreaker",
                "exile",
                "omen",
                "time_echo",
                "two_timed",
                "empty_tomb",
                "resurrection_complete",
                "protected_from_disaster",
                "mechanics_weighed",
                "depleting",
                "syncretic",
                "returned_to_old_god",
                "revived_language",
                "on_watch",
                "mocked",
                "protected_from_ruin",
                "spared_soul",
                "ghost",
                "wizard",
                "age_changer",
                "time_returned",
                "legendary",
                "prophet",
                "bloodline_curse",
                "essence_drained",
                "returned_from_death",
                "saw_the_creator",
                "deified",
                "protected",
                "depleted",
                "agent_selected",
                "capital",
                "abandoned",
                "dissolved",
                "desolate",
                "razed",
                "fell_in_battle",
                "died_in_siege",
                "died_in_disaster",
                "died_of_plague",
                "slain_in_captivity",
                "doomed",
                "fate_shielded",
                "commemoration",
                "estranged_by_plague",
                "endangered",
                "extinct",
                "pilgrimage_site",
                "repealed",
                "merged",
                "disbanded",
                "assimilated",
                "forgotten",
                "swallowed",
                name="flag",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_entity_flags_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "flag", name=op.f("pk_entity_flags")),
    )
    with op.batch_alter_table("entity_flags", schema=None) as batch_op:
        batch_op.create_index("ix_entity_flags_flag", ["flag"], unique=False)

    op.create_table(
        "entity_tags",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_entity_tags_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "tag", name=op.f("pk_entity_tags")),
    )
    with op.batch_alter_table("entity_tags", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_entity_tags_tag"), ["tag"], unique=False)

    op.create_table(
        "entity_traits",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "trait",
            sa.Enum(
                "flying",
                "venomous",
                "soul_eater",
                "radiant",
                "fissiparous",
                "hive_mind",
                "stoneskin",
                "time_rewinder",
                "shapeshifter",
                "mind_reader",
                name="trait",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_entity_traits_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "trait", name=op.f("pk_entity_traits")),
    )
    with op.batch_alter_table("entity_traits", schema=None) as batch_op:
        batch_op.create_index("ix_entity_traits_trait", ["trait"], unique=False)

    op.create_table(
        "epoch_agents",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_epoch_agents_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_epoch_agents_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("epoch", "entity_id", name=op.f("pk_epoch_agents")),
    )
    op.create_table(
        "folk_beliefs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column("local_name", sa.String(length=200), nullable=True),
        sa.Column("account", sa.Text(), nullable=False),
        sa.Column("misconception", sa.Text(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_folk_beliefs_god_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_folk_beliefs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "god_node_id", name=op.f("pk_folk_beliefs")),
    )
    with op.batch_alter_table("folk_beliefs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_folk_beliefs_god_node_id"), ["god_node_id"], unique=False)

    op.create_table(
        "historian_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("historian", sa.String(length=200), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_historian_views_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historian_views")),
        sa.UniqueConstraint("epoch", "people_entity_id", name="uq_historian_views_epoch_people"),
    )
    with op.batch_alter_table("historian_views", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_historian_views_epoch"), ["epoch"], unique=False)

    op.create_table(
        "horizon_intuitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("how", sa.Text(), nullable=True),
        sa.Column(
            "method",
            sa.Enum(
                "ancient_gate",
                "space_fold",
                "light_sail",
                "cosmic_mount",
                "dream_journey",
                "river_of_dead",
                "divine_bridge",
                "slingshot_orbit",
                "swallowed",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "status", sa.Enum("pending", "processing", "born", "wasted", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("result_world_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_horizon_intuitions_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_world_id"], ["worlds.id"], name=op.f("fk_horizon_intuitions_result_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_horizon_intuitions_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_horizon_intuitions")),
    )
    with op.batch_alter_table("horizon_intuitions", schema=None) as batch_op:
        batch_op.create_index("ix_horizon_intuitions_status", ["status"], unique=False)

    op.create_table(
        "language_profiles",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("phonology", sa.JSON(), nullable=False),
        sa.Column(
            "writing_system",
            sa.Enum("alphabet", "syllabary", "pictographic", "knot", "notch", name="writing_system", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("script_epoch", sa.Integer(), nullable=True),
        sa.Column("parent_language_id", sa.Integer(), nullable=True),
        sa.Column("seed", sa.String(length=120), nullable=False),
        sa.Column("signature", sa.JSON(), nullable=True),
        sa.Column("alphabet", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_language_profiles_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_language_id"], ["entities.id"], name=op.f("fk_language_profiles_parent_language_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_language_profiles")),
    )
    op.create_table(
        "lexemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=60), nullable=False),
        sa.Column("word_key", sa.String(length=60), nullable=False),
        sa.Column("meaning", sa.String(length=300), nullable=False),
        sa.Column(
            "part_of_speech",
            sa.Enum(
                "noun",
                "verb",
                "adjective",
                "affix",
                "title",
                "place_name",
                "proper_name",
                "number",
                "interjection",
                name="part_of_speech",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("etymology", sa.String(length=300), nullable=True),
        sa.Column("example", sa.String(length=300), nullable=True),
        sa.Column(
            "added_by_kind",
            sa.Enum(
                "creator",
                "son",
                "mortal",
                "foreign_god",
                "fate",
                "engine",
                "system",
                name="added_by_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("added_by_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["added_by_node_id"], ["nodes.id"], name=op.f("fk_lexemes_added_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_lexemes_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lexemes")),
        sa.UniqueConstraint("language_entity_id", "word_key", name="uq_lexemes_language_word"),
    )
    with op.batch_alter_table("lexemes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_lexemes_language_entity_id"), ["language_entity_id"], unique=False)

    op.create_table(
        "network_reviews",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_network_reviews_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_network_reviews")),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=True),
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
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=90), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("chronicle_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("body IS NULL OR length(body) <= 600", name=op.f("ck_notifications_body_length")),
        sa.CheckConstraint("severity BETWEEN 1 AND 4", name=op.f("ck_notifications_severity_range")),
        sa.CheckConstraint("title IS NULL OR length(title) <= 90", name=op.f("ck_notifications_title_length")),
        sa.ForeignKeyConstraint(["chronicle_id"], ["chronicle.id"], name=op.f("fk_notifications_chronicle_id_chronicle"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_notifications_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.create_index("ix_notifications_category", ["category", "id"], unique=False)
        batch_op.create_index("ix_notifications_unread", ["is_read", "id"], unique=False)

    op.create_table(
        "outer_bargains",
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_bargains_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_outer_bargains_son_id_sons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("outer_entity_id", "son_id", name=op.f("pk_outer_bargains")),
    )
    op.create_table(
        "resource_commodities",
        sa.Column("resource_entity_id", sa.Integer(), nullable=False),
        sa.Column("commodity", sa.Enum("food", "ore", "goods", name="commodity", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_resource_commodities_resource_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resource_entity_id", name=op.f("pk_resource_commodities")),
    )
    with op.batch_alter_table("resource_commodities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resource_commodities_commodity"), ["commodity"], unique=False)

    op.create_table(
        "resource_mechanics",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "mechanic",
            sa.Enum(
                "decaying", "addictive", "sentient", "depletion_price", "fixed", "sacred", name="mechanic", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_resource_mechanics_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "mechanic", name=op.f("pk_resource_mechanics")),
    )
    with op.batch_alter_table("resource_mechanics", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resource_mechanics_mechanic"), ["mechanic"], unique=False)

    op.create_table(
        "resurrection_orders",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=False),
        sa.Column("completed_epoch", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_resurrection_orders_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_resurrection_orders_son_id_sons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cult_entity_id", name=op.f("pk_resurrection_orders")),
    )
    with op.batch_alter_table("resurrection_orders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resurrection_orders_son_id"), ["son_id"], unique=False)

    op.create_table(
        "reverences",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_reverences_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_reverences_god_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "god_node_id", name=op.f("pk_reverences")),
    )
    with op.batch_alter_table("reverences", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_reverences_god_node_id"), ["god_node_id"], unique=False)

    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_a_id", sa.Integer(), nullable=False),
        sa.Column("world_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "ancient_gate",
                "space_fold",
                "light_sail",
                "cosmic_mount",
                "dream_journey",
                "river_of_dead",
                "divine_bridge",
                "slingshot_orbit",
                "swallowed",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("duration_epochs", sa.Integer(), nullable=False),
        sa.Column("danger", sa.Integer(), nullable=False),
        sa.Column("known", sa.Boolean(), nullable=False),
        sa.Column("controller_entity_id", sa.Integer(), nullable=True),
        sa.Column("vehicle_entity_id", sa.Integer(), nullable=True),
        sa.Column("builder_son_id", sa.Integer(), nullable=True),
        sa.Column("bound_star_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "closure",
            sa.Enum("sealed", "severed", "forgotten", "collapsed", "snapped", name="closure", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("temp_open_until_epoch", sa.Integer(), nullable=True),
        sa.Column("temp_closed_until_epoch", sa.Integer(), nullable=True),
        sa.Column("closed_by_forgetting_world_id", sa.Integer(), nullable=True),
        sa.Column("sacrifice_paid_epoch", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("danger BETWEEN 0 AND 100", name=op.f("ck_routes_danger_range")),
        sa.CheckConstraint("duration_epochs >= 1", name=op.f("ck_routes_duration_epochs_min")),
        sa.CheckConstraint("world_a_id <> world_b_id", name=op.f("ck_routes_distinct_worlds")),
        sa.ForeignKeyConstraint(["bound_star_id"], ["stars.id"], name=op.f("fk_routes_bound_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["builder_son_id"], ["sons.id"], name=op.f("fk_routes_builder_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["closed_by_forgetting_world_id"], ["worlds.id"], name=op.f("fk_routes_closed_by_forgetting_world_id_worlds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["controller_entity_id"], ["entities.id"], name=op.f("fk_routes_controller_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_entity_id"], ["entities.id"], name=op.f("fk_routes_vehicle_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_a_id"], ["worlds.id"], name=op.f("fk_routes_world_a_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_b_id"], ["worlds.id"], name=op.f("fk_routes_world_b_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routes")),
    )
    with op.batch_alter_table("routes", schema=None) as batch_op:
        batch_op.create_index("ix_routes_world_a", ["world_a_id", "active"], unique=False)
        batch_op.create_index("ix_routes_world_b", ["world_b_id", "active"], unique=False)

    op.create_table(
        "souls",
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("origin_world_id", sa.Integer(), nullable=False),
        sa.Column("realm_entity_id", sa.Integer(), nullable=True),
        sa.Column("descended_epoch", sa.Integer(), nullable=False),
        sa.Column("bound_to_entity_id", sa.Integer(), nullable=True),
        sa.Column("harvested_by_entity_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["bound_to_entity_id"], ["entities.id"], name=op.f("fk_souls_bound_to_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["harvested_by_entity_id"], ["entities.id"], name=op.f("fk_souls_harvested_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_souls_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_world_id"], ["worlds.id"], name=op.f("fk_souls_origin_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["realm_entity_id"], ["entities.id"], name=op.f("fk_souls_realm_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_souls_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("spirit_entity_id", name=op.f("pk_souls")),
        sa.UniqueConstraint("mortal_entity_id", name=op.f("uq_souls_mortal_entity_id")),
    )
    with op.batch_alter_table("souls", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_souls_origin_world_id"), ["origin_world_id"], unique=False)

    op.create_table(
        "thread_links",
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("related", "advanced", name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_thread_links_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], name=op.f("fk_thread_links_thread_id_threads"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("thread_id", "entity_id", "role", name=op.f("pk_thread_links")),
    )
    with op.batch_alter_table("thread_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_thread_links_entity_id"), ["entity_id"], unique=False)

    op.create_table(
        "vessel_profiles",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("gate", "ship", "mount", "bridge", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_vessel_profiles_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_vessel_profiles")),
    )
    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_vessel_profiles_kind"), ["kind"], unique=False)

    op.create_table(
        "wars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("mobilizing", "ongoing", "ended", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "hostility",
                "uprising",
                "tribute_revolt",
                "incited",
                "declared",
                "betrayal",
                "conquest_journey",
                "foreign_god",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("cause_text", sa.Text(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("last_clash_epoch", sa.Integer(), nullable=True),
        sa.Column("battles", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("violence", sa.Integer(), nullable=True),
        sa.Column(
            "ending",
            sa.Enum(
                "victory",
                "conquest",
                "tribute",
                "exhaustion",
                "peace",
                "white_peace",
                "betrayal",
                "same_front",
                "no_side_left",
                "miracle",
                name="ending",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("victor_entity_id", sa.Integer(), nullable=True),
        sa.Column("loser_entity_id", sa.Integer(), nullable=True),
        sa.Column("incited_by_son_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("status <> 'ended' OR (ended_epoch IS NOT NULL AND ending IS NOT NULL)", name=op.f("ck_wars_ended_has_outcome")),
        sa.CheckConstraint("battles >= 0", name=op.f("ck_wars_battles_min")),
        sa.CheckConstraint("ended_epoch IS NULL OR ended_epoch >= started_epoch", name=op.f("ck_wars_ends_after_start")),
        sa.CheckConstraint(
            "victor_entity_id IS NULL OR loser_entity_id IS NULL OR victor_entity_id <> loser_entity_id", name=op.f("ck_wars_distinct_victor_loser")
        ),
        sa.ForeignKeyConstraint(["event_entity_id"], ["entities.id"], name=op.f("fk_wars_event_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incited_by_son_id"], ["sons.id"], name=op.f("fk_wars_incited_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["loser_entity_id"], ["entities.id"], name=op.f("fk_wars_loser_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["victor_entity_id"], ["entities.id"], name=op.f("fk_wars_victor_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_wars_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wars")),
        sa.UniqueConstraint("event_entity_id", name=op.f("uq_wars_event_entity_id")),
    )
    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.create_index("ix_wars_status", ["status"], unique=False)
        batch_op.create_index("ix_wars_world_status", ["world_id", "status"], unique=False)

    op.create_table(
        "armies",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("commander_entity_id", sa.Integer(), nullable=True),
        sa.Column("raised_epoch", sa.Integer(), nullable=False),
        sa.Column("disbanded_epoch", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["commander_entity_id"], ["entities.id"], name=op.f("fk_armies_commander_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_armies_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_armies_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_armies_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_armies")),
    )
    with op.batch_alter_table("armies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_armies_owner_entity_id"), ["owner_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_armies_war_id"), ["war_id"], unique=False)

    op.create_table(
        "bonds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "inside",
                "lives_in",
                "worships",
                "enemy",
                "ally",
                "descends_from",
                "protects",
                "rules",
                "owns",
                "beat",
                "killed",
                "cursed",
                "blessed",
                "source_of",
                "tells_of",
                "destroyed",
                "loves",
                "fears",
                "hunts",
                "trades_with",
                "prophesies",
                "caused",
                "celebrates",
                "forbids",
                "speaks",
                "produced",
                "built",
                "migrated_to",
                "discovered",
                "soul_descended_to",
                "party_to",
                "member_of",
                "knows",
                "pays_tribute",
                "related",
                "holds_captive",
                "spy_network",
                "pursues",
                "companion",
                "rival",
                "apprentice_of",
                "commands",
                "part_of",
                "passenger_of",
                "captain_of",
                "tamed",
                "truce",
                "owes",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "side",
                "victor",
                "loser",
                "commander",
                "dueled",
                "spirit_binding",
                "homeland",
                "mentioned_in_fate",
                "fulfilled_prophecy",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("active", "past", "hidden_rejected", "hidden_closed", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("closed_reason", sa.String(length=120), nullable=True),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("debt_amount", sa.Integer(), nullable=True),
        sa.Column("debt_what", sa.String(length=120), nullable=True),
        sa.Column("debt_due_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "debt_status",
            sa.Enum("open", "overdue", "repaid", "forgiven", name="debt_status", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("truce_until_epoch", sa.Integer(), nullable=True),
        sa.Column("pair_low", sa.Integer(), nullable=False),
        sa.Column("pair_high", sa.Integer(), nullable=False),
        sa.Column("role_key", sa.String(length=120), nullable=False),
        sa.Column("description_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint(
            "kind = 'owes' OR (debt_amount IS NULL AND debt_due_epoch IS NULL AND debt_status IS NULL)", name=op.f("ck_bonds_debt_only_on_owes")
        ),
        sa.CheckConstraint("kind = 'truce' OR truce_until_epoch IS NULL", name=op.f("ck_bonds_truce_only_on_truce")),
        sa.CheckConstraint("debt_amount IS NULL OR debt_amount >= 0", name=op.f("ck_bonds_debt_amount_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_bonds_epoch_min")),
        sa.CheckConstraint("source_node_id <> target_node_id", name=op.f("ck_bonds_not_self")),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_bonds_source_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_bonds_target_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_bonds_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bonds")),
    )
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.create_index("ix_bonds_pair", ["source_node_id", "target_node_id"], unique=False)
        batch_op.create_index("ix_bonds_pair_reverse", ["target_node_id", "source_node_id"], unique=False)
        batch_op.create_index("ix_bonds_source", ["source_node_id", "kind", "state"], unique=False)
        batch_op.create_index("ix_bonds_target", ["target_node_id", "kind", "state"], unique=False)
        batch_op.create_index(batch_op.f("ix_bonds_war_id"), ["war_id"], unique=False)
        batch_op.create_index(
            "ux_bonds_active_inside",
            ["source_node_id"],
            unique=True,
            sqlite_where=sa.text("state = 'active' AND kind = 'inside' AND (role IS NULL OR role <> 'spirit_binding')"),
        )
        batch_op.create_index(
            "ux_bonds_active_role",
            ["source_node_id", "target_node_id", "kind", "role_key", "description_key"],
            unique=True,
            sqlite_where=sa.text("state = 'active' AND kind IN ('party_to', 'related')"),
        )
        batch_op.create_index(
            "ux_bonds_active_singular",
            ["pair_low", "pair_high", "kind"],
            unique=True,
            sqlite_where=sa.text(
                "state = 'active' AND kind IN ('celebrates', 'descends_from', 'fears', 'forbids', 'loves', 'part_of', 'pursues', 'source_of', 'tells_of')"
            ),
        )
        batch_op.create_index(
            "ux_bonds_active_state",
            ["source_node_id", "target_node_id", "kind"],
            unique=True,
            sqlite_where=sa.text(
                "state = 'active' AND kind NOT IN ('ally', 'beat', 'blessed', 'caused', 'companion', 'cursed', 'destroyed', 'discovered', 'enemy', 'killed', 'migrated_to', 'party_to', 'prophesies', 'related', 'rival', 'trades_with', 'truce')"
            ),
        )
        batch_op.create_index(
            "ux_bonds_active_unordered",
            ["pair_low", "pair_high", "kind"],
            unique=True,
            sqlite_where=sa.text("state = 'active' AND kind IN ('ally', 'companion', 'enemy', 'rival', 'trades_with', 'truce')"),
        )

    op.create_table(
        "journeys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("traveller_entity_id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("vehicle_entity_id", sa.Integer(), nullable=True),
        sa.Column("origin_world_id", sa.Integer(), nullable=False),
        sa.Column("destination_world_id", sa.Integer(), nullable=False),
        sa.Column(
            "intent",
            sa.Enum("colony", "trade", "exploration", "conquest", "pilgrimage", name="intent", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.Column("epochs_left", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("underway", "waiting", "arrived", "lost", "recalled", "stranded", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("memory_lost", sa.Boolean(), nullable=False),
        sa.Column("start_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column("result_entity_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("epochs_left >= 0", name=op.f("ck_journeys_epochs_left_min")),
        sa.CheckConstraint("population >= 0", name=op.f("ck_journeys_population_min")),
        sa.ForeignKeyConstraint(["destination_world_id"], ["worlds.id"], name=op.f("fk_journeys_destination_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_world_id"], ["worlds.id"], name=op.f("fk_journeys_origin_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_entity_id"], ["entities.id"], name=op.f("fk_journeys_result_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_journeys_route_id_routes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["traveller_entity_id"], ["entities.id"], name=op.f("fk_journeys_traveller_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_entity_id"], ["entities.id"], name=op.f("fk_journeys_vehicle_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journeys")),
    )
    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.create_index("ix_journeys_route", ["route_id", "status"], unique=False)
        batch_op.create_index("ix_journeys_status", ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_journeys_traveller_entity_id"), ["traveller_entity_id"], unique=False)

    op.create_table(
        "legendary_quests",
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("dead_star", "sealed_gate", "archive", "expel_outer", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("target_star_id", sa.Integer(), nullable=True),
        sa.Column("target_route_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "opened_by",
            sa.Enum(
                "creator", "son", "mortal", "foreign_god", "fate", "engine", "system", name="opened_by", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("deadline_epoch", sa.Integer(), nullable=False),
        sa.Column("prior_journey_ids", sa.JSON(), nullable=False),
        sa.Column(
            "outcome", sa.Enum("completed", "failed", "invalidated", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_legendary_quests_target_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_route_id"], ["routes.id"], name=op.f("fk_legendary_quests_target_route_id_routes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_star_id"], ["stars.id"], name=op.f("fk_legendary_quests_target_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], name=op.f("fk_legendary_quests_thread_id_threads"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("thread_id", name=op.f("pk_legendary_quests")),
    )
    op.create_table(
        "sieges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column("besieged_entity_id", sa.Integer(), nullable=False),
        sa.Column("besieger_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum("ongoing", "breached", "repulsed", "lifted", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.CheckConstraint("rounds >= 0", name=op.f("ck_sieges_rounds_min")),
        sa.ForeignKeyConstraint(["besieged_entity_id"], ["entities.id"], name=op.f("fk_sieges_besieged_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["besieger_entity_id"], ["entities.id"], name=op.f("fk_sieges_besieger_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_sieges_war_id_wars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sieges")),
    )
    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.create_index("ix_sieges_war_status", ["war_id", "status"], unique=False)

    op.create_table(
        "sky_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("eclipse", "comet", "alignment", "supernova", "black_sun", "void_storm", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("star_id", sa.Integer(), nullable=True),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("caused_by_node_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_sky_events_epoch_min")),
        sa.CheckConstraint("until_epoch IS NULL OR until_epoch >= epoch", name=op.f("ck_sky_events_until_after_start")),
        sa.ForeignKeyConstraint(["caused_by_node_id"], ["nodes.id"], name=op.f("fk_sky_events_caused_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_sky_events_route_id_routes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_sky_events_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_sky_events_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sky_events")),
    )
    with op.batch_alter_table("sky_events", schema=None) as batch_op:
        batch_op.create_index("ix_sky_events_world_epoch", ["world_id", "epoch"], unique=False)

    op.create_table(
        "war_sides",
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("side", sa.Enum("attacker", "defender", name="side", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("left_epoch", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_war_sides_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_war_sides_war_id_wars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("war_id", "entity_id", name=op.f("pk_war_sides")),
        sa.UniqueConstraint("war_id", "side", "entity_id", name="uq_war_sides_side_entity"),
    )
    with op.batch_alter_table("war_sides", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_war_sides_entity_id"), ["entity_id"], unique=False)

    op.create_table(
        "battles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("record_entity_id", sa.Integer(), nullable=True),
        sa.Column("place_entity_id", sa.Integer(), nullable=True),
        sa.Column("winner_entity_id", sa.Integer(), nullable=False),
        sa.Column("loser_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum(
                "field_victory",
                "great_victory",
                "siege_repulsed",
                "siege_breached",
                "siege_starvation",
                name="outcome",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("gap", sa.Double(), nullable=False),
        sa.Column("siege_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["loser_entity_id"], ["entities.id"], name=op.f("fk_battles_loser_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_battles_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["record_entity_id"], ["entities.id"], name=op.f("fk_battles_record_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["siege_id"], ["sieges.id"], name=op.f("fk_battles_siege_id_sieges"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_battles_war_id_wars"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_entity_id"], ["entities.id"], name=op.f("fk_battles_winner_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_battles")),
    )
    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.create_index("ix_battles_war_epoch", ["war_id", "epoch"], unique=False)

    op.create_table(
        "captives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("captive_entity_id", sa.Integer(), nullable=False),
        sa.Column("captor_entity_id", sa.Integer(), nullable=False),
        sa.Column("home_entity_id", sa.Integer(), nullable=True),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("bond_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "held",
                "ransomed",
                "escaped",
                "executed",
                "turncoat",
                "rescued",
                "released",
                name="status",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("taken_epoch", sa.Integer(), nullable=False),
        sa.Column("released_epoch", sa.Integer(), nullable=True),
        sa.Column("ransom_paid", sa.Integer(), nullable=True),
        sa.CheckConstraint("captive_entity_id <> captor_entity_id", name=op.f("ck_captives_distinct_parties")),
        sa.ForeignKeyConstraint(["bond_id"], ["bonds.id"], name=op.f("fk_captives_bond_id_bonds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["captive_entity_id"], ["entities.id"], name=op.f("fk_captives_captive_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["captor_entity_id"], ["entities.id"], name=op.f("fk_captives_captor_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_entity_id"], ["entities.id"], name=op.f("fk_captives_home_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_captives_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_captives")),
    )
    with op.batch_alter_table("captives", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_captives_captive_entity_id"), ["captive_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_captives_captor_entity_id"), ["captor_entity_id"], unique=False)
        batch_op.create_index("ix_captives_status", ["status"], unique=False)

    op.create_table(
        "hero_quests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hero_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("hunt", "thread", "relic", "knowledge", "vengeance", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("bond_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "succeeded", "failed", "died", "abandoned", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["bond_id"], ["bonds.id"], name=op.f("fk_hero_quests_bond_id_bonds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hero_entity_id"], ["entities.id"], name=op.f("fk_hero_quests_hero_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_hero_quests_target_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], name=op.f("fk_hero_quests_thread_id_threads"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hero_quests")),
    )
    with op.batch_alter_table("hero_quests", schema=None) as batch_op:
        batch_op.create_index("ix_hero_quests_hero_status", ["hero_entity_id", "status"], unique=False)

    op.create_table(
        "tributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payer_entity_id", sa.Integer(), nullable=False),
        sa.Column("receiver_entity_id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("bond_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("active", "ended", "revolted", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("payer_entity_id <> receiver_entity_id", name=op.f("ck_tributes_distinct_parties")),
        sa.ForeignKeyConstraint(["bond_id"], ["bonds.id"], name=op.f("fk_tributes_bond_id_bonds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payer_entity_id"], ["entities.id"], name=op.f("fk_tributes_payer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_entity_id"], ["entities.id"], name=op.f("fk_tributes_receiver_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_tributes_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tributes")),
    )
    with op.batch_alter_table("tributes", schema=None) as batch_op:
        batch_op.create_index("ix_tributes_pair", ["payer_entity_id", "receiver_entity_id"], unique=False)
        batch_op.create_index("ix_tributes_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("tributes", schema=None) as batch_op:
        batch_op.drop_index("ix_tributes_status")
        batch_op.drop_index("ix_tributes_pair")

    op.drop_table("tributes")
    with op.batch_alter_table("hero_quests", schema=None) as batch_op:
        batch_op.drop_index("ix_hero_quests_hero_status")

    op.drop_table("hero_quests")
    with op.batch_alter_table("captives", schema=None) as batch_op:
        batch_op.drop_index("ix_captives_status")
        batch_op.drop_index(batch_op.f("ix_captives_captor_entity_id"))
        batch_op.drop_index(batch_op.f("ix_captives_captive_entity_id"))

    op.drop_table("captives")
    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.drop_index("ix_battles_war_epoch")

    op.drop_table("battles")
    with op.batch_alter_table("war_sides", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_war_sides_entity_id"))

    op.drop_table("war_sides")
    with op.batch_alter_table("sky_events", schema=None) as batch_op:
        batch_op.drop_index("ix_sky_events_world_epoch")

    op.drop_table("sky_events")
    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.drop_index("ix_sieges_war_status")

    op.drop_table("sieges")
    op.drop_table("legendary_quests")
    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_journeys_traveller_entity_id"))
        batch_op.drop_index("ix_journeys_status")
        batch_op.drop_index("ix_journeys_route")

    op.drop_table("journeys")
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.drop_index(
            "ux_bonds_active_unordered", sqlite_where=sa.text("state = 'active' AND kind IN ('ally', 'companion', 'enemy', 'rival', 'trades_with', 'truce')")
        )
        batch_op.drop_index(
            "ux_bonds_active_state",
            sqlite_where=sa.text(
                "state = 'active' AND kind NOT IN ('ally', 'beat', 'blessed', 'caused', 'companion', 'cursed', 'destroyed', 'discovered', 'enemy', 'killed', 'migrated_to', 'party_to', 'prophesies', 'related', 'rival', 'trades_with', 'truce')"
            ),
        )
        batch_op.drop_index(
            "ux_bonds_active_singular",
            sqlite_where=sa.text(
                "state = 'active' AND kind IN ('celebrates', 'descends_from', 'fears', 'forbids', 'loves', 'part_of', 'pursues', 'source_of', 'tells_of')"
            ),
        )
        batch_op.drop_index("ux_bonds_active_role", sqlite_where=sa.text("state = 'active' AND kind IN ('party_to', 'related')"))
        batch_op.drop_index(
            "ux_bonds_active_inside", sqlite_where=sa.text("state = 'active' AND kind = 'inside' AND (role IS NULL OR role <> 'spirit_binding')")
        )
        batch_op.drop_index(batch_op.f("ix_bonds_war_id"))
        batch_op.drop_index("ix_bonds_target")
        batch_op.drop_index("ix_bonds_source")
        batch_op.drop_index("ix_bonds_pair_reverse")
        batch_op.drop_index("ix_bonds_pair")

    op.drop_table("bonds")
    with op.batch_alter_table("armies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_armies_war_id"))
        batch_op.drop_index(batch_op.f("ix_armies_owner_entity_id"))

    op.drop_table("armies")
    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.drop_index("ix_wars_world_status")
        batch_op.drop_index("ix_wars_status")

    op.drop_table("wars")
    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_vessel_profiles_kind"))

    op.drop_table("vessel_profiles")
    with op.batch_alter_table("thread_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_thread_links_entity_id"))

    op.drop_table("thread_links")
    with op.batch_alter_table("souls", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_souls_origin_world_id"))

    op.drop_table("souls")
    with op.batch_alter_table("routes", schema=None) as batch_op:
        batch_op.drop_index("ix_routes_world_b")
        batch_op.drop_index("ix_routes_world_a")

    op.drop_table("routes")
    with op.batch_alter_table("reverences", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reverences_god_node_id"))

    op.drop_table("reverences")
    with op.batch_alter_table("resurrection_orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resurrection_orders_son_id"))

    op.drop_table("resurrection_orders")
    with op.batch_alter_table("resource_mechanics", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resource_mechanics_mechanic"))

    op.drop_table("resource_mechanics")
    with op.batch_alter_table("resource_commodities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resource_commodities_commodity"))

    op.drop_table("resource_commodities")
    op.drop_table("outer_bargains")
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index("ix_notifications_unread")
        batch_op.drop_index("ix_notifications_category")

    op.drop_table("notifications")
    op.drop_table("network_reviews")
    with op.batch_alter_table("lexemes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lexemes_language_entity_id"))

    op.drop_table("lexemes")
    op.drop_table("language_profiles")
    with op.batch_alter_table("horizon_intuitions", schema=None) as batch_op:
        batch_op.drop_index("ix_horizon_intuitions_status")

    op.drop_table("horizon_intuitions")
    with op.batch_alter_table("historian_views", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_historian_views_epoch"))

    op.drop_table("historian_views")
    with op.batch_alter_table("folk_beliefs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_folk_beliefs_god_node_id"))

    op.drop_table("folk_beliefs")
    op.drop_table("epoch_agents")
    with op.batch_alter_table("entity_traits", schema=None) as batch_op:
        batch_op.drop_index("ix_entity_traits_trait")

    op.drop_table("entity_traits")
    with op.batch_alter_table("entity_tags", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_entity_tags_tag"))

    op.drop_table("entity_tags")
    with op.batch_alter_table("entity_flags", schema=None) as batch_op:
        batch_op.drop_index("ix_entity_flags_flag")

    op.drop_table("entity_flags")
    with op.batch_alter_table("designated_heirs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_designated_heirs_heir_entity_id"))

    op.drop_table("designated_heirs")
    with op.batch_alter_table("creation_verdicts", schema=None) as batch_op:
        batch_op.drop_index("ix_creation_verdicts_epoch_verdict")

    op.drop_table("creation_verdicts")
    with op.batch_alter_table("creation_rewards", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_creation_rewards_son_id"))

    op.drop_table("creation_rewards")
    with op.batch_alter_table("creation_motifs", schema=None) as batch_op:
        batch_op.drop_index("ix_creation_motifs_motif_epoch")

    op.drop_table("creation_motifs")
    op.drop_table("community_societies")
    with op.batch_alter_table("community_relations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_community_relations_entity_b_id"))

    op.drop_table("community_relations")
    with op.batch_alter_table("community_relation_events", schema=None) as batch_op:
        batch_op.drop_index("ix_community_relation_events_pair")

    op.drop_table("community_relation_events")
    op.drop_table("civilization_tier_locks")
    with op.batch_alter_table("chronicle_entities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chronicle_entities_entity_id"))

    op.drop_table("chronicle_entities")
    with op.batch_alter_table("canon_facts", schema=None) as batch_op:
        batch_op.drop_index("ix_canon_facts_subject")
        batch_op.drop_index("ix_canon_facts_object")

    op.drop_table("canon_facts")
    op.drop_table("archive_holdings")
    op.drop_table("addictions")
    op.drop_table("addiction_immunities")
    op.drop_table("son_relations")
    with op.batch_alter_table("son_powers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_son_powers_effect"))

    op.drop_table("son_powers")
    op.drop_table("foreign_god_powers")
    with op.batch_alter_table("fate_rewards", schema=None) as batch_op:
        batch_op.drop_index("ix_fate_rewards_son_epoch")

    op.drop_table("fate_rewards")
    with op.batch_alter_table("entities", schema=None) as batch_op:
        batch_op.drop_index("ix_entities_world_type_status")
        batch_op.drop_index(batch_op.f("ix_entities_world_id"))
        batch_op.drop_index("ix_entities_type_status")
        batch_op.drop_index("ix_entities_pending", sqlite_where=sa.text("pending_name = 1"))
        batch_op.drop_index(batch_op.f("ix_entities_maker_entity_id"))
        batch_op.drop_index(batch_op.f("ix_entities_location_id"))
        batch_op.drop_index(batch_op.f("ix_entities_importance"))
        batch_op.drop_index("ix_entities_engine_kind_status")
        batch_op.drop_index(batch_op.f("ix_entities_creator_son_id"))

    op.drop_table("entities")
    op.drop_table("climate_orders")
    with op.batch_alter_table("chronicle", schema=None) as batch_op:
        batch_op.drop_index("ix_chronicle_world_epoch")
        batch_op.drop_index("ix_chronicle_son")
        batch_op.drop_index("ix_chronicle_kind_epoch")
        batch_op.drop_index("ix_chronicle_epoch")

    op.drop_table("chronicle")
    op.drop_table("world_maps")
    with op.batch_alter_table("world_leak_items", schema=None) as batch_op:
        batch_op.drop_index("ix_world_leak_items_epoch_world")

    op.drop_table("world_leak_items")
    with op.batch_alter_table("sons", schema=None) as batch_op:
        batch_op.drop_index("ix_sons_status")
        batch_op.drop_index(batch_op.f("ix_sons_parent_son_id"))
        batch_op.drop_index(batch_op.f("ix_sons_current_world_id"))

    op.drop_table("sons")
    with op.batch_alter_table("motif_overrides", schema=None) as batch_op:
        batch_op.drop_index("ix_motif_overrides_world")

    op.drop_table("motif_overrides")
    op.drop_table("map_snapshots")
    with op.batch_alter_table("map_notes", schema=None) as batch_op:
        batch_op.drop_index("ix_map_notes_world")

    op.drop_table("map_notes")
    with op.batch_alter_table("foreign_gods", schema=None) as batch_op:
        batch_op.drop_index("ix_foreign_gods_world_status")

    op.drop_table("foreign_gods")
    op.drop_table("epoch_world_narratives")
    with op.batch_alter_table("deferred_steps", schema=None) as batch_op:
        batch_op.drop_index("ix_deferred_steps_status")

    op.drop_table("deferred_steps")
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_worlds_star_id"))
        batch_op.drop_index(batch_op.f("ix_worlds_patron_son_id"))
        batch_op.drop_index(batch_op.f("ix_worlds_parent_world_id"))
        batch_op.drop_index("ix_worlds_discovery")
        batch_op.drop_index(batch_op.f("ix_worlds_creator_son_id"))

    op.drop_table("worlds")
    with op.batch_alter_table("ledger_changes", schema=None) as batch_op:
        batch_op.drop_index("ix_ledger_changes_row")
        batch_op.drop_index(batch_op.f("ix_ledger_changes_entry_id"))

    op.drop_table("ledger_changes")
    with op.batch_alter_table("action_records", schema=None) as batch_op:
        batch_op.drop_index("ix_action_records_target")
        batch_op.drop_index("ix_action_records_kind_epoch")
        batch_op.drop_index("ix_action_records_actor_epoch")

    op.drop_table("action_records")
    op.drop_table("turn_counters")
    op.drop_table("stars")
    op.drop_table("name_registry")
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_index("ix_messages_sender")
        batch_op.drop_index("ix_messages_recipient")

    op.drop_table("messages")
    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.drop_index("ix_ledger_entries_epoch")
        batch_op.drop_index("ix_ledger_entries_actor")

    op.drop_table("ledger_entries")
    with op.batch_alter_table("images", schema=None) as batch_op:
        batch_op.drop_index("ix_images_target")
        batch_op.drop_index("ix_images_sha256")
        batch_op.drop_index("ix_images_object_key")

    op.drop_table("images")
    with op.batch_alter_table("god_conflicts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_god_conflicts_epoch"))
        batch_op.drop_index(batch_op.f("ix_god_conflicts_defender_node_id"))
        batch_op.drop_index(batch_op.f("ix_god_conflicts_attacker_node_id"))

    op.drop_table("god_conflicts")
    op.drop_table("epoch_steps")
    op.drop_table("epoch_phase_timings")
    op.drop_table("epoch_engine_phases")
    op.drop_table("creator")
    with op.batch_alter_table("agent_turns", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_agent_turns_epoch"))

    op.drop_table("agent_turns")
    with op.batch_alter_table("threads", schema=None) as batch_op:
        batch_op.drop_index("ix_threads_status")

    op.drop_table("threads")
    op.drop_table("scores")
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.drop_index("ux_scenarios_running_key", sqlite_where=sa.text("status = 'running'"))

    op.drop_table("scenarios")
    op.drop_table("rule_overrides")
    with op.batch_alter_table("nodes", schema=None) as batch_op:
        batch_op.drop_index("ix_nodes_kind_name")
        batch_op.drop_index(batch_op.f("ix_nodes_kind"))

    op.drop_table("nodes")
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_jobs_status"))
        batch_op.drop_index(batch_op.f("ix_jobs_kind"))

    op.drop_table("jobs")
    op.drop_table("epochs")
    op.drop_table("epoch_year_cursors")
    op.drop_table("epoch_stats")
    op.drop_table("epoch_runs")
    with op.batch_alter_table("creator_mood_inputs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_creator_mood_inputs_epoch"))

    op.drop_table("creator_mood_inputs")
    with op.batch_alter_table("councils", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_councils_epoch"))

    op.drop_table("councils")
    op.drop_table("cosmos")
    op.drop_table("applied_fixups")
    op.drop_table("achievements")
