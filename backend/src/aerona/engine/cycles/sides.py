from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.random import SeededRandom
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.domain.enums.demography import Sex

PAIRED = {Sex.FEMALE: Sex.MALE, Sex.MALE: Sex.FEMALE}
SIDES = (Sex.FEMALE, Sex.MALE)


def first_sex(system: KinshipSystemRow) -> str:
    return system.first_side.value


def second_sex(system: KinshipSystemRow) -> str:
    return PAIRED.get(system.first_side, Sex.OTHER).value


def drawn_side(people_id: int) -> Sex:
    return SeededRandom.for_epoch(people_id, 0, "first_side").pick(list(SIDES))


async def system_of_people(session: AsyncSession, people_id: int | None) -> KinshipSystemRow | None:
    return await session.get(KinshipSystemRow, people_id) if people_id is not None else None
