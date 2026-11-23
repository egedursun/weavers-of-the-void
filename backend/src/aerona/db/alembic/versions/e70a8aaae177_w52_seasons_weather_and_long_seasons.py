import sqlalchemy as sa
from alembic import op

revision = "e70a8aaae177"
down_revision = "5d0b7e3a9c21"
branch_labels = None
depends_on = None

RETYPED = (
    (
        "forced_weather",
        "kind",
        "kind",
        (
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
        ),
        (
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
            "frost",
            "ice_storm",
            "drizzle",
            "sleet",
            "freezing_fog",
            "thunderstorm",
            "tornado",
            "cyclone",
        ),
        False,
    ),
    (
        "network_outages",
        "cause",
        "cause",
        ("storm", "flare", "war", "sabotage", "intrusion", "decay", "rite", "power", "shortage", "divine"),
        ("storm", "flare", "war", "sabotage", "intrusion", "decay", "rite", "power", "shortage", "divine", "ice_storm"),
        False,
    ),
    (
        "tradition_effects",
        "effect",
        "effect",
        ("cohesion", "satisfaction", "piety", "value", "fertility", "martial", "placation", "harvest", "safety", "food_saved", "rest", "vigil"),
        (
            "cohesion",
            "satisfaction",
            "piety",
            "value",
            "fertility",
            "martial",
            "placation",
            "harvest",
            "safety",
            "food_saved",
            "rest",
            "vigil",
            "trade",
            "forage",
        ),
        False,
    ),
    (
        "notable_years",
        "kind",
        "kind",
        ("hunger", "plenty", "weather", "pestilence", "disaster", "discovery", "contact", "omen"),
        ("hunger", "plenty", "weather", "pestilence", "disaster", "discovery", "contact", "omen", "peace", "founding"),
        False,
    ),
    (
        "notable_years",
        "weather",
        "weather",
        (
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
        ),
        (
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
            "frost",
            "ice_storm",
            "drizzle",
            "sleet",
            "freezing_fog",
            "thunderstorm",
            "tornado",
            "cyclone",
        ),
        True,
    ),
    (
        "battles",
        "weather",
        "weather",
        (
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
        ),
        (
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
            "frost",
            "ice_storm",
            "drizzle",
            "sleet",
            "freezing_fog",
            "thunderstorm",
            "tornado",
            "cyclone",
        ),
        True,
    ),
    (
        "tradition_profiles",
        "calendar_slot",
        "calendar_slot",
        ("sowing", "harvest", "midwinter", "campaign", "holy_day"),
        (
            "sowing",
            "harvest",
            "midwinter",
            "campaign",
            "holy_day",
            "new_year",
            "midsummer",
            "remembrance",
            "market",
            "wild_harvest",
            "rains",
            "assembly",
            "tax",
            "pilgrimage",
        ),
        True,
    ),
)
CAUSES_OLD = ("orbit", "natural_law", "divine")
CAUSES_NEW = ("orbit", "natural_law", "divine", "impact", "eruption", "stellar", "ocean_shift", "made")
SHAPES = ("cycling", "single")
REACHES = ("world", "north", "south", "equator", "poles")
SPELLS = ("summer", "winter")
ONSETS = ("early", "on_time", "late", "failed")
SEASONS_OLD = 12
RENAMED_KINDS = (("lore.commemoration_year", "tradition.remembrance_founded"), ("tools.son.add_season", "season.added"))
KIND_COLUMNS = (("incidents", "kind"), ("chronicle", "template_key"))
SEASONS_NEW = 8


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, name, old, new, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        gone = ", ".join(f"'{value}'" for value in new if value not in old)
        if not forward and nullable:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})")
        elif not forward:
            op.execute(f"DELETE FROM {table} WHERE {column} IN ({gone})")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(after, name), existing_nullable=nullable)


def season_count(limit: int, previous: int) -> None:
    op.execute(f"UPDATE worlds SET season_count = {limit} WHERE season_count > {limit}")
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.drop_constraint("season_count_range", type_="check")
        batch_op.create_check_constraint("season_count_range", f"season_count IS NULL OR season_count BETWEEN 1 AND {limit}")


