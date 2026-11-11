from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.urban import FINE_HOMES, HOUSING_ORDER, NEEDS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.urban import DistrictServiceRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.enums.society import Commodity
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.society import supply_index
from aerona.engine.primitives.stats import stat_or
from aerona.engine.settlement.book import Town, town_of
from aerona.engine.settlement.life import add_district, housing_of
from aerona.engine.urban.coverage import people_of_districts

LAND_STEP = 20


@dataclass
class HousingTally:
    risen: int = 0
    fallen: int = 0
    slums: int = 0
    mobs: int = 0


async def needs_met(ctx: TickContext, district: DistrictRow) -> float:
    rows = {
        row.service: row.coverage
        for row in await ctx.session.scalars(
            select(DistrictServiceRow).where(DistrictServiceRow.district_id == district.id, DistrictServiceRow.service.in_(NEEDS))
        )
    }
    return sum(rows.get(service, 0) for service in NEEDS) / len(NEEDS)


def step_home(district: DistrictRow, up: bool) -> bool:
    index = HOUSING_ORDER.index(district.housing)
    ceiling = min(len(HOUSING_ORDER) - 1, district.land_value // LAND_STEP)
    after = min(ceiling, index + 1) if up else max(0, index - 1)
    if after == index or "housing" in district.locked:
        return False
    district.housing = HOUSING_ORDER[after]
    return True


async def evolve_district(ctx: TickContext, town: Town, district: DistrictRow, goods: int, tally: HousingTally) -> None:
    table = ctx.rules.housing_evolution
    needs = await needs_met(ctx, district)
    rng = ctx.rng(f"homes.{district.id}")
    if needs >= table.rise_coverage and goods >= table.goods_needed and rng.chance(table.step_pct) and step_home(district, up=True):
        tally.risen += 1
    elif needs < table.fall_coverage and rng.chance(table.step_pct) and step_home(district, up=False):
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
        await note(ctx, f"The homeless of {town.entity.name} gathered as a mob.", key="settlement.homeless_mob", ids=[town.entity.id])


async def cramped_rich(ctx: TickContext, town: Town) -> bool:
    table = ctx.rules.housing_evolution
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    if society is None or not town.districts:
        return False
    fine = sum(1 for district in town.districts if district.housing in FINE_HOMES) / len(town.districts)
    rich = society.share_noble + society.share_merchant
    return fine * PERCENT < rich * table.fine_homes


async def house_town(ctx: TickContext, settlement: EntityRow, knowledge: KnowledgeMap, tally: HousingTally) -> None:
    table = ctx.rules.homelessness
    town = await town_of(ctx, settlement, knowledge)
    if not town.districts:
        return
    goods = await supply_index(ctx.session, settlement.id, Commodity.GOODS) or 0
    for district in town.districts:
        await evolve_district(ctx, town, district, goods, tally)
    population = stat_or(settlement, "population", 0)
    people = people_of_districts(population, town.districts)
    homeless = max(0, population - housing_of(ctx.rules, town)) + priced_out(ctx, town, people)
    profile = town.profile
    if "homeless" not in profile.locked:
        profile.homeless = min(population, homeless)
    share = profile.homeless / max(1, population)
    if "unrest" not in profile.locked:
        cramped = ctx.rules.housing_evolution.cramped_unrest if await cramped_rich(ctx, town) else 0
        profile.unrest = clamp_int(round_half_up(profile.unrest + share * table.unrest + cramped), 0, PERCENT)
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
    people = people_of_districts(stat_or(town.entity, "population", 0), town.districts)
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
