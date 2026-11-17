from aerona.engine.agrarian.lands import LandsTally, keep_lands
from aerona.engine.agrarian.resilience import ResilienceTally, keep_resilience
from aerona.engine.agrarian.rings import SpatialTally, keep_spatial
from aerona.engine.agrarian.soil import SoilTally, keep_soil
from aerona.engine.agrarian.staples import StaplesTally, keep_staples
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "settlement.population",
    "table.central_places",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.land_rings",
    "table.nodes",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.structure_profiles",
)
@writes(
    "table.central_places",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.land_rings",
)
async def spatial_economy(ctx: TickContext) -> None:
    tally = SpatialTally()
    await keep_spatial(ctx, tally)
    count(ctx, "spatial_economy", tally)


@reads(
    "people.population",
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.commons",
    "table.community_methods",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.entities",
    "table.famine_lore",
    "table.game_reserves",
    "table.geasa",
    "table.generations",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_profiles",
    "table.households",
    "table.incident_participants",
    "table.incidents",
    "table.intensification",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mandates",
    "table.nodes",
    "table.notable_years",
    "table.offices",
    "table.perennials",
    "table.place_environment",
    "table.plant_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.regimes",
    "table.region_crops",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.soil_microbiota",
    "table.soil_nutrients",
    "table.species_products",
    "table.species_ranges",
    "table.tradition_profiles",
    "table.vassalages",
)
@writes(
    "settlement.population",
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.commons",
    "table.entities",
    "table.famine_lore",
    "table.game_reserves",
    "table.households",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.intensification",
    "table.mandates",
    "table.mortal_profiles",
    "table.perennials",
    "table.settlement_profiles",
    "table.soil_nutrients",
)
async def agrarian_cycles(ctx: TickContext) -> None:
    soil = SoilTally()
    await keep_soil(ctx, soil)
    count(ctx, "agrarian_soil", soil)
    lands = LandsTally()
    await keep_lands(ctx, lands)
    count(ctx, "agrarian_lands", lands)


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.community_relations",
    "table.community_stocks",
    "table.creator",
    "table.creator_taboos",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.culture_values",
    "table.district_services",
    "table.districts",
    "table.divine_standing",
    "table.entities",
    "table.faction_profiles",
    "table.favours",
    "table.geasa",
    "table.goods_flows",
    "table.held_identities",
    "table.holder_levels",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.mandates",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.preparedness",
    "table.reconstructions",
    "table.region_environment",
    "table.relation_components",
    "table.relationships",
    "table.relief_aid",
    "table.reputations",
    "table.reverences",
    "table.ruler_currencies",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.speaker_cohorts",
    "table.structure_profiles",
    "table.tradition_profiles",
    "table.traits",
    "table.turf",
    "table.vassalages",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_stocks",
    "table.districts",
    "table.divine_standing",
    "table.favours",
    "table.gifts",
    "table.goods_flows",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.polity_profiles",
    "table.polity_treasury",
    "table.preparedness",
    "table.reconstructions",
    "table.relief_aid",
    "table.settlement_profiles",
    "table.settlement_treasury",
)
async def resilience(ctx: TickContext) -> None:
    tally = ResilienceTally()
    await keep_resilience(ctx, tally)
    count(ctx, "resilience", tally)


@reads(
    "settlement.piety",
    "table.bonds",
    "table.brands",
    "table.community_relations",
    "table.creator",
    "table.creator_taboos",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.geasa",
    "table.held_identities",
    "table.incident_participants",
    "table.incidents",
    "table.item_profiles",
    "table.keystone_resources",
    "table.memories",
    "table.mind_profiles",
    "table.minds",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.production_runs",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.reverences",
    "table.ruler_currencies",
    "table.sons",
    "table.species_products",
    "table.species_ranges",
    "table.tradition_profiles",
    "table.traits",
    "table.vassalages",
    "table.workshops",
    "table.worlds",
)
@writes(
    "settlement.piety",
    "table.brands",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.keystone_resources",
    "table.memories",
    "table.polity_profiles",
    "table.polity_treasury",
    "table.reputations",
    "table.species_ranges",
)
async def staples(ctx: TickContext) -> None:
    tally = StaplesTally()
    await keep_staples(ctx, tally)
    count(ctx, "staples", tally)


PHASES = (
    Phase("spatial_economy", spatial_economy),
    Phase("agrarian_cycles", agrarian_cycles),
    Phase("resilience", resilience),
    Phase("staples", staples),
)
