from sqlalchemy import select

from aerona.catalog.genetics import DWELLINGS
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.households import DwellingRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mind import Attribute
from aerona.domain.enums.urban import HousingLevel
from aerona.engine.demography.peoples import kin_from
from aerona.engine.genetics.life import raise_child
from aerona.engine.households.dwelling_kinds import dwelling_of_people, ensure_built_in_dwellings
from aerona.engine.households.formation import found_household
from aerona.engine.mind.split import attributes_of
from tests.engine.society.factories import Realm, context, mortal, people, settlement


async def test_every_built_in_dwelling_stands_on_a_step_of_the_housing_ladder(realm: Realm) -> None:
    await ensure_built_in_dwellings(realm.session)
    assert await ensure_built_in_dwellings(realm.session) == 0
    rows = {row.built_in_key: row for row in await realm.session.scalars(select(DwellingKindRow))}
    assert {key: row.category for key, row in rows.items()} == {key: spec.level for key, spec in DWELLINGS.items()}
    assert rows["tent"].mobile == 1 and rows["palace"].category is HousingLevel.MANOR and all(row.built_in for row in rows.values())


async def test_a_people_lives_in_its_own_kind_of_home_on_the_same_step(realm: Realm) -> None:
    folk = await people(realm, "Ovar")
    own = DwellingKindRow(name="Reed lodge", category=HousingLevel.HUT, rooms=2, quality=35, upkeep=1, mobile=0, created_epoch=1, locked=[])
    realm.session.add(own)
    await realm.session.flush()
    realm.session.add(KindHoldingRow(concept=KindConcept.DWELLING, kind_id=own.id, holder_node_id=folk.id, stance=KindStance.MAKES, locked=[]))
    await realm.session.flush()
    assert (await dwelling_of_people(realm.session, folk.id, "hut")).id == own.id
    assert (await dwelling_of_people(realm.session, folk.id, "cave")).id == own.id
    assert (await dwelling_of_people(realm.session, folk.id, "manor")).built_in_key == "manor"


async def test_a_new_household_lives_in_a_kind_of_dwelling(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Rookery")
    head = await mortal(realm, "Ivo", location_id=town.id)
    home = await found_household(ctx, head)
    dwelling = await realm.session.scalar(select(DwellingRow).where(DwellingRow.household_id == home.id))
    assert dwelling is not None and dwelling.dwelling_kind_id is not None
    kind = await realm.session.get(DwellingKindRow, dwelling.dwelling_kind_id)
    assert kind is not None and kind.rooms == dwelling.rooms


def test_a_species_diet_reaches_its_people_unchanged() -> None:
    for diet in Diet:
        assert kin_from(None, None, diet, set(), nocturnal=False, height_rank=None).diet is diet


async def test_inborn_potential_grows_into_attributes(realm: Realm) -> None:
    ctx = context(realm.session)
    child = await mortal(realm, "Lio")
    genome = GenomeRow(holder_node_id=child.id, genes={}, potential={Attribute.PATIENCE.value: 70, "perception": 99}, locked=[], likeness={}, marks=[])
    realm.session.add(genome)
    await realm.session.flush()
    await raise_child(ctx, child, genome, 5)
    grown = await attributes_of(realm.session, child.id)
    assert grown[Attribute.PATIENCE] == 75 and "perception" not in {member.value for member in grown}
