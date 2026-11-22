import importlib.util
from pathlib import Path
from types import ModuleType

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.sacred import BirthSignRow
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.environment.control import reorder_seasons
from aerona.engine.environment.time_control import add_season, remove_season
from aerona.services.integrity.season_positions import mend_season_positions
from tests.services.player.factories import make_entity, seed_player_world

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "check_season_positions.py"


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_season_positions", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def seasons_of(session: AsyncSession, world_id: int, count: int) -> list[WorldSeasonRow]:
    rows = [
        WorldSeasonRow(world_id=world_id, position=index, name=f"Season {index}", temperature_shift=0, rain_shift=0, growth=50, travel=50, campaign=50)
        for index in range(count)
    ]
    session.add_all(rows)
    await session.flush()
    return rows


async def test_removing_a_season_moves_a_gathering_and_a_birth_sign_with_it(session: AsyncSession) -> None:
    world = await seed_player_world(session)
    world_id = world.world.id
    world.world.season_count, world.world.year_length_days = 3, 360
    seasons = await seasons_of(session, world_id, 3)
    mortal = await make_entity(session, "Ada", EntityType.MORTAL, world_id=world_id)
    tradition = await make_entity(session, "Feast", EntityType.TRADITION, world_id=world_id, stats=TraditionStats(spread=10, rigidity=10))
    gathering = GatheringRow(host_node_id=mortal.id, kind=GatheringKind.FEAST, world_id=world_id, epoch=1, season=2)
    sign = BirthSignRow(mortal_entity_id=mortal.id, season=2)
    kept = TraditionProfileRow(tradition_entity_id=tradition.id, kind=TraditionFunction.FESTIVAL, cost={}, effects={}, locked=[], season_position=1)
    dated = IncidentRow(kind="test.dated", epoch=1, year=10, world_id=world_id, season=2, day=300)
    session.add_all([gathering, sign, kept, dated])
    await session.flush()
    await remove_season(session, seasons[1].id)
    assert (gathering.season, sign.season, kept.season_position, dated.season) == (1, 1, None, 1)
    await add_season(session, world_id, "Fresh", {}, 0)
    assert (gathering.season, sign.season) == (2, 2)
    await reorder_seasons(session, world_id, [2, 1, 0])
    assert (gathering.season, sign.season) == (0, 0)


async def test_a_position_beyond_the_seasons_is_mended(session: AsyncSession) -> None:
    world = await seed_player_world(session)
    world_id = world.world.id
    await seasons_of(session, world_id, 2)
    mortal = await make_entity(session, "Bo", EntityType.MORTAL, world_id=world_id)
    gathering = GatheringRow(host_node_id=mortal.id, kind=GatheringKind.FEAST, world_id=world_id, epoch=1, season=5)
    sign = BirthSignRow(mortal_entity_id=mortal.id, season=4)
    session.add_all([gathering, sign])
    await session.flush()
    assert await mend_season_positions(session) == 2
    await session.refresh(gathering)
    await session.refresh(sign)
    assert (gathering.season, sign.season) == (None, 1)


def test_every_season_column_is_classified_and_written_by_its_own_writers() -> None:
    assert checker().main() == 0


def test_an_unregistered_writer_is_caught() -> None:
    text = "from aerona.db.tables.gatherings import GatheringRow\nrow = GatheringRow(season=3)\nrow.season = 4\n"
    found = checker().writes_in("engine/sample.py", text, {"GatheringRow": {"season"}})
    assert len(found) == 2
