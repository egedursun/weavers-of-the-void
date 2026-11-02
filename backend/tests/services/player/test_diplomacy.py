import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, TravelMethod
from aerona.domain.models.entity_stats import KnowledgeStats
from aerona.engine.services.community_relations import relation
from aerona.rules.registry import Rules
from aerona.services.player import cosmic, diplomacy
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, add_world, bond, make_entity


async def _pair(session: AsyncSession, world: PlayerWorld) -> tuple[EntityRow, EntityRow]:
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    return first, second


async def test_decrees(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    first, second = await _pair(session, world)
    bonds = BondRepository(session)
    start = await relation(session, rules, first.id, second.id)
    await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=second.id, kind=diplomacy.DecreeKind.WAR))
    assert await bonds.exists_between(first.id, second.id, BondKind.ENEMY)
    assert await relation(session, rules, first.id, second.id) < start
    await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=second.id, kind=diplomacy.DecreeKind.PEACE))
    assert not await bonds.exists_between(first.id, second.id, BondKind.ENEMY)
    await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=second.id, kind=diplomacy.DecreeKind.ALLIANCE))
    assert await bonds.exists_between(first.id, second.id, BondKind.ALLY)
    await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=second.id, kind=diplomacy.DecreeKind.TRADE))
    assert await bonds.exists_between(first.id, second.id, BondKind.TRADES_WITH)
    with pytest.raises(ValidationFailedError):
        await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=first.id, kind=diplomacy.DecreeKind.TRADE))
    assert await action_kinds(session) == [ActionKind.DECLARE_WAR, ActionKind.DIPLOMACY, ActionKind.DIPLOMACY, ActionKind.ESTABLISH_TRADE]


async def test_marriage_decree_ends_enmity_and_seals_an_alliance(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await _pair(session, world)
    bonds = BondRepository(session)
    await bond(session, first.id, second.id, BondKind.ENEMY)
    outcome = await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=second.id, kind=diplomacy.DecreeKind.MARRIAGE))
    assert not await bonds.exists_between(first.id, second.id, BondKind.ENEMY)
    assert await bonds.exists_between(first.id, second.id, BondKind.ALLY)
    assert "Marriage" in outcome.message
    assert await action_kinds(session) == [ActionKind.DIPLOMACY]
    with pytest.raises(ConflictError):
        await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=second.id, kind=diplomacy.DecreeKind.MARRIAGE))


async def test_decree_needs_reach(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    far_region = await make_entity(session, "Kesh Vale", EntityType.REGION, world_id=other.id)
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    far = await make_entity(session, "Keshtown", EntityType.SETTLEMENT, world_id=other.id, location_id=far_region.id)
    with pytest.raises(ValidationFailedError):
        await diplomacy.decree(scope, diplomacy.Decree(entity_id=first.id, target_id=far.id, kind=diplomacy.DecreeKind.ALLIANCE))


async def test_expedition_guards(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    other = await add_world(session, "Kesh")
    await make_entity(session, "Kesh Vale", EntityType.REGION, world_id=other.id)
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    opened = await cosmic.open_route(scope, cosmic.OpenRoute(first_world_id=world.world.id, second_world_id=other.id, method=TravelMethod.ANCIENT_GATE))
    route_id = opened.created_ids[0]
    with pytest.raises(ValidationFailedError):
        await diplomacy.expedition(scope, diplomacy.Expedition(entity_id=town.id, route_id=route_id, percent=rules.god_hand.decree_expedition_max_pct + 1))
    town.civ_tier = 5
    lore = await EntityRepository(session).create(
        EntityDraft(
            name="Gate Lore",
            entity_type=EntityType.KNOWLEDGE,
            description="The true names of the gates.",
            stats=KnowledgeStats(level=1),
            power_level=2,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world.world.id,
            knowledge_branch=KnowledgeBranch.GATE_LORE,
            split_title=False,
        )
    )
    await bond(session, town.id, lore.id, BondKind.KNOWS)
    outcome = await diplomacy.expedition(scope, diplomacy.Expedition(entity_id=town.id, route_id=route_id, intent=JourneyIntent.TRADE))
    journey = await session.get(JourneyRow, outcome.values["journey_id"])
    assert journey is not None and journey.traveller_entity_id == town.id
    with pytest.raises(ValidationFailedError):
        await diplomacy.expedition(scope, diplomacy.Expedition(entity_id=town.id, route_id=route_id))


async def test_explore_and_discovery_round(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    outcome = await diplomacy.explore(scope, diplomacy.Explore(entity_id=town.id, kind=diplomacy.LandKind.PLACE))
    land = await session.get(EntityRow, outcome.created_ids[0])
    assert land is not None and land.entity_type in (EntityType.PLACE, EntityType.REGION)
    with pytest.raises(ValidationFailedError):
        await diplomacy.explore(scope, diplomacy.Explore(entity_id=world.region.id))
    round_outcome = await diplomacy.discovery_round(scope, diplomacy.DiscoveryRound(world_id=world.world.id))
    assert "discovery round" in round_outcome.message


async def test_federation(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await _pair(session, world)
    await bond(session, first.id, second.id, BondKind.ENEMY)
    with pytest.raises(ValidationFailedError):
        await diplomacy.found_federation(scope, diplomacy.Federation(member_ids=(first.id,)))
    outcome = await diplomacy.found_federation(scope, diplomacy.Federation(member_ids=(first.id, second.id)))
    faction = await session.get(EntityRow, outcome.created_ids[0])
    assert faction is not None and faction.entity_type is EntityType.FACTION
    bonds = BondRepository(session)
    assert await bonds.exists_between(first.id, second.id, BondKind.ALLY)
    assert not await bonds.exists_between(first.id, second.id, BondKind.ENEMY)
    members = list(await session.scalars(select(EntityRow.id).where(EntityRow.id.in_([first.id, second.id]))))
    assert len(members) == 2
    assert await EntityRepository(session).has_flag(faction.id, EntityFlag.FEDERATION)
