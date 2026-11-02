from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import AddictionRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.models.entity_stats import ResourceStats
from aerona.domain.models.profiles import TravelResource
from aerona.engine.gods.economy import cosmic_economy, resource_mechanics, spend_cosmic_resource
from aerona.engine.gods.queries import owners_of
from aerona.engine.gods.stats import Trait, trait_or
from aerona.rules.registry import Rules
from aerona.services.gods import cosmic_economy as service
from tests.engine.gods.factories import GodsWorld, add_world, bond, chronicle_keys, make_context, make_entity


def _economy(rules: Rules, **changes: int) -> Rules:
    return replace(rules, economy=replace(rules.economy, **changes))


async def _resource(session: AsyncSession, world: GodsWorld, mechanic: ResourceMechanic, abundance: int = 50) -> EntityRow:
    resource = await make_entity(
        session, f"Vein {mechanic.value}", EntityType.RESOURCE, world_id=world.world.id, location_id=world.region.id, stats=ResourceStats(abundance=abundance)
    )
    session.add(ResourceMechanicRow(entity_id=resource.id, mechanic=mechanic))
    await session.flush()
    return resource


async def test_decay_fixed_and_depletion(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    decaying = await _resource(session, world, ResourceMechanic.DECAYING)
    fixed = await _resource(session, world, ResourceMechanic.FIXED)
    cursed = await _resource(session, world, ResourceMechanic.DEPLETION_PRICE, abundance=0)
    await resource_mechanics(make_context(session, rules, 3, "resource_mechanics"))
    assert trait_or(decaying, Trait.ABUNDANCE, 0) == 50 - rules.economy.decay_loss
    assert trait_or(fixed, Trait.ABUNDANCE, 0) == 50 - rules.economy.fixed_regen_clawback
    entities = EntityRepository(session)
    assert await entities.has_flag(cursed.id, EntityFlag.DEPLETED)
    assert await entities.has_flag(world.region.id, EntityFlag.CURSED)
    assert world.cosmos.doom_clock == rules.economy.depletion_apocalypse


async def test_addiction_and_withdrawal_recovery(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _economy(rules, withdrawal_recovery_chance=100)
    resource = await _resource(session, world, ResourceMechanic.ADDICTIVE)
    people = await make_entity(session, "Eaters", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, resource.id, BondKind.OWNS, 1)
    await resource_mechanics(make_context(session, tuned, 1 + rules.economy.addiction_epochs, "resource_mechanics"))
    row = await session.get(AddictionRow, (people.id, resource.id))
    assert row is not None and row.addicted_since_epoch is not None
    assert god_lines.ECONOMY_ADDICTED.key in await chronicle_keys(session)

    await BondRepository(session).close_between(people.id, resource.id, [BondKind.OWNS], 4)
    await resource_mechanics(make_context(session, tuned, 5, "resource_mechanics"))
    assert row.addicted_since_epoch is None
    assert trait_or(people, Trait.PROSPERITY, 0) == 50 - rules.economy.withdrawal_loss


async def test_sentient_resource_leaves_poor_owner(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _economy(rules, sentient_resource_choose_chance=100, sentient_owner_prosperity=101)
    resource = await _resource(session, world, ResourceMechanic.SENTIENT)
    owner = await make_entity(session, "Owners", EntityType.PEOPLE, world_id=world.world.id)
    other = await make_entity(session, "Others", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, owner.id, resource.id, BondKind.OWNS, 1)
    await resource_mechanics(make_context(session, tuned, 3, "resource_mechanics"))
    assert [entity.id for entity in await owners_of(session, resource.id)] == [other.id]


async def test_cosmic_economy_deposits_monopoly_markets(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _economy(rules, cosmic_deposit_chance=100, market_found_chance=100, market_move_chance=0, pirate_chance=100, pirate_min_traffic=0)
    second = await add_world(session, "Kesh")
    await make_entity(session, "Kesh Vale", EntityType.REGION, world_id=second.id)
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    world.cosmos.travel_resource = TravelResource(name="Starsalt", rule="Folds space.")
    session.add(RouteRow(world_a_id=world.world.id, world_b_id=second.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=30, created_epoch=1))
    await session.flush()
    ctx = make_context(session, tuned, 3, "cosmic_economy")
    await cosmic_economy(ctx)
    deposits = list(await session.scalars(select(EntityRow).where(EntityRow.engine_kind == EngineKind.COSMIC_TRAVEL_RESOURCE)))
    assert len(deposits) == 1
    await cosmic_economy(make_context(session, tuned, 4, "cosmic_economy"))
    owners = await owners_of(session, deposits[0].id)
    assert len(owners) == 1
    assert await EntityRepository(session).has_flag(owners[0].id, EntityFlag.COSMIC_MONOPOLY)
    markets = list(await session.scalars(select(EntityRow).where(EntityRow.engine_kind == EngineKind.WANDERING_MARKET)))
    pirates = list(await session.scalars(select(EntityRow).where(EntityRow.engine_kind == EngineKind.VOID_PIRATES)))
    assert len(markets) == 1 and len(pirates) == 1
    route = await session.scalar(select(RouteRow))
    assert route is not None and route.danger > 30
    folded = await spend_cosmic_resource(ctx, owners[0])
    assert folded is not None and owners[0].fold_count == 1


async def test_economy_services(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    world.cosmos.travel_resource = TravelResource(name="Starsalt")
    deposit = await service.open_deposit(session, rules, world.region.id)
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await service.set_deposit_owner(session, rules, deposit.id, people.id)
    assert [owner.id for owner in await owners_of(session, deposit.id)] == [people.id]
    market = await service.found_wandering_market(session, rules, world.region.id)
    disbanded = await service.disband_faction(session, rules, market.id)
    assert disbanded.status.value == "destroyed"
    assert not await service.cure_addiction(session, rules, people.id, deposit.id)
