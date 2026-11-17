import pytest
from sqlalchemy import select

from aerona.core.errors import NotFoundError
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickContext, phase_window
from aerona.engine.phase import Phase
from aerona.engine.pipeline import (
    POST_TRANSITION_ORDER,
    PRE_TRANSITION_ORDER,
    TICK_ORDER,
    TRANSITION_ORDER,
    EnginePhaseError,
    after_transition,
    current_environment,
    describe_order,
    find_phase,
    run_epoch_transition,
    run_named_phase,
    run_tick,
)
from aerona.events.kinds import EventKind
from tests.engine.core.factories import seed_core_world, tell_history


async def chatter(ctx: TickContext) -> None:
    for index in range(4):
        await tell_history(ctx, f"A bell rang {index} times in the hills.", ids=[])


async def broken(ctx: TickContext) -> None:
    await tell_history(ctx, "This line must roll back.")
    raise RuntimeError("boom")


async def seeded(database: Database) -> None:
    async with database.write() as session:
        await seed_core_world(session)


async def test_tick_groups_repeated_lines_as_a_view_and_records_timing(database: Database) -> None:
    await seeded(database)
    events: list[EventKind] = []
    environment = await current_environment(database, lambda kind, payload: events.append(kind))
    result = await run_tick(environment, database, phases=[Phase("chatter", chatter)])
    assert result.fold.folded_groups == 1
    assert "chatter" in result.stats.phase_seconds
    assert EventKind.ENGINE_NOTE in events and EventKind.ENGINE_PHASE in events
    async with database.read() as session:
        rows = list(await session.scalars(select(ChronicleRow).order_by(ChronicleRow.id)))
    rang = [row for row in rows if row.template_key == "player.history"]
    assert len(rang) == 4 and all(row.visible and row.kind is not ChronicleKind.ENGINE_RAW for row in rang)
    assert not any("more events of the same kind" in row.text for row in rows)


async def test_failing_phase_names_the_step_and_rolls_back(database: Database) -> None:
    await seeded(database)
    environment = await current_environment(database)
    with pytest.raises(EnginePhaseError) as caught:
        await run_tick(environment, database, phases=[Phase("broken", broken)])
    assert caught.value.phase == "broken"
    async with database.read() as session:
        assert not list(await session.scalars(select(ChronicleRow).where(ChronicleRow.template_key == "test.broken")))


async def test_disabled_phases_are_skipped_and_named_phases_run(database: Database) -> None:
    await seeded(database)
    environment = await current_environment(database)
    result = await run_tick(environment, database, phases=[Phase("chatter", chatter)], disabled=frozenset({"chatter"}))
    assert "chatter" not in result.stats.phase_seconds
    stats = await run_named_phase(environment, database, "prosperity_reversion")
    assert "prosperity_reversion" in stats.phase_seconds
    with pytest.raises(NotFoundError):
        find_phase("no_such_phase")


async def test_transition_advances_the_epoch(database: Database) -> None:
    await seeded(database)
    environment = await current_environment(database)
    finished: list[int] = []

    async def finalize(session: object) -> None:
        finished.append(environment.epoch)

    await run_tick(environment, database, finalize=finalize)
    assert finished == [environment.epoch]
    await run_epoch_transition(await current_environment(database), database)
    async with database.read() as session:
        cosmos = await session.get(CosmosRow, 1)
    assert cosmos is not None and cosmos.epoch == environment.epoch + 1


def test_order_lists_every_phase_once() -> None:
    names = [phase.name for phase in TICK_ORDER + TRANSITION_ORDER]
    assert len(names) == len(set(names))
    assert names[0] == "dead_bonds_opening"
    assert names[len(TICK_ORDER) - 1] == "incident_threads"
    assert names.index("dead_bonds_closing") < names.index("mind_values")
    assert names[-1] == "advance_epoch"
    assert len(describe_order()) == len(names) + len(POST_TRANSITION_ORDER) + len(PRE_TRANSITION_ORDER)


async def test_tolerant_transition_steps_are_logged_not_fatal(database: Database) -> None:
    await seeded(database)
    environment = await current_environment(database)
    stats = await run_epoch_transition(environment, database, phases=[Phase("broken", broken)], tolerant=frozenset({"broken"}))
    assert stats.counters["broken.failed"] == 1


async def test_tick_lines_fall_inside_the_phase_year_window(database: Database) -> None:
    await seeded(database)
    environment = await current_environment(database, phase=EpochPhase.ENGINE)
    window = phase_window(environment.rules, EpochPhase.ENGINE)
    assert environment.window == window
    await run_tick(environment, database, phases=(Phase("chatter", chatter),))
    async with database.read() as session:
        years = [year for year in await session.scalars(select(ChronicleRow.year)) if year is not None]
    base = epoch_start_year(environment.epoch, environment.rules.time.years_per_epoch)
    assert years and all(base + window.start <= year <= base + window.end for year in years)
    assert after_transition(environment).window == phase_window(environment.rules, EpochPhase.NOT_STARTED)
