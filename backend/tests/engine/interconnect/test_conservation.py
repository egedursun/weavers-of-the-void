from collections import Counter
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.base import Base
from aerona.db.session import Database
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.war import WarEnding
from aerona.engine.context import TickContext
from aerona.engine.interconnect.conservation import journey_imbalance, residuals, snapshot, totals_by_phase, transfer_imbalance, unexplained, wrong_signs
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.interconnect.guards import recording, run_guarded
from aerona.engine.phase import Phase
from aerona.engine.phases.warfare import force_battle
from aerona.engine.pipeline import current_environment, run_epoch_transition, run_tick
from aerona.engine.primitives.manual import silent
from aerona.engine.primitives.stats import set_stats
from aerona.engine.services.war import declare_war, open_war
from aerona.engine.services.war_resolution import end_war
from aerona.rules.registry import Rules
from tests.engine.integration.factories import seed_rich_cosmos
from tests.engine.warfare.factories import make, make_ctx, tune

EPOCHS = 2
QUIET = {"battle_die": 1, "duel_chance": 0, "capture_chance": 0, "four_battle_exhaustion_chance": 0, "decisive_score": 50, "great_victory_diff": 1000}


async def test_a_whole_war_moves_soldiers_without_creating_or_losing_any_unaccounted(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET))
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=5000, martiality=40)
    before = await snapshot(session)

    async def run(step: TickContext) -> None:
        await declare_war(step, first.id, second.id, "grudge")
        war = await open_war(step, first, second)
        await force_battle(step, war.id)
        await end_war(step, war, WarEnding.PEACE, reason="test peace")

    await run_guarded(Phase("test_war", run), ctx)
    await session.flush()
    assert await residuals(session, before, ctx.environment.stats.flows) == {}
    assert totals_by_phase(ctx.environment.stats.flows)[("test_war", "population")] < 0


async def test_a_few_epochs_of_the_whole_engine_conserve_every_count(tmp_path: Path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path}/ledger.db"
    database = Database(url)
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with database.write() as session:
            await seed_rich_cosmos(session)
        for _ in range(EPOCHS):
            async with database.read() as session:
                before = await snapshot(session)
            tick = await run_tick(await current_environment(database, silent, None, phase=EpochPhase.ENGINE), database)
            transition = await run_epoch_transition(await current_environment(database, silent, None, phase=EpochPhase.TRANSITION), database)
            flows = Counter(tick.stats.flows)
            flows.update(transition.flows)
            async with database.read() as session:
                after = await snapshot(session)
                assert await residuals(session, before, flows) == {}
            assert unexplained(flows) == {}
            assert transfer_imbalance(flows) == {}
            assert wrong_signs(flows) == {}
            assert journey_imbalance(before, after, flows) == 0
    finally:
        await database.dispose()


async def test_new_entities_and_a_leaking_levy_are_caught(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, Rules())
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    before = await snapshot(session)

    async def leak(step: TickContext) -> None:
        with flowing(FlowCategory.LEVY):
            set_stats(folk, population=8000)
        await make(session, "Phantom Folk", EntityType.PEOPLE, world_id, population=500)

    await run_guarded(Phase("test_leak", leak), ctx)
    await session.flush()
    flows = ctx.environment.stats.flows
    assert transfer_imbalance(flows) == {("test_leak", "levy", "bodies"): -1000}
    found = await residuals(session, before, flows)
    assert len(found) == 1 and next(iter(found.values())) == 500
