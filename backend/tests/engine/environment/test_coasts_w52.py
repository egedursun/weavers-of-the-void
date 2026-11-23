from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.nature_kinds50 import COAST_FORMS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.water import CoastRow
from aerona.domain.enums.environment import CoastKind, RiverClass, TerrainKind
from aerona.domain.enums.water import CoastForm
from aerona.engine.phases.environment import estuary_sea
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.water.ice import WaterTally, coast_form, shape_coast
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed, tuned_rules

RULES = Rules()


def shore(terrain: TerrainKind = TerrainKind.COAST, *, river: RiverClass = RiverClass.NONE, coast: CoastKind = CoastKind.BEACH) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(dominant_terrain=terrain, river_class=river, coast_kind=coast, locked=[])


def test_a_river_mouth_is_an_estuary_and_a_mangrove_shore_its_own_form() -> None:
    assert coast_form(shore(TerrainKind.MANGROVE)) is CoastForm.MANGROVE
    assert coast_form(shore(river=RiverClass.RIVER)) is CoastForm.ESTUARY
    assert coast_form(shore(river=RiverClass.GREAT_RIVER)) is CoastForm.ESTUARY
    assert coast_form(shore()) is CoastForm.BEACH
    assert set(COAST_FORMS) == set(CoastForm)


def test_an_estuary_gives_more_catch_than_the_open_sea() -> None:
    assert estuary_sea(RULES, 30, False) == 30
    assert estuary_sea(RULES, 30, True) == 30 + RULES.coasts.estuary_fish_pct
    assert estuary_sea(RULES, None, True) == RULES.environment.coast_fishing_share + RULES.coasts.estuary_fish_pct


async def test_a_barrier_island_shifts_back_with_storms(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0].id
    land = await session.get(RegionEnvironmentRow, region)
    assert land is not None
    land.coast_kind = CoastKind.BEACH
    session.add(CoastRow(region_entity_id=region, form=CoastForm.BARRIER_ISLAND, rate=0, progress=50, locked=["rate"]))
    await session.flush()
    atlas = await RegionAtlas.load(session)
    still = await manual_context(session, "test", tuned_rules(coasts={"barrier_shift_pct": 0}))
    await shape_coast(still, land, (0, 0), atlas, WaterTally())
    row = await session.get(CoastRow, region)
    assert row is not None and row.progress == 50
    stormy = await manual_context(session, "test", tuned_rules(coasts={"barrier_shift_pct": 100}))
    await shape_coast(stormy, land, (0, 0), atlas, WaterTally())
    assert row.progress == 25
    assert await session.scalar(select(CoastRow.form).where(CoastRow.region_entity_id == region)) is CoastForm.BARRIER_ISLAND
