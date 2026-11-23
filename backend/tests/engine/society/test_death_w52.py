from aerona.catalog.death_causes import DEATH_CAUSES, death_cause_of
from aerona.db.tables.body import InjuryRow
from aerona.domain.enums.body import BodyPart, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.mortal import DeathCause
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.mortal.readings import mend_death_cause, mismatched_deaths
from tests.engine.society.factories import Realm, mortal


def test_twenty_nine_causes_and_drowning_comes_from_lack_of_air() -> None:
    assert len(DEATH_CAUSES) == len(DeathCause) == 29
    assert death_cause_of(HarmCause.DISASTER, DamageType.ASPHYXIA) is DeathCause.DROWNING
    assert death_cause_of(HarmCause.BATTLE) is DeathCause.BATTLE
    assert DEATH_CAUSES[DeathCause.BATTLE].violent and not DEATH_CAUSES[DeathCause.DROWNING].violent


async def test_a_death_cause_is_mended_to_match_its_last_wound(realm: Realm) -> None:
    sailor = await mortal(realm, "Sailor")
    profile, _ = await ensure_profile(realm.session, sailor.id, 3)
    profile.cause_of_death = DeathCause.ACCIDENT
    realm.session.add(
        InjuryRow(
            bearer_node_id=sailor.id,
            part=BodyPart.LUNGS,
            kind=InjuryKind.DESTROYED,
            damage_type=DamageType.ASPHYXIA,
            severity=5,
            state=InjuryState.LETHAL,
            function_loss=100,
            cause_kind=HarmCause.ACCIDENT,
            epoch=3,
            visible=False,
        )
    )
    await realm.session.flush()
    assert sailor.id in await mismatched_deaths(realm.session)
    await mend_death_cause(realm.session, sailor.id)
    assert profile.cause_of_death is DeathCause.DROWNING
