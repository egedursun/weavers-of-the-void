from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository, incident_for
from aerona.db.session import Database
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from tests.db.factories import make_entity, make_son, seed_world

YEARS = 50


def test_epoch_years() -> None:
    assert (epoch_start_year(1, YEARS), epoch_end_year(1, YEARS)) == (0, 50)
    assert epoch_start_year(3, YEARS) == 100


async def test_append_keeps_entity_order_and_derives_world(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Fen", EntityType.REGION, world_id=world_id)
    people = await make_entity(session, "Fenfolk", EntityType.PEOPLE, location_id=region.id)
    repository = ChronicleRepository(session)
    written = await repository.append(ChronicleDraft(3, ChronicleKind.WAR, "  The   fen burned. ", (people.id, region.id, people.id, 4242)))
    assert written.row.text == "The fen burned."
    assert written.row.world_id == world_id
    assert written.notification is NotificationCategory.WAR
    assert await repository.entity_ids(written.row.id) == [people.id, region.id]
    assert [row.id for row in await repository.mentioning(region.id, 5)] == [written.row.id]


async def test_engine_raw_lines_are_hidden(session: AsyncSession, world_id: int) -> None:
    repository = ChronicleRepository(session)
    raw = await repository.append(ChronicleDraft(1, ChronicleKind.ENGINE_RAW, "raw note"))
    shown = await repository.append(ChronicleDraft(1, ChronicleKind.WORLD, "a storm", feed_category=FeedCategory.SKY))
    assert not raw.row.visible
    assert shown.notification is NotificationCategory.DISASTER
    assert [row.id for row in await repository.recent(10)] == [shown.row.id]


async def test_son_lines_follow_the_son_world(session: AsyncSession, world_id: int) -> None:
    other = await seed_world(session, name="Thule", star_name="Thule Sun")
    son = await make_son(session, "Varos", other.id)
    written = await ChronicleRepository(session).append(ChronicleDraft(2, ChronicleKind.SPEECH, "Varos spoke.", son_id=son.id))
    assert written.row.world_id == other.id


async def test_a_line_takes_the_year_of_its_moment(session: AsyncSession, world_id: int) -> None:
    written = await ChronicleRepository(session).append(ChronicleDraft(3, ChronicleKind.FATE, "dated", year=147))
    assert written.row.year == 147


async def test_world_filter_follows_records_then_son_then_main_world(session: AsyncSession, world_id: int) -> None:
    other = await seed_world(session, name="Thule", star_name="Thule Sun")
    home_region = await make_entity(session, "Fen", EntityType.REGION, world_id=world_id)
    far_region = await make_entity(session, "Ice", EntityType.REGION, world_id=other.id)
    son = await make_son(session, "Varos", world_id)
    repository = ChronicleRepository(session)
    home = await repository.append(ChronicleDraft(1, ChronicleKind.WORLD, "home", (home_region.id,)))
    far = await repository.append(ChronicleDraft(1, ChronicleKind.WORLD, "far", (far_region.id,)))
    mixed = await repository.append(ChronicleDraft(1, ChronicleKind.WORLD, "mixed", (home_region.id, far_region.id)))
    unbound = await repository.append(ChronicleDraft(1, ChronicleKind.FATE, "unbound"))
    spoken = await repository.append(ChronicleDraft(1, ChronicleKind.SPEECH, "spoken", son_id=son.id, world_id=None))
    spoken.row.world_id = None
    son.current_world_id = other.id
    await session.flush()
    main_lines = {row.id for row in await repository.recent(20, world_id=world_id, primary_world_id=world_id)}
    far_lines = {row.id for row in await repository.recent(20, world_id=other.id, primary_world_id=world_id)}
    assert main_lines == {home.row.id, unbound.row.id}
    assert far_lines == {far.row.id, spoken.row.id}
    assert mixed.row.id not in main_lines | far_lines


async def test_the_last_incident_belongs_to_its_session_and_a_rollback_forgets_it(session: AsyncSession, database: Database, world_id: int) -> None:
    region = await make_entity(session, "Marsh", EntityType.REGION, world_id=world_id)
    written = await ChronicleRepository(session).append(ChronicleDraft(3, ChronicleKind.WAR, "The marsh rose.", (region.id,)))
    assert incident_for(session, region.id, 3) == written.incident_id
    async with database.read() as other:
        assert incident_for(other, region.id, 3) is None
    await session.rollback()
    assert incident_for(session, region.id, 3) is None
