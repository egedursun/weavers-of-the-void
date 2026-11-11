import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.zones import RING_OF_ZONE, ZONE_OF_DISTRICT
from aerona.core.errors import ConflictError
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import DistrictServiceRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.enums.urban import LandCover, LandGround, Morphology, UrbanService
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.context import TickContext
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import quarter_wants
from aerona.engine.urban.cityscape import land_tiles, provisional, slots_of
from aerona.engine.urban.coverage import CoverageTally, cover_town, place
from aerona.engine.urban.housing import HousingTally, house_town
from aerona.engine.urban.layout import HEX_KEY, distance, falloff, layout_of, plan_seed, seed_of
from aerona.engine.urban.planning import move, plan_town
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "urban", rules=tuned_rules(**namespaces))


async def built_town(session: AsyncSession, world: CoreWorld, ctx: TickContext, population: int = 2400) -> tuple[int, list[DistrictRow]]:
    town = await settlement(session, "Ashby", world, world.regions[0], population=population)
    await town_of(ctx, town, await KnowledgeMap.load(session))
    await session.flush()
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id).order_by(DistrictRow.id)))
    return town.id, districts


async def work(session: AsyncSession, world: CoreWorld, town_id: int, kind: StructureKind, level: int = 2) -> int:
    row = await entity(session, kind.value, EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town_id)
    session.add(
        StructureProfileRow(
            structure_entity_id=row.id, kind=kind, level=level, staff_pct=100, host_entity_id=town_id, construction_state=ConstructionState.COMPLETE
        )
    )
    await session.flush()
    return row.id


