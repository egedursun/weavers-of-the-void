from sqlalchemy import func, select

from aerona.agents.ports import bus_publisher
from aerona.agents.runtime import AgentRuntime
from aerona.db.repositories.cosmos import snapshot_rules
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import CreationVerdictRow
from aerona.db.tables.epochs import EpochEnginePhaseRow, EpochRunRow, EpochStepRow
from aerona.domain.enums.epoch import EngineStage, EpochStepKind, EpochStepStatus
from aerona.domain.enums.world import FateMode
from aerona.epoch.eta import estimate
from aerona.epoch.orchestrator import EpochOrchestrator
from aerona.epoch.ports import EpochHooks
from aerona.epoch.resume import half_epoch
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.rules.snapshot import with_value
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld


async def cosmos_epoch(database: Database) -> int:
    async with database.read() as session:
        return (await session.scalars(select(CosmosRow))).one().epoch


async def test_engine_only_epochs_run_end_to_end(database: Database, bus: EventBus, world: AgentWorld, rules: Rules) -> None:
    backups: list[str] = []

    async def backup(label: str) -> str:
        backups.append(label)
        return f"{label}.db"

    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False), publish=bus_publisher(bus))
    orchestrator = EpochOrchestrator(runtime, hooks=EpochHooks(backup=backup))
    first = await orchestrator.run()
    second = await orchestrator.run()
    assert (first.epoch, second.epoch) == (1, 2)
    assert await cosmos_epoch(database) == 3
    assert backups == ["epoch1", "epoch2"]
    async with database.read() as session:
        runs = list(await session.scalars(select(EpochRunRow).order_by(EpochRunRow.epoch)))
        cosmos = (await session.scalars(select(CosmosRow))).one()
        steps = {row.step: row.status for row in await session.scalars(select(EpochStepRow).where(EpochStepRow.epoch == 1))}
        engine_phases = int(await session.scalar(select(func.count()).select_from(EpochEnginePhaseRow).where(EpochEnginePhaseRow.epoch == 1)) or 0)
        assert await half_epoch(session) is None
        eta = await estimate(session, rules)
    assert all(run.finished for run in runs)
    assert cosmos.fate_debt_epoch == 1
    assert steps[EpochStepKind.FATE_JUDGMENT] is EpochStepStatus.DONE
    assert steps[EpochStepKind.CHRONICLE] is EpochStepStatus.SKIPPED
    assert engine_phases > 10
    assert eta.samples == 2
    kinds = [event.kind for event in bus.replay_after(0)]
    assert kinds.count(EventKind.EPOCH_FINISHED) == 2
    assert EventKind.ENGINE_PHASE in kinds


async def test_fate_off_records_unjudged_without_llm(database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        (await session.scalars(select(CosmosRow))).one().fate_mode = FateMode.OFF
    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    await EpochOrchestrator(runtime).run()
    async with database.read() as session:
        verdict = await session.get(CreationVerdictRow, world.creation.id)
    assert verdict is not None and verdict.verdict.value == "unjudged"


async def test_distribution_hook_runs_on_fresh_epochs(database: Database, world: AgentWorld) -> None:
    calls: list[int] = []

    async def distribute() -> int:
        calls.append(1)
        return 0

    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    await EpochOrchestrator(runtime, hooks=EpochHooks(distribute=distribute)).run()
    assert calls == [1]


async def test_post_transition_phases_run_and_switches_are_honoured(database: Database, world: AgentWorld, rules: Rules) -> None:
    async with database.write() as session:
        cosmos = (await session.scalars(select(CosmosRow))).one()
        cosmos.rules_snapshot = snapshot_rules(with_value(with_value(rules, "engine_phases", "reputation", 0), "engine_phases", "trade_income", 0))
    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    await EpochOrchestrator(runtime).run()
    async with database.read() as session:
        rows = list(await session.scalars(select(EpochEnginePhaseRow).where(EpochEnginePhaseRow.epoch == 1)))
    by_stage: dict[EngineStage, set[str]] = {}
    for row in rows:
        by_stage.setdefault(row.stage, set()).add(row.phase)
    assert {"creator_mood", "god_power", "goals"} <= by_stage[EngineStage.AFTER_TRANSITION]
    assert "reputation" not in by_stage[EngineStage.AFTER_TRANSITION]
    assert "trade_income" not in by_stage[EngineStage.TICK]
    assert "advance_epoch" in by_stage[EngineStage.TRANSITION]


async def test_after_tick_hook_runs_right_after_the_engine_tick(database: Database, world: AgentWorld) -> None:
    calls: list[tuple[int, int]] = []

    async def after_tick(epoch: int, since_id: int) -> None:
        async with database.read() as session:
            run = (await session.scalars(select(EpochRunRow).where(EpochRunRow.epoch == epoch))).one()
        assert not run.finished
        calls.append((epoch, since_id))

    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    await EpochOrchestrator(runtime, hooks=EpochHooks(after_tick=after_tick)).run()
    assert [epoch for epoch, _ in calls] == [1]
