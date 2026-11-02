from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import BondIndex, canon
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.services.war import declare_war
from aerona.rules.registry import Rules

TRADER_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.FACTION, EntityType.PEOPLE})
MINTER_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.FACTION})
CURRENCY_SUBTYPE = "currency"


TRADE_MODES = (MovementMode.ON_FOOT, MovementMode.WHEELED, MovementMode.BOAT)


def route_ease(rules: Rules, ground: EnvironmentBook | None, first: int, second: int) -> float:
    if ground is None:
        return 1.0
    eases: list[float] = []
    for endpoint in (first, second):
        region = ground.region_of(endpoint)
        if region is None:
            continue
        passable = max(region.passability.get(mode.value, PERCENT) for mode in TRADE_MODES)
        seasons = ground.seasons_of(region.world_id)
        travel = sum(season.travel for season in seasons) / len(seasons) if seasons else PERCENT
        eases.append(passable * travel / PERCENT / PERCENT)
    if not eases:
        return 1.0
    floor = rules.trade.route_ease_floor_pct / PERCENT
    return floor + (1 - floor) * sum(eases) / len(eases)


def route_income(
    ctx: TickContext, entities: Mapping[int, EntityRow], bonds: BondIndex, knowledge: KnowledgeMap, ground: EnvironmentBook | None = None
) -> dict[int, tuple[float, float]]:
    settings = ctx.rules.trade
    prosperity: dict[int, float] = defaultdict(float)
    wealth: dict[int, float] = defaultdict(float)
    for bond in bonds.bonds:
        if bond.kind is not BondKind.TRADES_WITH or not bond.active:
            continue
        ease = route_ease(ctx.rules, ground, bond.source_node_id, bond.target_node_id)
        for endpoint in (bond.source_node_id, bond.target_node_id):
            if endpoint not in entities:
                continue
            multiplier = knowledge.times(ctx.rules, endpoint, KnowledgeBranch.TRADE, settings.knowledge_mult) * ease
            prosperity[endpoint] += settings.route_prosperity * multiplier
            wealth[endpoint] += settings.route_wealth * ease
    return {entity_id: (prosperity[entity_id], wealth[entity_id]) for entity_id in prosperity}


async def trade_income(ctx: TickContext) -> None:
    settings = ctx.rules.trade
    entities = {entity.id: entity for entity in await canon(ctx.session)}
    bonds = await BondIndex.load(ctx.session, [BondKind.TRADES_WITH])
    knowledge = await KnowledgeMap.load(ctx.session)
    ground = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    for entity_id, (prosperity, wealth) in route_income(ctx, entities, bonds, knowledge, ground).items():
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


async def _rivalry(ctx: TickContext, first: EntityRow, second: EntityRow) -> None:
    rng = ctx.rng("rivalry")
    if not rng.chance(ctx.rules.trade.rivalry_war_chance):
        return
    if await declare_war(ctx, first.id, second.id, "rivalry over the same resource", cause=WarCause.RIVALRY):
        await note(
            ctx,
            f"{first.name} and {second.name} fell out over the same resource.",
            key="trade.rivalry",
            ids=[first.id, second.id],
            feed=FeedCategory.WAR,
            kind=ChronicleKind.WORLD,
        )


async def _barter(ctx: TickContext, first: EntityRow, second: EntityRow, entities: Mapping[int, EntityRow], goods: tuple[set[int], set[int]]) -> bool:
    if not ctx.rng("barter").chance(ctx.rules.trade.barter_chance):
        return False
    offered = ", ".join(entities[item].name for item in sorted(goods[0]))
    wanted = ", ".join(entities[item].name for item in sorted(goods[1]))
    if not await open_trade_route(ctx, first, second, f"{offered} in exchange for {wanted}"):
        return False
    await note(ctx, f"Resource barter began between {first.name} and {second.name}.", key="trade.barter", ids=[first.id, second.id], kind=ChronicleKind.TRADE)
    return True


