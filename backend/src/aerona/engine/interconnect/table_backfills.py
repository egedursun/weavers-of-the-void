from aerona.engine.interconnect.registry import Mechanic

TABLE_BACKFILLS: dict[tuple[str, str], str] = {
    (
        "community_opinion",
        "community_relations",
    ): "existing mechanic: relation values stood before the wave; mind_opinion refreshes them from the migrated memories",
    ("world_seasons", "calendars"): "existing mechanic: peoples who know astronomy adopt a calendar in the next epoch's seasons step",
    ("materials", "world_materials"): "none: catalog materials need no row; world substances appear from deposits, beasts and dead gods after the wave",
    ("extraction", "resource_workers"): "existing mechanic: workers are assigned to every profiled resource by the next extraction",
    ("extraction", "production_runs"): "existing mechanic: runs are recorded by the next extraction; earlier epochs kept no runs",
    ("refining", "production_runs"): "existing mechanic: runs are recorded by the next refining; earlier epochs kept no runs",
    ("markets", "market_prices"): "existing mechanic: prices are set by the next market clearing from present stocks",
    ("trade_routes", "trade_flows"): "existing mechanic: flows are recorded by the next trade step along the surveyed routes",
    ("epidemics", "disease_cures"): "none: cures are found from the next epoch; no outbreak was cured before the wave",
    ("epidemics", "quarantines"): "none: quarantines are ordered from the next epoch",
    ("polity_cycles", "vassalages"): "none: vassalages are sworn by treaties from the next epoch",
    ("geomorphology", "river_shifts"): "none: a river shift is recorded when a river moves; the courses rivers took before the wave are their present beds",
    ("spy_networks", "spy_networks"): "existing mechanic: the next espionage step gives every agent network bond its record",
}


def table_backfill(key: str, mechanic: Mechanic, table: str) -> str:
    return TABLE_BACKFILLS.get((key, table), mechanic.backfill)
