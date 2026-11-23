from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.engine.context import TickContext
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules


async def name_for_season(session: AsyncSession, rules: Rules, world: WorldRow, position: int) -> str:
    named = await Namer(session, rules).for_world(world.id, seed_of("season", world.id, position), NameKind.SEASON)
    return named or f"Season {position + 1}"


async def season_name(ctx: TickContext, world: WorldRow, position: int) -> str:
    return await name_for_season(ctx.session, ctx.rules, world, position)
