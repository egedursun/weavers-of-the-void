from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import PolityStressRow
from aerona.db.tables.sacred import ForecastModelRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import round_half_up


async def steer_forecast(ctx: TickContext, plan_id: int) -> int:
    row = await ctx.session.scalar(select(ForecastModelRow).where(ForecastModelRow.plan_id == plan_id).limit(1))
    if row is None or row.subject_entity_id is None or held(row.subject_entity_id):
        return 0
    stress = await ctx.session.get(PolityStressRow, row.subject_entity_id)
    if stress is None or "psi" in stress.locked:
        return 0
    lifted = round_half_up(ctx.rules.psychohistory.psi_shift * (PERCENT - row.disruption) / PERCENT)
    stress.psi = max(0, stress.psi - lifted)
    return lifted
