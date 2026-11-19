from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.warfare import ArmyRow, BattleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent
from aerona.domain.enums.war import BattleOutcome
from aerona.domain.models.entity_stats import ArmyStats, VesselStats
from aerona.engine.lifecycle.ruler_roles import ruler_role
from aerona.engine.phases.casualties import FateWrit, army_experience, disaster_casualties, war_casualties, write_fate
from aerona.engine.phases.travel import choose_intent, swallow_chance
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement
from tests.engine.cycles.factories import context, event, flags, tune, war


async def test_doomed_warrior_falls_and_a_shielded_one_survives(session: AsyncSession, world: CoreWorld) -> None:
    city = await settlement(session, "Redgate", world, world.regions[1])
    doomed = await mortal(session, "Tarn", world, city.id)
    shielded = await mortal(session, "Ilsa", world, city.id)
    for hero in (doomed, shielded):
        hero.mortal_role = MortalRole.WARRIOR
        await bond(session, hero.id, city.id, BondKind.PROTECTS)
    row = await war(session, world, world.people, city)
    record = await event(session, world, "Battle of Redgate", EngineKind.BATTLE, birth_epoch=10)
    session.add(
        BattleRow(
            war_id=row.id,
            epoch=10,
            sequence=1,
            record_entity_id=record.id,
            winner_entity_id=world.people.id,
            loser_entity_id=city.id,
            outcome=BattleOutcome.FIELD_VICTORY,
            gap=12.0,
        )
    )
    await session.flush()
    ctx = context(session, world, tune(Rules(), casualties={"warrior_loser_death": 100, "wound_chance": 0}), 10)
    await write_fate(ctx, doomed.id, FateWrit.DOOM)
    await write_fate(ctx, shielded.id, FateWrit.SHIELD)
    await war_casualties(ctx)
    assert doomed.status is EntityStatus.DEAD
    assert EntityFlag.FELL_IN_BATTLE.value in await flags(session, doomed.id)
    assert shielded.status is EntityStatus.CANON
    assert EntityFlag.FATE_SHIELDED.value not in await flags(session, shielded.id)


async def test_new_army_inherits_veterans(session: AsyncSession, world: CoreWorld) -> None:
    old = await entity(session, "Old Host", EntityType.ARMY, ArmyStats(size=100, morale=50, equipment=40, experience=80), world_id=world.world.id)
    new = await entity(session, "New Host", EntityType.ARMY, ArmyStats(size=100, morale=50, equipment=40, experience=10), world_id=world.world.id)
    session.add_all(
        [
            ArmyRow(entity_id=old.id, owner_entity_id=world.people.id, raised_epoch=3, disbanded_epoch=9),
            ArmyRow(entity_id=new.id, owner_entity_id=world.people.id, raised_epoch=10),
        ]
    )
    await session.flush()
    assert await army_experience(context(session, world, Rules(), 10), []) == 1
    assert stat(new, "experience") == 40


async def test_plague_takes_named_mortals_of_the_struck_people(session: AsyncSession, world: CoreWorld) -> None:
    healer = await mortal(session, "Mira", world, world.regions[0].id)
    await bond(session, healer.id, world.people.id, BondKind.PROTECTS)
    plague = await event(session, world, "Grey Cough", EngineKind.PLAGUE, severity=100, birth_epoch=10)
    await add_flag(session, plague.id, EntityFlag.DISASTER, 10)
    await BondRepository(session).connect(BondDraft(plague.id, world.people.id, BondKind.CAUSED, 10, "300 lives lost"))
    await disaster_casualties(context(session, world, tune(Rules(), casualties={"plague_death": 100}), 10))
    assert healer.status is EntityStatus.DEAD
    assert EntityFlag.DIED_OF_PLAGUE.value in await flags(session, healer.id)


async def test_ruler_role_follows_the_dominant_class(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    city = await settlement(session, "Crownmere", world, world.regions[1])
    assert ruler_role(rules, city, {SocialClass.WARRIOR: 60.0, SocialClass.FARMER: 40.0}) == "warrior-ruler"
    assert ruler_role(rules, city, {SocialClass.WARRIOR: 20.0, SocialClass.FARMER: 25.0}) == "sovereign"
    assert ruler_role(rules, None, {SocialClass.WARRIOR: 60.0}) == "heir"


async def test_road_swallow_chance_depends_on_the_event_and_the_armour(session: AsyncSession, world: CoreWorld) -> None:
    rules = tune(Rules(), travel={"lost_chance": 50, "special_loss_chance": 20, "raid_loss_chance": 10, "armor_risk_divisor": 100})
    ship = await entity(session, "Iron Gull", EntityType.VESSEL, VesselStats(armor=50), world_id=world.world.id)
    assert swallow_chance(rules, JourneyEventKind.LOST_WAY, ship) == 50
    assert swallow_chance(rules, JourneyEventKind.NOT_RELEASED, None) == 20
    assert swallow_chance(rules, JourneyEventKind.PIRATES, None) == 10
    assert swallow_chance(rules, JourneyEventKind.PIRATES, ship) == 5


def test_holy_site_and_warlike_communities_choose_pilgrimage_and_conquest() -> None:
    rules = tune(Rules(), travel={"pilgrimage_intent_chance": 100, "conquest_intent_chance": 100})
    rng = SeededRandom.for_epoch(1, 1, "intent")
    assert choose_intent(rules, rng, 0, False, holy_site=True) is JourneyIntent.PILGRIMAGE
    assert choose_intent(rules, rng, 0, False, warlike=True) is JourneyIntent.CONQUEST
    assert choose_intent(rules, rng, 0, True, holy_site=True, warlike=True) is not JourneyIntent.PILGRIMAGE
