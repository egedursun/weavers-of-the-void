from collections import Counter

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.industry import FOOD_JOBS
from aerona.catalog.methods import COLD, FUEL_HEAT
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow
from aerona.db.tables.industry import ENERGY_COLUMNS, CommunityIndustryRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.ecology import AnimalRole
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand, TerrainKind, WeatherEffect
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.engine.context import TickContext
from aerona.engine.ecology.domestication import kept_for
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import holdings
from aerona.engine.primitives.folk import HOMELAND_BONDS, present_among, towns_of_people
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import active_bonds, canon
from aerona.engine.primitives.stats import headcount
from aerona.rules.registry import Rules

THOUSAND = 1000
WORKING = tuple(job for job in Job if job is not Job.IDLE)
POOLED = tuple(job for job in WORKING if job not in FOOD_JOBS)


async def leys_by_region(ctx: TickContext) -> Counter[int]:
    counts: Counter[int] = Counter()
    for line in await ctx.session.scalars(select(LeyLineRow).where(LeyLineRow.severed.is_(False))):
        counts[line.region_a_id] += 1
        counts[line.region_b_id] += 1
    return counts


def river_energy(rules: Rules, river: RiverClass) -> int:
    table = rules.energy
    return {RiverClass.NONE: 0, RiverClass.STREAM: table.water_stream, RiverClass.RIVER: table.water_river, RiverClass.GREAT_RIVER: table.water_great_river}[
        river
    ]


def survival_heat(rules: Rules, population: int, band: TemperatureBand | None) -> int:
    if band not in COLD:
        return 0
    need = population * rules.energy.cold_heat_per_1000 / THOUSAND
    if band is TemperatureBand.FROZEN:
        need *= rules.energy.frozen_heat_pct / PERCENT
    return round_half_up(need)


def clergy_of(book: EconomyBook, community: EntityRow) -> int:
    hands = book.hands(community.id, Job.CLERGY)
    if hands is not None:
        return hands
    row = book.societies.get(community.id)
    share = row.share(SocialClass.PRIEST) if row is not None else 0.0
    return round_half_up(headcount(community) * share / PERCENT)


def pooled_workers(book: EconomyBook, community: EntityRow) -> int:
    hands = book.hands(community.id, *POOLED)
    return hands if hands is not None else headcount(community)


def own_hands(rules: Rules, workers: int) -> int:
    return round_half_up(workers * rules.energy.muscle_per_100_workers / PERCENT)


def worked_by_hand(book: EconomyBook, rules: Rules, community_id: int, kind: EnergyKind, *, need: int, workers: int) -> float:
    if need <= 0:
        return 1.0
    own = own_hands(rules, workers) if kind is EnergyKind.MUSCLE else 0
    rest = max(0, need - own)
    return min(1.0, (min(own, need) + (draw(book, community_id, kind, rest) if rest else 0)) / need)


async def mages_of(ctx: TickContext, community_id: int) -> int:
    mortals = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        or_(EntityRow.affiliated_entity_id == community_id, await present_among(ctx.session, [community_id])),
    )
    found = await ctx.session.scalar(
        select(func.count(SkillRow.holder_node_id)).where(
            SkillRow.holder_node_id.in_(mortals),
            SkillRow.skill == SkillKind.SPELLCRAFT,
            SkillRow.subject_node_id.is_(None),
            SkillRow.level >= ctx.rules.energy.mage_skill_at,
        )
    )
    return int(found or 0)


def weather_wind(ctx: TickContext, book: EconomyBook, community: EntityRow) -> int:
    ground = book.ground.region_of(community.id)
    if ground is None:
        return 0
    season = book.ground.growing_season(ground.world_id)
    return book.ground.weather(ctx.environment.world_seed, ctx.epoch, ground, season, f"wind.{community.id}").effect(WeatherEffect.WIND)


