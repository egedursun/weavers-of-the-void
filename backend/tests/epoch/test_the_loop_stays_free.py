import asyncio
import time
from collections.abc import Awaitable, Callable
from functools import partial

from sqlalchemy import select

from aerona.agents.runtime import AgentRuntime
from aerona.db.session import Database
from aerona.db.tables.epochs import EpochEnginePhaseRow
from aerona.domain.enums.epoch import EngineStage, EpochPhase
from aerona.engine.context import TickContext
from aerona.engine.phase import Phase
from aerona.engine.pipeline import current_environment
from aerona.epoch.concurrency import StopSignal
from aerona.epoch.context import EpochContext
from aerona.epoch.engine_process import close_engine_process, job_in_process
from aerona.epoch.phases.engine_tick import run_engine_stage
from aerona.epoch.ports import EpochHooks
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.books.render import ScreenLinks
from aerona.services.books.worker import close_books, in_books, order_for, page, warm
from aerona.services.integrity.data_repairs import GRAPH_ENDS_STEP, SCHEMA_STEP
from aerona.services.integrity.maintenance import HISTORY_STEP, Maintained, background_repairs, startup_repairs
from tests.agents.world import AgentWorld

BEAT = 0.02
HEAVY_SECONDS = 1.5
LONGEST_WAIT = 0.3
HEAVY_STEP = "heavy_reckoning"
HEAP_WIDTH = 200
HEAP_ROWS = 20000


async def heaviest_wait(work: Callable[[], Awaitable[object]]) -> float:
    waits: list[float] = []
    running = True

    async def beat() -> None:
        while running:
            began = time.perf_counter()
            await asyncio.sleep(BEAT)
            waits.append(time.perf_counter() - began - BEAT)

    beating = asyncio.create_task(beat())
    try:
        await work()
    finally:
        running = False
        await beating
    return max(waits, default=0.0)


async def reckon(_ctx: TickContext) -> None:
    finish = time.perf_counter() + HEAVY_SECONDS
    total = 0
    while time.perf_counter() < finish:
        total += sum(range(1000))


async def test_a_heavy_engine_step_never_holds_the_server_loop(database: Database, bus: EventBus, runtime: AgentRuntime, world: AgentWorld) -> None:
    published: list[str] = []
    bus.add_listener(lambda event: published.append(str(event.payload.get("phase"))) if event.kind is EventKind.ENGINE_PHASE else None)
    ec = EpochContext(runtime, EpochHooks(), StopSignal(), 1, False)
    environment = await current_environment(database, runtime.publish, phase=EpochPhase.ENGINE)
    wait = await heaviest_wait(lambda: run_engine_stage(ec, EngineStage.TICK, [Phase(HEAVY_STEP, reckon)], environment))
    async with database.read() as session:
        marked = await session.scalar(select(EpochEnginePhaseRow.phase).where(EpochEnginePhaseRow.phase == HEAVY_STEP))
    assert marked == HEAVY_STEP
    assert published == [HEAVY_STEP]
    assert wait < LONGEST_WAIT


async def test_building_the_book_never_holds_the_server_loop(database: Database, rules: Rules, world: AgentWorld) -> None:
    database.work_in_processes = True
    heap = [[object() for _ in range(HEAP_WIDTH)] for _ in range(HEAP_ROWS)]
    try:
        first = await heaviest_wait(lambda: in_books(database, warm, order_for(database, rules, ""), ScreenLinks()))
        database.gate.book_generation += 1
        again = await heaviest_wait(lambda: in_books(database, page, order_for(database, rules, ""), None, None, None, None))
    finally:
        close_books(database)
    assert heap and first < LONGEST_WAIT and again < LONGEST_WAIT


async def test_a_write_made_while_the_engine_runs_waits_its_turn_without_holding_the_loop(database: Database, runtime: AgentRuntime, world: AgentWorld) -> None:
    ec = EpochContext(runtime, EpochHooks(), StopSignal(), 1, False)
    environment = await current_environment(database, runtime.publish, phase=EpochPhase.ENGINE)
    engine = asyncio.create_task(run_engine_stage(ec, EngineStage.TICK, [Phase(HEAVY_STEP, reckon)], environment))
    await asyncio.sleep(HEAVY_SECONDS / 3)

    async def write() -> None:
        async with database.write() as session:
            await session.execute(select(1))

    wait = await heaviest_wait(write)
    await engine
    assert wait < LONGEST_WAIT


async def test_the_engine_in_its_own_process_never_holds_the_server_loop(database: Database, bus: EventBus, runtime: AgentRuntime, world: AgentWorld) -> None:
    database.work_in_processes = True
    published: list[str] = []
    bus.add_listener(lambda event: published.append(str(event.payload.get("phase"))) if event.kind is EventKind.ENGINE_PHASE else None)
    ec = EpochContext(runtime, EpochHooks(), StopSignal(), 1, False)
    environment = await current_environment(database, runtime.publish, phase=EpochPhase.ENGINE)
    try:
        await run_engine_stage(ec, EngineStage.TICK, [Phase(f"{HEAVY_STEP}_warm", reckon)], environment)
        engine = asyncio.create_task(run_engine_stage(ec, EngineStage.TICK, [Phase(HEAVY_STEP, reckon)], environment))
        await asyncio.sleep(HEAVY_SECONDS / 3)

        async def write() -> None:
            async with database.write() as session:
                await session.execute(select(1))

        written = await heaviest_wait(write)
        whole = await heaviest_wait(lambda: engine)
    finally:
        close_engine_process(database)
    async with database.read() as session:
        marked = set(await session.scalars(select(EpochEnginePhaseRow.phase)))
    assert {HEAVY_STEP, f"{HEAVY_STEP}_warm"} <= marked
    assert published == [f"{HEAVY_STEP}_warm", HEAVY_STEP]
    assert HEAVY_STEP in environment.stats.phase_seconds
    assert written < LONGEST_WAIT and whole < LONGEST_WAIT


async def test_the_startup_repairs_run_in_the_engine_process_without_holding_the_server_loop(database: Database, rules: Rules, world: AgentWorld) -> None:
    database.work_in_processes = True
    published: list[EventKind] = []
    try:
        found: list[Maintained] = []

        async def repair() -> None:
            found.append(await job_in_process(database, partial(startup_repairs, rules=rules), lambda kind, _payload: published.append(kind)))
            found.append(await job_in_process(database, partial(background_repairs, rules=rules), lambda kind, _payload: published.append(kind)))

        wait = await heaviest_wait(repair)
    finally:
        close_engine_process(database)
    startup, background = found
    assert "data_repairs" in startup.counters and HISTORY_STEP in startup.counters
    assert set(background.counters) == {GRAPH_ENDS_STEP, SCHEMA_STEP} and not background.failures
    assert wait < LONGEST_WAIT
