import json

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec
from aerona.constants.engine import LOCATION_CHAIN_MAX_HOPS
from aerona.db.base import Base
from aerona.db.ledger_capture import jsonable, key_text
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.changes import StateChangeRow, StateCheckpointRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactValue, IncidentTier, WitnessMode
from aerona.engine.recording.checkpoints import digest_of, kept_columns, present_rows, take_checkpoint
from aerona.engine.recording.legacy import retire_one
from aerona.engine.recording.past import state_at
from aerona.rules.registry import Rules

PHASE_PREFIX = "phase."
WITNESS_KEY = 1_000_000_000


def fits(spec: FactSpec, fact: IncidentFactRow) -> bool:
    if spec.value is FactValue.NODE:
        return fact.node_id is not None
    if spec.value is FactValue.NUMBER:
        return fact.number is not None and (spec.unit is None or fact.unit is spec.unit)
    if spec.value is FactValue.ENUM:
        return fact.enum_value is not None and (spec.enum is None or fact.enum_value in {member.value for member in spec.enum})
    return fact.name is not None


async def misfit_facts(session: AsyncSession) -> list[int]:
    found: list[int] = []
    statement = select(IncidentFactRow, IncidentRow.kind).join(IncidentRow, IncidentRow.id == IncidentFactRow.incident_id).order_by(IncidentFactRow.id)
    for fact, kind in await session.execute(statement):
        spec = INCIDENT_KINDS.get(kind)
        if spec is not None and spec.draft:
            continue
        declared = spec.fact(fact.key) if spec is not None else None
        if declared is None or not fits(declared, fact):
            found.append(fact.id)
    return found


async def drop_fact(session: AsyncSession, fact_id: int) -> None:
    await session.execute(delete(IncidentFactRow).where(IncidentFactRow.id == fact_id))


async def crossed_nesting(session: AsyncSession) -> list[int]:
    parents = {row.id: row.incident_id for row in await session.execute(select(IncidentStepRow.id, IncidentStepRow.incident_id))}
    found: list[int] = []
    for step_id, incident_id, parent_id in await session.execute(
        select(IncidentStepRow.id, IncidentStepRow.incident_id, IncidentStepRow.parent_step_id)
        .where(IncidentStepRow.parent_step_id.is_not(None))
        .order_by(IncidentStepRow.id)
    ):
        if parent_id == step_id or parents.get(parent_id) != incident_id:
            found.append(step_id)
    return found


async def clear_nesting(session: AsyncSession, step_id: int) -> None:
    step = await session.get(IncidentStepRow, step_id)
    if step is not None:
        step.parent_step_id = None


async def undeclared_steps(session: AsyncSession) -> list[int]:
    found: list[int] = []
    statement = select(IncidentStepRow.id, IncidentStepRow.action, IncidentRow.kind).join(IncidentRow, IncidentRow.id == IncidentStepRow.incident_id)
    for step_id, action, kind in await session.execute(statement.order_by(IncidentStepRow.id)):
        spec = INCIDENT_KINDS.get(kind)
        if spec is None or (not spec.draft and action not in spec.steps):
            found.append(step_id)
    return found


async def drop_step(session: AsyncSession, step_id: int) -> None:
    await session.execute(delete(IncidentStepRow).where(IncidentStepRow.id == step_id))


def moment_key(row: IncidentRow | IncidentStepRow) -> tuple[int, int, int, int] | None:
    if row.year is None:
        return None
    return (row.year, row.season or 0, row.day or 0, row.hour or 0)


async def early_moments(session: AsyncSession) -> list[int]:
    found: list[int] = []
    cause = IncidentRow.__table__.alias("cause")
    statement = (
        select(IncidentRow, cause.c.year, cause.c.season, cause.c.day, cause.c.hour)
        .join(cause, cause.c.id == IncidentRow.cause_incident_id)
        .where(IncidentRow.year.is_not(None), cause.c.year.is_not(None))
        .order_by(IncidentRow.id)
    )
    for incident, year, season, day, hour in await session.execute(statement):
        own = moment_key(incident)
        if own is not None and own < (year, season or 0, day or 0, hour or 0):
            found.append(incident.id)
    return found