async def barter_and_rivalry(ctx: TickContext) -> None:
    session = ctx.session
    entities = {entity.id: entity for entity in await canon(session)}
    bonds = await BondIndex.load(session, [BondKind.OWNS, BondKind.TRADES_WITH, BondKind.ENEMY])
    atlas = await RegionAtlas.load(session)
    traders = [entity for entity in entities.values() if entity.entity_type in TRADER_TYPES]
    holdings = {trader.id: owned_resources(bonds, entities, trader.id) for trader in traders}
    opened = 0
    for index, first in enumerate(traders):
        for second in traders[index + 1 :]:
            if opened >= ctx.rules.trade.barter_cap:
                ctx.count("barters", opened)
                return
            first_goods, second_goods = holdings[first.id], holdings[second.id]
            if not first_goods or not second_goods or not atlas.same_region(first.id, second.id):
                continue
            if bonds.between(first.id, second.id, BondKind.TRADES_WITH) or bonds.between(first.id, second.id, BondKind.ENEMY):
                continue
            if not (first_goods - second_goods and second_goods - first_goods):
                await _rivalry(ctx, first, second)
                continue
            if await _barter(ctx, first, second, entities, (first_goods - second_goods, second_goods - first_goods)):
                opened += 1
    ctx.count("barters", opened)


def currency_of(bonds: BondIndex, entities: Mapping[int, EntityRow], owner_id: int) -> EntityRow | None:
    for bond in bonds.outgoing(owner_id, BondKind.OWNS):
        item = entities.get(bond.target_node_id)
        if item is not None and item.entity_type is EntityType.ITEM and item.engine_kind is EngineKind.CURRENCY and item.status is EntityStatus.CANON:
            return item
    return None


