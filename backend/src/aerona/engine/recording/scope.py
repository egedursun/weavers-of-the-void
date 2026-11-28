from collections.abc import AsyncIterator, Iterable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.record_context import PHASE_FAMILY, RecordScope, Term, current_scope, happening, scoped
from aerona.db.repositories.chronicle import caused_by
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentTermRow
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import ProcessClock
from aerona.domain.models.calendar import YearWindow, epoch_start_year
from aerona.domain.models.moment import Moment
from aerona.engine.context import TickContext, TickEnvironment
from aerona.engine.recording.moments import incident_moment, moment_for
from aerona.engine.recording.rites import near_the_dead


def phase_key(phase: str) -> str:
    return f"{PHASE_FAMILY}.{phase}"


def phase_moment(environment: TickEnvironment) -> Moment:
    years = environment.rules.time.years_per_epoch
    window = environment.window or YearWindow(start=0, end=years)
    span = max(1, window.end - window.start)
    into = int(min(max(environment.step, 0.0), 1.0) * span) if environment.step is not None else 0
    return Moment(epoch_start_year(environment.epoch, years) + window.start + min(span - 1, into))


@contextmanager
def phase_scope(environment: TickEnvironment, phase: str) -> Iterator[RecordScope]:
    scope = RecordScope(key=phase_key(phase), epoch=environment.epoch, phase=phase, moment=phase_moment(environment), parent=current_scope())
    with scoped(scope) as found:
        yield found


def reason_rows(incident_id: int, terms: tuple[Term, ...]) -> list[dict[str, object]]:
    return [
        {
            "incident_id": incident_id,
            "position": position,
            "term": term.key,
            "source_node_id": term.source_node_id,
            "source_incident_id": term.source_incident_id,
            "op": term.op.value,
            "amount": term.amount,
        }
        for position, term in enumerate(terms)
    ]


def triggering(outer: RecordScope | None) -> int | None:
    while outer is not None:
        if outer.incident_id is not None:
            return outer.incident_id
        outer = outer.parent
    return None


async def open_incident(session: AsyncSession, scope: RecordScope, place_id: int | None) -> int:
    moment = scope.moment
    values: dict[str, Any] = {
        "kind": scope.key,
        "epoch": max(1, scope.epoch),
        "world_id": scope.world_id,
        "place_entity_id": place_id,
        "cause_incident_id": scope.cause_incident_id,
        "magnitude": 0,
        "year": moment.year if moment is not None else None,
        "season": moment.season if moment is not None else None,
        "day": moment.day if moment is not None else None,
        "hour": moment.hour if moment is not None else None,
    }
    connection = await session.connection()
    inserted = (await connection.execute(insert(IncidentRow).values(values))).inserted_primary_key
    if inserted is None:
        raise ValueError("A happening got no record.")
    return int(inserted[0])


@asynccontextmanager
async def recording(
    ctx: TickContext,
    key: str,
    *,
    cause: int | None = None,
    world_id: int | None = None,
    moment: Moment | None = None,
    place_id: int | None = None,
    clock: ProcessClock = ProcessClock.INSTANT,
    participants: Iterable[int] = (),
    progress: float | None = None,
) -> AsyncIterator[RecordScope]:
    outer = current_scope()
    cause_id = cause if cause is not None else triggering(outer)
    listed = list(participants)
    present = [*listed, *([place_id] if place_id is not None else [])]
    cause_moment = await incident_moment(ctx.session, cause_id)
    when = moment or await near_the_dead(
        ctx,
        key,
        listed,
        await moment_for(ctx, clock, key=key, participants=present, cause_moment=cause_moment, progress=progress, world_id=world_id),
        cause_moment,
    )
    scope = RecordScope(
        key=key,
        epoch=ctx.epoch,
        phase=ctx.phase,
        actor_kind=outer.actor_kind if outer is not None else ActorKind.ENGINE,
        actor_node_id=outer.actor_node_id if outer is not None else None,
        world_id=world_id if world_id is not None else outer.world_id if outer is not None else None,
        cause_incident_id=cause_id,
        moment=when,
        parent=outer,
    )
    scope.incident_id = await open_incident(ctx.session, scope, place_id)
    with scoped(scope), caused_by(scope.incident_id), happening() as reasons:
        yield scope
        terms = reasons.snapshot()
        if terms:
            await ctx.session.execute(insert(IncidentTermRow), reason_rows(scope.incident_id, terms))


@contextmanager
def at_step(scope: RecordScope, step_id: int | None) -> Iterator[RecordScope]:
    before = scope.step_id
    scope.step_id = step_id
    try:
        yield scope
    finally:
        scope.step_id = before
