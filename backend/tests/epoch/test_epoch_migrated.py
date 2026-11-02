from pathlib import Path

from sqlalchemy import select

from aerona.agents.runtime import AgentRuntime
from aerona.db.migrations import upgrade_to_head
from aerona.db.session import Database
from aerona.db.tables.epochs import EpochEnginePhaseRow
from aerona.domain.enums.epoch import EngineStage
from aerona.epoch.orchestrator import EpochOrchestrator
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel
from tests.agents.world import seed_agent_world


async def test_epoch_on_a_migrated_database_runs_post_transition_steps(tmp_path: Path, rules: Rules) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'migrated.db'}"
    await upgrade_to_head(url)
    database = Database(url)
    try:
        async with database.write() as session:
            await seed_agent_world(session, rules)
        await EpochOrchestrator(AgentRuntime(database=database, model=FakeModel(enabled=False))).run()
        async with database.read() as session:
            stages = list(await session.execute(select(EpochEnginePhaseRow.stage, EpochEnginePhaseRow.phase).where(EpochEnginePhaseRow.epoch == 1)))
    finally:
        await database.dispose()
    after = {phase for stage, phase in stages if stage is EngineStage.AFTER_TRANSITION}
    assert {"creator_mood", "god_power", "reputation", "goals"} <= after
