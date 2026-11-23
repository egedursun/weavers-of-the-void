from collections.abc import Mapping

from sqlalchemy import select

from aerona.core.total import partial
from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.settlement import DistrictHarm
from aerona.engine.context import TickContext

CAUSES: Mapping[DistrictHarm, RebuildCause] = partial(
    DistrictHarm,
    {
        DistrictHarm.FLOOD: RebuildCause.FLOOD,
        DistrictHarm.EARTHQUAKE: RebuildCause.QUAKE,
        DistrictHarm.STORM: RebuildCause.STORM,
        DistrictHarm.SACK: RebuildCause.SACK,
    },
    without=(DistrictHarm.DROUGHT,),
)


async def mark_ruin(ctx: TickContext, town: EntityRow, cause: RebuildCause) -> ReconstructionRow | None:
    if held(town.id):
        return None
    open_row = await ctx.session.scalar(
        select(ReconstructionRow).where(ReconstructionRow.settlement_entity_id == town.id, ReconstructionRow.finished_epoch.is_(None)).limit(1)
    )
    if open_row is not None:
        return open_row
    row = ReconstructionRow(settlement_entity_id=town.id, cause=cause, started_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def harm_ruin(ctx: TickContext, town: EntityRow, harm: DistrictHarm) -> ReconstructionRow | None:
    cause = CAUSES.get(harm)
    return await mark_ruin(ctx, town, cause) if cause is not None else None
