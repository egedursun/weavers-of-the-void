from sqlalchemy import ColumnElement, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_capture import finish_rebuilds
from aerona.db.record_context import RecordScope, acting, scoped, stepping
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow, StateCheckpointRow
from aerona.db.tables.interconnect import IncidentRow, ModifierRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.moment import Moment
from aerona.engine.recording.checkpoints import checkpoint_holds, take_checkpoint
from aerona.engine.recording.past import state_at, value_at
from aerona.engine.recording.terms import explaining, term
from tests.db.factories import seed_world


async def changes(session: AsyncSession, *conditions: ColumnElement[bool]) -> list[StateChangeRow]:
    return list(await session.scalars(select(StateChangeRow).where(*conditions).order_by(StateChangeRow.id)))


def modifier(target: int, magnitude: float, reason: str = "test") -> ModifierRow:
    return ModifierRow(
        target_node_id=target,
        target_key="prosperity",
        op=ModifierOp.ADD,
        magnitude=magnitude,
        source_kind=ModifierSource.TRAIT,
        reason_key=reason,
        start_epoch=1,
    )


async def test_every_write_is_recorded_with_its_before_after_actor_and_terms(session: AsyncSession) -> None:
    with acting(ActorKind.CREATOR, None, 3):
        world = await seed_world(session)
        await session.flush()
    inserted = await changes(session, StateChangeRow.table_name == "worlds", StateChangeRow.operation == LedgerOperation.INSERT)
    assert len(inserted) == 1 and inserted[0].node_id == world.id and inserted[0].actor_kind is ActorKind.CREATOR and inserted[0].after_text
    before = world.magnetism
    with scoped(RecordScope(key="test.change", epoch=4, moment=Moment(150, 1, 20, 3))), explaining():
        term("rules.test.magnetism_gain", 20)
        world.magnetism = before + 20
        await session.flush()
    updated = await changes(session, StateChangeRow.table_name == "worlds", StateChangeRow.field == "magnetism")
    assert [(row.before_number, row.after_number, row.epoch, row.year, row.day) for row in updated] == [(before, before + 20, 4, 150, 20)]
    explained = list(await session.scalars(select(StateChangeTermRow).where(StateChangeTermRow.change_id == updated[0].id)))
    assert [(row.term, row.amount) for row in explained] == [("rules.test.magnetism_gain", 20.0)]


async def test_bulk_writes_are_recorded_and_a_rebuild_records_only_what_differs(session: AsyncSession) -> None:
    world = await seed_world(session)
    kept, changed = modifier(world.id, 1.0, "kept"), modifier(world.id, 2.0, "changed")
    session.add_all([kept, changed])
    await session.flush()
    await session.execute(update(ModifierRow).where(ModifierRow.id == kept.id).values(magnitude=1.5))
    bulk = await changes(session, StateChangeRow.table_name == "modifiers", StateChangeRow.field == "magnitude")
    assert [(row.before_number, row.after_number) for row in bulk] == [(1.0, 1.5)]
    marker = int(await session.scalar(select(func.max(StateChangeRow.id))) or 0)
    await session.execute(delete(ModifierRow))
    session.add_all([modifier(world.id, 1.5, "kept"), modifier(world.id, 9.0, "changed")])
    await session.flush()
    await session.run_sync(finish_rebuilds)
    rebuilt = await changes(session, StateChangeRow.id > marker, StateChangeRow.table_name == "modifiers")
    assert sorted(row.operation for row in rebuilt) == [LedgerOperation.DELETE, LedgerOperation.INSERT]


async def test_unexplained_engine_writes_join_the_incident_of_their_step(session: AsyncSession) -> None:
    world = await seed_world(session)
    await session.flush()
    with scoped(RecordScope(key="phase.harvest", epoch=2, phase="harvest", moment=Moment(50))):
        world.danger = world.danger + 5
        await session.flush()
    row = (await changes(session, StateChangeRow.field == "danger"))[0]
    incident = await session.get(IncidentRow, row.incident_id)
    assert incident is not None and incident.kind == "phase.harvest" and incident.world_id == world.id and row.phase == "harvest"


async def test_the_past_of_a_record_is_rebuilt_from_its_changes_and_checkpoints_hold(session: AsyncSession) -> None:
    with scoped(RecordScope(key="test.one", epoch=1)):
        world = await seed_world(session)
        await session.flush()
        start = world.danger
        world.danger = start + 1
        await session.flush()
    await take_checkpoint(session, 1)
    with scoped(RecordScope(key="test.two", epoch=2)):
        world.danger = start + 7
        await session.flush()
    assert await value_at(session, "worlds", {"id": world.id}, "danger", epoch=1) == start + 1
    assert await value_at(session, "worlds", {"id": world.id}, "danger", epoch=2) == start + 7
    assert await state_at(session, "worlds", {"id": world.id}, epoch=0) is None
    checkpoint = await session.scalar(select(StateCheckpointRow).where(StateCheckpointRow.table_name == "worlds"))
    assert checkpoint is not None and await checkpoint_holds(session, checkpoint)


async def test_a_date_set_to_the_present_epoch_says_so(session: AsyncSession) -> None:
    world = await seed_world(session)
    await session.flush()
    with scoped(RecordScope(key="phase.test", epoch=7)), stepping():
        world.climate_since_epoch = 7
        world.magnetism = world.magnetism + 1
        await session.flush()
    dated = await changes(session, StateChangeRow.table_name == "worlds", StateChangeRow.field == "climate_since_epoch")
    plain = await changes(session, StateChangeRow.table_name == "worlds", StateChangeRow.field == "magnetism")
    assert list(await session.scalars(select(StateChangeTermRow.term).where(StateChangeTermRow.change_id == dated[0].id))) == ["epoch.present"]
    assert list(await session.scalars(select(StateChangeTermRow.term).where(StateChangeTermRow.change_id == plain[0].id))) == []
