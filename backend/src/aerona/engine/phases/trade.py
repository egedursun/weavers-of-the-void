from collections import defaultdict
from collections.abc import Mapping

from aerona.catalog.commodities import STRATEGIC_KINDS
from aerona.catalog.materials import COIN_MATERIALS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.record_context import Term
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.economy import CurrencyRow, ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.money import MINTERS, MoneyTally, adopt, coin_metal, found_currency, issued_by, mint, tend_currencies
from aerona.engine.economy.routes import Link, link_weight, trade_links
from aerona.engine.economy.stocks import epoch_need, holding
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.folkways.biases import lean_community
from aerona.engine.industry.owners import owners_starved
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import BondIndex, canon
from aerona.engine.primitives.stats import headcount, set_stats, stat
from aerona.engine.primitives.strength import military_strength
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.war import declare_war
from aerona.rules.registry import Rules

TRADER_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.FACTION, EntityType.PEOPLE})
STRATEGIC_INPUTS: dict[CommodityKind, tuple[CommodityKind, ...]] = {
    CommodityKind.ORE: (CommodityKind.WEAPONS, CommodityKind.ARMOUR, CommodityKind.TOOLS),
    CommodityKind.LIVESTOCK: (CommodityKind.MOUNTS,),
    CommodityKind.TIMBER: (CommodityKind.SIEGE_MATERIEL,),
}
STRATEGIC_MATERIALS = frozenset({MaterialKind.IRON, MaterialKind.STAR_METAL, MaterialKind.SKYSTEEL, MaterialKind.GREAT_BONE})


TRADE_MODES = (MovementMode.ON_FOOT, MovementMode.WHEELED, MovementMode.BOAT)


def footed_ease(ground: EnvironmentBook, seed: int, epoch: int, region: RegionEnvironmentRow) -> float:
    seasons: list[WorldSeasonRow | None] = [*ground.seasons_of(region.world_id)] or [None]
    slots = [
        max(ground.footed(seed, epoch, region, mode.value, season=season, slot=f"trade.{region.entity_id}.{index}") for mode in TRADE_MODES)
        for index, season in enumerate(seasons)
    ]
    return sum(slots) / len(slots) / PERCENT


def route_ease(rules: Rules, ground: EnvironmentBook | None, first: int, second: int, *, seed: int, epoch: int) -> float:
    if ground is None:
        return 1.0
    eases: list[float] = []
    for endpoint in (first, second):
        region = ground.region_of(endpoint)
        if region is None:
            continue
        eases.append(footed_ease(ground, seed, epoch, region))
    if not eases:
        return 1.0
    floor = rules.trade.route_ease_floor_pct / PERCENT
    return floor + (1 - floor) * sum(eases) / len(eases)


def route_income(
    ctx: TickContext, entities: Mapping[int, EntityRow], links: list[Link], knowledge: KnowledgeMap, ground: EnvironmentBook | None = None
) -> dict[int, tuple[float, float]]:
    settings = ctx.rules.trade
    prosperity: dict[int, float] = defaultdict(float)
    wealth: dict[int, float] = defaultdict(float)
    for link in links:
        ease = route_ease(ctx.rules, ground, link.first, link.second, seed=ctx.environment.world_seed, epoch=ctx.epoch) * link_weight(ctx, link)
        for endpoint in (link.first, link.second):
            if endpoint not in entities:
                continue
            multiplier = knowledge.times(ctx.rules, endpoint, KnowledgeBranch.TRADE, settings.knowledge_mult) * ease
            prosperity[endpoint] += settings.route_prosperity * multiplier
            wealth[endpoint] += settings.route_wealth * ease
    return {entity_id: (prosperity[entity_id], wealth[entity_id]) for entity_id in prosperity}


@reads(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.calendars",
    "table.entities",
    "table.forced_weather",
    "table.holder_levels",
    "table.nodes",
    "table.place_environment",
    "table.polity_profiles",
    "table.region_environment",
    "table.sky_events",
    "table.stars",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
    "trade_route.culture",
)
@writes("faction.wealth", "people.prosperity", "people.wealth", "settlement.prosperity", "settlement.wealth", "table.entities")
async def trade_income(ctx: TickContext) -> None:
    settings = ctx.rules.trade
    entities = {entity.id: entity for entity in await canon(ctx.session)}
    knowledge = await KnowledgeMap.load(ctx.session)
    ground = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    for entity_id, (prosperity, wealth) in route_income(ctx, entities, await trade_links(ctx), knowledge, ground).items():
        entity = entities[entity_id]
        add_prosperity(ctx.rules, entity, min(prosperity, settings.prosperity_cap))
        current = stat(entity, "wealth")
        if current is not None:
            set_stats(entity, wealth=clamp_int(current + min(wealth, settings.wealth_cap), 0, PERCENT))
        ctx.count("traders")


