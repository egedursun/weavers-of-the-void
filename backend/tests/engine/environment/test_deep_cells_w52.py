from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.strata import STRATA
from aerona.db.tables.geology import RegionStratumRow
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import UndergroundStratum
from aerona.engine.environment.cells import DeepTally, name_cells, shape_cell
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed

RULES = Rules()
U = UndergroundStratum
FOOT = frozenset({MovementMode.ON_FOOT})
SUBMERGED = frozenset({MovementMode.SUBMERGED})


def test_cells_take_their_stratum_terrain_light_and_a_drawn_extent() -> None:
    row = RegionStratumRow(region_entity_id=1, stratum=U.MAGMA_SEA, volume=0, pressure=0, locked=[])
    shape_cell(RULES, row, None, 7, None)
    assert row.terrain is STRATA[U.MAGMA_SEA].terrain and row.light == RULES.underground.magma_sea_light
    assert RULES.underground.extent_min <= row.extent <= 100
    realm = RegionStratumRow(region_entity_id=1, stratum=U.DEEP_UNDERWORLD, volume=0, pressure=0, locked=[])
    shape_cell(RULES, realm, None, 0, 42)
    assert realm.realm_entity_id == 42


async def test_a_dwellable_cell_takes_a_name_in_the_tongue_of_its_world_and_a_bare_one_does_not(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    dwelt = RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[])
    bare = RegionStratumRow(region_entity_id=region.id, stratum=U.AQUIFER, volume=0, pressure=0, locked=[])
    kept = RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_MIDDLE, volume=0, pressure=0, locked=["name"])
    session.add_all([dwelt, bare, kept])
    await session.flush()
    tally = DeepTally()
    await name_cells(await manual_context(session, "test"), tally)
    assert dwelt.name and tally.named == 1
    assert bare.name is None and kept.name is None
