import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.quests import QuestAim, QuestTargetKind
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import ClimateEra, Discovery, SkyEventKind, StarType
from aerona.domain.models.entity_stats import ItemStats, RegionStats, SpiritStats
from aerona.rules.registry import Rules
from aerona.services.player import cosmic
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, add_world, bond, make_entity


async def _route(scope: PlayerScope, first: int, second: int) -> RouteRow:
    outcome = await cosmic.open_route(scope, cosmic.OpenRoute(first_world_id=first, second_world_id=second, method=TravelMethod.ANCIENT_GATE))
    route = await scope.session.get(RouteRow, outcome.created_ids[0])
    assert route is not None
    return route


async def test_route_actions_cost_and_effect(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    world.creator.essence = 1000
    other = await add_world(session, "Kesh")
    route = await _route(scope, world.world.id, other.id)
    severed = await cosmic.route_action(scope, cosmic.RouteCommand(route_id=route.id, action=cosmic.RouteAction.SEVER, duration=3))
    assert not route.active
    assert severed.essence_spent == rules.beyond.sever_route_cost
    await cosmic.route_action(scope, cosmic.RouteCommand(route_id=route.id, action=cosmic.RouteAction.REOPEN))
    assert route.active
    with pytest.raises(ValidationFailedError):
        await cosmic.route_action(scope, cosmic.RouteCommand(route_id=route.id, action=cosmic.RouteAction.REVEAL))
    assert await action_kinds(session) == [ActionKind.REPAIR_ROUTE, ActionKind.SEVER_ROUTE, ActionKind.REPAIR_ROUTE]


async def test_hang_seal_cleanse_and_rekindle(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    world.creator.essence = 1000
    hung = await cosmic.hang_star(scope, cosmic.HangStar())
    star = await session.get(StarRow, hung.created_ids[0])
    assert star is not None and "Star" in star.name
    assert hung.essence_spent == rules.cosmic_costs.ignite_star
    other = await add_world(session, "Kesh")
    route = await _route(scope, world.world.id, other.id)
    world.world.leakage = 30
    other.leakage = 30
    await cosmic.seal_gate(scope, cosmic.RouteTarget(route_id=route.id))
    assert not route.active and world.world.leakage < 30
    leak = world.world.leakage
    if leak:
        await cosmic.cleanse_leak(scope, cosmic.WorldTarget(world_id=world.world.id))
        assert world.world.leakage < leak
    star.star_type = StarType.DEAD_STAR
    await cosmic.rekindle(scope, cosmic.StarTarget(star_id=star.id))
    assert star.star_type is StarType.REBORN_STAR
    with pytest.raises(ValidationFailedError):
        await cosmic.rekindle(scope, cosmic.StarTarget(star_id=star.id))


async def test_soul_bind_quest_and_sky(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    world.creator.essence = 1000
    soul = await make_entity(
        session, "Wandering Shade", EntityType.SPIRIT, world_id=world.world.id, location_id=world.region.id, stats=SpiritStats(strength=20)
    )
    sword = await make_entity(session, "Ashblade", EntityType.ITEM, world_id=world.world.id, location_id=world.region.id, stats=ItemStats(might=40))
    await cosmic.bind_soul(scope, cosmic.SoulBind(soul_id=soul.id, target_id=sword.id))
    assert soul.status is not EntityStatus.CANON
    with pytest.raises(ValidationFailedError):
        await cosmic.legendary_quest(scope, cosmic.LegendaryQuest(aim=QuestAim.FIND, target_kind=QuestTargetKind.KNOWLEDGE))
    sun = await session.get(StarRow, world.world.star_id)
    assert sun is not None
    sun.star_type = StarType.DEAD_STAR
    quest = await cosmic.legendary_quest(scope, cosmic.LegendaryQuest(aim=QuestAim.RESTORE, target_kind=QuestTargetKind.STAR))
    assert isinstance(quest.values["thread_id"], int)
    with pytest.raises(ValidationFailedError):
        await cosmic.order_sky_event(scope, cosmic.SkyEvent(kind=SkyEventKind.ECLIPSE))
    sky = await cosmic.order_sky_event(scope, cosmic.SkyEvent(kind=SkyEventKind.COMET, world_id=world.world.id))
    assert sky.message


async def test_exile_and_pardon(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    calm = await make_entity(session, "Calm Vale", EntityType.REGION, world_id=other.id, stats=RegionStats(danger=5))
    wild = await make_entity(session, "Wild Vale", EntityType.REGION, world_id=other.id, stats=RegionStats(danger=90))
    folk = await make_entity(session, "Orvtown", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    child = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id, location_id=folk.id)
    rival = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, folk.id, rival.id, BondKind.ENEMY)
    outcome = await cosmic.exile(scope, cosmic.Exile(entity_id=folk.id, world_id=other.id))
    assert folk.location_id == wild.id and folk.world_id == other.id and child.world_id == other.id
    assert calm.id != folk.location_id
    assert outcome.values["severed"] == 1
    assert not await BondRepository(session).exists_between(folk.id, rival.id, BondKind.ENEMY)
    assert await EntityRepository(session).has_flag(folk.id, EntityFlag.EXILE)
    await cosmic.pardon(scope, cosmic.EntityTarget(entity_id=folk.id))
    assert not await EntityRepository(session).has_flag(folk.id, EntityFlag.EXILE)
    with pytest.raises(ValidationFailedError):
        await cosmic.pardon(scope, cosmic.EntityTarget(entity_id=folk.id))


async def test_orbit_star_edit_and_delete(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    with pytest.raises(ValidationFailedError):
        await cosmic.set_orbit(scope, cosmic.Orbit(world_id=other.id, parent_world_id=other.id))
    await cosmic.set_orbit(scope, cosmic.Orbit(world_id=other.id, parent_world_id=world.world.id))
    assert other.parent_world_id == world.world.id and other.star_id == world.world.star_id
    with pytest.raises(ValidationFailedError):
        await cosmic.set_orbit(scope, cosmic.Orbit(world_id=world.world.id, parent_world_id=other.id))
    own_star = await session.scalar(select(StarRow).where(StarRow.name == "Kesh Sun"))
    assert own_star is not None
    await cosmic.edit_star(scope, cosmic.EditStar(star_id=own_star.id, brightness=500, name="Pale Kesh"))
    assert own_star.brightness == 100 and own_star.name == "Pale Kesh"
    star_id = own_star.id
    outcome = await cosmic.delete_star(scope, cosmic.StarTarget(star_id=star_id))
    assert await session.get(StarRow, star_id) is None
    assert outcome.ledger_entry_id is not None
    assert world.world.star_id is not None
    with pytest.raises(ValidationFailedError):
        await cosmic.delete_star(scope, cosmic.StarTarget(star_id=world.world.star_id))


async def test_climate_resource_and_deposit(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    await cosmic.command_climate(scope, cosmic.Climate(era=ClimateEra.DROUGHT, world_id=world.world.id))
    assert world.world.climate_era is ClimateEra.DROUGHT
    assert world.world.climate_epochs_left == rules.god_hand.decree_climate_epochs
    with pytest.raises(ValidationFailedError):
        await cosmic.command_climate(scope, cosmic.Climate(era=ClimateEra.RAIN, epochs=rules.god_hand.decree_climate_max_epochs + 1))
    with pytest.raises(ValidationFailedError):
        await cosmic.open_deposit(scope, cosmic.OpenDeposit(place_id=world.region.id))
    await cosmic.define_resource(scope, cosmic.DefineResource(name="Starsalt", rule="burns to fold space"))
    deposit = await cosmic.open_deposit(scope, cosmic.OpenDeposit(place_id=world.region.id))
    assert deposit.created_ids


async def test_forget_world_refuses_first(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    await cosmic.forget(scope, cosmic.WorldTarget(world_id=other.id))
    assert other.discovery is Discovery.FORGOTTEN
    with pytest.raises(ValidationFailedError):
        await cosmic.forget(scope, cosmic.WorldTarget(world_id=world.world.id))
