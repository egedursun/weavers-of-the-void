from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.operations.admiralty import AdmiraltyTally, keep_admiralties
from aerona.engine.operations.command import CommandTally, organise
from aerona.engine.operations.expeditions import ExpeditionTally, keep_expeditions
from aerona.engine.operations.supply import SupplyTally, keep_network
from aerona.engine.operations.theatres import TheatreTally, keep_theatres
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "army.morale",
    "army.size",
    "people.population",
    "table.armies",
    "table.army_officers",
    "table.army_profiles",
    "table.army_units",
    "table.bonds",
    "table.campaign_fronts",
    "table.commander_traits",
    "table.creator",
    "table.depots",
    "table.dimensions",
    "table.echelons",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.item_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.theatres",
    "table.transport_assets",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes(
    "army.morale",
    "army.size",
    "people.population",
    "table.army_units",
    "table.chronicle",
    "table.chronicle_entities",
    "table.depots",
    "table.echelons",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.theatres",
    "table.transport_assets",
)
async def order_of_battle(ctx: TickContext) -> None:
    command, supply, theatres = CommandTally(), SupplyTally(), TheatreTally()
    await organise(ctx, command)
    await keep_network(ctx, supply)
    await keep_theatres(ctx, theatres)
    count(ctx, "order_of_battle", command)
    count(ctx, "supply_network", supply)
    count(ctx, "theatres", theatres)


@reads(
    "table.admiralties",
    "table.bonds",
    "table.entities",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.vassalages",
    "table.vessel_profiles",
)
@writes("table.admiralties")
async def admiralty(ctx: TickContext) -> None:
    tally = AdmiraltyTally()
    await keep_admiralties(ctx, tally)
    count(ctx, "admiralty", tally)


@reads("table.bonds", "table.expedition_members", "table.expeditions", "table.quirks")
@writes("table.expedition_logs", "table.expedition_members", "table.expeditions", "table.quirks")
async def expeditions(ctx: TickContext) -> None:
    tally = ExpeditionTally()
    await keep_expeditions(ctx, tally)
    count(ctx, "expeditions", tally)


PHASES = (Phase("order_of_battle", order_of_battle), Phase("admiralty", admiralty), Phase("expeditions", expeditions))
