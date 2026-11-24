import ast
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "backend" / "src" / "aerona"
sys.path.insert(0, str(ROOT / "backend" / "src"))

SURFACE_ONLY: dict[str, str] = {
    "forced_weather.region_entity_id": "sky and weather",
    "region_winds.region_entity_id": "sky and weather",
    "weather_works.region_entity_id": "sky and weather",
    "weather_works.downwind_region_id": "sky and weather",
    "irregular_seasons.source_region_id": "sky and weather",
    "region_cryosphere.region_entity_id": "sky and weather",
    "carrion_pulses.region_entity_id": "sky and weather",
    "soil_microbiota.region_entity_id": "soil and fields",
    "soil_nutrients.region_entity_id": "soil and fields",
    "region_crops.region_entity_id": "soil and fields",
    "intensification.region_entity_id": "soil and fields",
    "land_rings.region_entity_id": "soil and fields",
    "perennials.region_entity_id": "soil and fields",
    "commons.region_entity_id": "soil and fields",
    "catch_grounds.region_entity_id": "soil and fields",
    "game_reserves.region_entity_id": "soil and fields",
    "protected_areas.region_entity_id": "soil and fields",
    "ecosystem_services.region_entity_id": "soil and fields",
    "trophic_levels.region_entity_id": "soil and fields",
    "keystone_resources.source_region_entity_id": "soil and fields",
    "region_geomorphology.region_entity_id": "soil and fields",
    "region_geology.region_entity_id": "soil and fields",
    "fossil_beds.region_entity_id": "soil and fields",
    "lost_lands.region_entity_id": "soil and fields",
    "source_density.region_entity_id": "soil and fields",
    "coasts.region_entity_id": "coasts and sea",
    "sea_waves.origin_region_id": "coasts and sea",
    "sea_waves.sea_region_id": "coasts and sea",
    "sea_wave_coasts.region_entity_id": "coasts and sea",
    "wave_warnings.region_entity_id": "coasts and sea",
    "sediment_flows.sink_region_id": "coasts and sea",
    "sediment_flows.source_region_id": "coasts and sea",
    "river_shifts.from_region_id": "coasts and sea",
    "river_shifts.to_region_id": "coasts and sea",
    "vessel_profiles.region_entity_id": "coasts and sea",
    "region_dangers.region_entity_id": "a land's whole standing, read for the region itself",
    "region_hazards.region_entity_id": "a land's whole standing, read for the region itself",
    "region_memories.region_entity_id": "a land's whole standing, read for the region itself",
    "region_dominion.region_entity_id": "a land's whole standing, read for the region itself",
    "regional_tensions.region_entity_id": "a land's whole standing, read for the region itself",
    "notable_years.region_entity_id": "a land's whole standing, read for the region itself",
    "place_environment.region_entity_id": "a land's whole standing, read for the region itself",
    "natural_law_profiles.region_entity_id": "a land's whole standing, read for the region itself",
    "dominions.region_entity_id": "a land's whole standing, read for the region itself",
    "miracle_records.region_entity_id": "a land's whole standing, read for the region itself",
    "event_footprints.region_entity_id": "a land's whole standing, read for the region itself",
    "phenomenon_footprints.region_entity_id": "a land's whole standing, read for the region itself",
    "dimensional_events.region_entity_id": "a land's whole standing, read for the region itself",
    "rifts.region_entity_id": "a land's whole standing, read for the region itself",
    "impact_events.region_entity_id": "a land's whole standing, read for the region itself",
    "outer_incursions.region_entity_id": "a land's whole standing, read for the region itself",
    "breach_points.region_entity_id": "a land's whole standing, read for the region itself",
    "species_traits.region_entity_id": "a land's whole standing, read for the region itself",
    "species_ranges.region_entity_id": "a land's whole standing, read for the region itself",
    "creature_groups.region_entity_id": "a land's whole standing, read for the region itself",
    "endemic_diseases.region_entity_id": "a land's whole standing, read for the region itself",
    "outbreaks.region_entity_id": "a land's whole standing, read for the region itself",
    "quarantines.region_entity_id": "a land's whole standing, read for the region itself",
    "disease_carriers.home_region_id": "a land's whole standing, read for the region itself",
    "disease_profiles.origin_region_id": "a land's whole standing, read for the region itself",
    "emotion_spirits.region_entity_id": "a land's whole standing, read for the region itself",
    "kin_groups.land_region_id": "a land's whole standing, read for the region itself",
    "offices.region_entity_id": "a land's whole standing, read for the region itself",
    "company_profiles.region_entity_id": "a land's whole standing, read for the region itself",
    "polity_territories.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "polity_map_knowledge.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "occupation_regimes.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "occupation_measures.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "theatres.front_region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "echelons.hq_region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "war_remnants.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "depots.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "vehicle_groups.region_entity_id": "a realm's hold on the land, kept per region and read at the surface",
    "trade_route_tolls.region_entity_id": "routes and signals over the land",
    "signal_links.from_region_id": "routes and signals over the land",
    "signal_links.to_region_id": "routes and signals over the land",
}
GRAPH_HOMES = ("cartography/", "engine/primitives/distance.py", "engine/primitives/deep.py")


def region_columns() -> list[str]:
    import_module("aerona.db.tables")
    base = import_module("aerona.db.base").Base
    return sorted(
        f"{table.name}.{column.name}"
        for table in base.metadata.sorted_tables
        for column in table.columns
        if column.name in {"region_id", "region_entity_id"} or column.name.endswith(("_region_id", "_region_entity_id"))
    )


def problems() -> list[str]:
    positions = import_module("aerona.catalog.depth_positions")
    import_module("aerona.db.tables")
    base = import_module("aerona.db.base").Base
    tables = {table.name: table for table in base.metadata.sorted_tables}
    depth_positions, surface_only = positions.DEPTH_POSITIONS, SURFACE_ONLY
    found: list[str] = []
    placed = {f"{table}.{column}" for table, column, _ in depth_positions}
    for name in region_columns():
        if name not in placed and name not in surface_only:
            found.append(f"{name} places a thing in a region but is in neither DEPTH_POSITIONS nor SURFACE_ONLY of catalog/depth_positions.py")
    for table, column, stratum in depth_positions:
        if table not in tables or column not in tables[table].columns or stratum not in tables[table].columns:
            found.append(f"{table}.{column} names a stratum column {stratum} that does not exist")
    for path in sorted(SOURCE.rglob("*.py")):
        relative = path.relative_to(SOURCE).as_posix()
        if "__pycache__" in relative or relative.startswith("db/alembic/"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(alias.name == "RegionGraph" for alias in node.names) and not relative.startswith(GRAPH_HOMES):
                found.append(f"backend/src/aerona/{relative}:{node.lineno}: reads RegionGraph directly and skips the deep; ask RegionAtlas for cells")
            if isinstance(node, ast.Attribute) and node.attr == "same_region":
                found.append(f"backend/src/aerona/{relative}:{node.lineno}: same_region ignores the level beneath a region; use same_cell")
    return found


def main() -> int:
    found = problems()
    for line in found:
        print(line)
    print(f"depth positions: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
