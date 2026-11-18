import asyncio
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import delete

from aerona.agents.runtime import AgentRuntime
from aerona.db.repositories.cosmos import CosmosRepository, snapshot_rules
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.session import Database
from aerona.db.tables.epochs import DeferredStepRow, EpochStepRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus, EpochStepKind, EpochStepStatus
from aerona.domain.enums.job import JobKind
from aerona.domain.models.profiles import Epic
from aerona.domain.models.stats import StatBlock
from aerona.epoch.concurrency import StopSignal
from aerona.epoch.context import EpochContext
from aerona.epoch.phases import deferred as deferred_module
from aerona.epoch.phases.deferred import CREATOR_EPIC_KEY, auto_deepen_candidates, deferred_worlds, launch_background, stale_epics
from aerona.epoch.phases.image_autogen import image_autogen
from aerona.epoch.phases.start import complete_missing
from aerona.epoch.ports import EpochHooks
from aerona.epoch.state import require_run
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.rules.snapshot import with_value
from aerona.services.epoch_wiring import BackgroundPool
from aerona.services.rules import RulesService
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld
from tests.polling import until


class Spawns:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def __call__(self, key: str, work: Callable[[], Awaitable[object]]) -> bool:
        self.keys.append(key)
        return True


def context(runtime: AgentRuntime, hooks: EpochHooks | None = None, epoch: int = 1) -> EpochContext:
    return EpochContext(runtime, hooks or EpochHooks(), StopSignal(), epoch, False)


async def tune(database: Database, rules: Rules, group: str, key: str, value: int) -> None:
    async with database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        cosmos.rules_snapshot = snapshot_rules(with_value(rules, group, key, value))


async def step(database: Database, kind: EpochStepKind) -> EpochStepStatus | None:
    async with database.read() as session:
        row = await session.get(EpochStepRow, (1, kind))
        return row.status if row is not None else None


async def test_auto_deepen_orders_named_records_before_unnamed_ones(runtime: AgentRuntime, world: AgentWorld) -> None:
    ids = await auto_deepen_candidates(context(runtime), 500)
    assert ids.index(world.pending.id) == len(ids) - 1
    assert len(ids) == len(set(ids))
    assert len(await auto_deepen_candidates(context(runtime), 1)) == 1