async def supply_of(ctx: TickContext, book: EconomyBook, community: EntityRow, leys: Counter[int]) -> tuple[dict[EnergyKind, int], int]:
    table = ctx.rules.energy
    region = book.ground.region_of(community.id)
    held = await holdings(ctx.session, community.id)
    beasts = held.get(CommodityKind.LIVESTOCK, 0) + held.get(CommodityKind.MOUNTS, 0)
    draught = await kept_for(ctx, community.id, AnimalRole.DRAFT)
    muscle = (
        pooled_workers(book, community) * table.muscle_per_100_workers / PERCENT
        + beasts * table.muscle_per_10_beasts / 10
        + draught * ctx.rules.husbandry.muscle_per_10_draught / 10
    )
    water = river_energy(ctx.rules, region.river_class) if region is not None else 0
    wind: float = table.wind_base
    if region is not None:
        wind += (table.wind_coast if region.coast_kind is not CoastKind.NONE else 0) + region.roughness * table.wind_heights_pct / PERCENT
    burnable = sum(held.get(kind, 0) * int(getattr(table, key)) for kind, key in FUEL_HEAT.items())
    need = survival_heat(ctx.rules, headcount(community), region.temperature_band if region is not None else None)
    magic = (region.magic_density * table.magic_density_pct / PERCENT + leys.get(region.entity_id, 0) * table.magic_per_ley) if region is not None else 0
    magic += await mages_of(ctx, community.id) * table.magic_per_mage
    wind *= 1 + weather_wind(ctx, book, community) * table.weather_wind_pct / PERCENT / PERCENT
    shrine = book.workshop(community.id, WorkshopKind.SHRINE_WORKSHOP)
    divine = (shrine.level if shrine is not None else 0) * table.divine_per_shrine + clergy_of(book, community) * table.divine_per_100_clergy / PERCENT
    plants = await power_levels(ctx, community, POWER_PLANTS - DAMS if book.lacks(community.id, Technique.ELECTRICITY) else POWER_PLANTS)
    collectors = await world_collectors(ctx, community)
    world = await ctx.session.get(WorldRow, community.world_id) if community.world_id is not None else None
    electric, stored = heated_by_power(ctx.rules, max(0, need - burnable), round_half_up(plants * table.electric_per_level))
    supply = total(
        EnergyKind,
        {
            EnergyKind.MUSCLE: round_half_up(muscle),
            EnergyKind.WATER: water,
            EnergyKind.WIND: round_half_up(wind),
            EnergyKind.HEAT: max(0, burnable - need),
            EnergyKind.MAGIC: round_half_up(magic),
            EnergyKind.DIVINE: round_half_up(divine),
            EnergyKind.FUEL: held.get(CommodityKind.FUEL, 0) * table.fuel_engine,
            EnergyKind.ELECTRIC: electric,
            EnergyKind.STORED: stored,
            EnergyKind.SOLAR: table.solar_base if region is not None and region.dominant_terrain is not TerrainKind.UNDERGROUND else 0,
            EnergyKind.GEOTHERMAL: table.geothermal_volcanic if region is not None and region.dominant_terrain is TerrainKind.VOLCANIC else 0,
            EnergyKind.TIDAL: table.tidal_coast if region is not None and region.coast_kind is not CoastKind.NONE else 0,
            EnergyKind.FISSION: held.get(CommodityKind.ORE, 0) * table.fission_per_10_ore // 10,
            EnergyKind.FUSION: table.fusion_base if plants > 0 else 0,
            EnergyKind.STELLAR: collectors * table.stellar_per_collector,
            EnergyKind.SOURCE: round_half_up(region.magic_density * table.source_density_pct / PERCENT) if region is not None else 0,
            EnergyKind.FEED: (beasts + draught) * table.feed_per_10_beasts // 10,
            EnergyKind.BELIEF: round_half_up(clergy_of(book, community) * table.belief_per_100_clergy / PERCENT),
            EnergyKind.VOID: (world.leakage if world is not None else 0) * table.void_leak_pct // PERCENT,
        },
    )
    return dict(supply), need


POWER_PLANTS = frozenset({StructureKind.POWER_PLANT, StructureKind.DAM, StructureKind.STAR_COLLECTOR})
POWER_HEAT = (EnergyKind.ELECTRIC, EnergyKind.STORED)
DAMS = frozenset({StructureKind.DAM})