def owned_resources(bonds: BondIndex, entities: Mapping[int, EntityRow], owner_id: int) -> set[int]:
    return {
        bond.target_node_id
        for bond in bonds.outgoing(owner_id, BondKind.OWNS)
        if bond.target_node_id in entities and entities[bond.target_node_id].entity_type is EntityType.RESOURCE
    }


async def open_trade_route(ctx: TickContext, first: EntityRow, second: EntityRow, description: str) -> bool:
    if first.id == second.id or first.status is not EntityStatus.CANON or second.status is not EntityStatus.CANON:
        return False
    bonds = BondRepository(ctx.session)
    if await bonds.exists_between(first.id, second.id, BondKind.TRADES_WITH) or await bonds.exists_between(first.id, second.id, BondKind.ENEMY):
        return False
    await bonds.connect(BondDraft(first.id, second.id, BondKind.TRADES_WITH, ctx.epoch, description))
    return True


async def _scarce(ctx: TickContext, community: EntityRow) -> list[CommodityKind]:
    population = headcount(community)
    short: list[CommodityKind] = []
    for kind in STRATEGIC_KINDS:
        need = epoch_need(ctx.rules, population, kind)
        if need > 0 and await holding(ctx.session, community.id, kind) * PERCENT < need * ctx.rules.trade.scarcity_pct:
            short.append(kind)
    return short


async def _yields(ctx: TickContext, resource_ids: set[int], wanted: list[CommodityKind]) -> EntityRow | None:
    for resource_id in sorted(resource_ids):
        profile = await ctx.session.get(ResourceProfileRow, resource_id)
        if profile is None:
            continue
        feeds = STRATEGIC_INPUTS.get(profile.commodity, ())
        if profile.commodity in wanted or any(kind in wanted for kind in feeds) or profile.material in STRATEGIC_MATERIALS:
            return await ctx.session.get(EntityRow, resource_id)
    return None


async def _seize(ctx: TickContext, hungry: EntityRow, holder: EntityRow, resource: EntityRow) -> bool:
    if held(hungry.id, holder.id, resource.id):
        return False
    pressed = 1 + await owners_starved(ctx.session, hungry.id) * ctx.rules.ownership.war_owner_pct / PERCENT
    leaning = await lean_community(ctx, hungry.id, BiasedDecision.WAR)
    if not ctx.rng(f"seize.{hungry.id}.{holder.id}.{ctx.epoch}").chance(ctx.rules.trade.rivalry_war_chance * pressed * leaning):
        return False
    if not await declare_war(ctx, hungry.id, holder.id, f"to seize {resource.name}", cause=WarCause.RESOURCE):
        return False
    await record(
        ctx,
        "trade.seize_resource",
        roles={IncidentRole.ACTOR: hungry.id, IncidentRole.OPPONENT: holder.id, IncidentRole.SUBJECT: resource.id},
        facts={"pressed": round(pressed * 100), "leaning": round(leaning * 100)},
        terms=(
            Term("trade.rivalry_war_chance", ctx.rules.trade.rivalry_war_chance),
            Term("ownership.war_owner_pct", pressed, ModifierOp.MULTIPLY, source_node_id=hungry.id),
            Term("biases.war", leaning, ModifierOp.MULTIPLY, source_node_id=hungry.id),
        ),
    )
    return True


async def _barter(ctx: TickContext, first: EntityRow, second: EntityRow, entities: Mapping[int, EntityRow], goods: tuple[set[int], set[int]]) -> bool:
    if held(first.id, second.id) or not ctx.rng("barter").chance(ctx.rules.trade.barter_chance * await lean_community(ctx, first.id, BiasedDecision.TRADE)):
        return False
    offered = ", ".join(entities[item].name for item in sorted(goods[0]))
    wanted = ", ".join(entities[item].name for item in sorted(goods[1]))
    if not await open_trade_route(ctx, first, second, f"{offered} in exchange for {wanted}"):
        return False
    await record(
        ctx,
        "trade.barter",
        roles={IncidentRole.GIVER: first.id, IncidentRole.RECEIVER: second.id, IncidentRole.PRODUCT: sorted(goods[0] | goods[1])},
        facts={"offered": len(goods[0]), "wanted": len(goods[1])},
        steps=(StepDraft(StepAction.OFFER, actor=first.id, target=second.id), StepDraft(StepAction.AGREE, actor=second.id, target=first.id)),
    )
    return True


async def strength_of(ctx: TickContext, entity: EntityRow, known: dict[int, float]) -> float:
    if entity.id not in known:
        known[entity.id] = await military_strength(ctx.session, ctx.rules, entity)
    return known[entity.id]


