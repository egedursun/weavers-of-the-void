from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import AMENITIES, NUISANCE_DISTRICTS, NUISANCES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import DistrictKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.engine.urban.coverage import reach_of, services_in
from aerona.engine.urban.layout import falloff
from aerona.engine.urban.planning import plan_town

NEUTRAL = PERCENT // 2


@dataclass
class DesirabilityTally:
    assessed: int = 0


async def land_value_of(session: AsyncSession, settlement_id: int) -> int:
    values = list(await session.scalars(select(DistrictRow.land_value).where(DistrictRow.settlement_entity_id == settlement_id)))
    return round_half_up(sum(values) / len(values)) if values else 0


async def fouled(ctx: TickContext, settlement: EntityRow) -> int:
    region = (await RegionAtlas.load(ctx.session)).top_region(settlement.id)
    row = await ctx.session.get(RegionPollutionRow, region) if region is not None else None
    return (row.air + row.water) // 2 if row is not None else 0


async def artworks(ctx: TickContext, settlement_id: int) -> int:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.entity_type == EntityType.ARTWORK, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == settlement_id)
    )
    return int(found or 0)


async def restless(ctx: TickContext, settlement_id: int) -> int:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == settlement_id)
    )
    return int(found or 0)


async def assess_town(ctx: TickContext, settlement: EntityRow, tally: DesirabilityTally) -> None:
    table = ctx.rules.desirability
    profile = await ctx.session.get(SettlementProfileRow, settlement.id)
    districts = list(await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement.id).order_by(DistrictRow.id)))
    if profile is None or not districts:
        return
    reach = reach_of(ctx.rules, profile.morphology)
    layout = await plan_town(ctx, settlement.id)
    structures = await services_in(ctx.session, settlement.id)
    spirits = await restless(ctx, settlement.id)
    common = (
        profile.prestige * table.prestige_pct / PERCENT
        - profile.crime * table.crime_pct / PERCENT
        - spirits * table.haunting
        - await fouled(ctx, settlement) * table.pollution_pct / PERCENT
        + await artworks(ctx, settlement.id) * table.artwork
    )
    for district in districts:
        score = NEUTRAL + common
        for _, structure in structures:
            weight = falloff(reach, layout.apart(structure.district_id, district.id)) if structure.district_id is not None else reach
            if structure.kind in AMENITIES:
                score += table.amenity * weight
            elif structure.kind in NUISANCES:
                score -= table.nuisance * weight
        for other in districts:
            if other.kind in NUISANCE_DISTRICTS:
                score -= table.nuisance * falloff(reach, layout.apart(other.id, district.id))
            if other.kind is DistrictKind.GARDENS:
                score += ctx.rules.city_plan.garden_amenity * other.level * falloff(reach, layout.apart(other.id, district.id))
        if "desirability" not in district.locked:
            district.desirability = clamp_int(round_half_up(score), 0, PERCENT)
        if "land_value" not in district.locked:
            gap = district.desirability - district.land_value
            district.land_value = clamp_int(district.land_value + max(-table.drift, min(table.drift, gap)), 0, PERCENT)
        tally.assessed += 1
    await ctx.session.flush()


async def assess_towns(ctx: TickContext, tally: DesirabilityTally) -> None:
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if not held(settlement.id) and stat_or(settlement, "population", 0) > 0:
            await assess_town(ctx, settlement, tally)
