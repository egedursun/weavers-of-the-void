from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.urban import AMENITIES, NUISANCE_DISTRICTS, NUISANCES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.engine.urban.coverage import reach_of, services_in

NEUTRAL = PERCENT // 2


@dataclass
class DesirabilityTally:
    assessed: int = 0


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
    structures = await services_in(ctx.session, settlement.id)
    spirits = await restless(ctx, settlement.id)
    common = profile.prestige * table.prestige_pct / PERCENT - profile.crime * table.crime_pct / PERCENT - spirits * table.haunting
    for district in districts:
        score = NEUTRAL + common
        for _, structure in structures:
            weight = 1.0 if structure.district_id == district.id else reach
            if structure.kind in AMENITIES:
                score += table.amenity * weight
            elif structure.kind in NUISANCES:
                score -= table.nuisance * weight
        for other in districts:
            if other.kind in NUISANCE_DISTRICTS:
                score -= table.nuisance * (1.0 if other.id == district.id else reach)
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