async def _seize_from_neighbours(
    ctx: TickContext, first: EntityRow, traders: list[EntityRow], holdings: dict[int, set[int]], maps: tuple[BondIndex, RegionAtlas, dict[int, float]]
) -> int:
    bonds, atlas, strengths = maps
    wanted = await _scarce(ctx, first) if first.entity_type in COMMUNITY_TYPES else []
    if not wanted:
        return 0
    for second in traders:
        if first.id == second.id or not holdings[second.id] or bonds.between(first.id, second.id, BondKind.ENEMY):
            continue
        if bonds.between(first.id, second.id, BondKind.TRADES_WITH) or not atlas.near(first.id, second.id, ctx.rules.trade_routes.contact_hops):
            continue
        target = await _yields(ctx, holdings[second.id], wanted)
        if target is None or await strength_of(ctx, first, strengths) <= await strength_of(ctx, second, strengths):
            continue
        if await _seize(ctx, first, second, target):
            return 1
    return 0


@reads(
    "people.martiality",
    "people.population",
    "settlement.defense",
    "settlement.population",
    "table.bias_weights",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.network_nodes",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.relationships",
    "table.resource_profiles",
    "table.skills",
    "table.spy_networks",
    "table.stars",
    "table.workshops",
    "table.world_maps",
    "table.worlds",
)
@writes("table.bias_weights", "table.bonds", "table.chronicle", "table.chronicle_entities", "table.incident_participants", "table.incidents")
async def barter_and_rivalry(ctx: TickContext) -> None:
    session = ctx.session
    entities = {entity.id: entity for entity in await canon(session)}
    bonds = await BondIndex.load(session, [BondKind.OWNS, BondKind.TRADES_WITH, BondKind.ENEMY])
    atlas = await RegionAtlas.load(session)
    traders = [entity for entity in entities.values() if entity.entity_type in TRADER_TYPES]
    holdings = {trader.id: owned_resources(bonds, entities, trader.id) for trader in traders}
    seized = 0
    strengths: dict[int, float] = {}
    for first in traders:
        seized += await _seize_from_neighbours(ctx, first, traders, holdings, (bonds, atlas, strengths))
    opened = 0
    for index, first in enumerate(traders):
        for second in traders[index + 1 :]:
            first_goods, second_goods = holdings[first.id], holdings[second.id]
            if not first_goods or not second_goods or not atlas.same_region(first.id, second.id):
                continue
            if bonds.between(first.id, second.id, BondKind.TRADES_WITH) or bonds.between(first.id, second.id, BondKind.ENEMY):
                continue
            if (
                first_goods - second_goods
                and second_goods - first_goods
                and await _barter(ctx, first, second, entities, (first_goods - second_goods, second_goods - first_goods))
            ):
                opened += 1
    ctx.count("barters", opened)
    ctx.count("seizures", seized)


@reads(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.entities",
    "table.forced_weather",
    "table.herds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.nodes",
    "table.place_environment",
    "table.plague_responses",
    "table.plant_profiles",
    "table.polity_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_products",
    "table.species_profiles",
    "table.stars",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.entities",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
)
async def currency(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = MoneyTally()
    for entity in sorted(book.entities.values(), key=lambda item: item.id):
        if entity.entity_type in MINTERS:
            await mint(ctx, book, entity, tally)
    await adopt(ctx, book, tally)
    await tend_currencies(ctx, book, tally)
    ctx.count("minted", tally.minted)
    ctx.count("adopted", tally.adopted)
    ctx.count("debased", tally.debased)
    ctx.count("reformed", tally.reformed)


async def impose_trade(ctx: TickContext, first_id: int, second_id: int) -> bool:
    first = await ctx.session.get(EntityRow, first_id)
    second = await ctx.session.get(EntityRow, second_id)
    if first is None or second is None:
        raise NotFoundError("No such community.")
    if first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Trade routes join communities.")
    opened = await open_trade_route(ctx, first, second, "by decree")
    if opened:
        await record(ctx, "trade.decree", roles={IncidentRole.ORIGIN: first.id, IncidentRole.DESTINATION: second.id})
    return opened


async def order_minting(ctx: TickContext, entity_id: int, metal: MaterialKind | None = None) -> CurrencyRow:
    entity = await ctx.session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such community.")
    if entity.entity_type not in MINTERS:
        raise ValidationFailedError("Only settlements, peoples and factions mint coins.")
    if await issued_by(ctx, entity.id) is not None:
        raise ValidationFailedError(f"{entity.name} already has its own coin.")
    lot = await coin_metal(ctx, entity.id)
    chosen = metal or (lot.material if lot is not None and lot.material is not None else MaterialKind.COPPER)
    if chosen not in COIN_MATERIALS:
        raise ValidationFailedError("Coins are struck from gold, silver, bronze or copper.")
    return await found_currency(ctx, entity, chosen)


PHASES = (
    Phase("trade_income", trade_income),
    Phase("barter_and_rivalry", barter_and_rivalry),
    Phase("currency", currency),
)
