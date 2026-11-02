from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.models.entity_stats import ItemStats, LegendStats, SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.records import RecordSpec, heir_of, introduce, open_record, retire, sweep_dead_bonds
from aerona.engine.records import death_path, retire_record, sweep_bonds_of_the_dead
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, mortal, settlement


def test_introduction_names_kind_and_place() -> None:
    assert introduce("Ashford", "settlement", "Greenvale", "Founded by migrants.") == "Ashford, a settlement in Greenvale. Founded by migrants."
    assert introduce("Old Ember", "ancestor spirit", None, "It lingers.") == "Old Ember, an ancestor spirit. It lingers."


async def test_engine_records_are_pending_unique_and_placed(ctx: TickContext, world: CoreWorld) -> None:
    spec = RecordSpec(EntityType.SETTLEMENT, "Kethrani", "A camp.", SettlementStats(population=50), 2, location_id=world.regions[0].id)
    first = await open_record(ctx.session, ctx.epoch, spec)
    assert first.name == "Kethrani II"
    assert first.origin is EntityOrigin.ENGINE
    assert first.pending_name
    assert first.description.startswith("Kethrani II, a settlement in Amberreach.")
    legend = await open_record(ctx.session, ctx.epoch, RecordSpec(EntityType.LEGEND, "Song of Stone", "Sung.", LegendStats(spread=10), 1, location_id=first.id))
    assert legend.location_id is None
    trinket = await open_record(ctx.session, ctx.epoch, RecordSpec(EntityType.ITEM, "Charm", "Small.", ItemStats(), 1, location_id=first.id))
    assert trinket.location_id == first.id


async def test_dead_bond_sweep_passes_property_and_closes_state(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[1])
    ruler = await mortal(session, "Orla", world, town.id)
    child = await mortal(session, "Brin", world, town.id)
    other_world, _ = await add_empty_world(session)
    await bond(session, child.id, ruler.id, BondKind.DESCENDS_FROM)
    await bond(session, ruler.id, town.id, BondKind.RULES)
    await bond(session, ruler.id, world.son.id, BondKind.WORSHIPS)
    sword = await entity(session, "Ember Edge", EntityType.ITEM, ItemStats(damage=40), world_id=world.world.id, location_id=town.id)
    await bond(session, ruler.id, sword.id, BondKind.OWNS)
    await bond(session, town.id, ruler.id, BondKind.PROTECTS)
    session.add(
        RouteRow(
            world_a_id=world.world.id,
            world_b_id=other_world.id,
            method=TravelMethod.ANCIENT_GATE,
            duration_epochs=1,
            danger=10,
            controller_entity_id=ruler.id,
            created_epoch=1,
        )
    )
    await retire(session, ruler, ctx.epoch, "Fell from a cliff.")
    assert (await heir_of(session, ruler)) == child
    result = await sweep_dead_bonds(session, ctx.epoch)
    assert result.transferred == 2
    bonds = BondRepository(session)
    assert await bonds.exists_between(child.id, town.id, BondKind.RULES)
    assert await bonds.exists_between(child.id, sword.id, BondKind.OWNS)
    assert not await bonds.exists_between(ruler.id, world.son.id, BondKind.WORSHIPS)
    assert not await bonds.exists_between(town.id, ruler.id, BondKind.PROTECTS)
    route = await session.scalar(select(RouteRow))
    assert route is not None and route.controller_entity_id is None


async def test_sweep_phase_reports_inheritance(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[1])
    elder = await mortal(session, "Aldo", world, town.id)
    await bond(session, elder.id, world.species.id, BondKind.TAMED)
    await retire(session, elder, ctx.epoch, "Faded.")
    result = await sweep_bonds_of_the_dead(ctx)
    assert result.closed >= 1


async def test_death_path_for_other_records_leaves_a_killed_bond(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    hunter = await mortal(session, "Tamsin", world, world.regions[2].id)
    assert await death_path(ctx, world.species, "was hunted to the last", killer_id=hunter.id)
    assert world.species.status is EntityStatus.DEAD
    killed = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.KILLED, BondRow.target_node_id == world.species.id))
    assert killed is not None and killed.source_node_id == hunter.id
    assert not await death_path(ctx, world.species, "again")


async def test_retire_record_by_hand(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    keeper = await mortal(session, "Ulla", world, world.regions[0].id)
    await retire_record(ctx, keeper.id, "was taken by the gods")
    assert keeper.status is EntityStatus.DEAD
    gone = await retire_record(ctx, world.language.id, "fell silent", EntityStatus.DESTROYED)
    assert gone.status is EntityStatus.DESTROYED
    states = set(await session.scalars(select(BondRow.state).where(BondRow.target_node_id == world.language.id)))
    assert BondState.ACTIVE not in states
