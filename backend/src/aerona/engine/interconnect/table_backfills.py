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
    ("law_effects", "sentences"): "none: sentences are recorded as towns judge their offenders from the next epoch; earlier trials kept no record",
    ("geomorphology", "river_shifts"): "none: a river shift is recorded when a river moves; the courses rivers took before the wave are their present beds",
    ("spy_networks", "spy_networks"): "existing mechanic: the next espionage step gives every agent network bond its record",
    ("disease_type", "disease_profiles"): "epidemics: every disease entity is profiled by the next epidemics step",
    ("disease_type", "species_hosts"): "none: host species are bound when a disease is forged or a son names a host after the wave",
    ("settlement_life", "district_designs"): "none: district designs are devised by the player or a son after the wave; no design stood before",
    ("toll_treasuries", "polity_treasury"): "existing mechanic: tolls of the age are booked to the realms by the next trade step",
    ("route_chokepoints", "trade_route_profiles"): "existing mechanic: the next trade step marks chokepoints on the surveyed routes",
    ("route_chokepoints", "treaty_clauses"): "none: route-control clauses are written into the peace of the next route war",
    ("people_kin", "people_biology"): "existing mechanic: people_cycles derives body plan, size, diet, traits and immunities for every people",
    ("people_climate_immunity", "people_biology"): "existing mechanic: people_cycles derives acclimatisation and immunities for every people",
    ("consumption_shortfalls", "community_needs"): "existing mechanic: the next society_economy step fills every class's basket",
    ("needs_basket", "community_needs"): "existing mechanic: the next society_economy step fills every class's basket",
    ("labour_reasons", "corvee_levies"): "none: corvee is imposed by the player after the wave; no levy stood before",
    ("debt_settlement", "loans"): "existing mechanic: banks lend to realms and communities from the next banking step",
    ("structure_profiles", "structure_designs"): "none: structure designs are drawn up by the player or a son after the wave; none stood before",
    (
        "arms_and_wear",
        "unit_designs",
    ): "none: designs are drawn up by the player, gods or a realm's muster from the next epoch; earlier armies fought with the catalog's units",
    ("tradition_keeping", "tradition_participation"): "tradition_cycles: every community that celebrates a tradition takes its participation row",
    ("tradition_keeping", "tradition_effects"): "tradition_cycles: every tradition seeds its typed effects from its kind or its own kind",
    ("genetics", "house_resemblances"): "bloodlines: a house gains its likeness once enough of its blood shares a look",
    ("households", "household_aggregates"): "households: the anonymous households of every cohort are reckoned each epoch",
    ("dwellings", "dwelling_furnishings"): "none: homes are furnished by gods and agents from the next epoch",
}


def table_backfill(key: str, mechanic: Mechanic, table: str) -> str:
    return TABLE_BACKFILLS.get((key, table), mechanic.backfill)
