from sqlalchemy import select

from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.departures import DepartureKind
from aerona.domain.enums.intrigue import HookDemand
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.departures.book import DepartureTally
from aerona.engine.departures.returns import tend_departed
from aerona.engine.departures.weigh import weigh_seats

LEGACY_FIXUP = "departures.legacy_step_downs"
PRESSED = "tools.mortal.leverage_pressed"


async def apply_legacy(ctx: TickContext, tally: DepartureTally) -> None:
    if not await fixup_due(ctx.session, LEGACY_FIXUP):
        return
    query = (
        select(IncidentRow.epoch, IncidentParticipantRow.node_id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .join(IncidentFactRow, IncidentFactRow.incident_id == IncidentRow.id)
        .where(
            IncidentRow.kind == PRESSED,
            IncidentParticipantRow.role == IncidentRole.TARGET,
            IncidentFactRow.key == "demand",
            IncidentFactRow.enum_value == HookDemand.STEP_DOWN.value,
        )
        .order_by(IncidentRow.id)
    )
    made = 0
    for epoch, target in await ctx.session.execute(query):
        ctx.session.add(DepartureRow(holder_node_id=target, kind=DepartureKind.RESIGNATION, conditions=[], epoch=epoch, standing=0, locked=[]))
        made += 1
    tally.marked += made
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"departures": made}))
    await ctx.session.flush()


async def tend_departures(ctx: TickContext) -> DepartureTally:
    tally = DepartureTally()
    await apply_legacy(ctx, tally)
    await tend_departed(ctx, tally)
    await weigh_seats(ctx, tally)
    return tally
