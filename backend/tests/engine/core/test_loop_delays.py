from dataclasses import replace

from sqlalchemy import func, select

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.loops import LoopSignalRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.loops import BalanceLoop
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world

LOOP = BalanceLoop.COMFORT_ZEAL
DELAY = 2


def delayed(epochs: int) -> Rules:
    rules = Rules()
    return replace(rules, loops=replace(rules.loops, delay_comfort_zeal=epochs))


async def test_a_loop_reads_its_driver_as_it_stood_its_delay_ago(database: Database) -> None:
    async with database.write() as session:
        world = await seed_core_world(session)
        cosmos = await CosmosRepository(session).require_cosmos()
        felt: list[int] = []
        for step, value in enumerate((10, 20, 30, 40, 50)):
            cosmos.epoch = step + 1
            ctx = await manual_context(session, "loop_delay", delayed(DELAY))
            felt.append(await lagged(ctx, LOOP, world.people.id, value))
        assert felt == [10, 10, 10, 20, 30]
        kept = await session.scalar(select(func.count()).select_from(LoopSignalRow).where(LoopSignalRow.loop == LOOP))
        assert kept == DELAY + 1


async def test_a_loop_without_delay_or_on_a_held_node_reads_the_present_and_keeps_nothing(database: Database) -> None:
    async with database.write() as session:
        world = await seed_core_world(session)
        ctx = await manual_context(session, "loop_delay", delayed(0))
        assert await lagged(ctx, LOOP, world.people.id, 70) == 70
        ctx = await manual_context(session, "loop_delay", delayed(DELAY))
        token = HELD_SCOPE.set(HeldScope(None, frozenset({world.people.id})))
        try:
            assert await lagged(ctx, LOOP, world.people.id, 80) == 80
        finally:
            HELD_SCOPE.reset(token)
        assert await session.scalar(select(func.count()).select_from(LoopSignalRow)) == 0
