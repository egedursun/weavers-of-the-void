from aerona.engine.context import TickContext
from aerona.engine.deepening.realms_w52 import RealmTally, deepen_realms
from aerona.engine.deepening.towns_w52 import TownTally, deepen_towns
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.assistive_aids",
    "table.bonds",
    "table.cooperatives",
    "table.cult_doctrines",
    "table.districts",
    "table.entities",
    "table.gardens",
    "table.item_profiles",
    "table.museum_collections",
    "table.museum_pieces",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.polity_members",
    "table.poor_relief",
    "table.public_clocks",
    "table.reconstructions",
    "table.region_environment",
    "table.relationships",
    "table.settlement_profiles",
    "table.structure_designs",
    "table.structure_profiles",
    "table.structure_sections",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.cult_doctrines",
    "table.districts",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.people_cultures",
    "table.poor_relief",
    "table.reconstructions",
    "table.region_environment",
    "table.relationships",
    "table.settlement_profiles",
)
async def deepened_towns(ctx: TickContext) -> None:
    tally = TownTally()
    await deepen_towns(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"deepened_{key}", value)


@reads(
    "table.claims",
    "table.confederations",
    "table.cosmos",
    "table.crime_cases",
    "table.culture_honour",
    "table.deep_passages",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.estate_privileges",
    "table.estate_profiles",
    "table.evidence",
    "table.faction_goals",
    "table.faction_profiles",
    "table.fugitives",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.household_members",
    "table.households",
    "table.memberships",
    "table.movements",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.settlement_profiles",
    "table.signal_links",
    "table.sons",
    "table.stars",
    "table.title_profiles",
    "table.vassalages",
    "table.worlds",
)
@writes(
    "table.appeals",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.crime_cases",
    "table.estate_profiles",
    "table.evidence",
    "table.faction_goals",
    "table.faction_profiles",
    "table.identities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memberships",
    "table.movements",
    "table.oaths",
    "table.offices",
    "table.people_culture",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.signal_links",
    "table.title_profiles",
)
async def deepened_realms(ctx: TickContext) -> None:
    tally = RealmTally()
    await deepen_realms(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"deepened_{key}", value)


PHASES = (Phase("deepened_towns", deepened_towns), Phase("deepened_realms", deepened_realms))
