from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.ecology import AwakeningTrigger, BeastTemper
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import BeastStats, EventStats
from aerona.engine.ecology.beast_acts import TRIGGERS, rob_hoards, triggered
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules

CERTAIN = tuned_rules(beast_waking={"theft_pct": 100, "sky_sign_pct": 100, "disturbance_pct": 100, "hoard_theft_pct": 100})


async def sleeper(session: AsyncSession, world: CoreWorld, name: str, trigger: AwakeningTrigger) -> tuple[EntityRow, BeastProfileRow, CreatureAnatomyRow]:
    region = world.regions[0]
    beast = await entity(session, name, EntityType.BEAST, BeastStats(hp=200), world_id=world.world.id, location_id=region.id)
    row = BeastProfileRow(beast_entity_id=beast.id, lair_place_id=region.id, temper=BeastTemper.SLEEPING, hoard={"gold": 40}, locked=[])
    shape = CreatureAnatomyRow(node_id=beast.id, awakening=trigger, locked=[])
    session.add_all([row, shape])
    await session.flush()
    return beast, row, shape


async def kinds(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(IncidentRow.kind)))


def test_every_trigger_has_its_test() -> None:
    assert set(TRIGGERS) == set(AwakeningTrigger) and len(AwakeningTrigger) == 6


async def test_a_robbed_hoard_wakes_a_beast_stirred_by_theft_and_it_remembers_the_thief(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", CERTAIN)
    beast, row, shape = await sleeper(session, world, "Hoard Wyrm", AwakeningTrigger.THEFT)
    town = await settlement(session, "Gilded Ford", world, world.regions[0])
    atlas = await RegionAtlas.load(session)
    assert await rob_hoards(ctx, atlas) == 1
    assert row.hoard["gold"] == 30
    await session.flush()
    remembered = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == beast.id, MemoryRow.kind == MemoryKind.HARMED_ME))
    assert remembered is not None and remembered.subject_node_id == town.id
    assert await triggered(ctx, atlas, shape, world.regions[0].id)
    await session.flush()
    assert {"beast.hoard_robbed", "beast.stirred"} <= await kinds(session)


async def test_a_sign_in_the_sky_and_a_battle_nearby_wake_their_sleepers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", CERTAIN)
    atlas = await RegionAtlas.load(session)
    _sky, _row, sky_shape = await sleeper(session, world, "Star Eater", AwakeningTrigger.SKY_SIGN)
    assert not await triggered(ctx, atlas, sky_shape, world.regions[0].id)
    session.add(SkyEventRow(kind=SkyEventKind.COMET, epoch=ctx.epoch, world_id=world.world.id))
    await session.flush()
    assert await triggered(ctx, atlas, sky_shape, world.regions[0].id)
    _war, _row2, war_shape = await sleeper(session, world, "War Sleeper", AwakeningTrigger.DISTURBANCE)
    assert not await triggered(ctx, atlas, war_shape, world.regions[0].id)
    fight = await entity(
        session, "Battle of the Ford", EntityType.EVENT, EventStats(), world_id=world.world.id, location_id=world.regions[0].id, birth_epoch=ctx.epoch
    )
    fight.engine_kind = EngineKind.BATTLE
    await session.flush()
    assert await triggered(ctx, await RegionAtlas.load(session), war_shape, world.regions[0].id)
