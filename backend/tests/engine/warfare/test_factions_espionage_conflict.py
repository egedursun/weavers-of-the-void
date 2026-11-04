import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import GodConflictRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.stats import StatBlock
from aerona.engine.phases.espionage import SpyOperation, espionage, order_spy_operation
from aerona.engine.phases.factions import FactionKind, decree_faction, dissolve_faction, factions
from aerona.engine.services.community_relations import relation, set_relation
from aerona.engine.services.conflict import foreign_god_war
from aerona.rules.registry import Rules
from tests.db.factories import make_son
from tests.engine.warfare.factories import bond, make, make_ctx, society, tune


async def test_warrior_society_founds_a_brotherhood(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), factions={"faction_chance": 100, "faction_min_population": 100, "revolt_disband_chance": 0})
    town = await make(session, "Forgeholm", EntityType.SETTLEMENT, world_id, population=3000, prosperity=10)
    await society(session, town.id, warrior=30.0)
    await factions(make_ctx(session, rules))
    faction = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.FACTION))
    assert faction is not None and faction.engine_kind is EngineKind.WARRIOR_BAND and faction.affiliated_entity_id == town.id
    assert faction.location_id == town.id
    assert await BondRepository(session).exists_between(faction.id, town.id, BondKind.DESCENDS_FROM)
    with pytest.raises(ConflictError):
        await decree_faction(make_ctx(session, rules), town.id, FactionKind.BROTHERHOOD)


async def test_idle_uprisings_disband_and_factions_can_be_dissolved(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), factions={"revolt_disband_chance": 100, "revolt_disband_min_age": 1, "faction_chance": 0})
    rebels = await make(session, "Grey Rebels", EntityType.FACTION, world_id, engine_kind=EngineKind.REBELS, strength=20)
    guild = await make(session, "Old Guild", EntityType.FACTION, world_id, strength=20)
    await factions(make_ctx(session, rules, epoch=5))
    assert rebels.status is EntityStatus.DEAD
    await dissolve_faction(make_ctx(session, rules, epoch=5), guild.id)
    assert guild.status is EntityStatus.DEAD


async def test_influential_faction_weaves_a_network_and_gets_caught(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), espionage={"spy_net_chance": 100, "spy_min_sway": 10, "spy_capture_base_pct": 100, "spy_war_chance": 0})
    spies = await make(session, "Whisper Guild", EntityType.FACTION, world_id, sway=80)
    target = await make(session, "Proud City", EntityType.SETTLEMENT, world_id, population=900, defense=40)
    await set_relation(make_ctx(session, rules), spies.id, target.id, -60, "rivalry")
    await espionage(make_ctx(session, rules, epoch=4))
    assert await BondRepository(session).exists_between(spies.id, target.id, BondKind.SPY_NETWORK)
    await espionage(make_ctx(session, rules, epoch=5))
    assert not await BondRepository(session).exists_between(spies.id, target.id, BondKind.SPY_NETWORK)
    assert await relation(session, rules, spies.id, target.id) == -60 - rules.espionage.spy_caught_relation_loss


async def test_ordered_spy_operation_steals_knowledge(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    spies = await make(session, "Whisper Guild", EntityType.FACTION, world_id, sway=80)
    target = await make(session, "Proud City", EntityType.SETTLEMENT, world_id, population=900, defense=40)
    lore = await make(session, "Bronze Casting", EntityType.KNOWLEDGE, world_id, level=2)
    await bond(session, target.id, lore.id, BondKind.KNOWS)
    text = await order_spy_operation(ctx, spies.id, target.id, SpyOperation.STEAL_KNOWLEDGE)
    assert "Bronze Casting" in text
    assert await BondRepository(session).exists_between(spies.id, lore.id, BondKind.KNOWS)


async def test_foreign_god_war_goes_through_the_shared_resolver(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    son = await make_son(session, "Thalor", world_id)
    god = await ForeignGodRepository(session).create(
        ForeignGodDraft(name="Old Mire", world_id=world_id, domain_primary=Domain.SEA, power=10, stats=StatBlock.uniform(20), created_epoch=1)
    )
    result = await foreign_god_war(ctx, son.id, god.id)
    assert await session.scalar(select(GodConflictRow)) is not None
    assert result.god_status in {ForeignGodStatus.DEFEATED, ForeignGodStatus.DEAD, ForeignGodStatus.AWAKE}
    son.status = SonStatus.ASLEEP
    with pytest.raises(ConflictError):
        await foreign_god_war(ctx, son.id, god.id)