async def test_epoch_end_launches_entity_and_foreign_god_deepening(runtime: AgentRuntime, database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        await ForeignGodRepository(session).create(
            ForeignGodDraft(name="Ulmar", world_id=world.core.world.id, domain_primary=Domain.SEA, power=30, stats=StatBlock.uniform(40), created_epoch=1)
        )
    spawn = Spawns()
    ec = context(runtime, EpochHooks(spawn=spawn))
    await launch_background(ec)
    assert any(key.startswith("foreign:") and key.endswith(":depth") for key in spawn.keys)
    assert any(key.startswith("entity:") and key.endswith(":depth") for key in spawn.keys)
    assert await step(database, EpochStepKind.BACKGROUND) is EpochStepStatus.DONE
    again = Spawns()
    await launch_background(context(runtime, EpochHooks(spawn=again)))
    assert again.keys == []


async def test_auto_deepen_off_spawns_no_deepening(runtime: AgentRuntime, database: Database, rules: Rules, world: AgentWorld) -> None:
    await tune(database, rules, "agents", "auto_deepen", 0)
    spawn = Spawns()
    await launch_background(context(runtime, EpochHooks(spawn=spawn)))
    assert not any(key.endswith(":depth") for key in spawn.keys)


async def test_stale_epics_are_refreshed_oldest_first(runtime: AgentRuntime, database: Database, rules: Rules, world: AgentWorld) -> None:
    await tune(database, rules, "agents", "epic_refresh_epochs", 3)
    async with database.write() as session:
        creator = await CosmosRepository(session).require_creator()
        creator.epic = Epic(title="Old song", epoch=1)
        world.core.son.epic = None
    spawn_none = await stale_epics(context(runtime, epoch=3))
    assert spawn_none == []
    due = await stale_epics(context(runtime, epoch=10))
    assert [item[0] for item in due] == [CREATOR_EPIC_KEY]
    spawn = Spawns()
    await launch_background(context(runtime, EpochHooks(spawn=spawn), epoch=10))
    assert CREATOR_EPIC_KEY in spawn.keys


async def test_stale_epics_disabled_by_zero_threshold(runtime: AgentRuntime, database: Database, rules: Rules, world: AgentWorld) -> None:
    await tune(database, rules, "agents", "epic_refresh_epochs", 0)
    async with database.write() as session:
        (await CosmosRepository(session).require_creator()).epic = Epic(title="Old song", epoch=1)
    assert await stale_epics(context(runtime, epoch=100)) == []


async def test_deferred_worlds_birth_pending_steps_and_skip_when_settled(
    runtime: AgentRuntime, database: Database, world: AgentWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def intuitions(_runtime: AgentRuntime) -> int:
        calls.append("intuitions")
        return 1

    async def births(_runtime: AgentRuntime) -> int:
        calls.append("births")
        return 2

    monkeypatch.setattr(deferred_module, "process_intuitions", intuitions)
    monkeypatch.setattr(deferred_module, "process_deferred_births", births)
    ec = context(runtime)
    await deferred_worlds(ec)
    assert calls == ["intuitions", "births"]
    assert ec.summary["worlds_born"] == 3
    assert await step(database, EpochStepKind.WORLD_BIRTH) is EpochStepStatus.DONE
    await deferred_worlds(context(runtime))
    assert calls == ["intuitions", "births"]


async def test_deferred_worlds_resumes_a_step_left_running(
    runtime: AgentRuntime, database: Database, world: AgentWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def none(_runtime: AgentRuntime) -> int:
        calls.append("run")
        return 0

    monkeypatch.setattr(deferred_module, "process_intuitions", none)
    monkeypatch.setattr(deferred_module, "process_deferred_births", none)
    ec = context(runtime)
    await ec.mark(EpochStepKind.WORLD_BIRTH, EpochStepStatus.RUNNING)
    await deferred_worlds(ec)
    assert calls == ["run", "run"]


async def test_deferred_world_failure_is_recorded(runtime: AgentRuntime, database: Database, world: AgentWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(_runtime: AgentRuntime) -> int:
        raise RuntimeError("no model")

    monkeypatch.setattr(deferred_module, "process_intuitions", boom)
    await deferred_worlds(context(runtime))
    assert await step(database, EpochStepKind.WORLD_BIRTH) is EpochStepStatus.FAILED
    async with database.read() as session:
        assert (await require_run(session, 1)).epoch == 1


async def test_image_autogen_runs_only_when_enabled(runtime: AgentRuntime, database: Database, rules: Rules, world: AgentWorld) -> None:
    ran: list[int] = []

    async def hook() -> None:
        ran.append(1)

    await tune(database, rules, "image_gen", "auto", 0)
    await image_autogen(context(runtime, EpochHooks(image_autogen=hook)))
    assert ran == [] and await step(database, EpochStepKind.IMAGES) is EpochStepStatus.SKIPPED
    await tune(database, rules, "image_gen", "auto", 1)
    await image_autogen(context(runtime, EpochHooks(image_autogen=hook)))
    assert ran == [1] and await step(database, EpochStepKind.IMAGES) is EpochStepStatus.DONE


async def test_image_autogen_failure_is_marked(runtime: AgentRuntime, database: Database, rules: Rules, world: AgentWorld) -> None:
    async def hook() -> None:
        raise RuntimeError("worker down")

    await tune(database, rules, "image_gen", "auto", 1)
    await image_autogen(context(runtime, EpochHooks(image_autogen=hook)))
    assert await step(database, EpochStepKind.IMAGES) is EpochStepStatus.FAILED


async def test_deferred_step_rows_are_untouched_by_a_settled_epoch(runtime: AgentRuntime, database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        session.add(DeferredStepRow(epoch=1, kind=DeferredStepKind.WORLD_BIRTH, status=DeferredStepStatus.DONE, payload={}))
    ec = context(runtime)
    await ec.mark(EpochStepKind.WORLD_BIRTH, EpochStepStatus.DONE)
    await deferred_worlds(ec)
    async with database.read() as session:
        assert await step(database, EpochStepKind.WORLD_BIRTH) is EpochStepStatus.DONE
        assert await session.get(DeferredStepRow, 1) is not None


async def test_missing_content_is_completed_first_and_a_failure_does_not_stop_the_epoch(runtime: AgentRuntime, bus: EventBus, world: AgentWorld) -> None:
    calls: list[int] = []

    async def complete() -> None:
        calls.append(1)

    await complete_missing(context(runtime, EpochHooks(complete_missing=complete)))
    assert calls == [1]

    async def broken() -> None:
        raise RuntimeError("the deepener is down")

    await complete_missing(context(runtime, EpochHooks(complete_missing=broken)))
    errors = [event.payload["text"] for event in bus.replay_after(0) if event.kind is EventKind.SYSTEM_ERROR]
    assert errors == ["Completion: the deepener is down"]


async def test_the_llm_kill_switch_skips_background_work(database: Database, world: AgentWorld) -> None:
    offline = AgentRuntime(database=database, model=FakeModel(enabled=False))
    spawn = Spawns()
    await launch_background(context(offline, EpochHooks(spawn=spawn)))
    assert spawn.keys == []
    assert await step(database, EpochStepKind.BACKGROUND) is None


async def test_stale_epics_wait_for_spare_pool_capacity(runtime: AgentRuntime, database: Database, rules: Rules, world: AgentWorld) -> None:
    await tune(database, rules, "agents", "epic_refresh_epochs", 3)
    async with database.write() as session:
        (await CosmosRepository(session).require_creator()).epic = Epic(title="Old song", epoch=1)
    full = Spawns()
    await launch_background(context(runtime, EpochHooks(spawn=full, spare=lambda: 0), epoch=10))
    assert CREATOR_EPIC_KEY not in full.keys
    async with database.write() as session:
        await session.execute(delete(EpochStepRow))
    idle = Spawns()
    await launch_background(context(runtime, EpochHooks(spawn=idle, spare=lambda: 1), epoch=10))
    assert CREATOR_EPIC_KEY in idle.keys


async def test_the_background_pool_leaves_slots_for_manual_jobs(database: Database, rules: Rules) -> None:
    service = RulesService(database)
    await service.load()
    jobs = JobManager(database, EventBus())
    pool = BackgroundPool(jobs, service)
    agents = service.current.agents
    assert pool.capacity == agents.concurrent_jobs - agents.manual_job_share
    gate = asyncio.Event()

    async def wait() -> None:
        await gate.wait()

    for index in range(pool.capacity):
        assert pool.spawn(f"entity:{index}:depth", wait)
    assert pool.spare() == 0
    assert not pool.spawn("entity:0:depth", wait)
    gate.set()
    await until(lambda: pool.spare() == pool.capacity)
    assert pool.spare() == pool.capacity
    await jobs.shutdown()


async def test_the_background_pool_refuses_content_jobs_during_genesis(database: Database, rules: Rules) -> None:
    service = RulesService(database)
    await service.load()
    jobs = JobManager(database, EventBus())
    pool = BackgroundPool(jobs, service)
    genesis_gate = asyncio.Event()

    async def genesis(_context: object) -> None:
        await genesis_gate.wait()

    async def work() -> None:
        return None

    await jobs.submit(JobKind.GENESIS, genesis, exclusive_group="world")
    assert not pool.spawn("entity:1:depth", work)
    genesis_gate.set()
    await until(lambda: not jobs.kind_running(JobKind.GENESIS))
    assert pool.spawn("entity:1:depth", work)
    await jobs.shutdown()
