from collections import Counter, defaultdict
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structures import WORKSHOP_STRUCTURES
from aerona.catalog.urban import HOME_DISTRICT
from aerona.catalog.zones import CIVIC_SERVICE_OF, RING_OF_ZONE, ZONE_OF_DISTRICT, ZONE_OF_STRUCTURE
from aerona.core.errors import ConflictError
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.tables.urban import DistrictServiceRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import BuildingForm, ConstructionState, StructureKind
from aerona.domain.enums.urban import LandCover, LandGround, Morphology, UrbanService
from aerona.domain.models.entity_stats import SettlementStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import quarter_wants
from aerona.engine.structures.needs import SiteFacts, wanted
from aerona.engine.structures.readers import Working
from aerona.engine.structures.settlement import civic_from
from aerona.engine.urban.cityscape import land_tiles, perimeter_of, perimeter_ring, pick_tile, provisional, slots_of
from aerona.engine.urban.coverage import CoverageTally, cover_town, people_of_districts, place
from aerona.engine.urban.housing import HousingTally, house_town
from aerona.engine.urban.layout import HEX_KEY, distance, falloff, layout_of, plan_seed, seed_of
from aerona.engine.urban.planning import move, plan_town, settle
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


async def test_walls_gates_and_wall_lined_kinds_stand_on_the_rim_of_the_town_not_inside_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, districts = await built_town(session, world, ctx)
    layout = await plan_town(ctx, town_id)
    wall = await work(session, world, town_id, StructureKind.WALL)
    gate = await work(session, world, town_id, StructureKind.GATE)
    lined = await work(session, world, town_id, StructureKind.WATCHTOWER)
    market = await work(session, world, town_id, StructureKind.MARKET)
    design = StructureDesignRow(name="Long rampart", base_kind=StructureKind.WATCHTOWER, form=BuildingForm.WALL_LINE)
    session.add(design)
    await session.flush()
    lined_profile = await session.get(StructureProfileRow, lined)
    assert lined_profile is not None
    lined_profile.design_id = design.id
    profiles = list(await session.scalars(select(StructureProfileRow).where(StructureProfileRow.host_entity_id == town_id)))
    perimeter = await perimeter_of(session, profiles)
    assert {wall, gate, lined} <= perimeter and market not in perimeter
    slots = slots_of(layout, profiles, districts, perimeter)
    rim = set(perimeter_ring(layout))
    inside = {cell for cells in layout.footprints.values() for cell in cells}
    for node in (wall, gate, lined):
        assert slots[node][0] in rim and slots[node][0] not in inside
    assert slots[market][0] in inside


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
    dry = [tile for tile in tiles if tile.ground not in (LandGround.WATER, LandGround.SHORE) and not tile.river]
    assert dry and all(tile.cover is LandCover.FOREST for tile in dry)
    assert any(tile.river for tile in tiles)
    assert all(tile.cover is LandCover.OPEN for tile in tiles if tile.river)
    taken: set[tuple[int, int]] = set()
    towns = [pick_tile(tiles, taken, (LandCover.BUILT,), (LandGround.LOWLAND, LandGround.SHORE)) for _ in range(6)]
    wet = {(tile.q, tile.r) for tile in tiles if tile.river or tile.ground is LandGround.WATER}
    assert not wet & set(towns)
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


def test_every_district_claims_its_whole_footprint_even_when_seats_crowd() -> None:
    rules = tuned_rules()
    crowded = [
        DistrictRow(id=1, settlement_entity_id=1, kind=DistrictKind.MARKET, level=2, hex_q=1, hex_r=0),
        DistrictRow(id=2, settlement_entity_id=1, kind=DistrictKind.PALACE, level=1, hex_q=0, hex_r=0),
        DistrictRow(id=3, settlement_entity_id=1, kind=DistrictKind.SLUMS, level=1, hex_q=2, hex_r=-1),
    ]
    layout = layout_of(rules, crowded, 0)
    for district in crowded:
        cells = layout.footprints[district.id]
        assert len(cells) == district.level * rules.city_plan.cells_per_level
        assert seed_of(district) in cells
    every = [cell for cells in layout.footprints.values() for cell in cells]
    assert len(every) == len(set(every))


