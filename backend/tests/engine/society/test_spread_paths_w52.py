from sqlalchemy import select

from aerona.catalog.spread_paths import CONTACT_PATHS, SPREAD_PATHS
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import SpreadPath
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.control import DiseaseDesign, create_disease
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.disease.paths import Carry, PathTally, carry, travels_by
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, tuned

CERTAIN = tuned(spread={"wildlife_pct": 100, "migration_pct": 100, "gathering_pct": 100, "waterway_pct": 100})


async def outbreak_of(realm: Realm, route: str) -> tuple[DiseaseBook, OutbreakRow]:
    ctx = context(realm.session, CERTAIN)
    disease = await create_disease(
        ctx, realm.region.id, DiseaseDesign(name=None, values={"primary_route": route, "target_functions": ["vital"]}, hold=True), son_id=None
    )
    book = await DiseaseBook.load(realm.session, CERTAIN, 3)
    row = await open_outbreak(ctx, book, book.diseases[disease.id], realm.region.id, path=SpreadPath.ORIGIN, severity=60)
    return book, row


def test_eleven_paths_each_with_a_carrier_and_the_contact_paths_read_from_the_catalogue() -> None:
    assert len(SPREAD_PATHS) == len(SpreadPath) == 13
    assert {
        SpreadPath.ROUTE,
        SpreadPath.ARMY,
        SpreadPath.JOURNEY,
        SpreadPath.SIEGE,
        SpreadPath.MIGRATION,
        SpreadPath.GATHERING,
        SpreadPath.LIVESTOCK,
    } == CONTACT_PATHS
    assert all(spec.carrier for spec in SPREAD_PATHS.values())
    assert SPREAD_PATHS[SpreadPath.WATERWAY].routes == {Transmission.WATER}


async def test_a_river_carries_only_a_water_borne_sickness_downstream(realm: Realm) -> None:
    book, airborne = await outbreak_of(realm, "inhalation")
    assert not travels_by(book, airborne, SpreadPath.WATERWAY)
    book, waterborne = await outbreak_of(realm, "water")
    assert travels_by(book, waterborne, SpreadPath.WATERWAY)
    tally = PathTally()
    await carry(context(realm.session, CERTAIN), book, Carry(waterborne, realm.far_region.id, SpreadPath.WATERWAY, "test"), tally)
    await realm.session.flush()
    carried = await realm.session.scalar(select(OutbreakRow).where(OutbreakRow.region_entity_id == realm.far_region.id))
    assert carried is not None and carried.path is SpreadPath.WATERWAY and carried.severity == 30
    assert tally.carried == {SpreadPath.WATERWAY: 1}
    assert "disease.spread" in set(await realm.session.scalars(select(IncidentRow.kind)))


async def test_a_path_never_carries_where_its_chance_is_nil(realm: Realm) -> None:
    book, waterborne = await outbreak_of(realm, "water")
    never = tuned(Rules(), spread={"waterway_pct": 0})
    await carry(context(realm.session, never), book, Carry(waterborne, realm.far_region.id, SpreadPath.WATERWAY, "never"), PathTally())
    assert await realm.session.scalar(select(OutbreakRow).where(OutbreakRow.region_entity_id == realm.far_region.id)) is None
