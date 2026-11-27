from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.moment import Moment
from aerona.engine.phases.ruins import abandon
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from tests.engine.core.factories import CoreWorld, settlement


async def test_a_town_is_never_told_abandoned_before_its_last_record(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "ruin")
    town = await settlement(session, "Lastlight", world, world.regions[0])
    start = epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    late = start + ctx.rules.time.years_per_epoch - 1
    await record(ctx, "settlement.rebuilt", roles={IncidentRole.SUBJECT: town.id}, facts={"cause": RebuildCause.FLOOD}, place=town.id, at_moment=Moment(start))
    await record(ctx, "settlement.rebuilt", roles={IncidentRole.SUBJECT: town.id}, facts={"cause": RebuildCause.PLAGUE}, place=town.id, at_moment=Moment(late))
    await abandon(ctx, town)
    ended = await session.scalar(select(IncidentRow.year).where(IncidentRow.kind == "ruins.abandoned"))
    assert ended is not None and ended >= late
