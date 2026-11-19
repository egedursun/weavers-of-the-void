from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fortune import CohortMishapRateRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount, set_stats

PER_MIL = 1000


async def keep_cohort_mishaps(ctx: TickContext) -> int:
    table = ctx.rules.everyday_mishaps
    kept = 0
    towns = select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for town in list(await ctx.session.scalars(towns)):
        if held(town.id) or await ctx.session.get(CohortMishapRateRow, (town.id, ctx.epoch)) is not None:
            continue
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        crowding = profile.fire_risk if profile is not None else PERCENT // 5
        cold = table.winter_pct if ctx.epoch % 4 == 3 else PERCENT
        rate = table.per_epoch(table.cohort_rate_per_mil) * (PERCENT + crowding) // PERCENT * cold // PERCENT
        people = headcount(town)
        dead = round_half_up(people * rate / PER_MIL)
        injured = dead * 4
        if dead and people > dead:
            with flowing(FlowCategory.DEATH):
                set_stats(town, population=people - dead)
        ctx.session.add(
            CohortMishapRateRow(
                community_entity_id=town.id,
                epoch=ctx.epoch,
                injured=injured,
                dead=dead,
                rate_pct=rate * PERCENT // PER_MIL,
                by_exposure={"dwelling": crowding, "season": cold},
            )
        )
        kept += 1
    return kept
