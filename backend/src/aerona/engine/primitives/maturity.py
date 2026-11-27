from collections.abc import Iterable, Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import LIFE_STAGE_TRAITS, having
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.life_traits import LifeStageTrait

UNDER_AGE = having(LIFE_STAGE_TRAITS, LifeStageTrait.UNDER_AGE)


def of_age_query() -> ColumnElement[bool]:
    return EntityRow.id.not_in(select(MortalProfileRow.entity_id).where(MortalProfileRow.life_stage.in_(sorted(UNDER_AGE))))


async def under_age(session: AsyncSession, ids: Iterable[int | None]) -> set[int]:
    wanted = sorted({node for node in ids if node is not None})
    if not wanted:
        return set()
    statement = select(MortalProfileRow.entity_id).where(MortalProfileRow.entity_id.in_(wanted), MortalProfileRow.life_stage.in_(sorted(UNDER_AGE)))
    return set(await session.scalars(statement))


async def of_age(session: AsyncSession, node_id: int | None) -> bool:
    return node_id is not None and node_id not in await under_age(session, [node_id])


async def of_age_among(session: AsyncSession, mortals: Sequence[EntityRow]) -> list[EntityRow]:
    young = await under_age(session, [mortal.id for mortal in mortals])
    return [mortal for mortal in mortals if mortal.id not in young]
