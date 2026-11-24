from dataclasses import dataclass, fields
from typing import Any, cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.life_traits import SETTLE_MODE_TRAITS, WAR_TERRAIN_TRAITS, having
from aerona.catalog.prehistory import WORLD_PREHISTORY
from aerona.catalog.world_views import BOUND_NEEDS, WORLD_VIEWS, WorldViewSpec
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.core.total import partial
from aerona.db.read_memo import memo_of
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.means import WaterLiftRow
from aerona.db.tables.sacred import GeniusLocusRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.world_views import SHARE_MAX, WORLD_VIEW_FIELDS, WorldViewRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.life_traits import SettleModeTrait, WarTerrainTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.physics import AirNeed
from aerona.domain.enums.prehistory import PrehistoryKind
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight
from aerona.engine.body.customs import people_id_of
from aerona.engine.body.variants import biology_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_types import disaster_pct, mechanics_of
from aerona.engine.economy.purse import take_coin
from aerona.engine.economy.stocks import goods_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

VIEW_TABLES = frozenset({WorldViewRow.__tablename__, WorldRow.__tablename__})
HEAT_STOCKS = commodities_with(CommodityTrait.HEAT_STOCK)
AIR_STOCKS = (CommodityKind.TOOLS,)
OFFERING_STOCKS = commodities_with(CommodityTrait.OFFERING)
DRAWN_FROM = partial(
    BindingNeed,
    {
        BindingNeed.HEAT: (HEAT_STOCKS, GoodsFlow.CONSUMPTION),
        BindingNeed.AIR: (AIR_STOCKS, GoodsFlow.CONSUMPTION),
        BindingNeed.OFFERINGS: (OFFERING_STOCKS, GoodsFlow.OFFERING),
    },
    without=(BindingNeed.NONE, BindingNeed.WATER, BindingNeed.BELIEF, BindingNeed.PLACE, BindingNeed.NAME),
)
UPKEPT = having(SETTLE_MODE_TRAITS, SettleModeTrait.UPKEPT)
COLD_BORN = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
LAND_UNFIT = having(WAR_TERRAIN_TRAITS, WarTerrainTrait.LAND_UNFIT)


@dataclass(frozen=True)
class WorldView:
    light: WorldLight = WorldLight.STAR
    need: BindingNeed = BindingNeed.NONE
    settle: SettleMode = SettleMode.GROUND
    war: WarTerrain = WarTerrain.LAND
    prehistory_kind: PrehistoryKind = PrehistoryKind.FULL
    seasons: bool = True
    nights: bool = True
    fire: bool = True
    soil: bool = True
    sea_roads: bool = False
    timber_pct: int = PERCENT
    food_need_pct: int = PERCENT
    capacity_pct: int = PERCENT
    ore_yield_pct: int = PERCENT
    ship_pct: int = PERCENT
    storm_pct: int = PERCENT
    quake_pct: int = PERCENT
    flood_pct: int = PERCENT
    drought_pct: int = PERCENT
    plague_pct: int = PERCENT
    route_danger: int = 0
    leak: int = 0
    leak_repair: int = 0
    sanity_erosion: int = 0
    fertility_decay: int = 0
    sea_pct: int = 25

    def disaster(self, disaster: Disaster) -> int:
        return {
            Disaster.STORM: self.storm_pct,
            Disaster.EARTHQUAKE: self.quake_pct,
            Disaster.FLOOD: self.flood_pct,
            Disaster.DROUGHT: self.drought_pct,
            Disaster.PLAGUE: self.plague_pct,
        }.get(disaster, PERCENT)


DISASTER_FIELDS = (
    (Disaster.STORM, "storm_pct"),
    (Disaster.EARTHQUAKE, "quake_pct"),
    (Disaster.FLOOD, "flood_pct"),
    (Disaster.DROUGHT, "drought_pct"),
    (Disaster.PLAGUE, "plague_pct"),
)


def share(value: int) -> int:
    return clamp_int(value, 0, SHARE_MAX)


