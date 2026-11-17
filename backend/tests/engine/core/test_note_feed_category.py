from typing import Any

from aerona.db.session import Database
from aerona.domain.enums.chronicle import FeedCategory
from aerona.engine.context import TickContext
from aerona.engine.phase import Phase
from aerona.engine.pipeline import current_environment, run_tick
from aerona.events.kinds import EventKind
from tests.engine.core.factories import seed_core_world, tell_history


async def war_line(ctx: TickContext) -> None:
    await tell_history(ctx, "Two clans clash over the salt fields.", feed=FeedCategory.WAR)
    await tell_history(ctx, "The wind turns.")


async def test_engine_notes_carry_their_feed_category(database: Database) -> None:
    async with database.write() as session:
        await seed_core_world(session)
    published: list[tuple[EventKind, dict[str, Any]]] = []
    environment = await current_environment(database, lambda kind, payload: published.append((kind, payload)))
    await run_tick(environment, database, phases=[Phase("war_line", war_line)])
    feeds = [payload["feed"] for kind, payload in published if kind is EventKind.ENGINE_NOTE]
    assert feeds == [FeedCategory.WAR.value, None]
