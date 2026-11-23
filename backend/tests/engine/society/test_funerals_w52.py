from sqlalchemy import select

from aerona.catalog.death_shapes import RITE_TREATMENTS
from aerona.catalog.peoples import FUNERALS
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.couplings import CarrionRest
from aerona.domain.enums.demography import FuneralCustom, InheritanceCustom, MartialStyle
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.death_work.handling import keep_custom
from tests.engine.society.factories import Realm, context, mortal, people, settlement, tuned


def test_twelve_customs_and_the_two_new_ones_act_on_the_body() -> None:
    assert len(FUNERALS) == len(FuneralCustom) == 13
    assert FUNERALS[FuneralCustom.MUMMIFICATION].preserves and FUNERALS[FuneralCustom.MUMMIFICATION].carrion is CarrionRest.MUMMIFIED
    assert FUNERALS[FuneralCustom.SECONDARY_BURIAL].second_rite
    assert set(RITE_TREATMENTS) == set(FuneralCustom)


async def test_a_second_burial_gathers_last_epochs_dead_and_binds_the_people(realm: Realm) -> None:
    folk = await people(realm, "Folk")
    town = await settlement(realm, "Town")
    culture = await realm.session.get(PeopleCultureRow, folk.id) or PeopleCultureRow(
        people_entity_id=folk.id,
        cohesion=50,
        literacy=20,
        urbanisation=30,
        martial_style=next(iter(MartialStyle)),
        inheritance=next(iter(InheritanceCustom)),
        locked=[],
    )
    realm.session.add(culture)
    culture.funeral_rite = FuneralCustom.SECONDARY_BURIAL
    before = culture.cohesion
    dead = await mortal(realm, "Elder", location_id=town.id)
    dead.status, dead.end_epoch = EntityStatus.DEAD, 2
    await realm.session.flush()
    await keep_custom(context(realm.session, tuned(funerals={"secondary_rite_years": 3}), epoch=3), folk, culture, [town.id], 1)
    kinds = set(await realm.session.scalars(select(IncidentRow.kind)))
    assert "death.funeral" in kinds
    assert "death.second_rite" in kinds
    assert culture.cohesion > before
