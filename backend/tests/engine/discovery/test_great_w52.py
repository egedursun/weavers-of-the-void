from aerona.catalog.discovery import FIELDS
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.discovery import GreatPersonRow
from aerona.domain.enums.discovery import GreatField
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.engine.lore.great_people import DEEDS, GREAT_FIXUP, retitle_scholars
from aerona.engine.mind.book import set_skill
from aerona.rules.model import keyed
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, settlement


def test_eleven_fields_each_with_a_deed_and_a_weight() -> None:
    assert len(GreatField) == 11 and set(FIELDS) == set(GreatField)
    assert all(field in DEEDS for field in GreatField)
    assert all(keyed(Rules().great_persons, field.value, "weight") == 50 for field in GreatField)


async def test_great_scholars_of_medicine_and_law_take_the_new_fields(realm: Realm) -> None:
    town = await settlement(realm, "Bookham")
    doctor = await mortal(realm, "Doctor", location_id=town.id)
    judge = await mortal(realm, "Judge", location_id=town.id)
    sage = await mortal(realm, "Sage", location_id=town.id)
    await set_skill(realm.session, doctor.id, SkillKind.MEDICINE, 80, epoch=1, source=SkillSource.PRACTICE)
    await set_skill(realm.session, judge.id, SkillKind.LAW, 70, epoch=1, source=SkillSource.PRACTICE)
    await set_skill(realm.session, sage.id, SkillKind.LORE, 90, epoch=1, source=SkillSource.PRACTICE)
    for person in (doctor, judge, sage):
        realm.session.add(
            GreatPersonRow(mortal_entity_id=person.id, field=GreatField.SCHOLAR, holder_entity_id=town.id, promoted_epoch=1, deed_done=True, locked=[])
        )
    await realm.session.flush()
    ctx = context(realm.session)
    assert await retitle_scholars(ctx) == 2
    fields = {row.mortal_entity_id: row.field for row in [await realm.session.get_one(GreatPersonRow, person.id) for person in (doctor, judge, sage)]}
    assert fields == {doctor.id: GreatField.HEALER, judge.id: GreatField.LAWGIVER, sage.id: GreatField.SCHOLAR}
    assert await realm.session.get(AppliedFixupRow, GREAT_FIXUP) is not None
    assert await retitle_scholars(ctx) == 0
