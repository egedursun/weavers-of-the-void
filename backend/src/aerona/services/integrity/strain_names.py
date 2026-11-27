import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.engine.disease.emergence import FIRST_STRAIN, strain_name

STACKED = re.compile(r"(?:, strain \d+(?: [IVXLC]+)?){2,}$|, strain \d+ [IVXLC]+$")
FIRST = re.compile(r", strain (\d+)")


def strain_base(name: str) -> tuple[str, int]:
    found = FIRST.search(name)
    return (name[: found.start()], int(found.group(1))) if found is not None else (name, FIRST_STRAIN)


async def stacked_strains(session: AsyncSession) -> list[int]:
    rows = await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.entity_type == EntityType.DISEASE).order_by(EntityRow.id))
    return [disease_id for disease_id, name in rows if STACKED.search(name) is not None and not held(disease_id)]


async def name_strain_once(session: AsyncSession, disease_id: int) -> None:
    row = await session.get(EntityRow, disease_id)
    if row is not None and STACKED.search(row.name) is not None:
        names = NameRepository(session)
        base, number = strain_base(row.name)
        await names.rename(disease_id, await strain_name(names, base, number, ignore_node_id=disease_id), free=True)