async def test_every_district_is_seated_on_its_own_hex_and_zones_keep_their_rings(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, districts = await built_town(session, world, ctx)
    layout = await plan_town(ctx, town_id)
    seeds = [seed_of(district) for district in districts]
    assert all(seed is not None for seed in seeds)
    assert len(set(seeds)) == len(seeds)
    cells = [cell for footprint in layout.footprints.values() for cell in footprint]
    assert len(cells) == len(set(cells))
    again = layout_of(ctx.rules, districts, 0)
    assert again.footprints == layout.footprints
    rings = {district.id: RING_OF_ZONE[ZONE_OF_DISTRICT[district.kind]] for district in districts}
    inner = min(districts, key=lambda district: rings[district.id])
    outer = max(districts, key=lambda district: rings[district.id])
    if rings[inner.id] < rings[outer.id]:
        inner_seed, outer_seed = seed_of(inner), seed_of(outer)
        assert inner_seed is not None and outer_seed is not None
        assert distance(inner_seed, (0, 0)) <= distance(outer_seed, (0, 0))


async def test_a_service_reaches_less_of_a_district_the_further_it_stands(session: AsyncSession, world: CoreWorld) -> None:
    assert falloff(0.8, 0) == 1
    assert falloff(0.8, 1) > falloff(0.8, 3)
    ctx = await context(session)
    town_id, _ = await built_town(session, world, ctx)
    temple = await work(session, world, town_id, StructureKind.TEMPLE, level=3)
    town = await session.get(EntityRow, town_id)
    assert town is not None
    await cover_town(ctx, town, CoverageTally())
    profile = await session.get(StructureProfileRow, temple)
    assert profile is not None and profile.district_id is not None
    layout = await plan_town(ctx, town_id)
    faith = {
        row.district_id: row.coverage
        for row in await session.scalars(select(DistrictServiceRow).where(DistrictServiceRow.service == UrbanService.FAITH))
        if row.district_id in layout.footprints
    }
    home = profile.district_id
    far = max(faith, key=lambda district_id: layout.apart(home, district_id))
    if layout.apart(home, far) > 0:
        assert faith[home] > faith[far]


async def test_the_god_moves_a_district_and_the_planner_keeps_it_there(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, districts = await built_town(session, world, ctx)
    await plan_town(ctx, town_id)
    first, *others = districts
    moved = await move(ctx, first.id, (9, -4))
    assert seed_of(moved) == (9, -4) and HEX_KEY in moved.locked
    await plan_town(ctx, town_id)
    assert seed_of(moved) == (9, -4)
    if others:
        taken = seed_of(others[0])
        assert taken is not None
        with pytest.raises(ConflictError):
            await move(ctx, first.id, taken)


async def test_a_town_with_civic_works_and_a_park_wants_a_civic_quarter_and_gardens(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, city_plan={"civic_quarter_at": 2, "gardens_prosperity": 0})
    town_id, _ = await built_town(session, world, ctx)
    for kind in (StructureKind.SCHOOL, StructureKind.HOSPITAL, StructureKind.PARK):
        await work(session, world, town_id, kind)
    town_row = await session.get(EntityRow, town_id)
    assert town_row is not None
    town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
    assert set(await quarter_wants(ctx, town)) == {f"district:{DistrictKind.CIVIC_QUARTER.value}", f"district:{DistrictKind.GARDENS.value}"}


async def test_an_almshouse_shelters_the_homeless_and_the_tally_counts_only_those_it_took_in(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, city_plan={"almshouse_shelter": 100000})
    town_id, _ = await built_town(session, world, ctx, population=90000)
    town = await session.get(EntityRow, town_id)
    assert town is not None
    bare = HousingTally()
    await house_town(ctx, town, await KnowledgeMap.load(session), bare)
    profile = await session.get(SettlementProfileRow, town_id)
    assert profile is not None and profile.homeless > 0 and bare.sheltered == 0
    before = profile.homeless
    await work(session, world, town_id, StructureKind.ALMSHOUSE, level=1)
    tally = HousingTally()
    await house_town(ctx, town, await KnowledgeMap.load(session), tally)
    assert profile.homeless == 0
    assert 0 < tally.sheltered <= before + 1000
    assert tally.sheltered < 100000


async def test_the_scene_draws_unseated_districts_exactly_where_the_engine_will_seat_them(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, districts = await built_town(session, world, ctx)
    for district in districts:
        district.hex_q = None
        district.hex_r = None
    await session.flush()
    drawn = provisional(ctx.rules, districts, Morphology.ORGANIC, 0, town_id)
    profile = await session.get(SettlementProfileRow, town_id)
    assert profile is not None
    profile.morphology = Morphology.ORGANIC
    seated = await plan_town(ctx, town_id)
    assert drawn.seeds == seated.seeds and drawn.footprints == seated.footprints


async def test_the_god_cannot_move_a_district_onto_a_hex_another_was_only_drawn_on(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, districts = await built_town(session, world, ctx)
    assert len(districts) >= 2
    for district in districts:
        district.hex_q = None
        district.hex_r = None
    await session.flush()
    drawn = provisional(ctx.rules, districts, Morphology.ORGANIC, 0, town_id)
    with pytest.raises(ConflictError):
        await move(ctx, districts[0].id, drawn.seeds[districts[1].id])


async def test_the_scene_draws_an_unplaced_building_in_the_district_the_engine_will_give_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, districts = await built_town(session, world, ctx)
    layout = await plan_town(ctx, town_id)
    market = await work(session, world, town_id, StructureKind.MARKET)
    profile = await session.get(StructureProfileRow, market)
    assert profile is not None and profile.district_id is None
    cell, _ = slots_of(layout, [profile], districts)[market]
    assert place(profile, districts) and profile.district_id is not None
    assert cell in layout.footprints[profile.district_id]


async def test_the_land_tiles_follow_the_land_shares_and_its_river(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await context(session))
    region = world.regions[0]
    land = await session.get(RegionEnvironmentRow, region.id)
    assert land is not None
    land.forest_cover = 100
    land.farmed = 0
    land.grazed = 0
    land.wetland = 0
    land.cleared = 0
    land.mined = 0
    land.built = 0
    land.river_class = RiverClass.RIVER
    tiles = land_tiles(land, region.id)
    assert tiles == land_tiles(land, region.id)
    dry = [tile for tile in tiles if tile.ground not in (LandGround.WATER, LandGround.SHORE)]
    assert dry and all(tile.cover is LandCover.FOREST for tile in dry)
    assert any(tile.river for tile in tiles)
    land.river_class = RiverClass.NONE
    land.forest_cover = 0
    assert not any(tile.river or tile.cover is LandCover.FOREST for tile in land_tiles(land, region.id))


def test_every_kind_of_district_finds_a_free_hex_in_every_growth_pattern() -> None:
    rules = tuned_rules()
    for morphology in Morphology:
        seated: list[DistrictRow] = []
        for index, kind in enumerate(DistrictKind):
            layout = layout_of(rules, seated, 2)
            cell = plan_seed(rules, layout, kind, morphology, rng=SeededRandom.for_epoch(1, 0, f"plan.{morphology.value}.{index}"), waterside=0)
            assert cell not in layout.seeds.values()
            seated.append(DistrictRow(id=index + 1, settlement_entity_id=1, kind=kind, level=1, hex_q=cell[0], hex_r=cell[1]))
        assert len({seed_of(row) for row in seated}) == len(DistrictKind)
