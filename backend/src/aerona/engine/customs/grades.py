from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.grade_duties import GRADE_DUTIES
from aerona.catalog.life_traits import AGE_GRADE_TRAITS, having
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow, GradeDutyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import AgeGrade, GradeDuty
from aerona.domain.enums.life_traits import AgeGradeTrait
from aerona.domain.enums.mind import ValueHolder
from aerona.engine.childhood.standing import below_marriage_age
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values

UNWED_GRADES = having(AGE_GRADE_TRAITS, AgeGradeTrait.UNWED_GRADES)


async def grade_of(session: AsyncSession, mortal_id: int) -> AgeGrade | None:
    member = await session.get(AgeSetMemberRow, mortal_id)
    found = await session.get(AgeSetRow, member.age_set_id) if member is not None else None
    return found.grade if found is not None else None


async def too_young_to_wed(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    if await grade_of(session, first.id) in UNWED_GRADES or await grade_of(session, second.id) in UNWED_GRADES:
        return True
    return await below_marriage_age(session, first, second)


async def duty_grade(session: AsyncSession, people_id: int, duty: GradeDuty) -> AgeGrade | None:
    row = await session.get(GradeDutyRow, (people_id, duty))
    return row.grade if row is not None else None


async def grade_ready(session: AsyncSession, people_id: int | None, duty: GradeDuty) -> bool:
    if people_id is None:
        return False
    grade = await duty_grade(session, people_id, duty)
    if grade is None:
        return False
    found = await session.scalar(select(AgeSetRow.id).where(AgeSetRow.people_entity_id == people_id, AgeSetRow.grade == grade).limit(1))
    return found is not None


async def derive_duties(ctx: TickContext, people_id: int) -> int:
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people_id)
    made = 0
    for duty, spec in GRADE_DUTIES.items():
        row = await ctx.session.get(GradeDutyRow, (people_id, duty))
        if row is not None or values.get(spec.axis, 0) < spec.from_value(ctx.rules):
            continue
        ctx.session.add(GradeDutyRow(people_entity_id=people_id, duty=duty, grade=spec.grade, locked=[]))
        made += 1
    return made


DUTIES_FIXUP = "grades.w52"


async def backfill_duties(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, DUTIES_FIXUP) is not None:
        return 0
    made = 0
    for people_id in sorted(set(await ctx.session.scalars(select(AgeSetRow.people_entity_id)))):
        if not held(people_id):
            made += await derive_duties(ctx, people_id)
    ctx.session.add(AppliedFixupRow(key=DUTIES_FIXUP, result={"duties": made}))
    await ctx.session.flush()
    return made
