from aerona.domain.enums.region import DangerSource, RegionMemoryKind
from aerona.engine.environment import region_control
from aerona.rules.registry import Rules
from aerona.services.wiki import ground_snapshot
from tests.api.conftest import ApiWorld, seeded
from tests.services.player.test_regions import ground_for


async def test_the_region_terrain_view_shows_dangers_memory_and_layers(api: ApiWorld) -> None:
    core = seeded(api).core
    region = core.regions[0]
    async with api.services.database.write() as session:
        session.add(ground_for(region.id, core.world.id))
        await session.flush()
        await region_control.set_danger(session, Rules(), region.id, DangerSource.BANDITS, 60, epoch=1, held=True)
        await region_control.add_memory(session, region.id, RegionMemoryKind.MASSACRE, 80, "The Red Ford", epoch=1, held=True)
    view = (await api.http.get(f"/api/regions/{region.id}/terrain")).json()
    assert view["dangers"][0]["source"] == "bandits" and view["dangers"][0]["held"] is True
    assert view["harms"]["merchants"] == 60 * Rules().regional_danger.bandits_merchants // 100
    assert view["memories"][0]["title"] == "The Red Ford" and view["darkness"] > 0
    assert view["haunting_pct"] > 100
    async with api.services.database.read() as session:
        ground = (await ground_snapshot(session, core.world.id))[region.id]
    assert ground.danger_source == "bandits" and ground.rainfall == 50
