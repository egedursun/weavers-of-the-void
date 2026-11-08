import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.turns.long_jobs import LONG_JOBS, LongJobRegistry, LongJobResult, resolve_orphaned_jobs
from aerona.db.tables.agency import AgentTurnRow
from aerona.domain.enums.agent import AgentKind, PendingJobKind
from aerona.domain.models.turn import PendingJob, TurnContext
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.cosmos.factories import make_world


def turn(son_id: int, job: PendingJob, epoch: int = 3) -> AgentTurnRow:
    return AgentTurnRow(
        agent_node_id=son_id, agent_kind=AgentKind.SON, epoch=epoch, action_points_left=1, context=TurnContext().with_pending_job(job), finished=False
    )


async def test_a_half_finished_birth_refunds_its_essence_and_its_action(session: AsyncSession, world: CoreWorld) -> None:
    son = world.son
    son.essence, son.last_acted_epoch = 10, 2
    row = turn(son.id, PendingJob(kind=PendingJobKind.WORLD_BIRTH, essence=7, action_points=1, epoch=3))
    session.add(row)
    await session.flush()
    resolved = await resolve_orphaned_jobs(session, tuned_rules(), 3)
    assert [(item.son_id, item.result) for item in resolved] == [(son.id, LongJobResult.REFUNDED)]
    assert son.essence == 17 and row.context.pending_job is None


async def test_a_birth_that_was_finished_is_not_refunded(session: AsyncSession, world: CoreWorld) -> None:
    son = world.son
    son.essence = 10
    born = await make_world(session, "New Shore", created_epoch=3)
    born.creator_son_id = son.id
    session.add(turn(son.id, PendingJob(kind=PendingJobKind.WORLD_BIRTH, essence=7, action_points=1, epoch=3)))
    await session.flush()
    resolved = await resolve_orphaned_jobs(session, tuned_rules(), 3)
    assert [item.result for item in resolved] == [LongJobResult.DONE] and son.essence == 10


async def test_a_running_job_is_left_alone_and_waited_for(session: AsyncSession, world: CoreWorld) -> None:
    registry = LongJobRegistry()
    gate = asyncio.Event()

    async def work() -> object:
        await gate.wait()
        return None

    task = asyncio.create_task(work())
    registry.register(world.son.id, task)
    assert registry.running(world.son.id) is task
    gate.set()
    await registry.wait(world.son.id)
    assert registry.running(world.son.id) is None
    LONG_JOBS.register(world.son.id, asyncio.create_task(asyncio.sleep(60)))
    session.add(turn(world.son.id, PendingJob(kind=PendingJobKind.CHILD_BIRTH, essence=7, action_points=1, epoch=3)))
    await session.flush()
    assert await resolve_orphaned_jobs(session, tuned_rules(), 3) == []
    running = LONG_JOBS.running(world.son.id)
    assert running is not None
    running.cancel()
    await asyncio.gather(running, return_exceptions=True)
