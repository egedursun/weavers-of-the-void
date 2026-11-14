import sqlalchemy as sa
from alembic import op

revision = "88d61a5796a9"
down_revision = "0f1d26d58e9d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("began_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "variant",
            sa.Enum(
                "ruin",
                "world_war",
                "outer_descent",
                "twilight_of_gods",
                "dimensional_collapse",
                "galactic_death",
                name="variant",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("carried", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("began_epoch >= 0", name=op.f("ck_ages_began_epoch_min")),
        sa.CheckConstraint("carried BETWEEN 0 AND 100", name=op.f("ck_ages_carried_range")),
        sa.CheckConstraint("number >= 1", name=op.f("ck_ages_number_min")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ages")),
    )
    op.create_table(
        "age_echoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("age_id", sa.Integer(), nullable=False),
        sa.Column(
            "template",
            sa.Enum(
                "rise_and_fall",
                "rags_to_riches",
                "revenge",
                "redemption",
                "quest",
                "tragedy",
                "forbidden_love",
                "rivalry",
                "mentor_and_heir",
                "exile_and_return",
                "corruption",
                "coming_of_age",
                "fall_of_a_house",
                "founding",
                "apotheosis",
                name="template",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("rival", "mentor", "beloved", "betrayer", "heir", "foe", "ally", name="role", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("echo_node_id", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_age_echoes_weight_range")),
        sa.ForeignKeyConstraint(["age_id"], ["ages.id"], name=op.f("fk_age_echoes_age_id_ages"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["echo_node_id"], ["nodes.id"], name=op.f("fk_age_echoes_echo_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_age_echoes_source_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_age_echoes")),
    )
    with op.batch_alter_table("age_echoes", schema=None) as batch_op:
        batch_op.create_index("ix_age_echoes_age", ["age_id"], unique=False)

    op.create_table(
        "setups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("prophecy", "omen", "dream", "foresight", "thread", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "payoff", sa.Enum("open", "fulfilled", "subverted", "lapsed", name="payoff", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("paid_epoch", sa.Integer(), nullable=True),
        sa.Column("payoff_text", sa.String(length=480), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_setups_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_setups")),
    )
    with op.batch_alter_table("setups", schema=None) as batch_op:
        batch_op.create_index("ix_setups_source", ["kind", "source_id"], unique=False)
        batch_op.create_index("ix_setups_subject", ["subject_node_id", "payoff"], unique=False)

    op.create_table(
        "arcs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "template",
            sa.Enum(
                "rise_and_fall",
                "rags_to_riches",
                "revenge",
                "redemption",
                "quest",
                "tragedy",
                "forbidden_love",
                "rivalry",
                "mentor_and_heir",
                "exile_and_return",
                "corruption",
                "coming_of_age",
                "fall_of_a_house",
                "founding",
                "apotheosis",
                name="template",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.Enum("inciting", "rising", "crisis", "climax", "resolution", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.Enum("open", "fulfilled", "failed", "twisted", "ironic", name="outcome", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("beats", sa.Integer(), nullable=False),
        sa.Column("drama", sa.Integer(), nullable=False),
        sa.Column("echo_id", sa.Integer(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("last_beat_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("beats >= 0", name=op.f("ck_arcs_beats_min")),
        sa.CheckConstraint("drama BETWEEN 0 AND 100", name=op.f("ck_arcs_drama_range")),
        sa.ForeignKeyConstraint(["echo_id"], ["age_echoes.id"], name=op.f("fk_arcs_echo_id_age_echoes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_arcs_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arcs")),
    )
    with op.batch_alter_table("arcs", schema=None) as batch_op:
        batch_op.create_index("ix_arcs_subject", ["subject_node_id", "outcome"], unique=False)

    op.create_table(
        "eco_transformations",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("target_moisture", sa.Integer(), nullable=False),
        sa.Column("target_forest", sa.Integer(), nullable=False),
        sa.Column("target_fertility", sa.Integer(), nullable=False),
        sa.Column("regions_changed", sa.Integer(), nullable=False),
        sa.Column("resistance", sa.Integer(), nullable=False),
        sa.Column("sabotage", sa.Integer(), nullable=False),
        sa.Column("last_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("regions_changed >= 0", name=op.f("ck_eco_transformations_regions_changed_min")),
        sa.CheckConstraint("resistance BETWEEN 0 AND 100", name=op.f("ck_eco_transformations_resistance_range")),
        sa.CheckConstraint("sabotage >= 0", name=op.f("ck_eco_transformations_sabotage_min")),
        sa.CheckConstraint("target_fertility BETWEEN 0 AND 100", name=op.f("ck_eco_transformations_target_fertility_range")),
        sa.CheckConstraint("target_forest BETWEEN 0 AND 100", name=op.f("ck_eco_transformations_target_forest_range")),
        sa.CheckConstraint("target_moisture BETWEEN 0 AND 100", name=op.f("ck_eco_transformations_target_moisture_range")),
        sa.ForeignKeyConstraint(["plan_id"], ["long_plans.id"], name=op.f("fk_eco_transformations_plan_id_long_plans"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", name=op.f("pk_eco_transformations")),
    )
    op.create_table(
        "arc_beats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("arc_id", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("inciting", "rising", "crisis", "climax", "resolution", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("text", sa.String(length=480), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["arc_id"], ["arcs.id"], name=op.f("fk_arc_beats_arc_id_arcs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arc_beats")),
    )
    with op.batch_alter_table("arc_beats", schema=None) as batch_op:
        batch_op.create_index("ix_arc_beats_arc", ["arc_id"], unique=False)

    op.create_table(
        "arc_figures",
        sa.Column("arc_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("rival", "mentor", "beloved", "betrayer", "heir", "foe", "ally", name="role", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["arc_id"], ["arcs.id"], name=op.f("fk_arc_figures_arc_id_arcs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_arc_figures_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("arc_id", "node_id", name=op.f("pk_arc_figures")),
    )
    with op.batch_alter_table("arc_figures", schema=None) as batch_op:
        batch_op.create_index("ix_arc_figures_node", ["node_id"], unique=False)

    op.create_table(
        "formation_histories",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("zone", sa.Enum("inner", "snow_line", "outer", name="zone", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("migration", sa.Enum("none", "inward", "outward", name="migration", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("bombardment", sa.Integer(), nullable=False),
        sa.Column("craters", sa.Integer(), nullable=False),
        sa.Column("core_share", sa.Integer(), nullable=False),
        sa.Column("mantle_heat", sa.Integer(), nullable=False),
        sa.Column("water_delivered", sa.Integer(), nullable=False),
        sa.Column("exotic_delivered", sa.Integer(), nullable=False),
        sa.Column("shaped", sa.Boolean(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bombardment BETWEEN 0 AND 100", name=op.f("ck_formation_histories_bombardment_range")),
        sa.CheckConstraint("core_share BETWEEN 0 AND 100", name=op.f("ck_formation_histories_core_share_range")),
        sa.CheckConstraint("craters >= 0", name=op.f("ck_formation_histories_craters_min")),
        sa.CheckConstraint("exotic_delivered BETWEEN 0 AND 100", name=op.f("ck_formation_histories_exotic_delivered_range")),
        sa.CheckConstraint("mantle_heat BETWEEN 0 AND 100", name=op.f("ck_formation_histories_mantle_heat_range")),
        sa.CheckConstraint("water_delivered BETWEEN 0 AND 100", name=op.f("ck_formation_histories_water_delivered_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_formation_histories_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_formation_histories")),
    )
    op.create_table(
        "irregular_seasons",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("cause", sa.Enum("orbit", "divine", name="cause", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("spell", sa.Enum("summer", "winter", name="spell", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("spell_started_epoch", sa.Integer(), nullable=False),
        sa.Column("spell_length", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("by_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_irregular_seasons_severity_range")),
        sa.CheckConstraint("spell_length >= 1", name=op.f("ck_irregular_seasons_spell_length_min")),
        sa.CheckConstraint("spell_started_epoch >= 0", name=op.f("ck_irregular_seasons_spell_started_epoch_min")),
        sa.ForeignKeyConstraint(["by_node_id"], ["nodes.id"], name=op.f("fk_irregular_seasons_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_irregular_seasons_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_irregular_seasons")),
    )
    op.create_table(
        "winter_forecasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("scholar_entity_id", sa.Integer(), nullable=True),
        sa.Column("predicted_end_epoch", sa.Integer(), nullable=False),
        sa.Column("heeded", sa.Boolean(), nullable=False),
        sa.Column("made_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_winter_forecasts_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scholar_entity_id"], ["entities.id"], name=op.f("fk_winter_forecasts_scholar_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_winter_forecasts_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_winter_forecasts")),
        sa.UniqueConstraint("world_id", "people_entity_id", name="uq_winter_forecasts_world_people"),
    )
    with op.batch_alter_table("winter_forecasts", schema=None) as batch_op:
        batch_op.create_index("ix_winter_forecasts_people", ["people_entity_id"], unique=False)

    with op.batch_alter_table("cosmos", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "age_cycle",
                sa.Enum("linear", "cyclic", name="age_cycle", native_enum=False, create_constraint=True, length=40),
                server_default="linear",
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("cosmos", schema=None) as batch_op:
        batch_op.drop_column("age_cycle")

    with op.batch_alter_table("winter_forecasts", schema=None) as batch_op:
        batch_op.drop_index("ix_winter_forecasts_people")

    op.drop_table("winter_forecasts")
    op.drop_table("irregular_seasons")
    op.drop_table("formation_histories")
    with op.batch_alter_table("arc_figures", schema=None) as batch_op:
        batch_op.drop_index("ix_arc_figures_node")

    op.drop_table("arc_figures")
    with op.batch_alter_table("arc_beats", schema=None) as batch_op:
        batch_op.drop_index("ix_arc_beats_arc")

    op.drop_table("arc_beats")
    op.drop_table("eco_transformations")
    with op.batch_alter_table("arcs", schema=None) as batch_op:
        batch_op.drop_index("ix_arcs_subject")

    op.drop_table("arcs")
    with op.batch_alter_table("setups", schema=None) as batch_op:
        batch_op.drop_index("ix_setups_subject")
        batch_op.drop_index("ix_setups_source")

    op.drop_table("setups")
    with op.batch_alter_table("age_echoes", schema=None) as batch_op:
        batch_op.drop_index("ix_age_echoes_age")

    op.drop_table("age_echoes")
    op.drop_table("ages")
