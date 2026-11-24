from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.changes import StateChangeRow
from aerona.domain.enums.node import ActorKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import shift_stat
from tests.engine.core.factories import CoreWorld


async def test_a_step_run_without_an_open_scope_still_writes_its_changes_to_its_step_and_epoch(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = 4
    await session.flush()
    ctx = await manual_context(session, "scope_probe")
    mark = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)

    async def nudge(step: TickContext) -> None:
        shift_stat(world.people, "piety", 3)

    await run_guarded(Phase("scope_probe_step", nudge), TickContext(ctx.environment, session, "scope_probe_step"))
    rows = list(await session.scalars(select(StateChangeRow).where(StateChangeRow.id > mark)))
    assert rows
    assert {(row.actor_kind, row.phase, row.epoch) for row in rows} == {(ActorKind.ENGINE, "scope_probe_step", 4)}
