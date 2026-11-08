from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.society import ReverenceRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.domain import Domain
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.phases.native_faith import holds_god, native_faith, syncretize
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, tuned_rules

TURNING = tuned_rules(native_faith={"turn_chance": 100, "syncretic_share": 0, "return_chance": 0}, faith={"default_piety": 50})
RETURNING = tuned_rules(native_faith={"turn_chance": 0, "return_chance": 100})


async def run_holding(session: AsyncSession, rules: object, held: int) -> None:
    ctx = await manual_context(session, "test", rules)
    token = HELD_SCOPE.set(HeldScope(None, frozenset({held})))
    try:
        await native_faith(ctx)
    finally:
        HELD_SCOPE.reset(token)


async def test_a_held_people_never_turns_to_an_old_god(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", TURNING)
    god = await add_foreign_god(session, TURNING, ctx.rng(), ctx.epoch, NewForeignGod("Ormuhl", world.world.id, (Domain.EARTH, None), power=5))
    world.people.stats = world.people.stats.model_copy(update={"piety": 10})
    await run_holding(session, TURNING, world.people.id)
    assert not await holds_god(session, world.people.id, god.id)


async def test_a_held_believer_never_returns_to_the_pantheon(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", RETURNING)
    god = await add_foreign_god(session, RETURNING, ctx.rng(), ctx.epoch, NewForeignGod("Ilvane", world.world.id, (Domain.SEA, None), power=40))
    await syncretize(session, RETURNING, world.people.id, god.id)
    await run_holding(session, RETURNING, world.people.id)
    assert await session.get(ReverenceRow, (world.people.id, god.id)) is not None


async def test_a_free_believer_returns_to_the_pantheon(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", RETURNING)
    god = await add_foreign_god(session, RETURNING, ctx.rng(), ctx.epoch, NewForeignGod("Ilvane", world.world.id, (Domain.SEA, None), power=40))
    await syncretize(session, RETURNING, world.people.id, god.id)
    await native_faith(ctx)
    assert await session.get(ReverenceRow, (world.people.id, god.id)) is None
