from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.minds import MindLawRow
from aerona.domain.enums.minds import MadeMindsLaw, MadeMindSouls, SoulContinuity
from aerona.engine.minds.profiles import world_of


def default_law(world_id: int) -> MindLawRow:
    return MindLawRow(
        world_id=world_id,
        made_minds=MadeMindsLaw.WILL_MAY_EMERGE,
        made_mind_souls=MadeMindSouls.GRANTED,
        soul_continuity=SoulContinuity.STAYS_WITH_FIRST,
        locked=[],
    )


async def soul_law(session: AsyncSession, node_id: int) -> MindLawRow:
    world = await world_of(session, node_id)
    row = await session.get(MindLawRow, world) if world is not None else None
    return row if row is not None else default_law(world or 0)
