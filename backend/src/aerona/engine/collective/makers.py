from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.engine.body.customs import people_of
from aerona.engine.renown.currencies import realm_of_community


async def makers_of(session: AsyncSession, owner: EntityRow) -> list[int]:
    people = await people_of(session, owner)
    candidates = (owner.id, await realm_of_community(session, owner.id), people.id if people is not None else None)
    return list(dict.fromkeys(item for item in candidates if item is not None))
