from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.entity_line import line_items
from aerona.catalog.strata import STRATA
from aerona.db.tables.geology import DeepPassageRow, PolityDeepKnowledgeRow, RegionStratumRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import DeepPassageOrigin, UndergroundStratum
from aerona.engine.environment.cells import (
    DeepTally,
    know_cells,
    lay_natural_passages,
    make_passage,
)
from aerona.engine.environment.levels import level_fault
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.wiki import political_map
from tests.engine.core.factories import seed_core_world, settlement, surveyed, tuned_rules

RULES = Rules()
U = UndergroundStratum
FOOT = frozenset({MovementMode.ON_FOOT})
SUBMERGED = frozenset({MovementMode.SUBMERGED})


async def test_a_settlement_below_is_far_from_the_surface_until_a_passage_joins_them(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    session.add(RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[]))
    top = await settlement(session, "Sunside", world, region)
    deep = await settlement(session, "Underhall", world, region)
    deep.stratum = U.CAVERN_UPPER
    await session.flush()
    atlas = await RegionAtlas.load(session)
    assert atlas.cell_of(deep.id) == (region.id, U.CAVERN_UPPER) and not atlas.same_cell(top.id, deep.id)
    assert atlas.hops(top.id, deep.id) is None
    ctx = await manual_context(session, "test")
    await make_passage(ctx, world.world.id, (region.id, None), (region.id, U.CAVERN_UPPER), origin=DeepPassageOrigin.NATURAL)
    atlas = await RegionAtlas.load(session)
    assert atlas.hops(top.id, deep.id) == RULES.underground.vertical_hop_cost and atlas.adjacent(top.id, deep.id)
    surface = await political_map(session, RULES, world.world.id)
    below = await political_map(session, RULES, world.world.id, U.CAVERN_UPPER)
    assert region.id in below and below != surface


async def test_natural_passages_join_neighbouring_cells_and_polities_learn_the_cells_they_hold(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    first, second = world.regions[0], world.regions[1]
    for region in (first, second):
        session.add(RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[]))
    town = await settlement(session, "Deepholt", world, first)
    town.stratum = U.CAVERN_UPPER
    await session.flush()
    ctx = await manual_context(session, "test", tuned_rules(underground={"natural_level_pct": 100}))
    atlas = await RegionAtlas.load(session)
    tally = DeepTally()
    await lay_natural_passages(ctx, tally)
    joined = await session.scalar(select(DeepPassageRow).where(DeepPassageRow.first_stratum == U.CAVERN_UPPER).limit(1))
    assert (second.id in atlas.neighbours(first.id)) == (joined is not None)
    await know_cells(ctx, tally)
    known = list(await session.scalars(select(PolityDeepKnowledgeRow)))
    assert known and known[0].level == RULES.underground.knowledge_per_crossing and known[0].held


async def test_a_thing_is_placed_only_in_a_cell_that_lies_beneath_its_region_and_a_dweller_only_where_one_can_dwell(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    region = world.regions[0]
    session.add_all(
        [
            RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[]),
            RegionStratumRow(region_entity_id=region.id, stratum=U.MAGMA_SEA, volume=0, pressure=0, locked=[]),
        ]
    )
    await session.flush()
    assert await level_fault(session, region, U.CAVERN_UPPER, EntityType.SETTLEMENT) is None
    assert "lies beneath" in (await level_fault(session, region, U.AQUIFER, EntityType.SETTLEMENT) or "")
    assert "dwell" in (await level_fault(session, region, U.MAGMA_SEA, EntityType.SETTLEMENT) or "")
    assert await level_fault(session, region, U.MAGMA_SEA, EntityType.SETTLEMENT, dwelling=False) is None
    assert await level_fault(session, region, U.MAGMA_SEA, EntityType.STRUCTURE) is None
    assert "region" in (await level_fault(session, world.people, U.CAVERN_UPPER, EntityType.STRUCTURE) or "")


async def test_an_actor_reads_where_a_thing_below_stands(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    region = world.regions[0]
    session.add(RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[]))
    town = await settlement(session, "Lowhall", world, region)
    town.stratum = U.CAVERN_UPPER
    await session.flush()
    [item] = await line_items(session, [town])
    assert item.location == f"the {STRATA[U.CAVERN_UPPER].label.lower()} beneath {region.name}"
