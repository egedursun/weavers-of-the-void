from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.domain import Domain
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.primitives.manual import manual_context
from aerona.services.search import SearchIndex, find_path, search
from tests.engine.core.factories import CoreWorld, tuned_rules

RULES = tuned_rules()


async def test_a_son_a_world_and_an_old_god_are_found_by_name(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "search", RULES)
    god = await add_foreign_god(session, RULES, ctx.rng(), ctx.epoch, NewForeignGod("Ormuhl", world.world.id, (Domain.EARTH, None), power=5))
    index = SearchIndex()
    sons = await search(session, RULES, index, world.son.name, "v1")
    assert any(hit.category.value == "son" and hit.id == world.son.id and hit.title == world.son.name for hit in sons)
    olds = await search(session, RULES, index, "Ormuhl", "v1")
    assert any(hit.id == god.id and hit.title == "Ormuhl" for hit in olds)
    assert await search(session, RULES, index, "x", "v1") == []
    assert index.version == "v1"


async def test_a_path_runs_from_an_old_god_through_its_world(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "search", RULES)
    god = await add_foreign_god(session, RULES, ctx.rng(), ctx.epoch, NewForeignGod("Ormuhl", world.world.id, (Domain.EARTH, None), power=5))
    found = await find_path(session, god.id, world.world.id)
    assert found.found and found.steps and found.steps[0].source == god.id
