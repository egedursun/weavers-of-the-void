from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import ADVANCE, STAGE_COVER, next_stage, path_of
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.environment import SoilKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.engine.environment.succession import SuccessionTally, grow_lands
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed, tuned_rules

RULES = Rules()
S = SuccessionStage


def test_dry_and_wet_paths_run_through_the_new_stages() -> None:
    assert path_of(S.BARE, wet=False, poor=False, dune=False) == (S.BARE, S.PIONEER, S.GRASSLAND, S.SHRUBLAND, S.YOUNG_FOREST, S.OLD_FOREST)
    assert path_of(S.OPEN_WATER, wet=True, poor=False, dune=False) == (S.OPEN_WATER, S.MARSH, S.BOG, S.SWAMP_FOREST)
    assert next_stage(S.BOG, True, poor=False, dune=False) is S.SWAMP_FOREST
    assert set(ADVANCE) >= {S.PIONEER, S.OPEN_WATER, S.BOG} and all(stage in STAGE_COVER for stage in S)


async def test_a_bog_lays_peat_as_it_grows_into_swamp_forest(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", tuned_rules(biome_succession={"fire_pct": 0}))
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.succession, land.succession_progress, land.base_wetland, land.wetland = S.BOG, 99, 80, 80
    land.soil, land.temperature, land.rainfall, land.soil_fertility, land.farmed = SoilKind.LOAM, 15, 80, 80, 0
    await session.flush()
    tally = SuccessionTally()
    await grow_lands(ctx, tally)
    assert tally.advanced >= 1 and land.succession is S.SWAMP_FOREST and land.soil is SoilKind.PEAT
    told = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "succession.advanced").order_by(IncidentRow.id))
    assert told is not None
    facts = {row.key: row.enum_value for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == told))}
    assert facts.get("before") == S.BOG.value and facts.get("stage") == S.SWAMP_FOREST.value
