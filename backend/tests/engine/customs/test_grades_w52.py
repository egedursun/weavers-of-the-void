from aerona.catalog.grade_duties import GRADE_DUTIES
from aerona.db.tables.customs import AgeSetRow, GradeDutyRow
from aerona.domain.enums.customs import AgeGrade, GradeDuty
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.customs.grades import derive_duties, grade_ready
from aerona.engine.mind.book import write_values
from tests.engine.society.factories import Realm, context, people


def test_no_grade_is_martial_by_name() -> None:
    assert not hasattr(AgeGrade, "WARRIORS")
    assert GRADE_DUTIES[GradeDuty.WAR].grade is AgeGrade.YOUNG_ADULTS


async def test_a_martial_people_gives_a_grade_the_duty_of_war_and_a_peaceful_one_gives_none(realm: Realm) -> None:
    warlike, peaceful = await people(realm, "The Shields"), await people(realm, "The Quiet Folk")
    await write_values(realm.session, ValueHolder.CULTURE, warlike.id, {ValueAxis.MARTIAL: 80})
    await write_values(realm.session, ValueHolder.CULTURE, peaceful.id, {ValueAxis.MARTIAL: -60})
    for folk in (warlike, peaceful):
        realm.session.add(AgeSetRow(people_entity_id=folk.id, name="The First Set", grade=AgeGrade.YOUNG_ADULTS, locked=[]))
    ctx = context(realm.session)
    await derive_duties(ctx, warlike.id)
    await derive_duties(ctx, peaceful.id)
    await realm.session.flush()
    assert await realm.session.get(GradeDutyRow, (warlike.id, GradeDuty.WAR)) is not None
    assert await grade_ready(realm.session, warlike.id, GradeDuty.WAR)
    assert not await grade_ready(realm.session, peaceful.id, GradeDuty.WAR)
