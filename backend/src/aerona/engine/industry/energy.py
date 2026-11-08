from collections import Counter

from sqlalchemy import func, or_, select

from aerona.catalog.methods import COLD, FUEL_HEAT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow
from aerona.db.tables.industry import ENERGY_COLUMNS, CommunityIndustryRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.ecology import SpeciesUse
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand, WeatherEffect
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.ecology.domestication import kept_for
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import holdings
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.rules.registry import Rules

THOUSAND = 1000
WORKING = tuple(job for job in Job if job is not Job.IDLE)


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


def workers_of(book: EconomyBook, community: EntityRow) -> int:
    hands = book.hands(community.id, *WORKING)
    return hands if hands is not None else headcount(community)


async def mages_of(ctx: TickContext, community_id: int) -> int:
    mortals = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        or_(EntityRow.affiliated_entity_id == community_id, EntityRow.location_id == community_id),
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
    draught = await kept_for(ctx, community.id, SpeciesUse.LABOUR)
    muscle = (
        workers_of(book, community) * table.muscle_per_100_workers / PERCENT
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
    supply = {
        EnergyKind.MUSCLE: round_half_up(muscle),
        EnergyKind.WATER: water,
        EnergyKind.WIND: round_half_up(wind),
        EnergyKind.HEAT: max(0, burnable - need),
        EnergyKind.MAGIC: round_half_up(magic),
        EnergyKind.DIVINE: round_half_up(divine),
    }
    return supply, need


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