def test_fields_and_graves_are_pushed_out_as_the_walls_grow_past_them() -> None:
    rules = tuned_rules()
    town = [
        DistrictRow(id=1, settlement_entity_id=1, kind=DistrictKind.FARMLAND, level=1, hex_q=1, hex_r=0, locked=[]),
        DistrictRow(id=2, settlement_entity_id=1, kind=DistrictKind.PALACE, level=3, hex_q=None, hex_r=None, locked=[]),
        DistrictRow(id=3, settlement_entity_id=1, kind=DistrictKind.RESIDENTIAL, level=3, hex_q=None, hex_r=None, locked=[]),
    ]
    settle(rules, town, Morphology.ORGANIC, 3)
    layout = layout_of(rules, town, 3)
    assert layout.walls_radius is not None
    farm = seed_of(town[0])
    assert farm is not None and distance(farm, (0, 0)) > layout.walls_radius
    held_farm = DistrictRow(id=4, settlement_entity_id=1, kind=DistrictKind.NECROPOLIS, level=1, hex_q=1, hex_r=-1, locked=[HEX_KEY])
    settle(rules, [*town, held_farm], Morphology.ORGANIC, 3)
    assert seed_of(held_farm) == (1, -1)


def structure_at(kind: StructureKind, level: int = 2) -> Working:
    return Working(
        EntityRow(name=kind.value, entity_type=EntityType.STRUCTURE),
        StructureProfileRow(kind=kind, level=level, effect_pct=100, capacity=100),
    )


