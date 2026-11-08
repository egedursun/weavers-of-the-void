from sqlalchemy import select

from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.disease.stigma import COLONY, expel_sick
from aerona.engine.mind.book import write_values
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, context, link, people, settlement
from tests.engine.society.test_disease_depth import book_of, forge


async def stricken(realm: Realm, purity: int) -> tuple[EntityRow, EntityRow]:
    disease = await forge(realm)
    profile = await realm.session.get(DiseaseProfileRow, disease.id)
    assert profile is not None
    profile.stigma = 90
    town = await settlement(realm, "Cleanmere", population=20000)
    folk = await people(realm, "Clean Folk")
    await link(realm.session, town.id, folk.id, BondKind.DESCENDS_FROM)
    await write_values(realm.session, ValueHolder.CULTURE, folk.id, {ValueAxis.PURITY: purity})
    outbreaks = list(await realm.session.scalars(select(OutbreakRow).where(OutbreakRow.disease_entity_id == disease.id)))
    if not outbreaks:
        realm.session.add(
            OutbreakRow(
                disease_entity_id=disease.id,
                region_entity_id=realm.region.id,
                path=SpreadPath.ORIGIN,
                status=OutbreakStatus.ACTIVE,
                severity=40,
                started_epoch=1,
            )
        )
    for row in await realm.session.scalars(select(OutbreakRow).where(OutbreakRow.disease_entity_id == disease.id)):
        row.infected = 20000
    await realm.session.flush()
    return disease, town


async def colonies(realm: Realm) -> list[EntityRow]:
    return list(await realm.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.subtype == COLONY)))


async def test_a_purity_minded_town_sends_its_sick_to_a_colony_and_reuses_it(realm: Realm) -> None:
    disease, town = await stricken(realm, purity=90)
    moved = await expel_sick(context(realm.session), await book_of(realm))
    [colony] = await colonies(realm)
    assert moved > 0 and stat(town, "population") == 20000 - moved and stat(colony, "population") == moved
    assert disease.name in (colony.description or "")
    again = await expel_sick(context(realm.session), await book_of(realm))
    assert again > 0 and len(await colonies(realm)) == 1


async def test_a_town_that_does_not_fear_impurity_or_is_held_keeps_its_sick(realm: Realm) -> None:
    _, town = await stricken(realm, purity=0)
    assert await expel_sick(context(realm.session), await book_of(realm)) == 0
    await write_values(
        realm.session,
        ValueHolder.CULTURE,
        (await realm.session.scalars(select(EntityRow.id).where(EntityRow.name == "Clean Folk"))).one(),
        {ValueAxis.PURITY: 90},
    )
    token = HELD_SCOPE.set(HeldScope(None, frozenset({town.id})))
    try:
        assert await expel_sick(context(realm.session), await book_of(realm)) == 0
    finally:
        HELD_SCOPE.reset(token)
    assert await colonies(realm) == []
