from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.generator import generate_map
from aerona.db.tables.celestial import WorldMapRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.cosmos.maps import generated_maps, map_is_stale, map_request, refresh_world_maps, regenerate_world_map, world_entities
from aerona.engine.phases.cosmos_upkeep import world_maps
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_world, tick


async def test_worlds_get_a_persisted_map_with_region_adjacency(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    world = await make_world(session, "Tessar", WorldType.OCEAN)
    regions = [await make_region(session, f"Tessar {index}", world.id, fertility=50) for index in range(4)]
    town = await make_entity(session, "Tessar Port", EntityType.SETTLEMENT, SettlementStats(population=900), world_id=world.id, location_id=regions[0].id)
    assert await map_is_stale(session, world.id)
    refreshed = await refresh_world_maps(session, rules, 1)
    assert world.id in {item.world_id for item in refreshed}
    stored = await session.get(WorldMapRow, world.id)
    assert stored is not None and {record["id"] for record in stored.geometry["regions"]} == {region.id for region in regions}
    assert not await map_is_stale(session, world.id)
    assert town.map_x is not None and town.map_y is not None
    atlas = await RegionAtlas.load(session)
    assert any(atlas.neighbour_regions(region.id) for region in regions)
    assert atlas.hops(town.id, regions[0].id) == 0


async def test_new_regions_redraw_the_map_on_the_next_tick(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    world = await make_world(session, "Velmar")
    await make_region(session, "Velmar Reach", world.id)
    await regenerate_world_map(session, rules, world.id, 1)
    added = await make_region(session, "Velmar Strand", world.id)
    assert await map_is_stale(session, world.id)
    await world_maps(tick(session, rules))
    stored = await session.get(WorldMapRow, world.id)
    assert stored is not None and added.id in {record["id"] for record in stored.geometry["regions"]}


async def test_parallel_map_generation_matches_the_serial_result(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    worlds = [await make_world(session, f"Shoal {index}", WorldType.OCEAN) for index in range(3)]
    for world in worlds:
        await make_region(session, f"{world.name} Land", world.id, fertility=50)
    requests = [map_request(world, await world_entities(session, world.id)) for world in worlds]
    parallel = await generated_maps(requests, rules)
    serial = [generate_map(request, rules) for request in requests]
    assert [item.world_map for item in parallel] == [item.world_map for item in serial]
