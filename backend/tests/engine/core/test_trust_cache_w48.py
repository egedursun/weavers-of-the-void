from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.domain.enums.intrigue import BeliefSource
from aerona.engine.intrigue.beliefs import believe
from tests.engine.core.factories import CoreWorld, mortal
from tests.engine.core.test_minds_w44 import at


async def test_many_beliefs_of_one_holder_ask_for_its_trust_once(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    watcher = await mortal(session, "Cass", world, world.regions[0].id)
    asked: list[str] = []

    def counted(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        if "source_trust" in statement:
            asked.append(statement)

    engine = session.bind.sync_engine if hasattr(session.bind, "sync_engine") else session.bind
    event.listen(engine, "before_cursor_execute", counted)
    try:
        for attribute in ("wealth", "population", "might", "piety"):
            await believe(ctx, watcher.id, world.people.id, attribute, 50, source=BeliefSource.OBSERVATION, confidence=80)
    finally:
        event.remove(engine, "before_cursor_execute", counted)
    assert len(asked) == 1


async def test_a_trust_set_later_in_the_session_is_heeded(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    watcher = await mortal(session, "Cass", world, world.regions[0].id)
    assert await believe(ctx, watcher.id, world.people.id, "wealth", 50, source=BeliefSource.RUMOUR, confidence=80) is not None
    session.add(SourceTrustRow(holder_node_id=watcher.id, source=BeliefSource.RUMOUR, trust=0, locked=[]))
    await session.flush()
    assert await believe(ctx, watcher.id, world.people.id, "population", 50, source=BeliefSource.RUMOUR, confidence=80) is None
