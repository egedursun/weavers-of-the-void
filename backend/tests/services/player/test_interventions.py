import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.intervention import Disaster, InterventionKind, Miracle
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.models.entity_stats import KnowledgeStats, SettlementStats
from aerona.rules.registry import Rules
from aerona.services.player import interventions
from aerona.services.player.interventions import BlessingKind, GodPunishmentKind
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, bond, changed_tables, make_entity, make_son


async def test_bless_essence_and_refuse_full(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, essence=10)
    outcome = await interventions.bless(scope, interventions.Bless(son_id=son.id, kind=BlessingKind.ESSENCE))
    assert son.essence == 10 + rules.god_actions.bless_essence_amount
    assert son.loyalty == 60 + rules.god_actions.bless_loyalty
    assert outcome.essence_spent == rules.costs.bless_essence
    son.existence = 100
    with pytest.raises(ValidationFailedError):
        await interventions.bless(scope, interventions.Bless(son_id=son.id, kind=BlessingKind.EXISTENCE))
    await interventions.bless(scope, interventions.Bless(son_id=son.id, kind=BlessingKind.STAT, stat=Stat.WISDOM))
    assert await action_kinds(session) == [ActionKind.BLESS_ESSENCE, ActionKind.BLESS_STAT]


async def test_punishments(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    hp = son.hp
    await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.LIGHTNING))
    assert son.hp < hp
    await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.CHAIN))
    assert son.chained
    with pytest.raises(ValidationFailedError):
        await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.CHAIN))
    await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.EXILE))
    assert son.status is SonStatus.EXILED
    await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.PARDON))
    assert son.status is SonStatus.ACTIVE and not son.chained
    with pytest.raises(ValidationFailedError):
        await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.SUPPRESS))
    son.rebel = True
    son.will, son.strength, son.level = 1, 1, 1
    world.creator.essence = 10_000
    outcome = await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.SUPPRESS))
    assert outcome.values["won"] is True
    assert await action_kinds(session) == [ActionKind.LIGHTNING, ActionKind.CHAIN, ActionKind.EXILE_SON, ActionKind.FORGIVE, ActionKind.SUPPRESS_REBELLION]


async def test_failed_suppression_records_a_distinct_kind(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    son.rebel = True
    son.will, son.strength, son.level = 100, 100, 50
    world.creator.essence = 100
    outcome = await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.SUPPRESS))
    assert outcome.values["won"] is False
    assert son.rebel
    assert await action_kinds(session) == [ActionKind.SUPPRESS_FAILED]


async def test_disaster_creates_event_and_bonds(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    city = await make_entity(
        session,
        "Ashford",
        EntityType.SETTLEMENT,
        world_id=world.world.id,
        location_id=world.region.id,
        stats=SettlementStats(population=900, prosperity=50, defense=40),
    )
    outcome = await interventions.intervene(
        scope, interventions.Intervene(entity_id=world.region.id, action=InterventionKind.DISASTER, disaster=Disaster.FLOOD)
    )
    assert outcome.essence_spent == rules.intervention_costs.disaster
    event = await session.get(EntityRow, outcome.created_ids[0])
    assert event is not None and event.entity_type is EntityType.EVENT
    assert city.stats.model_dump()["population"] < 900
    assert await BondRepository(session).exists_between(event.id, city.id, BondKind.CAUSED)
    assert "entities" in await changed_tables(session, outcome.ledger_entry_id)


async def test_disaster_refuses_non_place(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    with pytest.raises(ValidationFailedError):
        await interventions.intervene(scope, interventions.Intervene(entity_id=mortal.id, action=InterventionKind.DISASTER, disaster=Disaster.FLOOD))


async def test_peace_miracle_ends_wars_and_hostility(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, first.id, second.id, BondKind.ENEMY)
    await interventions.intervene(scope, interventions.Intervene(entity_id=first.id, action=InterventionKind.MIRACLE, miracle=Miracle.PEACE))
    assert not await BondRepository(session).exists_between(first.id, second.id, BondKind.ENEMY)
    with pytest.raises(ValidationFailedError):
        await interventions.intervene(scope, interventions.Intervene(entity_id=first.id, action=InterventionKind.MIRACLE, miracle=Miracle.PEACE))


async def test_protection_miracle_shields(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await interventions.intervene(scope, interventions.Intervene(entity_id=city.id, action=InterventionKind.MIRACLE, miracle=Miracle.PROTECTION))
    assert await EntityRepository(session).has_flag(city.id, EntityFlag.PROTECTED_FROM_DISASTER)


async def test_teach_and_forget_knowledge(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    lore = await make_entity(session, "Star Charts", EntityType.KNOWLEDGE, world_id=world.world.id, stats=KnowledgeStats(level=1, spread=10))
    await interventions.intervene(scope, interventions.Intervene(entity_id=city.id, action=InterventionKind.TEACH_KNOWLEDGE, knowledge_id=lore.id))
    assert [item.id for item in await interventions.known_knowledge(scope, city.id)] == [lore.id]
    with pytest.raises(ValidationFailedError):
        await interventions.intervene(scope, interventions.Intervene(entity_id=city.id, action=InterventionKind.TEACH_KNOWLEDGE, knowledge_id=lore.id))
    await interventions.set_knowledge(scope, interventions.SetKnowledge(entity_id=city.id, knowledge_id=lore.id, known=False))
    assert await interventions.known_knowledge(scope, city.id) == []


async def test_curse_marks_and_withers(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await interventions.intervene(scope, interventions.Intervene(entity_id=city.id, action=InterventionKind.CURSE))
    assert await EntityRepository(session).has_flag(city.id, EntityFlag.CURSED)
    refreshed = await session.scalar(select(EntityRow).where(EntityRow.id == city.id))
    assert refreshed is not None and refreshed.stats.model_dump()["prosperity"] == 50 - rules.god_actions.curse_stat_loss
