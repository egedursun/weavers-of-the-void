from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import CelestialStats, CultStats, StructureStats
from aerona.engine.body.afflictions import afflict, desecration_curse, desecrator_of, first_moon, join_outer_cult, moon_rampage, shrine_god, vengeance_package
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import add_flag, connect
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def test_a_moon_bound_bearer_rampages_among_its_neighbours(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", rules=tuned_rules(effect_packages={"rampage_pct": 100}))
    town = await settlement(session, "Brookhold", world, world.regions[0])
    bearer = await mortal(session, "Ulf", world, town.id)
    victim = await mortal(session, "Ana", world, town.id)
    row = await afflict(ctx, bearer, PackageKind.LYCANTHROPY, Transmission.CURSE)
    assert row is not None
    assert await first_moon(ctx, None) is None and await first_moon(ctx, world.world.id) is None
    hp = stat(victim, "hp") or 0
    await moon_rampage(ctx, bearer, row)
    assert stat(victim, "hp") == hp
    moon = await entity(session, "Pale Eye", EntityType.CELESTIAL, CelestialStats(brightness=100), world_id=world.world.id)
    moon.domain = Domain.MOON
    await session.flush()
    assert await first_moon(ctx, world.world.id) is moon
    await moon_rampage(ctx, bearer, row)
    assert (stat(victim, "hp") or 0) < hp


async def test_the_void_claims_its_bearers_for_an_outer_cult(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    bearer = await mortal(session, "Ulf", world, town.id)
    await join_outer_cult(ctx, bearer)
    cult = await entity(session, "The Hollow Choir", EntityType.CULT, CultStats(), world_id=world.world.id)
    await add_flag(session, cult.id, EntityFlag.OUTER_CULT, 1)
    await join_outer_cult(ctx, bearer)
    member = await session.scalar(select(BondRow).where(BondRow.source_node_id == bearer.id, BondRow.kind == BondKind.MEMBER_OF))
    assert member is not None and member.target_node_id == cult.id


async def test_one_who_razes_a_hunting_gods_shrine_may_be_cursed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", rules=tuned_rules(effect_packages={"desecration_pct": 100}))
    town = await settlement(session, "Brookhold", world, world.regions[0])
    raider = await mortal(session, "Rask", world, town.id)
    shrine = await entity(session, "The Antler Stone", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    assert await shrine_god(ctx, shrine) is None
    assert await desecration_curse(ctx, shrine, raider.id) is None
    await connect(session, shrine.id, world.son.id, BondKind.WORSHIPS, 1)
    assert await shrine_god(ctx, shrine) == world.son.id
    world.son.domain_primary = Domain.HUNT
    assert await desecrator_of(ctx, raider.id) is raider
    assert await desecrator_of(ctx, town.id) is raider
    curse = await desecration_curse(ctx, shrine, town.id)
    assert curse is not None and curse.package is vengeance_package(ctx, world.son) and curse.bearer_node_id == raider.id
    session.add(StructureProfileRow(structure_entity_id=shrine.id, kind=StructureKind.SHRINE, dedicated_son_id=world.son.id, locked=[]))
    await session.flush()
    assert await shrine_god(ctx, shrine) == world.son.id
    assert (await session.scalars(select(AfflictionRow).where(AfflictionRow.bearer_node_id == raider.id))).first() is not None
