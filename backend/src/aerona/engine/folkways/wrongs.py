from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.justice import CrimeCaseRow
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.mortal import CrimeKind


async def wrongly_condemned(session: AsyncSession, mortal_id: int) -> bool:
    found = await session.scalar(
        select(CrimeCaseRow.id)
        .where(
            CrimeCaseRow.accused_entity_id == mortal_id,
            CrimeCaseRow.crime == CrimeKind.WITCHCRAFT,
            CrimeCaseRow.wrongful.is_(True),
            CrimeCaseRow.verdict == Verdict.GUILTY,
        )
        .limit(1)
    )
    return found is not None
