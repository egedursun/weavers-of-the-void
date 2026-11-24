from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.couplings import DeepSealRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.couplings import SealKind
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, UndergroundStratum
from aerona.engine.environment.cells import (
    DeepTally,
    dig_toward,
    lay_natural_passages,
    live_passages,
    make_passage,
)
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, settlement, surveyed, tuned_rules

RULES = Rules()
U = UndergroundStratum
FOOT = frozenset({MovementMode.ON_FOOT})
SUBMERGED = frozenset({MovementMode.SUBMERGED})


async def test_passages_are_dug_collapse_flood_drain_clear_and_seal(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    for stratum in (U.AQUIFER, U.CAVERN_UPPER):
        session.add(RegionStratumRow(region_entity_id=region.id, stratum=stratum, volume=0, pressure=0, locked=[]))
    town = await settlement(session, "Delvers", world, region)
    await session.flush()
    ctx = await manual_context(session, "test", tuned_rules(underground={"dig_rate": 100, "collapse_pct": 100, "flood_pct": 0}))
    dug = await dig_toward(ctx, town, (region.id, None), (region.id, U.CAVERN_UPPER))
    assert dug.state is DeepPassageState.DIGGING and dug.progress == 0
    tally = DeepTally()
    await live_passages(ctx, tally)
    assert dug.state is DeepPassageState.OPEN and dug.opened and tally.dug == 1
    await live_passages(ctx, tally)
    assert dug.state is DeepPassageState.COLLAPSED and tally.collapsed == 1
    clearing = await manual_context(session, "clear", tuned_rules(underground={"clear_rate": 100, "collapse_pct": 0}))
    await live_passages(clearing, tally)
    assert dug.state is DeepPassageState.OPEN and tally.cleared == 1
    session.add(DeepSealRow(place_entity_id=region.id, passage_id=dug.id, kind=SealKind.STRUCTURE, strength=60, decay=5, epoch=1, locked=[]))
    await session.flush()
    await live_passages(clearing, tally)
    assert dug.state is DeepPassageState.SEALED and tally.sealed == 1
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"deep.passage_dug", "deep.passage_collapsed", "deep.passage_cleared", "deep.passage_sealed"} <= kinds


async def test_a_passage_already_open_between_two_ends_is_kept_and_never_doubled(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    first, second = world.regions[0], world.regions[1]
    for region in (first, second):
        session.add(RegionStratumRow(region_entity_id=region.id, stratum=U.CAVERN_UPPER, volume=0, pressure=0, locked=[]))
    await session.flush()
    ctx = await manual_context(session, "test", tuned_rules(underground={"natural_level_pct": 100, "natural_opening_pct": 100}))
    kept = await make_passage(ctx, world.world.id, (second.id, U.CAVERN_UPPER), (first.id, U.CAVERN_UPPER), origin=DeepPassageOrigin.DUG)
    await lay_natural_passages(ctx, DeepTally())
    again = await make_passage(ctx, world.world.id, (first.id, U.CAVERN_UPPER), (second.id, U.CAVERN_UPPER), origin=DeepPassageOrigin.NATURAL)
    assert again.id == kept.id and again.origin is DeepPassageOrigin.DUG
    total = await session.scalar(
        select(func.count()).select_from(DeepPassageRow).where(DeepPassageRow.first_stratum == U.CAVERN_UPPER, DeepPassageRow.second_stratum == U.CAVERN_UPPER)
    )
    assert total == 1