async def mint_currency(ctx: TickContext, minter: EntityRow) -> EntityRow:
    settings = ctx.rules.trade
    rng = ctx.rng(f"mint.{minter.id}")
    coin = await create_record(
        ctx,
        RecordSpec(
            name=f"{minter.name} Coin",
            entity_type=EntityType.ITEM,
            stats=ItemStats(damage=0, protection=0, might=clamp_int(settings.currency_might_base + rng.die(settings.currency_might_die), 0, PERCENT), curse=0),
            body=f"{minter.name} began to mint its own money.",
            power=settings.currency_power,
            world_id=minter.world_id,
            location_id=minter.id if minter.entity_type is EntityType.SETTLEMENT else minter.location_id,
            subtype=CURRENCY_SUBTYPE,
            engine_kind=EngineKind.CURRENCY,
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(minter.id, coin.id, BondKind.PRODUCED, ctx.epoch, "minting"))
    await bonds.connect(BondDraft(minter.id, coin.id, BondKind.OWNS, ctx.epoch, "minting"))
    await note(ctx, f"{minter.name} began minting its own coin.", key="trade.minting", ids=[minter.id, coin.id], kind=ChronicleKind.TRADE)
    return coin


def may_mint(ctx: TickContext, entity: EntityRow, knowledge: KnowledgeMap) -> bool:
    threshold = ctx.rules.trade.coinage_min_wealth
    rich = stat_or(entity, "prosperity", 0) >= threshold or stat_or(entity, "wealth", 0) >= threshold
    return entity.entity_type in MINTER_TYPES and knowledge.knows(entity.id, KnowledgeBranch.TRADE) and rich


async def _mint_round(ctx: TickContext, entities: Mapping[int, EntityRow], bonds: BondIndex, knowledge: KnowledgeMap) -> int:
    minted = 0
    rng = ctx.rng("minting")
    for entity in list(entities.values()):
        if not may_mint(ctx, entity, knowledge) or currency_of(bonds, entities, entity.id) is not None:
            continue
        if not rng.chance(ctx.rules.trade.coinage_chance):
            continue
        coin = await mint_currency(ctx, entity)
        bonds.add(await BondRepository(ctx.session).connect(BondDraft(entity.id, coin.id, BondKind.OWNS, ctx.epoch, "minting")))
        minted += 1
    return minted


async def _adopt(ctx: TickContext, adopter: EntityRow, owner: EntityRow, coin: EntityRow, bonds: BondIndex) -> None:
    bonds.add(await BondRepository(ctx.session).connect(BondDraft(adopter.id, coin.id, BondKind.OWNS, ctx.epoch, "adopted through trade")))
    await note(
        ctx, f"{adopter.name} began using the money of {owner.name}.", key="trade.adoption", ids=[owner.id, adopter.id, coin.id], kind=ChronicleKind.TRADE
    )


async def _spread_round(ctx: TickContext, entities: Mapping[int, EntityRow], bonds: BondIndex, session: AsyncSession) -> int:
    rng = ctx.rng("adoption")
    worlds = WorldRepository(session)
    adopted = 0
    for bond in sorted(bonds.bonds, key=lambda item: item.id):
        if bond.kind is not BondKind.TRADES_WITH or not bond.active:
            continue
        first, second = entities.get(bond.source_node_id), entities.get(bond.target_node_id)
        if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        if not await worlds.connected(first.world_id, second.world_id):
            continue
        first_coin, second_coin = currency_of(bonds, entities, first.id), currency_of(bonds, entities, second.id)
        if first_coin is not None and second_coin is None and rng.chance(ctx.rules.trade.currency_adopt_chance):
            await _adopt(ctx, second, first, first_coin, bonds)
            adopted += 1
        elif second_coin is not None and first_coin is None and rng.chance(ctx.rules.trade.currency_adopt_chance):
            await _adopt(ctx, first, second, second_coin, bonds)
            adopted += 1
        elif first_coin is not None and first_coin is second_coin:
            add_prosperity(ctx.rules, first, ctx.rules.trade.shared_currency_prosperity)
            add_prosperity(ctx.rules, second, ctx.rules.trade.shared_currency_prosperity)
    return adopted


async def currency(ctx: TickContext) -> None:
    session = ctx.session
    entities = {entity.id: entity for entity in await canon(session)}
    bonds = await BondIndex.load(session, [BondKind.OWNS, BondKind.TRADES_WITH])
    knowledge = await KnowledgeMap.load(session)
    minted = await _mint_round(ctx, entities, bonds, knowledge)
    entities = {entity.id: entity for entity in await canon(session)}
    ctx.count("minted", minted)
    ctx.count("adopted", await _spread_round(ctx, entities, bonds, session))


async def impose_trade(ctx: TickContext, first_id: int, second_id: int) -> bool:
    first = await ctx.session.get(EntityRow, first_id)
    second = await ctx.session.get(EntityRow, second_id)
    if first is None or second is None:
        raise NotFoundError("No such community.")
    if first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Trade routes join communities.")
    opened = await open_trade_route(ctx, first, second, "by decree")
    if opened:
        await note(
            ctx, f"A trade route opened between {first.name} and {second.name}.", key="trade.decree", ids=[first.id, second.id], kind=ChronicleKind.TRADE
        )
    return opened


async def order_minting(ctx: TickContext, entity_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such community.")
    if entity.entity_type not in MINTER_TYPES:
        raise ValidationFailedError("Only settlements and factions mint coins.")
    bonds = await BondIndex.load(ctx.session, [BondKind.OWNS])
    entities = {item.id: item for item in await canon(ctx.session, [EntityType.ITEM])}
    if currency_of(bonds, entities, entity.id) is not None:
        raise ValidationFailedError(f"{entity.name} already has its own coin.")
    return await mint_currency(ctx, entity)


PHASES = (
    Phase("trade_income", trade_income),
    Phase("barter_and_rivalry", barter_and_rivalry),
    Phase("currency", currency),
)
