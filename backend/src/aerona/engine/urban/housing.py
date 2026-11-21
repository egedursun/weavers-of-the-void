from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import FINE_HOMES, HOUSING_GATES, HOUSING_ORDER, NEEDS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import DistrictServiceRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.enums.urban import HousingLevel
from aerona.engine.city_rules.effects import above_cap, housing_cap
from aerona.engine.context import TickContext
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.society import supply_index
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.settlement.book import Town, town_of
from aerona.engine.settlement.life import add_district, housing_of
from aerona.engine.urban.coverage import people_of_districts

TRADITIONAL_HOMES = frozenset(level for level in HOUSING_ORDER if level not in HOUSING_GATES)


@dataclass
class HousingTally:
    risen: int = 0
    fallen: int = 0
    slums: int = 0
    mobs: int = 0
    sheltered: int = 0


async def needs_met(ctx: TickContext, district: DistrictRow) -> float:
    return await needs_met_in(ctx.session, district.id)


@memoized(DistrictServiceRow)
async def needs_met_in(session: AsyncSession, district_id: int) -> float:
    rows = {
        row.service: row.coverage
        for row in await session.scalars(select(DistrictServiceRow).where(DistrictServiceRow.district_id == district_id, DistrictServiceRow.service.in_(NEEDS)))
    }
    return sum(rows.get(service, 0) for service in NEEDS) / len(NEEDS)


def homes_open(knowledge: KnowledgeMap, holder_id: int) -> frozenset[HousingLevel]:
    return frozenset(level for level in HOUSING_ORDER if (gate := HOUSING_GATES.get(level)) is None or knowledge.level(holder_id, gate[0]) >= gate[1])


def step_home(district: DistrictRow, up: bool, open_homes: frozenset[HousingLevel] = TRADITIONAL_HOMES) -> bool:
    ladder = [level for level in HOUSING_ORDER if level in open_homes or level is district.housing]
    index = ladder.index(district.housing)
    ceiling = min(len(ladder) - 1, district.land_value * len(ladder) // PERCENT)
    after = min(ceiling, index + 1) if up else max(0, index - 1)
    if after == index or "housing" in district.locked:
        return False
    district.housing = ladder[after]
    return True


async def evolve_district(ctx: TickContext, town: Town, district: DistrictRow, goods: int, tally: HousingTally, *, open_homes: frozenset[HousingLevel]) -> None:
    table = ctx.rules.housing_evolution
    needs = await needs_met(ctx, district)
    rng = ctx.rng(f"homes.{district.id}")
    capped = above_cap(district.housing, await housing_cap(ctx.session, district))
    rising = needs >= table.rise_coverage and goods >= table.goods_needed and not capped
    if rising and rng.chance(table.step_pct) and step_home(district, up=True, open_homes=open_homes):
        tally.risen += 1
    elif needs < table.fall_coverage and rng.chance(table.step_pct) and step_home(district, up=False, open_homes=open_homes):
        tally.fallen += 1


def priced_out(ctx: TickContext, town: Town, people: dict[int, float]) -> int:
    table = ctx.rules.desirability
    return round_half_up(
        sum(
            people[district.id] * table.gentrify_homeless / PERCENT
            for district in town.districts
            if district.land_value >= table.gentrify_at and district.housing in FINE_HOMES
        )
    )


async def grow_slums(ctx: TickContext, town: Town, share: float, tally: HousingTally) -> None:
    table = ctx.rules.homelessness
    if share * PERCENT >= table.slum_share:
        await add_district(ctx, town, DistrictKind.SLUMS, material=BuildMaterial.TIMBER)
        tally.slums += 1
    if share * PERCENT >= table.mob_share:
        tally.mobs += 1
        if "public_order" not in town.profile.locked:
            town.profile.public_order = clamp_int(town.profile.public_order - table.unrest, 0, PERCENT)
        await record(
            ctx,
            "settlement.homeless_mob",
            roles={IncidentRole.PLACE: town.entity.id},
            facts={"homeless_share": round_half_up(share * PERCENT), "order_loss": table.unrest},
            place=town.entity.id,
        )


async def cramped_rich(ctx: TickContext, town: Town) -> bool:
    table = ctx.rules.housing_evolution
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    if society is None or not town.districts:
        return False
    fine = sum(1 for district in town.districts if district.housing in FINE_HOMES) / len(town.districts)
    rich = society.share_noble + society.share_merchant
    return fine * PERCENT < rich * table.fine_homes


async def almshouse_levels(ctx: TickContext, settlement_id: int) -> int:
    levels = await ctx.session.scalars(
        select(StructureProfileRow.level).where(
            StructureProfileRow.kind == StructureKind.ALMSHOUSE,
            StructureProfileRow.host_entity_id == settlement_id,
            StructureProfileRow.construction_state == ConstructionState.COMPLETE,
        )
    )
    return int(sum(levels))


async def house_town(ctx: TickContext, settlement: EntityRow, knowledge: KnowledgeMap, tally: HousingTally) -> None:
    table = ctx.rules.homelessness
    town = await town_of(ctx, settlement, knowledge)
    if not town.districts:
        return
    goods = await supply_index(ctx.session, settlement.id, Commodity.GOODS) or 0
    open_homes = homes_open(knowledge, settlement.id)
    for district in town.districts:
        await evolve_district(ctx, town, district, goods, tally, open_homes=open_homes)
    population = stat_or(settlement, "population", 0)
    people = people_of_districts(ctx.rules, population, town.districts)
    almshouses = await almshouse_levels(ctx, settlement.id)
    sheltered = almshouses * ctx.rules.city_plan.almshouse_shelter
    unhoused = max(0, population - housing_of(ctx.rules, town)) + await lagged(ctx, BalanceLoop.GENTRIFICATION, town.entity.id, priced_out(ctx, town, people))
    homeless = max(0, unhoused - sheltered)
    tally.sheltered += min(sheltered, unhoused)
    profile = town.profile
    if "homeless" not in profile.locked:
        profile.homeless = min(population, homeless)
    share = profile.homeless / max(1, population)
    if "unrest" not in profile.locked:
        cramped = ctx.rules.housing_evolution.cramped_unrest if await cramped_rich(ctx, town) else 0
        calm = almshouses * ctx.rules.city_plan.almshouse_calm
        profile.unrest = clamp_int(round_half_up(profile.unrest + share * table.unrest + cramped - calm), 0, PERCENT)
    await grow_slums(ctx, town, share, tally)
    await ctx.session.flush()


async def house_towns(ctx: TickContext, tally: HousingTally) -> None:
    knowledge = await KnowledgeMap.load(ctx.session)
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if not held(settlement.id) and stat_or(settlement, "population", 0) > 0:
            await house_town(ctx, settlement, knowledge, tally)


async def clear_slums(ctx: TickContext, town: Town) -> int:
    slums = [district for district in town.districts if district.kind is DistrictKind.SLUMS]
    if not slums:
        return 0
    people = people_of_districts(ctx.rules, stat_or(town.entity, "population", 0), town.districts)
    displaced = round_half_up(sum(people[district.id] for district in slums))
    for district in slums:
        await ctx.session.delete(district)
        town.districts.remove(district)
    await add_district(ctx, town, DistrictKind.CRAFT_QUARTER, material=BuildMaterial.STONE)
    if "homeless" not in town.profile.locked:
        town.profile.homeless += displaced
    if "unrest" not in town.profile.locked:
        town.profile.unrest = clamp_int(town.profile.unrest + ctx.rules.homelessness.clearance_unrest, 0, PERCENT)
    await ctx.session.flush()
    return displaced
