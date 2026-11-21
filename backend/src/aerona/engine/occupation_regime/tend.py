from sqlalchemy import select

from aerona.db.tables.occupation_regimes import OccupationRegimeRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.occupation_regime.book import RegimeTally, occupation_of
from aerona.engine.occupation_regime.collaborators import recruit, tend_collaborators
from aerona.engine.occupation_regime.liberation import liberate
from aerona.engine.occupation_regime.measures import tend_measures
from aerona.engine.occupation_regime.rule import apply_legacy, ensure_regimes, govern


async def tend_regimes(ctx: TickContext) -> RegimeTally:
    tally = RegimeTally()
    await apply_legacy(ctx, tally)
    await ensure_regimes(ctx, tally)
    for regime in list(
        await ctx.session.scalars(select(OccupationRegimeRow).where(OccupationRegimeRow.ended_epoch.is_(None)).order_by(OccupationRegimeRow.id))
    ):
        if held(regime.region_entity_id) or held(regime.occupier_entity_id):
            continue
        occupation = await occupation_of(ctx, regime)
        if occupation is None:
            await liberate(ctx, regime, tally)
            continue
        await tend_collaborators(ctx, regime, occupation.resistance, tally)
        await recruit(ctx, regime, occupation.control, tally)
        await tend_measures(ctx, regime, occupation.resistance, tally)
        await govern(ctx, regime, tally)
    return tally