def power_for_heat(rules: Rules, heat: int) -> int:
    rate = rules.energy.power_heat_pct
    return -(-heat * PERCENT // rate) if heat > 0 and rate > 0 else 0


def heated_by_power(rules: Rules, unwarmed: int, made: int) -> tuple[int, int]:
    wanted = power_for_heat(rules, unwarmed)
    stored = made * rules.energy.stored_pct // PERCENT
    from_electric = min(made, wanted)
    return made - from_electric, stored - min(stored, wanted - from_electric)


def warm_from_power(rules: Rules, book: EconomyBook, community_id: int, heat: int) -> int:
    row = book.industry.get(community_id)
    if row is None:
        return 0
    given = 0
    for kind in POWER_HEAT:
        units = min(available(row, kind), power_for_heat(rules, heat - given))
        if units <= 0:
            continue
        row.spent = {**row.spent, kind.value: row.spent.get(kind.value, 0) + units}
        given = min(heat, given + units * rules.energy.power_heat_pct // PERCENT)
    return given


@memoized(StructureProfileRow)
async def levels_by_host(session: AsyncSession, kinds: frozenset[StructureKind]) -> dict[int, int]:
    statement = select(StructureProfileRow.host_entity_id, StructureProfileRow.level).where(
        StructureProfileRow.kind.in_(list(kinds)), StructureProfileRow.construction_state == ConstructionState.COMPLETE
    )
    found: dict[int, int] = {}
    for host, level in await session.execute(statement):
        if host is not None:
            found[host] = found.get(host, 0) + level
    return found


async def people_towns(session: AsyncSession, people_id: int) -> list[int]:
    ruled = [bond.target_node_id for bond in await active_bonds(session, [BondKind.RULES], sources=[people_id])]
    return sorted({*await towns_of_people(session, people_id), *ruled})


@memoized(EntityRow, BondRow)
async def peoples_drawing(session: AsyncSession) -> dict[int, tuple[tuple[int, int], ...]]:
    peoples = [people.id for people in await canon(session, [EntityType.PEOPLE])]
    homes: dict[int, set[int]] = {people: {people} for people in peoples}
    ruled: dict[int, set[int]] = {people: set() for people in peoples}
    for bond in await active_bonds(session, HOMELAND_BONDS, sources=peoples):
        if bond.kind is BondKind.RULES:
            ruled[bond.source_node_id].add(bond.target_node_id)
        if bond.role is BondRole.HOMELAND:
            homes[bond.source_node_id].add(bond.target_node_id)
    for bond in await active_bonds(session, [BondKind.DESCENDS_FROM], targets=peoples):
        homes[bond.target_node_id].add(bond.source_node_id)
    places = sorted(set().union(*homes.values())) if homes else []
    settled = set(
        await session.scalars(
            select(EntityRow.id).where(EntityRow.id.in_(places), EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        )
    )
    drawing: dict[int, list[tuple[int, int]]] = {}
    for people in peoples:
        towns = sorted((homes[people] & settled) | ruled[people])
        for town in towns:
            drawing.setdefault(town, []).append((people, len(towns)))
    return {town: tuple(found) for town, found in drawing.items()}


async def drawers_at(session: AsyncSession, town_id: int) -> dict[int, float]:
    weights = {town_id: 1.0}
    for people_id, towns in (await peoples_drawing(session)).get(town_id, ()):
        weights[people_id] = 1 / towns
    return weights


async def drawing_folk(session: AsyncSession, town_id: int) -> dict[int, float]:
    found: dict[int, float] = {}
    for drawer, weight in (await drawers_at(session, town_id)).items():
        entity = await session.get(EntityRow, drawer)
        found[drawer] = headcount(entity) * weight if entity is not None else 0.0
    return found


async def power_levels(ctx: TickContext, community: EntityRow, kinds: frozenset[StructureKind]) -> float:
    levels = await levels_by_host(ctx.session, kinds)
    hosts = [*await people_towns(ctx.session, community.id), community.id] if community.entity_type is EntityType.PEOPLE else [community.id]
    share = 0.0
    for host in hosts:
        if not levels.get(host):
            continue
        folk = await drawing_folk(ctx.session, host)
        whole = sum(folk.values())
        share += levels[host] * (folk.get(community.id, 0.0) / whole if whole > 0 else float(community.id == host))
    return share


@memoized(StructureProfileRow, EntityRow)
async def collectors_by_world(session: AsyncSession) -> dict[int, int]:
    statement = (
        select(EntityRow.world_id, func.count())
        .select_from(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.host_entity_id)
        .where(StructureProfileRow.kind == StructureKind.STAR_COLLECTOR, EntityRow.world_id.is_not(None))
        .group_by(EntityRow.world_id)
    )
    return {world_id: int(count) for world_id, count in await session.execute(statement)}


async def world_collectors(ctx: TickContext, community: EntityRow) -> int:
    if community.world_id is None:
        return 0
    return (await collectors_by_world(ctx.session)).get(community.world_id, 0)


def industry_row(ctx: TickContext, book: EconomyBook, community_id: int) -> CommunityIndustryRow:
    row = book.industry.get(community_id)
    if row is None:
        row = CommunityIndustryRow(
            community_node_id=community_id,
            spent={},
            short={},
            epoch=ctx.epoch,
            locked=[],
            meal_quality=50,
            drink=0,
            market_access=100,
            black_market=0,
            light=0,
            heat_need=0,
            tools_worn=0,
            spoiled=0,
            preserved=0,
            **dict.fromkeys(ENERGY_COLUMNS, 0),
        )
        ctx.session.add(row)
        book.industry[community_id] = row
    return row


async def gauge(ctx: TickContext, book: EconomyBook, community: EntityRow, leys: Counter[int]) -> CommunityIndustryRow:
    row = industry_row(ctx, book, community.id)
    supply, need = await supply_of(ctx, book, community, leys)
    for kind, amount in supply.items():
        if kind.value not in row.locked:
            setattr(row, kind.value, amount)
    if "heat_need" not in row.locked:
        row.heat_need = need
    row.spent, row.short, row.epoch = {}, {}, ctx.epoch
    if "tools_worn" not in row.locked:
        row.tools_worn = 0
    if "spoiled" not in row.locked:
        row.spoiled = 0
    if "preserved" not in row.locked:
        row.preserved = 0
    return row


def available(row: CommunityIndustryRow | None, kind: EnergyKind) -> int:
    if row is None:
        return 0
    return max(0, int(getattr(row, kind.value)) - row.spent.get(kind.value, 0))


def draw(book: EconomyBook, community_id: int, kind: EnergyKind, need: int) -> int:
    row = book.industry.get(community_id)
    if need <= 0:
        return 0
    if row is None:
        return need
    granted = min(need, available(row, kind))
    row.spent = {**row.spent, kind.value: row.spent.get(kind.value, 0) + granted}
    if granted < need and kind is EnergyKind.HEAT and magic_heat_pct(book) > 0:
        rate = magic_heat_pct(book)
        spells = min(available(row, EnergyKind.MAGIC), -(-(need - granted) * PERCENT // rate))
        row.spent = {**row.spent, EnergyKind.MAGIC.value: row.spent.get(EnergyKind.MAGIC.value, 0) + spells}
        granted = min(need, granted + spells * rate // PERCENT)
    if granted < need:
        row.short = {**row.short, kind.value: row.short.get(kind.value, 0) + need - granted}
    return granted


def magic_heat_pct(book: EconomyBook) -> int:
    return book.magic_heat_pct


def scale_by_energy(book: EconomyBook, community_id: int, kind: EnergyKind, need: int) -> float:
    if need <= 0:
        return 1.0
    return draw(book, community_id, kind, need) / need


def unmet_pct(row: CommunityIndustryRow, kind: EnergyKind) -> int:
    short = row.short.get(kind.value, 0)
    wanted = row.spent.get(kind.value, 0) + short
    return round_half_up(short * PERCENT / wanted) if wanted else 0


def taste_meal(ctx: TickContext, book: EconomyBook, community: EntityRow, quality: int) -> None:
    row = industry_row(ctx, book, community.id)
    if "meal_quality" not in row.locked:
        row.meal_quality = max(0, min(PERCENT, quality))
