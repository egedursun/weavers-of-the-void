from dataclasses import dataclass, field

from sqlalchemy import func, select

from aerona.catalog.commodities import COMMODITIES, FOOD_KINDS
from aerona.catalog.methods import FUEL_FAMILY, FUEL_HEAT
from aerona.constants.units import PERCENT
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.economy import ProductionRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.environment import CoastKind, TemperatureBand
from aerona.domain.enums.industry import ProcessKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import tools_factor
from aerona.engine.economy.stocks import DEFAULT_QUALITY, aggregate_need, epoch_need, goods_of, holdings, nourishment_need
from aerona.engine.environment.profile import CropMix, crop_mix
from aerona.engine.industry.energy import scale_by_energy
from aerona.engine.industry.methods import feed, method_for
from aerona.engine.industry.pollution import fish_factor, region_id_of
from aerona.engine.mind.preferences import demand_factor, market_fit
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.engine.settlement.storage import capacity_of, storage_room, store_kind
from aerona.rules.registry import Rules

THOUSAND = 1000
HARVEST_STEP = "harvest"
EATING_ORDER = (
    CommodityKind.BREAD,
    CommodityKind.MEAT,
    CommodityKind.CHEESE,
    CommodityKind.LIVESTOCK,
    CommodityKind.FISH,
    CommodityKind.TUBERS,
    CommodityKind.GRAIN,
    CommodityKind.FRUIT,
    CommodityKind.MILK,
)
TENTH = 10
COMMONS_MATERIAL = {CommodityKind.TIMBER: MaterialKind.WOOD, CommodityKind.STONE: MaterialKind.STONE}
COLD_LAND = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
ORCHARD_LAND = frozenset({TemperatureBand.TEMPERATE, TemperatureBand.WARM, TemperatureBand.HOT})


@dataclass(frozen=True)
class Meal:
    fed_pct: int
    eaten: dict[CommodityKind, int] = field(default_factory=dict)
    short: dict[CommodityKind, int] = field(default_factory=dict)
    wanted: dict[CommodityKind, int] = field(default_factory=dict)
    quality: int = DEFAULT_QUALITY


@dataclass(frozen=True)
class Wear:
    wanted: dict[CommodityKind, int] = field(default_factory=dict)
    got: dict[CommodityKind, int] = field(default_factory=dict)

    @property
    def short(self) -> dict[CommodityKind, int]:
        return {kind: amount - self.got.get(kind, 0) for kind, amount in self.wanted.items() if amount > self.got.get(kind, 0)}


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
    farming = method_for(book, community.id, ProcessKind.FARMING)
    fishing = method_for(book, community.id, ProcessKind.FISHING)
    crews = round_half_up(farmers * ctx.rules.energy.extraction_per_100_workers / PERCENT)
    land = units * farming.output_pct / PERCENT * scale_by_energy(book, community.id, farming.energy, farming.energy_need * crews)
    land *= await feed(ctx, community.id, farming, crews)
    sea = units * fishing.output_pct / PERCENT * fish_factor(ctx.rules, book.pollution.get(region_id_of(book, community.id) or -1))
    if mix.fish > 0:
        sea *= scale_by_energy(book, community.id, fishing.energy, round_half_up(fishing.energy_need * crews * mix.fish))
    fodder = round_half_up(land * mix.pasture * table.fodder_share_pct / PERCENT)
    chain = ctx.rules.food_chain
    herds = round_half_up(land * mix.pasture) - fodder
    milk = round_half_up(herds * chain.milk_pct / PERCENT)
    tuber_share, fruit_share = field_shares(ctx, book, community)
    fields = land * mix.grain
    split = {
        CommodityKind.GRAIN: round_half_up(fields * (1 - tuber_share - fruit_share)),
        CommodityKind.TUBERS: round_half_up(fields * tuber_share),
        CommodityKind.FRUIT: round_half_up(fields * fruit_share),
        CommodityKind.LIVESTOCK: herds - milk,
        CommodityKind.MILK: milk,
        CommodityKind.DUNG: round_half_up(herds * chain.dung_per_10 / TENTH),
        CommodityKind.FODDER: fodder,
        CommodityKind.FISH: round_half_up(sea * mix.fish),
    }
    for kind, amount in split.items():
        bonus = fishing.quality_bonus if kind is CommodityKind.FISH else farming.quality_bonus
        await goods_of(ctx.session, ctx.epoch).add(community.id, kind, max(0, amount), GoodsFlow.HARVEST, quality=DEFAULT_QUALITY + bonus)
    ctx.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=community.id,
            step=HARVEST_STEP,
            output=CommodityKind.GRAIN,
            quantity=max(0, split[CommodityKind.GRAIN] + split[CommodityKind.LIVESTOCK]),
            quality=DEFAULT_QUALITY + farming.quality_bonus,
            inputs={},
            workers=farmers,
            method=farming.kind,
        )
    )
    return split