def default_values(rules: Rules, world_type: WorldType) -> dict[str, object]:
    spec: WorldViewSpec = WORLD_VIEWS.get(world_type, WorldViewSpec())
    mechanics = mechanics_of(world_type)
    values: dict[str, object] = {
        "light": spec.light,
        "need": spec.need,
        "settle": spec.settle,
        "war": spec.war,
        "prehistory_kind": WORLD_PREHISTORY[world_type],
        "seasons": spec.seasons,
        "nights": spec.nights,
        "fire": spec.fire,
        "soil": spec.soil,
        "sea_roads": mechanics.sea_roads,
        "timber_pct": share(spec.timber_pct),
        "food_need_pct": share(spec.food_need_pct),
        "sea_pct": clamp_int(spec.sea_pct if spec.sea_pct is not None else rules.environment.coast_fishing_share, 0, PERCENT),
        "capacity_pct": share(mechanics.capacity_pct(rules) if mechanics.capacity_pct is not None else PERCENT),
        "ore_yield_pct": share(mechanics.ore_yield_pct(rules) if mechanics.ore_yield_pct is not None else PERCENT),
        "ship_pct": share(mechanics.ship_pct(rules) if mechanics.ship_pct is not None else PERCENT),
        "route_danger": clamp_int(mechanics.route_danger(rules), 0, PERCENT),
        "leak": clamp_int(mechanics.leak(rules), 0, PERCENT),
        "leak_repair": clamp_int(mechanics.leak_repair(rules), 0, PERCENT),
        "sanity_erosion": clamp_int(mechanics.sanity_erosion(rules), 0, PERCENT),
        "fertility_decay": clamp_int(mechanics.fertility_decay(rules), 0, PERCENT),
    }
    for disaster, key in DISASTER_FIELDS:
        values[key] = share(disaster_pct(rules, world_type, disaster))
    return values


def default_view(rules: Rules, world_type: WorldType) -> WorldView:
    return WorldView(**cast(dict[str, Any], default_values(rules, world_type)))


def view_from(row: WorldViewRow) -> WorldView:
    return WorldView(**{item.name: getattr(row, item.name) for item in fields(WorldView)})


async def world_views(session: AsyncSession, rules: Rules) -> dict[int, WorldView]:
    memo = memo_of(session, "world_views", VIEW_TABLES)
    if memo is not None and "all" in memo:
        known: dict[int, WorldView] = memo["all"]
        return known
    rows = {row.world_id: row for row in await session.scalars(select(WorldViewRow))}
    found = {
        world_id: view_from(rows[world_id]) if world_id in rows else default_view(rules, world_type)
        for world_id, world_type in await session.execute(select(WorldRow.id, WorldRow.world_type))
    }
    if memo is not None:
        memo["all"] = found
    return found


async def view_of(session: AsyncSession, rules: Rules, world_id: int | None) -> WorldView:
    if world_id is None:
        return WorldView()
    return (await world_views(session, rules)).get(world_id, WorldView())


def light_pct(rules: Rules, light: WorldLight) -> int:
    table = rules.world_views
    return {
        WorldLight.STAR: table.star_light_pct,
        WorldLight.LAVA_GLOW: table.lava_light_pct,
        WorldLight.MAGIC: table.magic_light_pct,
        WorldLight.INNER_SUN: table.inner_sun_light_pct,
        WorldLight.DIVINE: table.divine_light_pct,
        WorldLight.SHIP_CYCLE: table.ship_light_pct,
        WorldLight.BIOLUMINESCENCE: table.living_light_pct,
        WorldLight.MADE_LIGHT: table.made_light_pct,
        WorldLight.FADING_GOD: table.fading_light_pct,
        WorldLight.NONE: table.dark_light_pct,
    }[light]


def unfit_for_land_war(view: WorldView) -> bool:
    return view.war in LAND_UNFIT


async def seed_view(session: AsyncSession, rules: Rules, world: WorldRow, epoch: int) -> WorldViewRow:
    row = await session.get(WorldViewRow, world.id)
    if row is None:
        row = WorldViewRow(world_id=world.id, updated_epoch=epoch, locked=[], **default_values(rules, world.world_type))
        session.add(row)
        await session.flush()
    return row


async def reset_view(session: AsyncSession, rules: Rules, world: WorldRow, epoch: int) -> WorldViewRow:
    row = await seed_view(session, rules, world, epoch)
    for key, value in default_values(rules, world.world_type).items():
        if key in WORLD_VIEW_FIELDS:
            setattr(row, key, value)
    row.updated_epoch = epoch
    await session.flush()
    return row


@dataclass
class ViewTally:
    seeded: int = 0
    met: int = 0
    short: int = 0
    upkept: int = 0
    unpaid: int = 0


async def seed_views(ctx: TickContext, tally: ViewTally) -> None:
    known = set(await ctx.session.scalars(select(WorldViewRow.world_id)))
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if world.id in known or held(world.id):
            continue
        await seed_view(ctx.session, ctx.rules, world, ctx.epoch)
        tally.seeded += 1


async def drawn(ctx: TickContext, town_id: int, stocks: tuple[CommodityKind, ...], wanted: int, flow: GoodsFlow) -> int:
    ledger = goods_of(ctx.session, ctx.epoch)
    taken = 0
    for commodity in stocks:
        if taken >= wanted:
            break
        taken += await ledger.take_units(town_id, commodity, wanted - taken, flow)
    return taken


