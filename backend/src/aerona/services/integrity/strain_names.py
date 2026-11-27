import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType

STACKED = re.compile(r"(?:, strain \d+){2,}$")
LAST = re.compile(r", strain \d+$")


def once_named(name: str) -> str:
    found = STACKED.search(name)
    if found is None:
        return name
    last = LAST.search(found.group(0))
    return name[: found.start()] + (last.group(0) if last is not None else "")


async def stacked_strains(session: AsyncSession) -> list[int]:
    rows = await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.entity_type == EntityType.DISEASE).order_by(EntityRow.id))
    return [disease_id for disease_id, name in rows if STACKED.search(name) is not None and not held(disease_id)]


async def name_strain_once(session: AsyncSession, disease_id: int) -> None:
    row = await session.get(EntityRow, disease_id)
    if row is not None and STACKED.search(row.name) is not None:
        await NameRepository(session).rename(disease_id, once_named(row.name), free=True)
