from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarEnding
from aerona.engine.context import TickContext
from aerona.engine.interconnect.conservation import residuals, snapshot, totals_by_phase
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.phase import Phase
from aerona.engine.phases.warfare import force_battle
from aerona.engine.services.war import declare_war, open_war
from aerona.engine.services.war_resolution import end_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, tune

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
