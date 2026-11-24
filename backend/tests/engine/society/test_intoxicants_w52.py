from aerona.catalog.life.customs import PACKAGES
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import Intoxicant, IntoxicantUse
from aerona.engine.customs.intoxicants import within_reach
from tests.engine.society.factories import Realm, context, people


def test_nine_intoxicants_seven_uses_each_with_its_dependence() -> None:
    assert len(Intoxicant) == 11 and len(IntoxicantUse) == 9
    assert set(PACKAGES) == set(Intoxicant)


async def test_a_made_substance_needs_its_technique(realm: Realm) -> None:
    folk = await people(realm, "Makers")
    ctx = context(realm.session)
    assert not await within_reach(ctx, folk.id, Intoxicant.SYNTHETIC)
    assert await within_reach(ctx, folk.id, Intoxicant.WINE)
    realm.session.add(HolderTechniqueRow(holder_entity_id=folk.id, technique=Technique.INDUSTRIAL_CHEMISTRY))
    await realm.session.flush()
    assert await within_reach(ctx, folk.id, Intoxicant.SYNTHETIC)
    assert not await within_reach(ctx, folk.id, Intoxicant.ANIMAL_DERIVED)
