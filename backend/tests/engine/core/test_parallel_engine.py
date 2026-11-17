import json
import random
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.write_guard import WRITE_GUARD
from aerona.engine.context import TickContext
from aerona.engine.parallel.effects import Effect, EffectKind, commit, merged
from aerona.engine.parallel.pool import compute_shards
from aerona.engine.pipeline import TICK_ORDER, current_environment, run_phases
from aerona.engine.startup import dwellings_built_in, kinds_built_in
from aerona.engine.stats import within_budget
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld
from tests.engine.integration.factories import seed_rich_cosmos

BUDGET = Path(__file__).resolve().parents[4] / "docs" / "work" / "engine-budget.json"


def square_sum(numbers: tuple[int, ...]) -> int:
    return sum(number * number for number in numbers)


def test_a_shard_kernel_gives_the_same_results_with_one_worker_or_many() -> None:
    shards = [tuple(range(start, start + 50)) for start in range(0, 400, 50)]
    assert compute_shards(square_sum, shards, 1) == compute_shards(square_sum, shards, 3)


def test_effects_merge_in_one_canonical_order_whatever_order_the_shards_return() -> None:
    effects = [Effect((world,), entity_id, sequence, EffectKind.SHIFT_STAT, "prosperity", 1) for world in (2, 1) for entity_id in (9, 4) for sequence in (1, 0)]
    shuffled = effects[:]
    random.Random(7).shuffle(shuffled)
    assert merged([effects]) == merged([shuffled[:3], shuffled[3:]])
    assert [(effect.shard, effect.entity_id, effect.sequence) for effect in merged([shuffled])][:2] == [((1,), 4, 0), ((1,), 4, 1)]


async def test_effects_commit_serially_and_spare_held_nodes(session: AsyncSession, world: CoreWorld) -> None:
    town = world.regions[0]
    kept = world.regions[1]
    applied = await commit(
        session,
        merged(
            [
                [
                    Effect((world.world.id,), town.id, 0, EffectKind.SET_COLUMN, "map_x", 0.25, "entities"),
                    Effect((world.world.id,), kept.id, 0, EffectKind.SET_COLUMN, "map_x", 0.75, "entities"),
                ]
            ]
        ),
    )
    assert applied == 2 and town.map_x == 0.25
    token = WRITE_GUARD.set(lambda node_id, _key: node_id == kept.id)
    try:
        held_count = await commit(session, [Effect((world.world.id,), kept.id, 0, EffectKind.SET_COLUMN, "map_x", 0.5, "entities")])
    finally:
        WRITE_GUARD.reset(token)
    assert held_count == 0 and kept.map_x == 0.75


async def test_a_tick_of_the_reference_world_stays_within_its_statement_budget(database: Database) -> None:
    async with database.write() as session:
        await seed_rich_cosmos(session)
    prepared = await current_environment(database, rules=Rules())
    async with database.write() as session:
        await dwellings_built_in(TickContext(prepared, session, "startup.built_in_dwellings"))
        await kinds_built_in(TickContext(prepared, session, "startup.built_in_kinds"))
    statements = 0

    def counted(*_: object) -> None:
        nonlocal statements
        statements += 1

    event.listen(database.engine.sync_engine, "before_cursor_execute", counted)
    try:
        environment = await current_environment(database, rules=Rules())
        await run_phases(environment, database, TICK_ORDER)
    finally:
        event.remove(database.engine.sync_engine, "before_cursor_execute", counted)
    budget = json.loads(BUDGET.read_text(encoding="utf-8"))["tick_statements"]
    assert within_budget(Rules(), statements, budget), f"a tick of the reference world ran {statements} statements against a budget of {budget}"
