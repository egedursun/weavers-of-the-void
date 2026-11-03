from dataclasses import dataclass, field

from sqlalchemy import func, select

from aerona.catalog.commodities import COMMODITIES, FOOD_KINDS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import tools_factor
from aerona.engine.economy.stocks import aggregate_need, epoch_need, goods_of, holdings, nourishment_need
from aerona.engine.environment.profile import CropMix, crop_mix
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.rules.registry import Rules

THOUSAND = 1000
EATING_ORDER = (CommodityKind.BREAD, CommodityKind.LIVESTOCK, CommodityKind.FISH, CommodityKind.GRAIN)


@dataclass(frozen=True)
class Meal:
    fed_pct: int
    eaten: dict[CommodityKind, int] = field(default_factory=dict)
    short: dict[CommodityKind, int] = field(default_factory=dict)


def mix_of(ctx: TickContext, book: EconomyBook, community: EntityRow) -> CropMix:
    region = book.ground.region_of(community.id)
    if region is None:
        return CropMix(1.0, 0.0, 0.0)
    return crop_mix(ctx.rules, farmed=region.farmed, grazed=region.grazed, coastal=region.coast_kind is not CoastKind.NONE, river=region.river_class)


async def harvest_goods(ctx: TickContext, book: EconomyBook, community: EntityRow, rate: float, farmer_share: float) -> dict[CommodityKind, int]:
    table = ctx.rules.economy
    hands = book.hands(community.id, Job.FARMING, Job.HERDING, Job.FISHING)
    farmers = hands if hands is not None else round_half_up(headcount(community) * farmer_share / PERCENT)
    tools = await tools_factor(ctx, community.id, farmers)
    units = farmers * table.farm_units_per_1000_farmers / THOUSAND * rate * tools
    mix = mix_of(ctx, book, community)
    fodder = round_half_up(units * mix.pasture * table.fodder_share_pct / PERCENT)
    split = {
        CommodityKind.GRAIN: round_half_up(units * mix.grain),
        CommodityKind.LIVESTOCK: round_half_up(units * mix.pasture) - fodder,
        CommodityKind.FODDER: fodder,
        CommodityKind.FISH: round_half_up(units * mix.fish),
    }
    for kind, amount in split.items():
        await goods_of(ctx.session, ctx.epoch).add(community.id, kind, max(0, amount), GoodsFlow.HARVEST)
    return split


async def eat(ctx: TickContext, community: EntityRow) -> Meal:
    population = headcount(community)
    need = nourishment_need(ctx.rules, population)
    if need <= 0:
        return Meal(PERCENT)
    ledger = goods_of(ctx.session, ctx.epoch)
    eaten: dict[CommodityKind, int] = {}
    left = need
    for kind in EATING_ORDER:
        share = epoch_need(ctx.rules, population, kind)
        taken = sum(lot.quantity for lot in await ledger.take(community.id, kind, share, GoodsFlow.CONSUMPTION, best_first=False))
        eaten[kind] = taken
        left = max(0, left - taken * COMMODITIES[kind].nourishment)
    held = await holdings(ctx.session, community.id)
    for kind in EATING_ORDER:
        if left <= 0:
            break
        value = COMMODITIES[kind].nourishment
        units = min(held.get(kind, 0), -(-left // value))
        if units <= 0:
            continue
        taken = sum(lot.quantity for lot in await ledger.take(community.id, kind, units, GoodsFlow.CONSUMPTION, best_first=False))
        eaten[kind] = eaten.get(kind, 0) + taken
        left = max(0, left - taken * value)
    fed = round_half_up((need - left) * PERCENT / need)
    return Meal(fed, eaten)


async def gather_commons(ctx: TickContext, book: EconomyBook, community: EntityRow, farmer_share: float) -> dict[CommodityKind, int]:
    table = ctx.rules.economy
    region = book.ground.region_of(community.id)
    if region is None:
        return {}
    farmers = headcount(community) * farmer_share / PERCENT
    gathered = {
        CommodityKind.TIMBER: round_half_up(farmers * table.commons_timber_per_1000_farmers / THOUSAND * region.forest_cover / PERCENT),
        CommodityKind.STONE: round_half_up(farmers * table.commons_stone_per_1000_farmers / THOUSAND * region.roughness / PERCENT),
    }
    ledger = goods_of(ctx.session, ctx.epoch)
    for kind, amount in gathered.items():
        material = MaterialKind.WOOD if kind is CommodityKind.TIMBER else MaterialKind.STONE
        await ledger.add(community.id, kind, amount, GoodsFlow.HARVEST, material=material)
    return gathered


async def prosthetic_demand(ctx: TickContext, community: EntityRow) -> int:
    maimed = await ctx.session.scalar(select(func.coalesce(func.sum(MaimedCohortRow.count), 0)).where(MaimedCohortRow.community_entity_id == community.id))
    return round_half_up(int(maimed or 0) * ctx.rules.economy.prosthetic_tools_per_1000_maimed / THOUSAND)


async def wear(ctx: TickContext, community: EntityRow) -> dict[CommodityKind, int]:
    population = headcount(community)
    short: dict[CommodityKind, int] = {}
    for kind in COMMODITIES:
        if kind in FOOD_KINDS:
            continue
        need = epoch_need(ctx.rules, population, kind)
        if kind is CommodityKind.TOOLS:
            need += await prosthetic_demand(ctx, community)
        if need <= 0:
            continue
        taken = sum(lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, kind, need, GoodsFlow.CONSUMPTION, best_first=False))
        if taken < need:
            short[kind] = need - taken
    return short


def store_kind(aggregate: Commodity) -> WorkshopKind:
    return WorkshopKind.GRANARY if aggregate is Commodity.FOOD else WorkshopKind.WAREHOUSE


def storage_index(rules: Rules, store: WorkshopRow | None, aggregate: Commodity) -> int:
    table = rules.economy
    per_level = table.storage_per_granary_level if aggregate is Commodity.FOOD else table.storage_per_warehouse_level
    return table.storage_base_index + (store.level * per_level if store is not None else 0)


async def enforce_storage(ctx: TickContext, book: EconomyBook, community: EntityRow) -> int:
    population = headcount(community)
    spilled = 0
    held = await holdings(ctx.session, community.id)
    for aggregate in Commodity:
        family = {kind: quantity for kind, quantity in held.items() if COMMODITIES[kind].aggregate is aggregate and quantity > 0}
        stocked = sum(family.values())
        need = aggregate_need(ctx.rules, population, aggregate)
        room = round_half_up(
            storage_index(ctx.rules, book.workshop(community.id, store_kind(aggregate)), aggregate) * max(1, need) / ctx.rules.economy.supply_index_epoch
        )
        excess = stocked - room
        if excess <= 0:
            continue
        for kind, quantity in sorted(family.items(), key=lambda item: (-item[1], item[0].value)):
            part = min(quantity, round_half_up(excess * quantity / stocked))
            spilled += sum(lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, kind, part, GoodsFlow.OVERFLOW, best_first=False))
    return spilled


def farmer_share(book: EconomyBook, community: EntityRow) -> float:
    row = book.societies.get(community.id)
    return row.share(SocialClass.FARMER) if row is not None else PERCENT / len(SocialClass)