async def test_the_new_works_keep_order_calm_unrest_drill_militia_and_add_to_investment(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town_id, _ = await built_town(session, world, ctx)
    town = await session.get(EntityRow, town_id)
    profile = await session.get(SettlementProfileRow, town_id)
    assert town is not None and profile is not None
    profile.locked = []
    profile.unrest, profile.public_order, profile.prestige, profile.militia, profile.investment_pool = 50, 20, 10, 0, 0
    kinds: dict[StructureKind, list[Working]] = defaultdict(list)
    for kind in (
        StructureKind.TOWN_HALL,
        StructureKind.TAVERN,
        StructureKind.ORPHANAGE,
        StructureKind.PLAZA,
        StructureKind.TRAINING_GROUND,
        StructureKind.MUSEUM,
        StructureKind.GUILDHALL,
        StructureKind.MINT,
        StructureKind.BARRACKS,
    ):
        kinds[kind].append(structure_at(kind))
    civic_from(ctx, town, profile, kinds)
    table = ctx.rules.structure_functions
    assert profile.public_order == 20 + table.town_hall_order
    assert profile.unrest == 50 - (table.tavern_unrest_cut + table.orphanage_unrest_cut + table.plaza_unrest_cut + table.training_unrest_cut)
    assert profile.prestige == 10 + table.museum_prestige
    assert profile.militia == round(100 * table.garrison_militia_pct / 100 + 2 * table.training_militia)
    assert profile.investment_pool == 2 * (table.guildhall_investment + table.mint_investment)


def test_towns_call_for_the_new_works_when_their_life_needs_them(world: CoreWorld) -> None:
    rules = tuned_rules()
    town = SettlementProfileRow(size_tier=SizeTier.CITY, homeless=0, unrest=0, crime=0, sanitation=100, prestige=0)
    base = SiteFacts(
        site=EntityRow(name="Ashby", entity_type=EntityType.SETTLEMENT, stats=SettlementStats(population=60000, prosperity=50, defense=30, piety=50)),
        town=town,
        shares={SocialClass.ARTISAN: 50, SocialClass.WARRIOR: 50},
        knowledge=KnowledgeMap({}),
        at_war=True,
        patron=False,
        coastal=False,
        river=False,
        literacy=100,
        capital=False,
        outbreak=True,
        present=Counter({StructureKind.MARKET: 1}),
        workshops={StructureKind.BREWERY, StructureKind.MINT},
        barred=set(),
    )
    asked = set(wanted(rules, base))
    assert {
        StructureKind.TAVERN,
        StructureKind.TOWN_HALL,
        StructureKind.GUILDHALL,
        StructureKind.BARRACKS,
        StructureKind.ORPHANAGE,
        StructureKind.TRAINING_GROUND,
        StructureKind.MUSEUM,
        StructureKind.PLAZA,
        StructureKind.BREWERY,
        StructureKind.MINT,
    } <= asked
    peace = replace(base, capital=True, at_war=False, outbreak=False, present=Counter(), workshops=set())
    assert not {StructureKind.TOWN_HALL, StructureKind.BARRACKS, StructureKind.ORPHANAGE, StructureKind.TAVERN, StructureKind.PLAZA} & set(wanted(rules, peace))


def test_every_new_work_has_a_zone_a_district_to_stand_in_and_a_house_for_any_workshop() -> None:
    for kind in StructureKind:
        assert kind in ZONE_OF_STRUCTURE
    for workshop in WorkshopKind:
        assert workshop in WORKSHOP_STRUCTURES, workshop
    for kind in (StructureKind.ORPHANAGE, StructureKind.APOTHECARY, StructureKind.TRAINING_GROUND, StructureKind.MUSEUM):
        assert kind in CIVIC_SERVICE_OF and HOME_DISTRICT[kind] is DistrictKind.CIVIC_QUARTER


def test_outer_districts_never_lie_on_or_inside_the_walls_and_footprints_stay_whole() -> None:
    rules = tuned_rules()
    town = [
        DistrictRow(id=1, settlement_entity_id=1, kind=DistrictKind.FARMLAND, level=2, hex_q=None, hex_r=None, locked=[]),
        DistrictRow(id=2, settlement_entity_id=1, kind=DistrictKind.MARKET, level=2, hex_q=None, hex_r=None, locked=[]),
        DistrictRow(id=3, settlement_entity_id=1, kind=DistrictKind.PALACE, level=1, hex_q=None, hex_r=None, locked=[]),
        DistrictRow(id=4, settlement_entity_id=1, kind=DistrictKind.RESIDENTIAL, level=3, hex_q=None, hex_r=None, locked=[]),
        DistrictRow(id=5, settlement_entity_id=1, kind=DistrictKind.HARBOUR, level=1, hex_q=None, hex_r=None, locked=[]),
    ]
    settle(rules, town, Morphology.ORGANIC, 3)
    layout = layout_of(rules, town, 3)
    assert layout.walls_radius is not None
    for district in town:
        cells = layout.footprints[district.id]
        if district.kind in (DistrictKind.FARMLAND, DistrictKind.HARBOUR):
            assert all(distance(cell, (0, 0)) > layout.walls_radius for cell in cells)
        else:
            assert all(distance(cell, (0, 0)) < layout.walls_radius for cell in cells)
        joined = {cells[0]}
        for _ in cells:
            joined |= {cell for cell in cells if any(distance(cell, other) == 1 for other in joined)}
        assert joined == set(cells)


def test_people_live_where_a_district_has_homes_for_them() -> None:
    rules = tuned_rules()
    town = [
        DistrictRow(id=1, settlement_entity_id=1, kind=DistrictKind.RESIDENTIAL, level=2),
        DistrictRow(id=2, settlement_entity_id=1, kind=DistrictKind.MARKET, level=2),
        DistrictRow(id=3, settlement_entity_id=1, kind=DistrictKind.NECROPOLIS, level=2),
        DistrictRow(id=4, settlement_entity_id=1, kind=DistrictKind.PALACE, level=2),
    ]
    people = people_of_districts(rules, 10000, town)
    assert people[1] > people[2] > people[4] > people[3] == 0
    assert round(sum(people.values())) == 10000
    plan = rules.city_plan
    assert people[1] / people[2] == plan.residential_housing_pct / plan.market_housing_pct
