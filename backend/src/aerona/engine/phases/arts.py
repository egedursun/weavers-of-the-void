from aerona.engine.arts.forgery import ForgeryTally, keep_forgeries
from aerona.engine.arts.market import MarketTally, keep_market
from aerona.engine.arts.movements import MovementTally, keep_movements
from aerona.engine.arts.sport import SportTally, keep_sport
from aerona.engine.constructs.making import MakingTally, make_constructs
from aerona.engine.constructs.orders import OrderTally, keep_constructs
from aerona.engine.constructs.remaking import RemadeTally, keep_remade
from aerona.engine.constructs.wards import SealTally, keep_seals
from aerona.engine.context import TickContext
from aerona.engine.ecology.contracts import ContractTally, keep_contracts
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.sacred.astrology import SignTally, sign_births


@reads(
    "faction.wealth",
    "house.wealth",
    "item.curse",
    "item.damage",
    "item.might",
    "item.protection",
    "mortal.creativity",
    "settlement.population",
    "table.art_prices",
    "table.artwork_profiles",
    "table.bonds",
    "table.brands",
    "table.canon_works",
    "table.collectors",
    "table.community_stocks",
    "table.courts",
    "table.creator",
    "table.currencies",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.forgeries",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.gatherings",
    "table.good_kinds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mortal_profiles",
    "table.museum_collections",
    "table.name_registry",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.relics",
    "table.resource_profiles",
    "table.secrets",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.state_changes",
    "table.world_materials",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.art_prices",
    "table.art_sales",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.collectors",
    "table.courts",
    "table.crime_cases",
    "table.entities",
    "table.forgeries",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.item_history",
    "table.item_profiles",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.node_materials",
    "table.polity_profiles",
    "table.relics",
    "table.secrets",
    "table.settlement_profiles",
)
async def art_market(ctx: TickContext) -> None:
    market, forgeries = MarketTally(), ForgeryTally()
    await keep_market(ctx, market)
    await keep_forgeries(ctx, forgeries)
    count(ctx, "art_market", market)
    count(ctx, "forgeries", forgeries)


@reads(
    "people.population",
    "settlement.population",
    "table.art_movements",
    "table.artwork_profiles",
    "table.canon_works",
    "table.culture_values",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.node_births",
    "table.nodes",
    "table.structure_profiles",
)
@writes(
    "table.artwork_profiles",
    "table.canon_works",
    "table.chronicle",
    "table.chronicle_entities",
    "table.culture_values",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
)
async def art_movements(ctx: TickContext) -> None:
    tally = MovementTally()
    await keep_movements(ctx, tally)
    count(ctx, "art_movements", tally)


@reads(
    "settlement.population",
    "table.clubs",
    "table.entities",
    "table.faction_profiles",
    "table.games",
    "table.kind_holdings",
    "table.leagues",
    "table.nodes",
    "table.structure_profiles",
)
async def pastimes(ctx: TickContext) -> None:
    tally = SportTally()
    await keep_sport(ctx, tally)
    count(ctx, "pastimes", tally)


@reads("table.army_units", "table.bonds", "table.constructs", "table.entities", "table.holder_levels", "table.nodes", "table.polity_profiles", "table.skills")
async def constructs(ctx: TickContext) -> None:
    making, orders, seals = MakingTally(), OrderTally(), SealTally()
    await make_constructs(ctx, making)
    await keep_constructs(ctx, orders)
    await keep_seals(ctx, seals)
    count(ctx, "constructs_made", making)
    count(ctx, "constructs", orders)
    count(ctx, "construct_seals", seals)


@reads("settlement.population", "table.beast_profiles", "table.deep_passages", "table.entities", "table.monster_contracts", "table.node_births", "table.nodes")
@writes("table.chronicle", "table.chronicle_entities", "table.incident_facts", "table.incident_participants", "table.incidents", "table.monster_contracts")
async def monster_contracts(ctx: TickContext) -> None:
    tally = ContractTally()
    await keep_contracts(ctx, tally)
    count(ctx, "monster_contracts", tally)


@reads(
    "celestial.cycle",
    "celestial.influence",
    "celestial.visibility",
    "mortal.age",
    "mortal.perception",
    "mortal.willpower",
    "settlement.population",
    "table.divination_systems",
    "table.entities",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.world_seasons",
)
@writes("mortal.perception", "mortal.willpower", "table.birth_signs", "table.entities")
async def birth_signs(ctx: TickContext) -> None:
    tally = SignTally()
    await sign_births(ctx, tally)
    count(ctx, "birth_signs", tally)


@reads("table.remade")
async def remade_lives(ctx: TickContext) -> None:
    tally = RemadeTally()
    await keep_remade(ctx, tally)
    count(ctx, "remade", tally)


PHASES = (
    Phase("art_market", art_market),
    Phase("art_movements", art_movements),
    Phase("pastimes", pastimes),
    Phase("constructs", constructs),
    Phase("monster_contracts", monster_contracts),
    Phase("birth_signs", birth_signs),
    Phase("remade_lives", remade_lives),
)
