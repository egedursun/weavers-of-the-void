import sqlalchemy as sa
from alembic import op

revision = "40f493adbbbe"
down_revision = "c4e8a2f6b913"
branch_labels = None
depends_on = None

RANGES = (
    ("community_industry", "ck_community_industry_fusion_min", "fusion", 0, None, "fusion >= 0"),
    ("community_industry", "ck_community_industry_stellar_min", "stellar", 0, None, "stellar >= 0"),
    ("community_industry", "ck_community_industry_source_min", "source", 0, None, "source >= 0"),
    ("community_industry", "ck_community_industry_feed_min", "feed", 0, None, "feed >= 0"),
    ("community_industry", "ck_community_industry_fuel_min", "fuel", 0, None, "fuel >= 0"),
    ("community_industry", "ck_community_industry_electric_min", "electric", 0, None, "electric >= 0"),
    ("community_industry", "ck_community_industry_belief_min", "belief", 0, None, "belief >= 0"),
    ("community_industry", "ck_community_industry_stored_min", "stored", 0, None, "stored >= 0"),
    ("community_industry", "ck_community_industry_void_min", "void", 0, None, "void >= 0"),
    ("community_industry", "ck_community_industry_solar_min", "solar", 0, None, "solar >= 0"),
    ("community_industry", "ck_community_industry_geothermal_min", "geothermal", 0, None, "geothermal >= 0"),
    ("community_industry", "ck_community_industry_tidal_min", "tidal", 0, None, "tidal >= 0"),
    ("community_industry", "ck_community_industry_fission_min", "fission", 0, None, "fission >= 0"),
    ("stars", "ck_stars_radiation_range", "radiation", 0, 100, "radiation BETWEEN 0 AND 100"),
    ("stars", "ck_stars_sacredness_range", "sacredness", 0, 100, "sacredness BETWEEN 0 AND 100"),
    ("stars", "ck_stars_stability_range", "stability", 0, 100, "stability BETWEEN 0 AND 100"),
    ("stars", "ck_stars_lifecycle_clock_min", "lifecycle_clock", 0, None, "lifecycle_clock IS NULL OR lifecycle_clock >= 0"),
    ("worlds", "ck_worlds_magnetism_range", "magnetism", 0, 100, "magnetism BETWEEN 0 AND 100"),
    ("worlds", "ck_worlds_radiation_range", "radiation", 0, 100, "radiation BETWEEN 0 AND 100"),
    ("worlds", "ck_worlds_biosphere_health_range", "biosphere_health", 0, 100, "biosphere_health BETWEEN 0 AND 100"),
    ("worlds", "ck_worlds_mood_range", "mood", -100, 100, "mood BETWEEN -100 AND 100"),
    ("games", "ck_games_betting_range", "betting", 0, 100, "betting BETWEEN 0 AND 100"),
    ("games", "ck_games_violence_range", "violence", 0, 100, "violence BETWEEN 0 AND 100"),
    ("games", "ck_games_chance_share_range", "chance_share", 0, 100, "chance_share BETWEEN 0 AND 100"),
    ("games", "ck_games_spectators_range", "spectators", 0, 100, "spectators BETWEEN 0 AND 100"),
    ("games", "ck_games_prestige_range", "prestige", 0, 100, "prestige BETWEEN 0 AND 100"),
    ("games", "ck_games_team_size_range", "team_size", 1, 500, "team_size BETWEEN 1 AND 500"),
    ("designs", "ck_designs_cost_min", "cost", 0, None, "cost >= 0"),
    ("designs", "ck_designs_armour_range", "armour", 0, 100, "armour BETWEEN 0 AND 100"),
    ("designs", "ck_designs_upkeep_min", "upkeep", 0, None, "upkeep >= 0"),
    ("designs", "ck_designs_tech_level_range", "tech_level", 0, 10, "tech_level BETWEEN 0 AND 10"),
    ("designs", "ck_designs_strangeness_range", "strangeness", 0, 100, "strangeness BETWEEN 0 AND 100"),
    ("designs", "ck_designs_fuel_use_min", "fuel_use", 0, None, "fuel_use >= 0"),
    ("designs", "ck_designs_troops_min", "troops", 0, None, "troops >= 0"),
    ("designs", "ck_designs_structure_min", "structure", 0, None, "structure >= 0"),
    ("dishes", "ck_dishes_fermented_range", "fermented", 0, 100, "fermented BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_prep_skill_range", "prep_skill", 0, 100, "prep_skill BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_sweet_range", "sweet", 0, 100, "sweet BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_sour_range", "sour", 0, 100, "sour BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_saline_range", "saline", 0, 100, "saline BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_bitter_range", "bitter", 0, 100, "bitter BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_savoury_range", "savoury", 0, 100, "savoury BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_pungent_range", "pungent", 0, 100, "pungent BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_cooling_range", "cooling", 0, 100, "cooling BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_numbing_range", "numbing", 0, 100, "numbing BETWEEN 0 AND 100"),
    ("dishes", "ck_dishes_smoky_range", "smoky", 0, 100, "smoky BETWEEN 0 AND 100"),
    ("fossil_beds", "ck_fossil_beds_layer_range", "layer", 0, 100, "layer BETWEEN 0 AND 100"),
    ("mortal_profiles", "ck_mortal_profiles_attraction_range", "attraction", 0, 100, "attraction BETWEEN 0 AND 100"),
    ("people_culture", "ck_people_culture_ornament_range", "ornament", 0, 100, "ornament BETWEEN 0 AND 100"),
    ("people_culture", "ck_people_culture_scale_range", "scale", 0, 100, "scale BETWEEN 0 AND 100"),
    ("people_culture", "ck_people_culture_geometry_range", "geometry", 0, 100, "geometry BETWEEN 0 AND 100"),
    ("people_culture", "ck_people_culture_symmetry_range", "symmetry", 0, 100, "symmetry BETWEEN 0 AND 100"),
    ("people_culture", "ck_people_culture_colour_range", "colour", 0, 100, "colour BETWEEN 0 AND 100"),
    ("region_environment", "ck_region_environment_rainfall_shift_range", "rainfall_shift", -100, 100, "rainfall_shift BETWEEN -100 AND 100"),
    ("region_environment", "ck_region_environment_temperature_shift_range", "temperature_shift", -100, 100, "temperature_shift BETWEEN -100 AND 100"),
    ("region_environment", "ck_region_environment_leak_range", "leak", 0, 100, "leak BETWEEN 0 AND 100"),
    ("routes", "ck_routes_capacity_min", "capacity", 0, None, "capacity >= 0"),
    ("routes", "ck_routes_traffic_min", "traffic", 0, None, "traffic >= 0"),
    ("routes", "ck_routes_window_every_min", "window_every", 0, None, "window_every >= 0"),
    ("routes", "ck_routes_window_offset_min", "window_offset", 0, None, "window_offset >= 0"),
    ("routes", "ck_routes_toll_pct_range", "toll_pct", 0, 100, "toll_pct BETWEEN 0 AND 100"),
    ("routes", "ck_routes_piracy_range", "piracy", 0, 100, "piracy BETWEEN 0 AND 100"),
    ("routes", "ck_routes_wear_range", "wear", 0, 100, "wear BETWEEN 0 AND 100"),
    ("structure_designs", "ck_structure_designs_storeys_range", "storeys", 1, 200, "storeys BETWEEN 1 AND 200"),
    ("time_budgets", "ck_time_budgets_sleep_range", "sleep", 0, 100, "sleep BETWEEN 0 AND 100"),
    ("time_budgets", "ck_time_budgets_art_range", "art", 0, 100, "art BETWEEN 0 AND 100"),
    ("time_budgets", "ck_time_budgets_learning_range", "learning", 0, 100, "learning BETWEEN 0 AND 100"),
    ("time_budgets", "ck_time_budgets_housework_range", "housework", 0, 100, "housework BETWEEN 0 AND 100"),
    ("time_budgets", "ck_time_budgets_care_range", "care", 0, 100, "care BETWEEN 0 AND 100"),
    ("union_customs", "ck_union_customs_exchange_value_min", "exchange_value", 0, None, "exchange_value >= 0"),
    ("community_dishes", "ck_community_dishes_short_epochs_min", "short_epochs", 0, None, "short_epochs >= 0"),
    ("incident_participants", "ck_incident_participants_fidelity_range", "fidelity", 0, 100, "fidelity IS NULL OR fidelity BETWEEN 0 AND 100"),
    ("journeys", "ck_journeys_escorts_min", "escorts", 0, None, "escorts >= 0"),
    ("journeys", "ck_journeys_convoy_min", "convoy", 1, None, "convoy >= 1"),
    ("unit_designs", "ck_unit_designs_discipline_range", "discipline", 0, 100, "discipline BETWEEN 0 AND 100"),
    ("unit_designs", "ck_unit_designs_training_epochs_min", "training_epochs", 0, None, "training_epochs >= 0"),
    ("unit_designs", "ck_unit_designs_crew_per_vehicle_min", "crew_per_vehicle", 0, None, "crew_per_vehicle >= 0"),
    ("vessel_profiles", "ck_vessel_profiles_cargo_capacity_min", "cargo_capacity", 0, None, "cargo_capacity >= 0"),
    ("vessel_profiles", "ck_vessel_profiles_seaworthiness_range", "seaworthiness", 0, 100, "seaworthiness BETWEEN 0 AND 100"),
    ("vessel_profiles", "ck_vessel_profiles_condition_range", "condition", 0, 100, "condition BETWEEN 0 AND 100"),
    ("vessel_profiles", "ck_vessel_profiles_seamanship_range", "seamanship", 0, 100, "seamanship BETWEEN 0 AND 100"),
    ("vessel_profiles", "ck_vessel_profiles_crew_min", "crew", 0, None, "crew >= 0"),
    ("vessel_profiles", "ck_vessel_profiles_renown_min", "renown", 0, None, "renown >= 0"),
    ("army_units", "ck_army_units_organisation_range", "organisation", 0, 100, "organisation BETWEEN 0 AND 100"),
    ("army_units", "ck_army_units_discipline_range", "discipline", 0, 100, "discipline BETWEEN 0 AND 100"),
    ("army_units", "ck_army_units_ammunition_min", "ammunition", 0, None, "ammunition >= 0"),
    ("army_units", "ck_army_units_missing_min", "missing", 0, None, "missing >= 0"),
    ("structure_profiles", "ck_structure_profiles_style_scale_range", "style_scale", 0, 100, "style_scale BETWEEN 0 AND 100"),
    ("structure_profiles", "ck_structure_profiles_style_symmetry_range", "style_symmetry", 0, 100, "style_symmetry BETWEEN 0 AND 100"),
    ("structure_profiles", "ck_structure_profiles_style_ornament_range", "style_ornament", 0, 100, "style_ornament BETWEEN 0 AND 100"),
    ("structure_profiles", "ck_structure_profiles_style_geometry_range", "style_geometry", 0, 100, "style_geometry BETWEEN 0 AND 100"),
    ("structure_profiles", "ck_structure_profiles_style_colour_range", "style_colour", 0, 100, "style_colour BETWEEN 0 AND 100"),
)
SHAPES = (
    ("worlds", "ck_worlds_one_place", "galaxy_id IS NULL OR dimension_id IS NULL"),
    ("worlds", "ck_worlds_placed_by_star", "(star_id IS NULL AND parent_world_id IS NULL) OR (galaxy_id IS NULL AND dimension_id IS NULL)"),
)


def clamp(table: str, column: str, low: int, high: int | None) -> None:
    op.execute(sa.text(f"UPDATE {table} SET {column} = {low} WHERE {column} < {low}"))
    if high is not None:
        op.execute(sa.text(f"UPDATE {table} SET {column} = {high} WHERE {column} > {high}"))


def checks_by_table() -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    for table, name, _column, _low, _high, text in RANGES:
        found.setdefault(table, []).append((name, text))
    for table, name, text in SHAPES:
        found.setdefault(table, []).append((name, text))
    return found


def upgrade() -> None:
    for table, _name, column, low, high, _text in RANGES:
        clamp(table, column, low, high)
    for table, checks in sorted(checks_by_table().items()):
        with op.batch_alter_table(table) as batch:
            for name, text in checks:
                batch.create_check_constraint(name, sa.text(text))


def downgrade() -> None:
    for table, checks in sorted(checks_by_table().items()):
        with op.batch_alter_table(table) as batch:
            for name, _text in checks:
                batch.drop_constraint(name, type_="check")