def share_out() -> None:
    with op.batch_alter_table("world_seasons", schema=None) as batch_op:
        batch_op.add_column(sa.Column("share_pct", sa.Integer(), nullable=False, server_default="1"))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, world_id, position, temperature_shift FROM world_seasons ORDER BY world_id, position")).all()
    worlds: dict[int, list[tuple[int, int, int]]] = {}
    for row_id, world_id, position, warmth in rows:
        worlds.setdefault(world_id, []).append((row_id, position, warmth))
    for seasons in worlds.values():
        base, left = divmod(100, len(seasons))
        warmest = max(seasons, key=lambda item: (item[2], -item[1]))[0]
        for row_id, _, _ in seasons:
            share = base + (left if row_id == warmest else 0)
            connection.execute(sa.text("UPDATE world_seasons SET share_pct = :share WHERE id = :id"), {"share": share, "id": row_id})
    with op.batch_alter_table("world_seasons", schema=None) as batch_op:
        batch_op.alter_column("share_pct", existing_type=sa.Integer(), server_default=None, existing_nullable=False)
        batch_op.create_check_constraint("share_pct_range", "share_pct BETWEEN 1 AND 100")


def long_seasons() -> None:
    op.create_table(
        "irregular_seasons_w52",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("cause", enum_of(CAUSES_NEW, "cause"), nullable=False),
        sa.Column("shape", enum_of(SHAPES, "shape"), nullable=False),
        sa.Column("spell", enum_of(SPELLS, "spell"), nullable=False),
        sa.Column("spell_started_epoch", sa.Integer(), nullable=False),
        sa.Column("spell_length", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("reach", enum_of(REACHES, "reach"), nullable=False),
        sa.Column("source_impact_id", sa.Integer(), nullable=True),
        sa.Column("source_region_id", sa.Integer(), nullable=True),
        sa.Column("source_star_id", sa.Integer(), nullable=True),
        sa.Column("source_incident_id", sa.Integer(), nullable=True),
        sa.Column("by_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("spell_started_epoch >= 0", name=op.f("ck_irregular_seasons_spell_started_epoch_min")),
        sa.CheckConstraint("spell_length >= 1", name=op.f("ck_irregular_seasons_spell_length_min")),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_irregular_seasons_severity_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_irregular_seasons_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_impact_id"], ["impact_events.id"], name=op.f("fk_irregular_seasons_source_impact_id_impact_events"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_region_id"], ["entities.id"], name=op.f("fk_irregular_seasons_source_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_star_id"], ["stars.id"], name=op.f("fk_irregular_seasons_source_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_incident_id"], ["incidents.id"], name=op.f("fk_irregular_seasons_source_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["by_node_id"], ["nodes.id"], name=op.f("fk_irregular_seasons_by_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_irregular_seasons")),
    )
    op.execute(
        "INSERT INTO irregular_seasons_w52 (world_id, cause, shape, spell, spell_started_epoch, spell_length, severity, reach, by_node_id, locked) "
        "SELECT world_id, cause, 'cycling', spell, spell_started_epoch, spell_length, severity, 'world', by_node_id, locked FROM irregular_seasons ORDER BY world_id"
    )
    op.create_table(
        "winter_forecasts_w52",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("long_season_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("scholar_entity_id", sa.Integer(), nullable=True),
        sa.Column("predicted_end_epoch", sa.Integer(), nullable=False),
        sa.Column("heeded", sa.Boolean(), nullable=False),
        sa.Column("made_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["long_season_id"], ["irregular_seasons.id"], name=op.f("fk_winter_forecasts_long_season_id_irregular_seasons"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_winter_forecasts_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_winter_forecasts_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scholar_entity_id"], ["entities.id"], name=op.f("fk_winter_forecasts_scholar_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_winter_forecasts")),
        sa.UniqueConstraint("long_season_id", "people_entity_id", name="uq_winter_forecasts_season_people"),
    )
    op.execute(
        "INSERT INTO winter_forecasts_w52 (id, long_season_id, world_id, people_entity_id, scholar_entity_id, predicted_end_epoch, heeded, made_epoch, locked) "
        "SELECT forecast.id, spell.id, forecast.world_id, forecast.people_entity_id, forecast.scholar_entity_id, forecast.predicted_end_epoch, forecast.heeded, "
        "forecast.made_epoch, forecast.locked FROM winter_forecasts AS forecast JOIN irregular_seasons_w52 AS spell ON spell.world_id = forecast.world_id"
    )
    op.drop_table("winter_forecasts")
    op.drop_table("irregular_seasons")
    op.rename_table("irregular_seasons_w52", "irregular_seasons")
    op.rename_table("winter_forecasts_w52", "winter_forecasts")
    with op.batch_alter_table("irregular_seasons", schema=None) as batch_op:
        batch_op.create_index("ix_irregular_seasons_world", ["world_id"], unique=False)
    with op.batch_alter_table("winter_forecasts", schema=None) as batch_op:
        batch_op.create_index("ix_winter_forecasts_people", ["people_entity_id"], unique=False)


def onsets() -> None:
    op.create_table(
        "season_onsets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("season_position", sa.Integer(), nullable=False),
        sa.Column("onset", enum_of(ONSETS, "onset"), nullable=False),
        sa.Column("by_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("season_position >= 0", name=op.f("ck_season_onsets_season_position_min")),
        sa.ForeignKeyConstraint(["by_node_id"], ["nodes.id"], name=op.f("fk_season_onsets_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_season_onsets_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_season_onsets")),
    )
    with op.batch_alter_table("season_onsets", schema=None) as batch_op:
        batch_op.create_index("ix_season_onsets_world_year", ["world_id", "year"], unique=False)


def rename(pairs: tuple[tuple[str, str], ...]) -> None:
    for table, column in KIND_COLUMNS:
        for former, current in pairs:
            op.execute(f"UPDATE {table} SET {column} = '{current}' WHERE {column} = '{former}'")


def upgrade() -> None:
    rename(RENAMED_KINDS)
    retype(True)
    season_count(SEASONS_NEW, SEASONS_OLD)
    share_out()
    onsets()
    long_seasons()


def downgrade() -> None:
    op.create_table(
        "irregular_seasons_w51",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("cause", enum_of(CAUSES_OLD, "cause"), nullable=False),
        sa.Column("spell", enum_of(SPELLS, "spell"), nullable=False),
        sa.Column("spell_started_epoch", sa.Integer(), nullable=False),
        sa.Column("spell_length", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("by_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["by_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("world_id"),
    )
    op.execute(
        "INSERT INTO irregular_seasons_w51 SELECT world_id, cause, spell, spell_started_epoch, spell_length, severity, by_node_id, locked FROM irregular_seasons "
        "WHERE id IN (SELECT MIN(id) FROM irregular_seasons WHERE cause IN ('orbit', 'natural_law', 'divine') GROUP BY world_id)"
    )
    with op.batch_alter_table("winter_forecasts", schema=None) as batch_op:
        batch_op.drop_constraint("uq_winter_forecasts_season_people", type_="unique")
    op.execute("DELETE FROM winter_forecasts WHERE long_season_id NOT IN (SELECT MIN(id) FROM irregular_seasons GROUP BY world_id)")
    with op.batch_alter_table("winter_forecasts", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_winter_forecasts_long_season_id_irregular_seasons"), type_="foreignkey")
        batch_op.drop_column("long_season_id")
        batch_op.create_unique_constraint("uq_winter_forecasts_world_people", ["world_id", "people_entity_id"])
    op.drop_table("irregular_seasons")
    op.rename_table("irregular_seasons_w51", "irregular_seasons")
    op.drop_table("season_onsets")
    with op.batch_alter_table("world_seasons", schema=None) as batch_op:
        batch_op.drop_constraint("share_pct_range", type_="check")
        batch_op.drop_column("share_pct")
    season_count(SEASONS_OLD, SEASONS_NEW)
    retype(False)
    rename(tuple((current, former) for former, current in RENAMED_KINDS))