async def follow_cause(session: AsyncSession, incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    cause = await session.get(IncidentRow, incident.cause_incident_id) if incident is not None and incident.cause_incident_id is not None else None
    if incident is not None and cause is not None:
        incident.year, incident.season, incident.day, incident.hour = cause.year, cause.season, cause.day, cause.hour


async def steps_out_of_order(session: AsyncSession) -> list[int]:
    found: list[int] = []
    last: dict[int, tuple[int, int, int, int]] = {}
    for step in await session.scalars(
        select(IncidentStepRow).where(IncidentStepRow.year.is_not(None)).order_by(IncidentStepRow.incident_id, IncidentStepRow.position)
    ):
        own = moment_key(step)
        before = last.get(step.incident_id)
        if own is not None and before is not None and own < before:
            found.append(step.id)
        if own is not None:
            last[step.incident_id] = max(own, before) if before is not None else own
    return found


async def follow_step(session: AsyncSession, step_id: int) -> None:
    step = await session.get(IncidentStepRow, step_id)
    if step is None:
        return
    previous = await session.scalar(
        select(IncidentStepRow)
        .where(IncidentStepRow.incident_id == step.incident_id, IncidentStepRow.position < step.position, IncidentStepRow.year.is_not(None))
        .order_by(IncidentStepRow.position.desc())
        .limit(1)
    )
    if previous is not None:
        step.year, step.season, step.day, step.hour = previous.year, previous.season, previous.day, previous.hour


PRESENT_MODES = (WitnessMode.SAW, WitnessMode.TOOK_PART)


def witness_key(incident_id: int, node_id: int) -> int:
    return incident_id * WITNESS_KEY + node_id


async def last_moves(session: AsyncSession) -> dict[int, int]:
    statement = (
        select(StateChangeRow.node_id, func.max(StateChangeRow.epoch))
        .where(StateChangeRow.table_name == EntityRow.__tablename__, StateChangeRow.field == "location_id", StateChangeRow.node_id.is_not(None))
        .group_by(StateChangeRow.node_id)
    )
    return {int(node_id): int(epoch) for node_id, epoch in await session.execute(statement) if node_id is not None}


def held_by(places: dict[int, int | None], place_id: int, entity_id: int) -> bool:
    current: int | None = entity_id
    for _ in range(LOCATION_CHAIN_MAX_HOPS + 1):
        if current is None:
            return False
        if current == place_id:
            return True
        current = places.get(current)
    return False


async def absent_witnesses(session: AsyncSession) -> list[int]:
    statement = (
        select(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id, IncidentRow.place_entity_id, IncidentRow.epoch)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(
            IncidentParticipantRow.role == IncidentRole.WITNESS,
            IncidentParticipantRow.witness_mode.in_(PRESENT_MODES),
            IncidentRow.place_entity_id.is_not(None),
        )
        .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
    )
    witnesses = list(await session.execute(statement))
    if not witnesses:
        return []
    places = {int(entity_id): location_id for entity_id, location_id in await session.execute(select(EntityRow.id, EntityRow.location_id))}
    moved = await last_moves(session)
    return [
        witness_key(incident_id, node_id)
        for incident_id, node_id, place_id, epoch in witnesses
        if node_id in places
        and places[node_id] is not None
        and moved.get(node_id, -1) < epoch
        and place_id is not None
        and not held_by(places, place_id, node_id)
    ]


async def modeless_witnesses(session: AsyncSession) -> list[int]:
    statement = (
        select(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
        .where(IncidentParticipantRow.role == IncidentRole.WITNESS, IncidentParticipantRow.witness_mode.is_(None))
        .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
    )
    return [witness_key(incident_id, node_id) for incident_id, node_id in await session.execute(statement)]


async def give_witness_mode(session: AsyncSession, key: int) -> None:
    incident_id, node_id = divmod(key, WITNESS_KEY)
    row = await session.get(IncidentParticipantRow, (incident_id, node_id, IncidentRole.WITNESS))
    if row is None:
        return
    cosmos = CosmosRepository(session)
    rules = await cosmos.rules() if await cosmos.get() is not None else Rules()
    incident = await session.get(IncidentRow, incident_id)
    place = incident.place_entity_id if incident is not None else None
    places = {int(entity_id): location_id for entity_id, location_id in await session.execute(select(EntityRow.id, EntityRow.location_id))}
    present = place is None or node_id not in places or held_by(places, place, node_id)
    row.witness_mode = WitnessMode.SAW if present else WitnessMode.HEARD
    row.fidelity = rules.records.fidelity_saw if present else rules.records.fidelity_heard


async def drop_witness(session: AsyncSession, key: int) -> None:
    incident_id, node_id = divmod(key, WITNESS_KEY)
    await session.execute(
        delete(IncidentParticipantRow).where(
            IncidentParticipantRow.incident_id == incident_id, IncidentParticipantRow.node_id == node_id, IncidentParticipantRow.role == IncidentRole.WITNESS
        )
    )


async def unscoped_changes(session: AsyncSession) -> list[int]:
    statement = select(StateChangeRow.id).where(StateChangeRow.incident_id.is_(None), StateChangeRow.actor_kind == ActorKind.ENGINE)
    return list(await session.scalars(statement.order_by(StateChangeRow.id)))


async def scope_change(session: AsyncSession, change_id: int) -> None:
    change = await session.get(StateChangeRow, change_id)
    if change is None:
        return
    kind = f"{PHASE_PREFIX}{change.phase}" if change.phase else f"{PHASE_PREFIX}unknown"
    incident_id = await session.scalar(
        select(IncidentRow.id).where(IncidentRow.kind == kind, IncidentRow.epoch == change.epoch).order_by(IncidentRow.id).limit(1)
    )
    if incident_id is None:
        incident = IncidentRow(kind=kind, epoch=max(1, change.epoch), year=change.year, tier=IncidentTier.LINE, locked=[], magnitude=0)
        session.add(incident)
        await session.flush()
        incident_id = incident.id
    change.incident_id = incident_id


async def checkpoint_still_holds(session: AsyncSession, checkpoint: StateCheckpointRow) -> bool:
    table = Base.metadata.tables[checkpoint.table_name]
    primary = list(table.primary_key.columns)
    rows = {key_text({column.name: jsonable(row[column.name]) for column in primary}): dict(row) for row in await present_rows(session, table)}
    later = select(StateChangeRow.row_key).where(StateChangeRow.table_name == table.name, StateChangeRow.id > checkpoint.last_change_id).distinct()
    for row_key in sorted(set(await session.scalars(later))):
        then = await state_at(session, table.name, json.loads(row_key), epoch=checkpoint.epoch, until_change_id=checkpoint.last_change_id)
        if then is None:
            rows.pop(row_key, None)
        else:
            rows[row_key] = then
    count, digest = digest_of(rows.values(), kept_columns(table))
    return count == checkpoint.row_count and digest == checkpoint.digest


async def broken_checkpoints(session: AsyncSession) -> list[int]:
    latest = select(StateCheckpointRow.table_name, func.max(StateCheckpointRow.epoch).label("epoch")).group_by(StateCheckpointRow.table_name).subquery()
    statement = (
        select(StateCheckpointRow)
        .join(latest, (latest.c.table_name == StateCheckpointRow.table_name) & (latest.c.epoch == StateCheckpointRow.epoch))
        .order_by(StateCheckpointRow.table_name, StateCheckpointRow.id)
    )
    found: list[int] = []
    for checkpoint in await session.scalars(statement):
        if checkpoint.table_name in Base.metadata.tables and not await checkpoint_still_holds(session, checkpoint):
            found.append(checkpoint.id)
    return found


async def retake_checkpoint(session: AsyncSession, checkpoint_id: int) -> None:
    checkpoint = await session.get(StateCheckpointRow, checkpoint_id)
    if checkpoint is None:
        return
    epoch = checkpoint.epoch
    await session.execute(delete(StateCheckpointRow).where(StateCheckpointRow.epoch == epoch))
    await take_checkpoint(session, epoch)


async def unknown_kinds(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(IncidentRow.id).where(IncidentRow.kind.not_in(list(INCIDENT_KINDS))).order_by(IncidentRow.id)))


async def retire_kind(session: AsyncSession, incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    if incident is not None:
        await retire_one(session, incident)
