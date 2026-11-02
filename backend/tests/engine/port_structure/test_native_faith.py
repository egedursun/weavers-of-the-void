from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.society import ReverenceRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.phases.native_faith import holds_god, native_faith, syncretize
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules


async def test_open_natives_turn_to_the_old_god_and_feed_it(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(native_faith={"turn_chance": 100, "syncretic_share": 100, "return_chance": 0}, faith={"default_piety": 50})
    ctx = await manual_context(session, "test", rules)
    god = await add_foreign_god(session, rules, ctx.rng(), ctx.epoch, NewForeignGod("Ormuhl", world.world.id, (Domain.EARTH, None), power=5))
    world.people.stats = world.people.stats.model_copy(update={"piety": 10})
    await native_faith(ctx)
    assert await holds_god(session, world.people.id, god.id)
    assert await session.get(ReverenceRow, (world.people.id, god.id)) is not None
    assert await has_flag(session, world.people.id, EntityFlag.SYNCRETIC)
    assert god.power > 5


async def test_creator_weaves_a_faith_with_an_old_god(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    ctx = await manual_context(session, "test", rules)
    god = await add_foreign_god(session, rules, ctx.rng(), ctx.epoch, NewForeignGod("Ilvane", world.world.id, (Domain.SEA, None), power=40))
    await syncretize(session, rules, world.people.id, god.id)
    assert await session.get(ReverenceRow, (world.people.id, god.id)) is not None
