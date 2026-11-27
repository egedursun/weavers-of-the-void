from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.moment import Moment, latest


async def death_floor(session: AsyncSession, nodes: Iterable[int]) -> Moment | None:
    floors: list[Moment] = []
    for node in sorted({node for node in nodes if node is not None}):
        entity = await session.get(EntityRow, node)
        if entity is None or entity.entity_type is not EntityType.MORTAL or entity.status is not EntityStatus.DEAD:
            continue
        year = getattr(entity.stats, "death_year", None)
        if isinstance(year, int):
            floors.append(Moment(year))
    return latest(*floors)
