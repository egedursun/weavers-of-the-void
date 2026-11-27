from collections.abc import Collection

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.engine.context import TickContext
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

NAME_TRIES = 8


async def name_for_season(session: AsyncSession, rules: Rules, world: WorldRow, position: int, taken: Collection[str] = ()) -> str:
    namer = Namer(session, rules)
    for attempt in range(NAME_TRIES):
        named = await namer.for_world(world.id, seed_of("season", world.id, position, *([attempt] if attempt else [])), NameKind.SEASON)
        if named and named not in taken:
            return named
    return f"Season {position + 1}"


async def season_name(ctx: TickContext, world: WorldRow, position: int, taken: Collection[str] = ()) -> str:
    return await name_for_season(ctx.session, ctx.rules, world, position, taken)
