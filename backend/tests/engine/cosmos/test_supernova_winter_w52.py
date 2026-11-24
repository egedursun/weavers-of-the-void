from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ages import IrregularSeasonRow
from aerona.domain.enums.ages import SeasonCause, SeasonSpell
from aerona.engine.context import TickContext
from aerona.engine.cosmos.remnants import after_supernova
from tests.engine.cosmos.factories import Cosmos


async def test_a_supernova_brings_a_long_winter_to_the_worlds_its_star_lit(session: AsyncSession, ctx: TickContext, cosmos: Cosmos) -> None:
    await after_supernova(ctx, cosmos.star)
    spells = list(await session.scalars(select(IrregularSeasonRow).where(IrregularSeasonRow.world_id == cosmos.home.id)))
    assert [(row.cause, row.spell, row.source_star_id) for row in spells] == [(SeasonCause.STELLAR, SeasonSpell.WINTER, cosmos.star.id)]
    assert spells[0].severity == ctx.rules.long_seasons.supernova_severity
    await after_supernova(ctx, cosmos.star)
    assert len(list(await session.scalars(select(IrregularSeasonRow).where(IrregularSeasonRow.world_id == cosmos.home.id)))) == 1
