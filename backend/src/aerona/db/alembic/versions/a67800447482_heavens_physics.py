import sqlalchemy as sa
from alembic import op

revision = "a67800447482"
down_revision = "c3f8a1d5e7b9"
branch_labels = None
depends_on = None


OLD_SKY_EVENTS = ("eclipse", "comet", "alignment", "supernova", "black_sun", "void_storm", "flare")
NEW_SKY_EVENTS = (*OLD_SKY_EVENTS, "aurora", "transit")


def sky_kinds(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="kind", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    op.create_table(
        "star_systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("galaxy_id", sa.Integer(), nullable=True),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("separation", sa.Float(), nullable=False),
        sa.Column("band_inner", sa.Float(), nullable=False),
        sa.Column("band_outer", sa.Float(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 1", name=op.f("ck_star_systems_created_epoch_min")),
        sa.CheckConstraint("separation >= 0", name=op.f("ck_star_systems_separation_positive")),
        sa.ForeignKeyConstraint(["galaxy_id"], ["galaxies.id"], name=op.f("fk_star_systems_galaxy_id_galaxies"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_star_systems")),
    )
    with op.batch_alter_table("star_systems", schema=None) as batch_op:
        batch_op.create_index("ix_star_systems_galaxy", ["galaxy_id"], unique=False)

    op.create_table(
        "terraforming",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "aim",
            sa.Enum(
                "thicken_air",
                "thin_air",
                "breathable_air",
                "warm",
                "cool",
                "water",
                "dry",
                "brighten",
                "darken",
                name="aim",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("by_node_id", sa.Integer(), nullable=True),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("epochs_left", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epochs_left >= 0", name=op.f("ck_terraforming_epochs_left_min")),
        sa.CheckConstraint("started_epoch >= 1", name=op.f("ck_terraforming_started_epoch_min")),
        sa.CheckConstraint("step BETWEEN 1 AND 100", name=op.f("ck_terraforming_step_range")),
        sa.ForeignKeyConstraint(["by_node_id"], ["nodes.id"], name=op.f("fk_terraforming_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_terraforming_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_terraforming")),
    )
    with op.batch_alter_table("terraforming", schema=None) as batch_op:
        batch_op.create_index("ix_terraforming_world", ["world_id"], unique=False)

    op.create_table(
        "world_life",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "complexity",
            sa.Enum("none", "microbial", "simple", "complex", "sapient", name="complexity", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("environments", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_life_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_life")),
    )
    op.create_table(
        "world_physics",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("eccentricity", sa.Float(), nullable=False),
        sa.Column("inclination", sa.Float(), nullable=False),
        sa.Column("argument", sa.Float(), nullable=False),
        sa.Column("mass", sa.Float(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("iron", sa.Integer(), nullable=False),
        sa.Column("rock", sa.Integer(), nullable=False),
        sa.Column("ice", sa.Integer(), nullable=False),
        sa.Column("gas", sa.Integer(), nullable=False),
        sa.Column("exotic", sa.Integer(), nullable=False),
        sa.Column("rotation_hours", sa.Float(), nullable=False),
        sa.Column("nitrogen", sa.Integer(), nullable=False),
        sa.Column("oxygen", sa.Integer(), nullable=False),
        sa.Column("carbon_dioxide", sa.Integer(), nullable=False),
        sa.Column("methane", sa.Integer(), nullable=False),
        sa.Column("water_vapour", sa.Integer(), nullable=False),
        sa.Column("exotic_gas", sa.Integer(), nullable=False),
        sa.Column("pressure", sa.Float(), nullable=False),
        sa.Column("albedo", sa.Integer(), nullable=False),
        sa.Column("tectonics", sa.Integer(), nullable=False),
        sa.Column("volcanism", sa.Integer(), nullable=False),
        sa.Column("hydrosphere", sa.Integer(), nullable=False),
        sa.Column("cryosphere", sa.Integer(), nullable=False),
        sa.Column("circumbinary", sa.Boolean(), nullable=False),
        sa.Column("insolation", sa.Float(), nullable=False),
        sa.Column("surface_temperature", sa.Float(), nullable=False),
        sa.Column("gravity_g", sa.Float(), nullable=False),
        sa.Column("escape_velocity", sa.Float(), nullable=False),
        sa.Column("tidally_locked", sa.Boolean(), nullable=False),
        sa.Column("ringed", sa.Boolean(), nullable=False),
        sa.Column("aurora", sa.Integer(), nullable=False),
        sa.Column("eclipse_years", sa.Integer(), nullable=False),
        sa.Column("heat_shift", sa.Integer(), nullable=False),
        sa.Column("sea_level", sa.Integer(), nullable=False),
        sa.Column("habitable", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("albedo BETWEEN 0 AND 100", name=op.f("ck_world_physics_albedo_range")),
        sa.CheckConstraint("aurora BETWEEN 0 AND 100", name=op.f("ck_world_physics_aurora_range")),
        sa.CheckConstraint("carbon_dioxide BETWEEN 0 AND 100", name=op.f("ck_world_physics_carbon_dioxide_range")),
        sa.CheckConstraint("cryosphere BETWEEN 0 AND 100", name=op.f("ck_world_physics_cryosphere_range")),
        sa.CheckConstraint("eccentricity >= 0 AND eccentricity < 1", name=op.f("ck_world_physics_eccentricity_range")),
        sa.CheckConstraint("exotic BETWEEN 0 AND 100", name=op.f("ck_world_physics_exotic_range")),
        sa.CheckConstraint("exotic_gas BETWEEN 0 AND 100", name=op.f("ck_world_physics_exotic_gas_range")),
        sa.CheckConstraint("gas BETWEEN 0 AND 100", name=op.f("ck_world_physics_gas_range")),
        sa.CheckConstraint("hydrosphere BETWEEN 0 AND 100", name=op.f("ck_world_physics_hydrosphere_range")),
        sa.CheckConstraint("ice BETWEEN 0 AND 100", name=op.f("ck_world_physics_ice_range")),
        sa.CheckConstraint("iron BETWEEN 0 AND 100", name=op.f("ck_world_physics_iron_range")),
        sa.CheckConstraint("mass > 0", name=op.f("ck_world_physics_mass_positive")),
        sa.CheckConstraint("methane BETWEEN 0 AND 100", name=op.f("ck_world_physics_methane_range")),
        sa.CheckConstraint("nitrogen BETWEEN 0 AND 100", name=op.f("ck_world_physics_nitrogen_range")),
        sa.CheckConstraint("oxygen BETWEEN 0 AND 100", name=op.f("ck_world_physics_oxygen_range")),
        sa.CheckConstraint("pressure >= 0", name=op.f("ck_world_physics_pressure_positive")),
        sa.CheckConstraint("radius > 0", name=op.f("ck_world_physics_radius_positive")),
        sa.CheckConstraint("rock BETWEEN 0 AND 100", name=op.f("ck_world_physics_rock_range")),
        sa.CheckConstraint("rotation_hours > 0", name=op.f("ck_world_physics_rotation_positive")),
        sa.CheckConstraint("tectonics BETWEEN 0 AND 100", name=op.f("ck_world_physics_tectonics_range")),
        sa.CheckConstraint("volcanism BETWEEN 0 AND 100", name=op.f("ck_world_physics_volcanism_range")),
        sa.CheckConstraint("water_vapour BETWEEN 0 AND 100", name=op.f("ck_world_physics_water_vapour_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_physics_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_physics")),
    )
    op.create_table(
        "star_physics",
        sa.Column("star_id", sa.Integer(), nullable=False),
        sa.Column("mass", sa.Float(), nullable=False),
        sa.Column("metallicity", sa.Integer(), nullable=False),
        sa.Column("age_epochs", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.Enum("primary", "companion", name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("maker_son_id", sa.Integer(), nullable=True),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("luminosity", sa.Float(), nullable=False),
        sa.Column("lifetime_epochs", sa.Integer(), nullable=False),
        sa.Column("band_inner", sa.Float(), nullable=False),
        sa.Column("band_outer", sa.Float(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("age_epochs >= 0", name=op.f("ck_star_physics_age_epochs_min")),
        sa.CheckConstraint("mass > 0", name=op.f("ck_star_physics_mass_positive")),
        sa.CheckConstraint("metallicity BETWEEN 0 AND 100", name=op.f("ck_star_physics_metallicity_range")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_star_physics_upkeep_min")),
        sa.ForeignKeyConstraint(["maker_son_id"], ["sons.id"], name=op.f("fk_star_physics_maker_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_star_physics_star_id_stars"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["system_id"], ["star_systems.id"], name=op.f("fk_star_physics_system_id_star_systems"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("star_id", name=op.f("pk_star_physics")),
    )
    with op.batch_alter_table("star_physics", schema=None) as batch_op:
        batch_op.create_index("ix_star_physics_system", ["system_id"], unique=False)

    op.create_table(
        "world_surveys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("observer_entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "level",
            sa.Enum("unknown", "rumoured", "detected", "observed", "surveyed", "mapped", name="level", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_world_surveys_epoch_min")),
        sa.ForeignKeyConstraint(["observer_entity_id"], ["entities.id"], name=op.f("fk_world_surveys_observer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_surveys_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_surveys")),
        sa.UniqueConstraint("observer_entity_id", "world_id", name="one_survey"),
    )
    with op.batch_alter_table("world_surveys", schema=None) as batch_op:
        batch_op.create_index("ix_world_surveys_world", ["world_id"], unique=False)

    op.create_table(
        "cosmic_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "asteroid_field", "wormhole", "periodic_comet", "rogue_world", "gravity_well", name="kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("galaxy_id", sa.Integer(), nullable=True),
        sa.Column("star_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("world_b_id", sa.Integer(), nullable=True),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("density", sa.Integer(), nullable=False),
        sa.Column("radiation", sa.Integer(), nullable=False),
        sa.Column("travel", sa.Integer(), nullable=False),
        sa.Column("omen_weight", sa.Integer(), nullable=False),
        sa.Column("richness", sa.Integer(), nullable=False),
        sa.Column("pirates", sa.Integer(), nullable=False),
        sa.Column("instability", sa.Integer(), nullable=False),
        sa.Column("period_epochs", sa.Integer(), nullable=False),
        sa.Column("next_return_epoch", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 1", name=op.f("ck_cosmic_features_created_epoch_min")),
        sa.CheckConstraint("density BETWEEN 0 AND 100", name=op.f("ck_cosmic_features_density_range")),
        sa.CheckConstraint("ended_epoch IS NULL OR ended_epoch >= created_epoch", name=op.f("ck_cosmic_features_ended_after_start")),
        sa.CheckConstraint("instability BETWEEN 0 AND 100", name=op.f("ck_cosmic_features_instability_range")),
        sa.CheckConstraint("omen_weight BETWEEN 0 AND 100", name=op.f("ck_cosmic_features_omen_weight_range")),
        sa.CheckConstraint("period_epochs >= 0", name=op.f("ck_cosmic_features_period_epochs_min")),
        sa.CheckConstraint("pirates BETWEEN 0 AND 100", name=op.f("ck_cosmic_features_pirates_range")),
        sa.CheckConstraint("radiation BETWEEN 0 AND 100", name=op.f("ck_cosmic_features_radiation_range")),
        sa.CheckConstraint("radius >= 0", name=op.f("ck_cosmic_features_radius_positive")),
        sa.CheckConstraint("richness BETWEEN 0 AND 100", name=op.f("ck_cosmic_features_richness_range")),
        sa.CheckConstraint("travel BETWEEN -100 AND 100", name=op.f("ck_cosmic_features_travel_range")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_cosmic_features_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["galaxy_id"], ["galaxies.id"], name=op.f("fk_cosmic_features_galaxy_id_galaxies"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_cosmic_features_route_id_routes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_cosmic_features_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_b_id"], ["worlds.id"], name=op.f("fk_cosmic_features_world_b_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_cosmic_features_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cosmic_features")),
    )
    with op.batch_alter_table("cosmic_features", schema=None) as batch_op:
        batch_op.create_index("ix_cosmic_features_galaxy", ["galaxy_id"], unique=False)
        batch_op.create_index("ix_cosmic_features_star", ["star_id"], unique=False)

    op.create_table(
        "impact_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("feature_id", sa.Integer(), nullable=True),
        sa.Column(
            "body", sa.Enum("asteroid", "comet", "rogue_world", "called", name="body", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("due_epoch", sa.Integer(), nullable=False),
        sa.Column("warned_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "outcome", sa.Enum("pending", "struck", "deflected", "missed", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("crater_place_id", sa.Integer(), nullable=True),
        sa.Column("winter_epochs", sa.Integer(), nullable=False),
        sa.Column("deflected_by_node_id", sa.Integer(), nullable=True),
        sa.Column("called_by_node_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("due_epoch >= 1", name=op.f("ck_impact_events_due_epoch_min")),
        sa.CheckConstraint("size BETWEEN 0 AND 100", name=op.f("ck_impact_events_size_range")),
        sa.CheckConstraint("winter_epochs >= 0", name=op.f("ck_impact_events_winter_epochs_min")),
        sa.ForeignKeyConstraint(["called_by_node_id"], ["nodes.id"], name=op.f("fk_impact_events_called_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["crater_place_id"], ["entities.id"], name=op.f("fk_impact_events_crater_place_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deflected_by_node_id"], ["nodes.id"], name=op.f("fk_impact_events_deflected_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["feature_id"], ["cosmic_features.id"], name=op.f("fk_impact_events_feature_id_cosmic_features"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_impact_events_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_impact_events_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_impact_events")),
    )
    with op.batch_alter_table("impact_events", schema=None) as batch_op:
        batch_op.create_index("ix_impact_events_world", ["world_id", "outcome"], unique=False)

    with op.batch_alter_table("people_biology", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "biochemistry",
                sa.Enum(
                    "carbon_water",
                    "carbon_ammonia",
                    "silicon",
                    "crystal",
                    "void",
                    "spirit",
                    name="biochemistry",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=False,
                server_default=sa.text("'carbon_water'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "air",
                sa.Enum("oxygen", "carbon_dioxide", "methane", "none", name="air", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default=sa.text("'oxygen'"),
            )
        )
        batch_op.add_column(sa.Column("gravity_low", sa.Float(), nullable=False, server_default=sa.text("0.5")))
        batch_op.add_column(sa.Column("gravity_high", sa.Float(), nullable=False, server_default=sa.text("1.6")))
        batch_op.create_check_constraint("gravity_band", "gravity_low > 0 AND gravity_high >= gravity_low")
    with op.batch_alter_table("sky_events", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=sky_kinds(OLD_SKY_EVENTS), type_=sky_kinds(NEW_SKY_EVENTS), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("sky_events", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=sky_kinds(NEW_SKY_EVENTS), type_=sky_kinds(OLD_SKY_EVENTS), existing_nullable=False)
    with op.batch_alter_table("people_biology", schema=None) as batch_op:
        batch_op.drop_constraint("gravity_band", type_="check")
        batch_op.drop_column("gravity_high")
        batch_op.drop_column("gravity_low")
        batch_op.drop_column("air")
        batch_op.drop_column("biochemistry")

    with op.batch_alter_table("impact_events", schema=None) as batch_op:
        batch_op.drop_index("ix_impact_events_world")

    op.drop_table("impact_events")
    with op.batch_alter_table("cosmic_features", schema=None) as batch_op:
        batch_op.drop_index("ix_cosmic_features_star")
        batch_op.drop_index("ix_cosmic_features_galaxy")

    op.drop_table("cosmic_features")
    with op.batch_alter_table("world_surveys", schema=None) as batch_op:
        batch_op.drop_index("ix_world_surveys_world")

    op.drop_table("world_surveys")
    with op.batch_alter_table("star_physics", schema=None) as batch_op:
        batch_op.drop_index("ix_star_physics_system")

    op.drop_table("star_physics")
    op.drop_table("world_physics")
    op.drop_table("world_life")
    with op.batch_alter_table("terraforming", schema=None) as batch_op:
        batch_op.drop_index("ix_terraforming_world")

    op.drop_table("terraforming")
    with op.batch_alter_table("star_systems", schema=None) as batch_op:
        batch_op.drop_index("ix_star_systems_galaxy")

    op.drop_table("star_systems")