async def water_met(ctx: TickContext, town: EntityRow, atlas: RegionAtlas, people: int) -> bool:
    table = ctx.rules.world_views
    region = atlas.top_region(town.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    if ground is not None and ground.rainfall >= table.rain_water_from:
        return True
    devices = sum(row.count for row in await ctx.session.scalars(select(WaterLiftRow).where(WaterLiftRow.settlement_entity_id == town.id)))
    return devices * table.water_lift_share * PERCENT >= people


async def born_free(ctx: TickContext, town: EntityRow, need: BindingNeed) -> bool:
    folk = await people_id_of(ctx.session, town)
    nature = await biology_of(ctx.session, folk)
    if (need is BindingNeed.AIR and not nature.breathes) or (need is BindingNeed.WATER and not nature.drinks):
        return True
    biology = await ctx.session.get(PeopleBiologyRow, folk) if folk is not None else None
    if biology is None:
        return False
    if need is BindingNeed.AIR:
        return biology.air is AirNeed.NONE
    return need is BindingNeed.HEAT and biology.acclimatised in COLD_BORN


async def bound_met(ctx: TickContext, town: EntityRow, need: BindingNeed) -> bool:
    if need is BindingNeed.PLACE:
        guardian = await ctx.session.scalar(
            select(GeniusLocusRow.spirit_entity_id)
            .where(or_(GeniusLocusRow.community_entity_id == town.id, GeniusLocusRow.place_entity_id == town.id))
            .order_by(GeniusLocusRow.spirit_entity_id)
            .limit(1)
        )
        return guardian is not None
    folk = await people_id_of(ctx.session, town)
    culture = await ctx.session.get(PeopleCultureRow, folk) if folk is not None else None
    return culture is not None and culture.literacy >= ctx.rules.world_views.name_literacy_from


async def need_met(ctx: TickContext, town: EntityRow, view: WorldView, atlas: RegionAtlas) -> bool:
    if await born_free(ctx, town, view.need):
        return True
    table = ctx.rules.world_views
    people = stat(town, "population") or 0
    wanted = max(1, people * table.need_per_100 // PERCENT)
    if view.need is BindingNeed.WATER:
        return await water_met(ctx, town, atlas, people)
    if view.need in DRAWN_FROM:
        stocks, flow = DRAWN_FROM[view.need]
        return await drawn(ctx, town.id, stocks, wanted, flow) >= wanted
    if view.need is BindingNeed.BELIEF:
        return (stat(town, "piety") or 0) >= table.belief_from
    if view.need in BOUND_NEEDS:
        return await bound_met(ctx, town, view.need)
    return True


async def suffer(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow | None) -> None:
    table = ctx.rules.world_views
    if profile is not None and "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest + table.shortfall_unrest, 0, PERCENT)
    shift_stat(town, "prosperity", -table.shortfall_prosperity, ctx.rules.society.default_stat)


async def upkept(ctx: TickContext, town: EntityRow, view: WorldView, tally: ViewTally) -> bool | None:
    if view.settle not in UPKEPT:
        return None
    upkeep = max(ctx.rules.world_views.float_upkeep, ctx.rules.world_views.float_upkeep * stat_or(town, "population", 0) // PER_MILLE)
    if await take_coin(ctx.session, ctx.rules, town, upkeep):
        tally.upkept += 1
        return True
    tally.unpaid += 1
    shift_stat(town, "prosperity", -ctx.rules.world_views.upkeep_unpaid_prosperity, ctx.rules.society.default_stat)
    return False


async def keep_needs(ctx: TickContext, tally: ViewTally) -> None:
    views = await world_views(ctx.session, ctx.rules)
    atlas = await RegionAtlas.load(ctx.session)
    for town in await canon(ctx.session, [EntityType.SETTLEMENT]):
        view = views.get(town.world_id) if town.world_id is not None else None
        if view is None or held(town.id):
            continue
        sealed = await upkept(ctx, town, view, tally)
        if view.need is BindingNeed.NONE:
            continue
        met = (
            (sealed or await born_free(ctx, town, view.need)) if view.need is BindingNeed.AIR and sealed is not None else await need_met(ctx, town, view, atlas)
        )
        if met:
            tally.met += 1
            continue
        tally.short += 1
        await suffer(ctx, town, await ctx.session.get(SettlementProfileRow, town.id))
        await record(ctx, "world_views.short", roles={IncidentRole.SUBJECT: town.id}, facts={"need": view.need}, place=town.id)


async def keep_views(ctx: TickContext, tally: ViewTally) -> None:
    await seed_views(ctx, tally)
    await keep_needs(ctx, tally)
    await ctx.session.flush()
