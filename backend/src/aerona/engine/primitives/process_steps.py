from collections.abc import Iterable, Sequence

from sqlalchemy import func, select

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.records import IncidentStepRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import ProcessClock
from aerona.domain.models.moment import Moment, latest
from aerona.engine.context import TickContext
from aerona.engine.recording.moments import incident_moment, moment_for
from aerona.engine.recording.record import StepDraft, checked_steps, write_steps
from aerona.engine.recording.scope import recording


async def open_process(ctx: TickContext, key: str, clock: ProcessClock, participants: Sequence[tuple[int, IncidentRole]], *, place: int | None = None) -> int:
    async with recording(ctx, key, clock=clock, participants=[node for node, _ in participants[:1]], place_id=place) as scope:
        incident = scope.incident_id
    if incident is None:
        raise ValueError(f"The process {key} got no record.")
    ctx.session.add_all(
        IncidentParticipantRow(incident_id=incident, node_id=node, role=role, position=position)
        for position, (node, role) in enumerate(dict.fromkeys(participants))
    )
    return incident


def step_moment(row: IncidentStepRow | None) -> Moment | None:
    return Moment(row.year, row.season, row.day, row.hour) if row is not None and row.year is not None else None


async def append_steps(ctx: TickContext, incident: int, key: str, clock: ProcessClock, drafts: Iterable[StepDraft]) -> list[IncidentStepRow]:
    session = ctx.session
    written: list[IncidentStepRow] = []
    drafts = list(drafts)
    checked_steps(INCIDENT_KINDS[key], drafts)
    for draft in drafts:
        count = await session.scalar(select(func.count()).select_from(IncidentStepRow).where(IncidentStepRow.incident_id == incident)) or 0
        last = await session.scalar(
            select(IncidentStepRow).where(IncidentStepRow.incident_id == incident).order_by(IncidentStepRow.position.desc(), IncidentStepRow.id.desc()).limit(1)
        )
        after = latest(await incident_moment(session, incident), step_moment(last))
        participants = [node for node in (draft.actor, draft.target) if node is not None]
        moment = draft.moment or await moment_for(ctx, clock, key=f"{key}.{incident}.{count}", participants=participants, cause_moment=after)
        rows = await write_steps(ctx, incident, [draft], moment.at_least(after), clock)
        for row in rows:
            row.position += count
        written.extend(rows)
    return written
