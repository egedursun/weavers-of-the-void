import asyncio

import pytest
from sqlalchemy import func, select

from aerona.agents.runtime import AgentRuntime
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import CreationVerdictRow
from aerona.db.tables.epochs import EpochEnginePhaseRow, EpochRow, EpochRunRow
from aerona.db.tables.lore import ChronicleRow, FateRewardRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.job import JobStatus
from aerona.engine.context import TickContext
from aerona.engine.phase import Phase
from aerona.engine.pipeline import TICK_ORDER
from aerona.epoch import orchestrator as orchestrator_module
from aerona.epoch.context import EpochContext
from aerona.epoch.orchestrator import EpochOrchestrator
from aerona.epoch.phases import engine_tick as engine_tick_module
from aerona.epoch.phases import fate as fate_module
from aerona.epoch.resume import half_epoch
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.manager import JobManager
from aerona.llm.records import AgentRun
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld
from tests.epoch.scripts import script_full_epoch

JOB_WAIT_SECONDS = 120


class SimulatedCrashError(RuntimeError):
    pass


async def speakers(database: Database) -> list[str]:
    async with database.read() as session:
        rows = await session.scalars(select(ChronicleRow.text).where(ChronicleRow.kind == ChronicleKind.SPEECH))
        return [text.split(":", 1)[0] for text in rows]


async def counts(database: Database) -> tuple[int, int, int]:
    async with database.read() as session:
        words = int(await session.scalar(select(func.count()).select_from(ChronicleRow).where(ChronicleRow.kind == ChronicleKind.SPEECH)) or 0)
        rewards = int(await session.scalar(select(func.count()).select_from(FateRewardRow)) or 0)
        epoch = (await session.scalars(select(CosmosRow))).one().epoch
    return words, rewards, epoch


async def test_full_epoch_with_scripted_model(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    script_full_epoch(model, world)
    report = await EpochOrchestrator(runtime).run()
    async with database.read() as session:
        age = await session.get(EpochRow, 1)
        verdict = await session.get(CreationVerdictRow, world.creation.id)
    words, rewards, epoch = await counts(database)
    assert not report.stopped
    assert epoch == 2
    assert words >= 2
    assert rewards == 1
    assert age is not None and age.name == "Age of Dry Wells"
    assert verdict is not None and verdict.verdict is Verdict.ACCEPTED


@pytest.mark.parametrize(
    "target",
    ["son_turns", "mortal_turns", "engine_tick", "voices", "auto_council", "transition"],
)
async def test_crash_at_each_phase_resumes_without_repeating(
    runtime: AgentRuntime, model: FakeModel, world: AgentWorld, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    database = runtime.database
    script_full_epoch(model, world)
    original = getattr(orchestrator_module, target)
    crashed: list[bool] = []

    async def crash_once(ec: EpochContext) -> None:
        if not crashed:
            crashed.append(True)
            await original(ec)
            raise SimulatedCrashError(target)
        await original(ec)

    monkeypatch.setattr(orchestrator_module, target, crash_once)
    orchestrator = EpochOrchestrator(runtime)
    with pytest.raises(SimulatedCrashError):
        await orchestrator.run()
    async with database.read() as session:
        half = await half_epoch(session)
    assert half is not None or target == "transition"
    await orchestrator.run()
    _, rewards, epoch = await counts(database)
    async with database.read() as session:
        first = await session.get(EpochRunRow, 1)
    assert first is not None and first.finished
    if target == "transition":
        assert epoch == 3
        return
    voices = await speakers(database)
    assert epoch == 2
    assert rewards == 1
    assert len(voices) == len(set(voices)) >= 2


async def test_crash_between_verdict_and_chronicle_keeps_the_verdict_once(
    runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    script_full_epoch(model, world)
    original = fate_module.chronicle
    calls: list[int] = []

    async def failing(ec: EpochContext, renamed: list[tuple[str, str]]) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise SimulatedCrashError("chronicle")
        await original(ec, renamed)

    monkeypatch.setattr(fate_module, "chronicle", failing)
    orchestrator = EpochOrchestrator(runtime)
    with pytest.raises(SimulatedCrashError):
        await orchestrator.run()
    await orchestrator.run()
    _, rewards, epoch = await counts(database)
    async with database.read() as session:
        age = await session.get(EpochRow, 1)
    assert rewards == 1 and epoch == 2
    assert age is not None and age.narrative


async def test_engine_crash_mid_tick_resumes_from_the_failed_phase(database: Database, world: AgentWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    failing_index = 3
    target = TICK_ORDER[failing_index]
    attempts: list[int] = []

    async def flaky(ctx: TickContext) -> None:
        attempts.append(1)
        if len(attempts) == 1:
            raise SimulatedCrashError("engine")
        await target.run(ctx)

    phases = (*TICK_ORDER[:failing_index], Phase(target.name, flaky), *TICK_ORDER[failing_index + 1 :])
    monkeypatch.setattr(engine_tick_module, "TICK_ORDER", phases)
    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    orchestrator = EpochOrchestrator(runtime)
    with pytest.raises(Exception, match="engine"):
        await orchestrator.run()
    async with database.read() as session:
        done = int(await session.scalar(select(func.count()).select_from(EpochEnginePhaseRow).where(EpochEnginePhaseRow.epoch == 1)) or 0)
    assert done == failing_index
    await orchestrator.run()
    async with database.read() as session:
        run = await session.get(EpochRunRow, 1)
    assert run is not None and run.finished
    assert len(attempts) == 2


async def test_stop_request_pauses_after_the_current_turn(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    script_full_epoch(model, world)
    orchestrator = EpochOrchestrator(runtime)
    default = model.default_run
    assert default is not None

    def stopping() -> AgentRun:
        orchestrator.request_stop()
        return default

    model.runs.append(stopping)
    report = await orchestrator.run()
    assert report.stopped
    async with database.read() as session:
        half = await half_epoch(session)
    assert half is not None and half.epoch == 1
    resumed = await orchestrator.run()
    assert not resumed.stopped
    assert (await counts(database))[2] == 2


async def test_epoch_runs_as_a_world_job(runtime: AgentRuntime, model: FakeModel, database: Database, bus: EventBus, world: AgentWorld) -> None:
    script_full_epoch(model, world)
    jobs = JobManager(database, bus)
    orchestrator = EpochOrchestrator(runtime, jobs)
    finished = asyncio.Event()

    async def watch() -> None:
        async for event in bus.subscribe():
            if event.kind in (EventKind.JOB_FINISHED, EventKind.JOB_FAILED):
                finished.set()
                return

    watcher = asyncio.create_task(watch())
    await asyncio.sleep(0)
    job_id = await orchestrator.submit()
    await asyncio.wait_for(finished.wait(), timeout=JOB_WAIT_SECONDS)
    await watcher
    await asyncio.sleep(0)
    row = await jobs.get(job_id)
    assert row.status == JobStatus.SUCCEEDED.value
    assert row.result is not None and row.result["epoch"] == 1