def field_shares(ctx: TickContext, book: EconomyBook, community: EntityRow) -> tuple[float, float]:
    chain = ctx.rules.food_chain
    region = book.ground.region_of(community.id)
    if region is None:
        return chain.tuber_pct / PERCENT, 0.0
    poor = region.temperature_band in COLD_LAND or region.soil_fertility < chain.poor_soil_at
    tubers = (chain.tuber_cold_pct if poor else chain.tuber_pct) / PERCENT
    orchards = region.temperature_band in ORCHARD_LAND and region.moisture >= chain.fruit_moisture_at
    return tubers, (chain.fruit_pct / PERCENT if orchards else 0.0)


def eating_order(staples: tuple[CommodityKind, ...]) -> tuple[CommodityKind, ...]:
    return (*staples, *(kind for kind in EATING_ORDER if kind not in staples))


def diet_demand(rules: Rules, population: int, staples: tuple[CommodityKind, ...]) -> dict[CommodityKind, int]:
    base = {kind: epoch_need(rules, population, kind) for kind in EATING_ORDER}
    if not staples:
        return base
    weight = {kind: base[kind] * (rules.consumption.staple_demand_pct if kind in staples else PERCENT) / PERCENT for kind in base}
    wanted = sum(base[kind] * COMMODITIES[kind].nourishment for kind in base)
    weighted = sum(weight[kind] * COMMODITIES[kind].nourishment for kind in base)
    scale = wanted / weighted if weighted > 0 else 1.0
    return {kind: round_half_up(weight[kind] * scale) for kind in base}


async def substitute_order(ctx: TickContext, community: EntityRow, order: tuple[CommodityKind, ...]) -> tuple[CommodityKind, ...]:
    table = ctx.rules.substitution
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    tastes = await market_fit(ctx.session, community.id)

    def cost(kind: CommodityKind) -> float:
        spec = COMMODITIES[kind]
        price = spec.base_price * (society.price(spec.aggregate) / PERCENT if society is not None else 1.0)
        per_meal = price / max(1, spec.nourishment) * table.price_pct / PERCENT
        liking = float(demand_factor(ctx.rules, tastes, kind.value) ** (table.liking_pct / PERCENT))
        return per_meal / max(0.1, liking)

    return tuple(sorted(order, key=lambda kind: (cost(kind), order.index(kind))))


