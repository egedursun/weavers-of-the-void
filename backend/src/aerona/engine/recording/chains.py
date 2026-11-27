from collections.abc import Iterable, Sequence

from sqlalchemy import select

from aerona.catalog.incident_kinds.sequence import AFTER_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import ProcessClock
from aerona.domain.models.moment import Moment, latest
from aerona.engine.context import TickContext

CURSORS = "record_chain_cursors"
PRINCIPALS = frozenset(
    {
        IncidentRole.SUBJECT,
        IncidentRole.ACTOR,
        IncidentRole.CO_ACTOR,
        IncidentRole.TARGET,
        IncidentRole.VICTIM,
        IncidentRole.BENEFICIARY,
        IncidentRole.OPPONENT,
        IncidentRole.RECEIVER,
        IncidentRole.HOST,
        IncidentRole.AUTHORITY,
    }
)

Cursor = tuple[int, str, float | None, int]


def happening_clock(spec: IncidentKindSpec) -> ProcessClock:
    return ProcessClock.INSTANT if spec.clock is ProcessClock.PHASE and spec.told else spec.clock


def principals(participants: Sequence[tuple[int, IncidentRole]]) -> list[int]:
    return sorted({node for node, role in participants if role in PRINCIPALS})


def anchors(ctx: TickContext) -> dict[Cursor, Moment]:
    found: dict[Cursor, Moment] = ctx.session.sync_session.info.setdefault(CURSORS, {})
    return found


def cursor(ctx: TickContext, node: int) -> Cursor:
    return (ctx.epoch, ctx.phase, ctx.environment.step, node)


def anchored(ctx: TickContext, nodes: Iterable[int]) -> Moment | None:
    known = anchors(ctx)
    return latest(*(known.get(cursor(ctx, node)) for node in nodes))


def anchor_at(ctx: TickContext, nodes: Iterable[int], moment: Moment) -> None:
    known = anchors(ctx)
    for node in nodes:
        key = cursor(ctx, node)
        before = known.get(key)
        known[key] = moment if before is None or before.before(moment) else before


async def followed(ctx: TickContext, key: str, nodes: Sequence[int]) -> Moment | None:
    before = AFTER_KINDS.get(key)
    if not before or not nodes:
        return None
    row = (
        await ctx.session.execute(
            select(IncidentRow.year, IncidentRow.season, IncidentRow.day, IncidentRow.hour)
            .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
            .where(
                IncidentRow.epoch == ctx.epoch,
                IncidentRow.kind.in_(sorted(before)),
                IncidentRow.year.is_not(None),
                IncidentParticipantRow.node_id.in_(list(nodes)),
                IncidentParticipantRow.role.in_(sorted(PRINCIPALS)),
            )
            .order_by(IncidentRow.year.desc(), IncidentRow.season.desc(), IncidentRow.day.desc(), IncidentRow.hour.desc())
            .limit(1)
        )
    ).first()
    return Moment(row[0], row[1], row[2], row[3]) if row is not None and row[0] is not None else None
