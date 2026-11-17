import logging

from sqlalchemy.exc import SQLAlchemyError

from aerona.engine.context import TickContext
from aerona.engine.gods.queries import creator_row
from aerona.engine.gods.reputation import drift_son, refresh_automatic_passions
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.queries import living_sons

logger = logging.getLogger(__name__)


@reads("table.action_records", "table.creator", "table.messages", "table.nodes", "table.sons")
@writes("table.chronicle", "table.creator", "table.incident_participants", "table.incidents", "table.sons")
async def reputation(ctx: TickContext) -> None:
    creator = await creator_row(ctx.session)
    for son in await living_sons(ctx.session):
        try:
            async with ctx.session.begin_nested():
                await drift_son(ctx, son, creator)
        except (SQLAlchemyError, ValueError) as error:
            logger.warning("Reputation drift skipped for son %s: %s", son.id, error)
            ctx.count("skipped_sons")
    await refresh_automatic_passions(ctx.session, ctx.rules, ctx.epoch)


PHASES = (Phase("reputation", reputation),)
