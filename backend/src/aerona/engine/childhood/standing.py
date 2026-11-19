from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.childhood import ChildStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.stats import stat_or


async def standing_of(session: AsyncSession, entity: EntityRow) -> ChildStandingRow | None:
    folk = await people_of(session, entity)
    return await session.get(ChildStandingRow, folk.id) if folk is not None else None


def age_of(entity: EntityRow) -> int:
    return stat_or(entity, "age", 0)


async def below_responsibility(session: AsyncSession, entity: EntityRow) -> ChildStandingRow | None:
    standing = await standing_of(session, entity)
    return standing if standing is not None and age_of(entity) < standing.responsibility_age else None


async def below_marriage_age(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    for entity in (first, second):
        standing = await standing_of(session, entity)
        if standing is not None and age_of(entity) < standing.marriage_age:
            return True
    return False


def crossed(entity: EntityRow, age: int, span: int) -> bool:
    now = age_of(entity)
    return now - span < age <= now
