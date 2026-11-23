from aerona.catalog.life.crafts import AID_NEEDS, FROM_SKILL
from aerona.db.tables.crafts import AssistiveAidRow
from aerona.domain.enums.crafts import AssistiveAid
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.mind import SkillKind
from aerona.engine.crafts.aiding import lens_in
from tests.engine.society.factories import Realm, mortal, settlement


def test_six_aids_and_the_microscope_needs_its_technique() -> None:
    assert len(AssistiveAid) == 6 and set(AID_NEEDS) == set(AssistiveAid)
    assert AID_NEEDS[AssistiveAid.MICROSCOPE] == (Technique.EMPIRICISM,) and FROM_SKILL[SkillKind.MEDICINE] is AssistiveAid.MICROSCOPE


async def test_a_healer_with_a_microscope_lets_the_town_see_agents(realm: Realm) -> None:
    town = await settlement(realm, "Lens")
    healer = await mortal(realm, "Iria", location_id=town.id)
    assert not await lens_in(realm.session, town.id)
    realm.session.add(AssistiveAidRow(holder_node_id=healer.id, kind=AssistiveAid.MICROSCOPE, since_epoch=1, locked=[]))
    await realm.session.flush()
    assert await lens_in(realm.session, town.id)
