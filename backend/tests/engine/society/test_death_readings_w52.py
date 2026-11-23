from sqlalchemy import select

import aerona.engine.mortal.death as death_module
from aerona.db.tables.mortal import DeathReadingRow
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mortal import DeathCause, DeathReading
from aerona.engine.mortal.readings import derive_reading, reading_for, seed_people
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, people

RULES = Rules()


def test_the_fixed_sets_are_gone_and_readings_vary_by_culture() -> None:
    assert not hasattr(death_module, "GLORIOUS_DEATHS")
    assert not hasattr(death_module, "SHAMEFUL_DEATHS")
    martial = {ValueAxis.MARTIAL: 90}
    peaceful = {ValueAxis.MARTIAL: -90}
    assert derive_reading(RULES, martial, DeathCause.BATTLE) is DeathReading.GLORIOUS
    assert derive_reading(RULES, peaceful, DeathCause.BATTLE) is not DeathReading.GLORIOUS
    uneasy = {ValueAxis.SUPERSTITION: 90}
    assert derive_reading(RULES, uneasy, DeathCause.CURSE) is DeathReading.CURSED
    assert derive_reading(RULES, {}, DeathCause.CURSE) is DeathReading.PLAIN


async def test_every_people_reads_every_death_and_a_mortal_dies_by_their_reading(realm: Realm) -> None:
    folk = await people(realm, "Folk")
    made = await seed_people(context(realm.session), folk.id)
    assert made == len(DeathCause)
    row = await realm.session.get(DeathReadingRow, (folk.id, DeathCause.DROWNING))
    assert row is not None
    row.reading = DeathReading.CURSED
    sailor = await mortal(realm, "Sailor")
    assert await reading_for(realm.session, RULES, sailor, DeathCause.DROWNING) in set(DeathReading)
    assert len(list(await realm.session.scalars(select(DeathReadingRow).where(DeathReadingRow.people_entity_id == folk.id)))) == len(DeathCause)
