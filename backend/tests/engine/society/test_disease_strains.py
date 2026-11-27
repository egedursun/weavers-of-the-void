from sqlalchemy import select

from aerona.catalog import diseases
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.bond import BondKind
from aerona.engine.disease.emergence import name_of, new_strain, plain
from tests.engine.society.factories import Realm, context
from tests.engine.society.test_disease_depth import book_of, forge


async def test_a_disease_breeds_a_strain_that_descends_from_it(realm: Realm) -> None:
    ctx = context(realm.session)
    parent = await forge(realm)
    book = await book_of(realm)
    strain = await new_strain(ctx, book, parent, realm.region)
    assert strain is not None and strain.id != parent.id
    profile = await realm.session.get(DiseaseProfileRow, strain.id)
    assert profile is not None and profile.parent_disease_id == parent.id
    descends = await realm.session.scalar(select(BondRow).where(BondRow.source_node_id == strain.id, BondRow.kind == BondKind.DESCENDS_FROM))
    assert descends is not None and descends.target_node_id == parent.id
    assert strain.name.endswith(", strain 2") and plain(parent.name) in strain.name
    book.profiles.pop(parent.id)
    assert await new_strain(ctx, book, parent, realm.region) is None


def test_a_sickness_is_named_by_how_it_spreads_and_where_it_rose_and_nothing_else() -> None:
    region = EntityRow(name="Fenmark")
    assert name_of(Transmission.INHALATION, region) == "the airborne sickness of Fenmark"
    assert name_of(Transmission.CURSE, None) == "the cursed sickness"
    assert set(diseases.VECTOR_LABELS) == set(Transmission)
    lists = [name for name, value in vars(diseases).items() if name.isupper() and isinstance(value, tuple) and all(isinstance(item, str) for item in value)]
    assert lists == []


async def test_a_strain_never_takes_a_number_an_ended_strain_still_holds(realm: Realm) -> None:
    ctx = context(realm.session)
    parent = await forge(realm)
    book = await book_of(realm)
    first = await new_strain(ctx, book, parent, realm.region)
    assert first is not None
    book.profiles.pop(first.id)
    second = await new_strain(ctx, book, parent, realm.region)
    assert second is not None
    assert second.name == f"{plain(parent.name)}, strain 3"
