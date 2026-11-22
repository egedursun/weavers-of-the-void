from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import AGE_GRADE_TRAITS, having
from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.customs import AgeGrade
from aerona.domain.enums.life_traits import AgeGradeTrait
from aerona.engine.childhood.standing import below_marriage_age

UNWED_GRADES = having(AGE_GRADE_TRAITS, AgeGradeTrait.UNWED_GRADES)


async def grade_of(session: AsyncSession, mortal_id: int) -> AgeGrade | None:
    member = await session.get(AgeSetMemberRow, mortal_id)
    found = await session.get(AgeSetRow, member.age_set_id) if member is not None else None
    return found.grade if found is not None else None


async def too_young_to_wed(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    if await grade_of(session, first.id) in UNWED_GRADES or await grade_of(session, second.id) in UNWED_GRADES:
        return True
    return await below_marriage_age(session, first, second)


async def warriors_ready(session: AsyncSession, people_id: int | None) -> bool:
    if people_id is None:
        return False
    found = await session.scalar(select(AgeSetRow.id).where(AgeSetRow.people_entity_id == people_id, AgeSetRow.grade == AgeGrade.WARRIORS).limit(1))
    return found is not None
