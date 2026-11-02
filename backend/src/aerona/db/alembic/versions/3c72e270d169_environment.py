import sqlalchemy as sa
from alembic import op

import aerona.db.types

revision = "3c72e270d169"
down_revision = "069aeb7ac3ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "world_seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("temperature_shift", sa.Integer(), nullable=False),
        sa.Column("rain_shift", sa.Integer(), nullable=False),
        sa.Column("growth", sa.Integer(), nullable=False),
        sa.Column("travel", sa.Integer(), nullable=False),
        sa.Column("campaign", sa.Integer(), nullable=False),
        sa.Column("edited", sa.Boolean(), nullable=False),
        sa.CheckConstraint("campaign BETWEEN 0 AND 100", name=op.f("ck_world_seasons_campaign_range")),
        sa.CheckConstraint("growth BETWEEN 0 AND 100", name=op.f("ck_world_seasons_growth_range")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_world_seasons_position_min")),
        sa.CheckConstraint("travel BETWEEN 0 AND 100", name=op.f("ck_world_seasons_travel_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_seasons_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_seasons")),
        sa.UniqueConstraint("world_id", "position", name="one_season_per_position"),
    )
    with op.batch_alter_table("world_seasons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_world_seasons_world_id"), ["world_id"], unique=False)

    op.create_table(
        "place_environment",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "terrain",
            sa.Enum(
                "plain",
                "steppe",
                "forest",
                "jungle",
                "marsh",
                "hills",
                "mountains",
                "high_pass",
                "desert",
                "tundra",
                "ice_sheet",
                "volcanic",
                "coast",
                "island",
                "river_valley",
                "canyon",
                "underground",
                "crystal_field",
                "flesh",
                "void_shore",
                "ruin_field",
                "urban",
                "sea",
                name="terrain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("cover", sa.Enum("open", "light", "heavy", name="cover", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "water_source",
            sa.Enum("none", "spring", "well", "river", "lake", "sea", name="water_source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("height_advantage", sa.Integer(), nullable=False),
        sa.Column("chokepoint", sa.Boolean(), nullable=False),
        sa.Column("soil_fertility", sa.Integer(), nullable=False),
        sa.Column("derived_fertility", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("height_advantage BETWEEN 0 AND 100", name=op.f("ck_place_environment_height_advantage_range")),
        sa.CheckConstraint("soil_fertility BETWEEN 0 AND 100", name=op.f("ck_place_environment_soil_fertility_range")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_place_environment_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_place_environment_region_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_place_environment")),
    )
    with op.batch_alter_table("place_environment", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_place_environment_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "region_environment",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("surveyed", sa.Boolean(), nullable=False),
        sa.Column("biome_mix", sa.JSON(), nullable=False),
        sa.Column(
            "dominant_terrain",
            sa.Enum(
                "plain",
                "steppe",
                "forest",
                "jungle",
                "marsh",
                "hills",
                "mountains",
                "high_pass",
                "desert",
                "tundra",
                "ice_sheet",
                "volcanic",
                "coast",
                "island",
                "river_valley",
                "canyon",
                "underground",
                "crystal_field",
                "flesh",
                "void_shore",
                "ruin_field",
                "urban",
                "sea",
                name="dominant_terrain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("elevation_mean", sa.Integer(), nullable=False),
        sa.Column("roughness", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Integer(), nullable=False),
        sa.Column("moisture", sa.Integer(), nullable=False),
        sa.Column("base_forest", sa.Integer(), nullable=False),
        sa.Column("forest_cover", sa.Integer(), nullable=False),
        sa.Column("base_wetland", sa.Integer(), nullable=False),
        sa.Column("wetland", sa.Integer(), nullable=False),
        sa.Column(
            "river_class",
            sa.Enum("none", "stream", "river", "great_river", name="river_class", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "coast_kind",
            sa.Enum("none", "cliff", "beach", "harbour_site", "reef", name="coast_kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "soil",
            sa.Enum(
                "thin",
                "loam",
                "clay",
                "sand",
                "volcanic",
                "peat",
                "salt",
                "ash",
                "crystal",
                "bone",
                name="soil",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("soil_fertility", sa.Integer(), nullable=False),
        sa.Column("soil_base", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Integer(), nullable=False),
        sa.Column(
            "temperature_band",
            sa.Enum("frozen", "cold", "temperate", "warm", "hot", "searing", name="temperature_band", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("rainfall", sa.Integer(), nullable=False),
        sa.Column("seasonality", sa.Integer(), nullable=False),
        sa.Column("disease_load", sa.Integer(), nullable=False),
        sa.Column("mineral_layers", sa.JSON(), nullable=False),
        sa.Column("magic_density", sa.Integer(), nullable=False),
        sa.Column("passability", sa.JSON(), nullable=False),
        sa.Column("defensibility", sa.Integer(), nullable=False),
        sa.Column("scars", sa.JSON(), nullable=False),
        sa.Column("cleared", sa.Integer(), nullable=False),
        sa.Column("farmed", sa.Integer(), nullable=False),
        sa.Column("grazed", sa.Integer(), nullable=False),
        sa.Column("mined", sa.Integer(), nullable=False),
        sa.Column("built", sa.Integer(), nullable=False),
        sa.Column("erosion", sa.Integer(), nullable=False),
        sa.Column("harvest_pct", sa.Integer(), nullable=False),
        sa.Column("derived_fertility", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("base_forest BETWEEN 0 AND 100", name=op.f("ck_region_environment_base_forest_range")),
        sa.CheckConstraint("base_wetland BETWEEN 0 AND 100", name=op.f("ck_region_environment_base_wetland_range")),
        sa.CheckConstraint("built BETWEEN 0 AND 100", name=op.f("ck_region_environment_built_range")),
        sa.CheckConstraint("cleared BETWEEN 0 AND 100", name=op.f("ck_region_environment_cleared_range")),
        sa.CheckConstraint("defensibility BETWEEN 0 AND 100", name=op.f("ck_region_environment_defensibility_range")),
        sa.CheckConstraint("disease_load BETWEEN 0 AND 100", name=op.f("ck_region_environment_disease_load_range")),
        sa.CheckConstraint("elevation_mean BETWEEN 0 AND 100", name=op.f("ck_region_environment_elevation_mean_range")),
        sa.CheckConstraint("erosion BETWEEN 0 AND 100", name=op.f("ck_region_environment_erosion_range")),
        sa.CheckConstraint("farmed BETWEEN 0 AND 100", name=op.f("ck_region_environment_farmed_range")),
        sa.CheckConstraint("forest_cover BETWEEN 0 AND 100", name=op.f("ck_region_environment_forest_cover_range")),
        sa.CheckConstraint("grazed BETWEEN 0 AND 100", name=op.f("ck_region_environment_grazed_range")),
        sa.CheckConstraint("harvest_pct >= 0", name=op.f("ck_region_environment_harvest_pct_min")),
        sa.CheckConstraint("latitude BETWEEN 0 AND 100", name=op.f("ck_region_environment_latitude_range")),
        sa.CheckConstraint("magic_density BETWEEN 0 AND 100", name=op.f("ck_region_environment_magic_density_range")),
        sa.CheckConstraint("mined BETWEEN 0 AND 100", name=op.f("ck_region_environment_mined_range")),
        sa.CheckConstraint("moisture BETWEEN 0 AND 100", name=op.f("ck_region_environment_moisture_range")),
        sa.CheckConstraint("rainfall BETWEEN 0 AND 100", name=op.f("ck_region_environment_rainfall_range")),
        sa.CheckConstraint("roughness BETWEEN 0 AND 100", name=op.f("ck_region_environment_roughness_range")),
        sa.CheckConstraint("seasonality BETWEEN 0 AND 100", name=op.f("ck_region_environment_seasonality_range")),
        sa.CheckConstraint("soil_base BETWEEN 0 AND 100", name=op.f("ck_region_environment_soil_base_range")),
        sa.CheckConstraint("soil_fertility BETWEEN 0 AND 100", name=op.f("ck_region_environment_soil_fertility_range")),
        sa.CheckConstraint("temperature BETWEEN 0 AND 100", name=op.f("ck_region_environment_temperature_range")),
        sa.CheckConstraint("wetland BETWEEN 0 AND 100", name=op.f("ck_region_environment_wetland_range")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_region_environment_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_region_environment_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_region_environment")),
    )
    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.create_index("ix_region_environment_world", ["world_id"], unique=False)

    op.create_table(
        "calendars",
        sa.Column("knowledge_entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("adopted_epoch", sa.Integer(), nullable=False),
        sa.Column("anchor_year", sa.Integer(), nullable=False),
        sa.Column("anchor_incident_id", sa.Integer(), nullable=True),
        sa.Column("month_names", sa.JSON(), nullable=False),
        sa.Column("holy_days", sa.JSON(), nullable=False),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("adopted_epoch >= 0", name=op.f("ck_calendars_adopted_epoch_min")),
        sa.CheckConstraint("anchor_year >= 0", name=op.f("ck_calendars_anchor_year_min")),
        sa.ForeignKeyConstraint(["anchor_incident_id"], ["incidents.id"], name=op.f("fk_calendars_anchor_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["knowledge_entity_id"], ["entities.id"], name=op.f("fk_calendars_knowledge_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_calendars_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("knowledge_entity_id", name=op.f("pk_calendars")),
    )
    with op.batch_alter_table("calendars", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_calendars_world_id"), ["world_id"], unique=False)

    op.create_table(
        "notable_years",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("hunger", "plenty", "weather", "pestilence", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "weather",
            sa.Enum(
                "clear",
                "overcast",
                "rain",
                "downpour",
                "storm",
                "fog",
                "snow",
                "blizzard",
                "heat_wave",
                "drought_wind",
                "sandstorm",
                "hail",
                "magic_storm",
                "ash_fall",
                "void_rain",
                "eclipse_dark",
                "aurora",
                name="weather",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_notable_years_epoch_min")),
        sa.CheckConstraint("magnitude >= 0", name=op.f("ck_notable_years_magnitude_min")),
        sa.CheckConstraint("year >= 0", name=op.f("ck_notable_years_year_min")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_notable_years_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_notable_years_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_notable_years_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notable_years")),
    )
    with op.batch_alter_table("notable_years", schema=None) as batch_op:
        batch_op.create_index("ix_notable_years_world_year", ["world_id", "year"], unique=False)

    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("axial_tilt", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("year_length_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("season_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("day_length_hours", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("moon_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tidal_strength", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(op.f("ck_worlds_axial_tilt_range"), "axial_tilt IS NULL OR axial_tilt BETWEEN 0 AND 90")
        batch_op.create_check_constraint(op.f("ck_worlds_season_count_range"), "season_count IS NULL OR season_count BETWEEN 1 AND 6")
        batch_op.create_check_constraint(op.f("ck_worlds_year_length_positive"), "year_length_days IS NULL OR year_length_days >= 1")
        batch_op.create_check_constraint(op.f("ck_worlds_day_length_positive"), "day_length_hours IS NULL OR day_length_hours >= 1")
        batch_op.create_check_constraint(op.f("ck_worlds_moon_count_min"), "moon_count IS NULL OR moon_count >= 0")
        batch_op.create_check_constraint(op.f("ck_worlds_tidal_strength_range"), "tidal_strength IS NULL OR tidal_strength BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_worlds_tidal_strength_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_worlds_moon_count_min"), type_="check")
        batch_op.drop_constraint(op.f("ck_worlds_day_length_positive"), type_="check")
        batch_op.drop_constraint(op.f("ck_worlds_year_length_positive"), type_="check")
        batch_op.drop_constraint(op.f("ck_worlds_season_count_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_worlds_axial_tilt_range"), type_="check")
        batch_op.drop_column("tidal_strength")
        batch_op.drop_column("moon_count")
        batch_op.drop_column("day_length_hours")
        batch_op.drop_column("season_count")
        batch_op.drop_column("year_length_days")
        batch_op.drop_column("axial_tilt")

    with op.batch_alter_table("notable_years", schema=None) as batch_op:
        batch_op.drop_index("ix_notable_years_world_year")

    op.drop_table("notable_years")
    with op.batch_alter_table("calendars", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_calendars_world_id"))

    op.drop_table("calendars")
    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.drop_index("ix_region_environment_world")

    op.drop_table("region_environment")
    with op.batch_alter_table("place_environment", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_place_environment_region_entity_id"))

    op.drop_table("place_environment")
    with op.batch_alter_table("world_seasons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_world_seasons_world_id"))

    op.drop_table("world_seasons")