async def eat(ctx: TickContext, community: EntityRow, staples: tuple[CommodityKind, ...] = ()) -> Meal:
    population = headcount(community)
    need = nourishment_need(ctx.rules, population)
    if need <= 0:
        return Meal(PERCENT)
    ledger = goods_of(ctx.session, ctx.epoch)
    order = eating_order(staples)
    wanted = diet_demand(ctx.rules, population, staples)
    eaten: dict[CommodityKind, int] = {}
    tasted: list[tuple[int, int]] = []
    left = need
    for kind in order:
        lots = await ledger.take(community.id, kind, wanted.get(kind, 0), GoodsFlow.CONSUMPTION, best_first=False)
        taken = sum(lot.quantity for lot in lots)
        tasted.extend((lot.quality, lot.quantity) for lot in lots)
        eaten[kind] = taken
        left = max(0, left - taken * COMMODITIES[kind].nourishment)
    held = await holdings(ctx.session, community.id)
    for kind in await substitute_order(ctx, community, order):
        if left <= 0:
            break
        value = COMMODITIES[kind].nourishment
        units = min(held.get(kind, 0), -(-left // value))
        if units <= 0:
            continue
        lots = await ledger.take(community.id, kind, units, GoodsFlow.CONSUMPTION, best_first=False)
        taken = sum(lot.quantity for lot in lots)
        tasted.extend((lot.quality, lot.quantity) for lot in lots)
        eaten[kind] = eaten.get(kind, 0) + taken
        left = max(0, left - taken * value)
    fed = round_half_up((need - left) * PERCENT / need)
    short = {kind: amount - min(amount, eaten.get(kind, 0)) for kind, amount in wanted.items() if amount > eaten.get(kind, 0)}
    portions = sum(quantity for _, quantity in tasted)
    quality = round_half_up(sum(value * quantity for value, quantity in tasted) / portions) if portions else DEFAULT_QUALITY
    return Meal(fed, eaten, short, wanted, quality)


async def gather_commons(ctx: TickContext, book: EconomyBook, community: EntityRow, farmer_share: float) -> dict[CommodityKind, int]:
    table = ctx.rules.economy
    region = book.ground.region_of(community.id)
    if region is None:
        return {}
    farmers = headcount(community) * farmer_share / PERCENT
    gathered = {
        CommodityKind.TIMBER: round_half_up(farmers * table.commons_timber_per_1000_farmers / THOUSAND * region.forest_cover / PERCENT),
        CommodityKind.STONE: round_half_up(farmers * table.commons_stone_per_1000_farmers / THOUSAND * region.roughness / PERCENT),
        CommodityKind.PEAT: round_half_up(farmers * ctx.rules.food_chain.peat_per_1000 / THOUSAND * region.wetland / PERCENT),
    }
    ledger = goods_of(ctx.session, ctx.epoch)
    for kind, amount in gathered.items():
        material = COMMONS_MATERIAL.get(kind)
        await ledger.add(community.id, kind, amount, GoodsFlow.HARVEST, material=material)
    return gathered


async def prosthetic_demand(ctx: TickContext, community: EntityRow) -> int:
    maimed = await ctx.session.scalar(select(func.coalesce(func.sum(MaimedCohortRow.count), 0)).where(MaimedCohortRow.community_entity_id == community.id))
    return round_half_up(int(maimed or 0) * ctx.rules.economy.prosthetic_tools_per_1000_maimed / THOUSAND)


async def wear(ctx: TickContext, community: EntityRow) -> Wear:
    population = headcount(community)
    wanted: dict[CommodityKind, int] = {}
    got: dict[CommodityKind, int] = {}
    for kind in COMMODITIES:
        if kind in FOOD_KINDS:
            continue
        need = epoch_need(ctx.rules, population, kind)
        if kind is CommodityKind.TOOLS:
            need += await prosthetic_demand(ctx, community)
        if need <= 0:
            continue
        wanted[kind] = need
        got[kind] = sum(lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, kind, need, GoodsFlow.CONSUMPTION, best_first=False))
    if CommodityKind.FUEL in wanted and got.get(CommodityKind.FUEL, 0) < wanted[CommodityKind.FUEL]:
        got[CommodityKind.FUEL] += await burn_substitutes(ctx, community, wanted[CommodityKind.FUEL] - got[CommodityKind.FUEL])
    return Wear(wanted, got)


async def burn_substitutes(ctx: TickContext, community: EntityRow, short: int) -> int:
    table = ctx.rules.energy
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    fuel_heat = max(1, table.heat_per_fuel)

    def cost(kind: CommodityKind) -> float:
        spec = COMMODITIES[kind]
        price = spec.base_price * (society.price(spec.aggregate) / PERCENT if society is not None else 1.0)
        return price / max(1, int(getattr(table, FUEL_HEAT[kind])))

    covered = 0
    heat = short * fuel_heat
    for kind in sorted((kind for kind in FUEL_FAMILY if kind not in (CommodityKind.FUEL, CommodityKind.TIMBER)), key=lambda item: (cost(item), item.value)):
        per = int(getattr(table, FUEL_HEAT[kind]))
        if heat <= 0 or per <= 0:
            continue
        burned = sum(
            lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, kind, -(-heat // per), GoodsFlow.CONSUMPTION, best_first=False)
        )
        heat -= burned * per
        covered += burned * per // fuel_heat
    return min(short, covered)


async def enforce_storage(ctx: TickContext, book: EconomyBook, community: EntityRow) -> int:
    population = headcount(community)
    spilled = 0
    held = await holdings(ctx.session, community.id)
    infrastructure = await ctx.session.get(SettlementInfrastructureRow, community.id)
    for aggregate in Commodity:
        family = {kind: quantity for kind, quantity in held.items() if COMMODITIES[kind].aggregate is aggregate and quantity > 0}
        stocked = sum(family.values())
        need = aggregate_need(ctx.rules, population, aggregate)
        store = book.workshop(community.id, store_kind(aggregate))
        room = storage_room(ctx.rules, capacity_of(ctx.rules, infrastructure, store, aggregate, book.design_of(store)), need)
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
