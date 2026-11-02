import pytest
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import HeroQuestKind, HeroQuestStatus
from aerona.domain.models.entity_stats import ItemStats, SpeciesStats
from aerona.engine.phases.heroes import (
    assign_apprentice,
    hero_births,
    heroes,
    is_hero,
    raise_hero,
    recall_hero,
    resolve_quest,
    send_on_quest,
    success_chance,
)
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, bonded, chronicle_keys, context, knowledge, link, make, mortal, named, people, settlement, son, tuned

RULES = Rules()


async def lost_lore(realm: Realm) -> EntityRow:
    lore = await knowledge(realm, "Old Lore", KnowledgeBranch.MEDICINE)
    realm.session.add(EntityFlagRow(entity_id=lore.id, flag=EntityFlag.LOST, epoch=1))
    await realm.session.flush()
    return lore


async def test_hero_test_and_success_chance(realm: Realm) -> None:
    strong = await mortal(realm, "Strong", strength=60, agility=40)
    weak = await mortal(realm, "Weak", strength=10, agility=10, intellect=0)
    knight = await mortal(realm, "Knight", strength=10, agility=10, role=MortalRole.KNIGHT)
    assert is_hero(RULES, strong, set(), set())
    assert not is_hero(RULES, weak, set(), set())
    assert is_hero(RULES, weak, {weak.id}, set())
    assert is_hero(RULES, knight, set(), set())
    assert not is_hero(RULES, strong, set(), {strong.id})
    assert success_chance(RULES, weak, 0, chosen=False) == RULES.heroes.quest_success_min_pct / 100
    assert success_chance(RULES, strong, 10, chosen=True) == RULES.heroes.quest_success_max_pct / 100


async def test_populous_people_bear_heroes(realm: Realm) -> None:
    folk = await people(realm, "Many", population=20000)
    god = await son(realm.session, "Guide", realm.world.id)
    await link(realm.session, folk.id, god.id, BondKind.WORSHIPS)
    ctx = context(realm.session, tuned(heroes={"birth_chance": 100}))
    await hero_births(ctx)
    born = [item for item in await named(realm.session, EntityType.MORTAL) if item.mortal_role is MortalRole.HERO]
    assert len(born) == 1
    assert await bonded(realm.session, born[0].id, folk.id, BondKind.DESCENDS_FROM)
    assert await bonded(realm.session, born[0].id, god.id, BondKind.WORSHIPS)
    assert "heroes.birth" in await chronicle_keys(realm.session)


async def test_knowledge_quest_starts_and_succeeds(realm: Realm) -> None:
    home = await settlement(realm, "Keep")
    hero = await mortal(realm, "Seeker", location_id=home.id, role=MortalRole.HERO)
    await link(realm.session, hero.id, home.id, BondKind.PROTECTS)
    lore = await lost_lore(realm)
    start = tuned(heroes={"quest_chance": 100})
    await heroes(context(realm.session, start, epoch=3))
    quest = await realm.session.scalar(select(HeroQuestRow).where(HeroQuestRow.hero_entity_id == hero.id))
    assert quest is not None and quest.kind is HeroQuestKind.KNOWLEDGE
    assert await bonded(realm.session, hero.id, lore.id, BondKind.PURSUES)
    finish = tuned(heroes={"quest_success_min_pct": 100, "quest_chance": 0})
    await heroes(context(realm.session, finish, epoch=4))
    assert quest.status is HeroQuestStatus.SUCCEEDED
    assert await bonded(realm.session, home.id, lore.id, BondKind.KNOWS)
    assert await realm.session.get(EntityFlagRow, (lore.id, EntityFlag.LOST)) is None
    assert not await bonded(realm.session, hero.id, lore.id, BondKind.PURSUES)


async def test_failed_quest_can_kill_or_wound(realm: Realm) -> None:
    hero = await mortal(realm, "Doomed", role=MortalRole.HERO, hp=80)
    await lost_lore(realm)
    ctx = context(realm.session, tuned(heroes={"quest_success_max_pct": 0, "quest_death_chance": 0}), epoch=3)
    await send_on_quest(ctx, hero.id)
    status = await resolve_quest(context(realm.session, ctx.rules, epoch=4), hero.id)
    assert status is HeroQuestStatus.ACTIVE
    assert stat(hero, "hp") == 80 - RULES.heroes.quest_epoch_hp_loss
    deadly = context(realm.session, tuned(heroes={"quest_success_max_pct": 0, "quest_death_chance": 100}), epoch=5)
    assert await resolve_quest(deadly, hero.id) is HeroQuestStatus.DIED
    assert hero.status is EntityStatus.DEAD


async def test_companions_and_apprentices(realm: Realm) -> None:
    home = await settlement(realm, "Hall")
    first = await mortal(realm, "Ash", location_id=home.id, role=MortalRole.HERO, age=60, lifespan=70, charisma=90)
    second = await mortal(realm, "Birch", location_id=home.id, role=MortalRole.HERO)
    await link(realm.session, first.id, home.id, BondKind.PROTECTS)
    await link(realm.session, second.id, home.id, BondKind.PROTECTS)
    blade = await make(realm.session, "Old Blade", EntityType.ITEM, ItemStats(damage=80), world_id=realm.world.id, location_id=home.id)
    await link(realm.session, first.id, blade.id, BondKind.OWNS)
    rules = tuned(heroes={"quest_chance": 0, "companion_chance": 100, "apprentice_chance": 100, "weapon_bequest_chance": 100})
    await heroes(context(realm.session, rules))
    assert await bonded(realm.session, first.id, second.id, BondKind.COMPANION)
    apprentices = [item for item in await named(realm.session, EntityType.MORTAL) if item.engine_kind is EngineKind.APPRENTICE]
    assert len(apprentices) == 1
    assert await bonded(realm.session, apprentices[0].id, first.id, BondKind.APPRENTICE_OF)
    assert await bonded(realm.session, apprentices[0].id, blade.id, BondKind.OWNS)
    assert not await bonded(realm.session, first.id, blade.id, BondKind.OWNS)
    with pytest.raises(ValidationFailedError):
        await assign_apprentice(context(realm.session), first.id)


async def test_manual_hero_controls(realm: Realm) -> None:
    folk = await people(realm, "Callers")
    ctx = context(realm.session)
    hero = await raise_hero(ctx, folk.id)
    assert hero.mortal_role is MortalRole.HERO
    with pytest.raises(ValidationFailedError):
        await send_on_quest(ctx, hero.id)
    await lost_lore(realm)
    quest = await send_on_quest(ctx, hero.id, kind=HeroQuestKind.KNOWLEDGE)
    with pytest.raises(ValidationFailedError):
        await send_on_quest(ctx, hero.id)
    recalled = await recall_hero(ctx, hero.id)
    assert recalled.id == quest.id and recalled.status is HeroQuestStatus.ABANDONED
    with pytest.raises(ValidationFailedError):
        await resolve_quest(ctx, hero.id)
    apprentice = await assign_apprentice(ctx, hero.id)
    assert apprentice.mortal_role is MortalRole.APPRENTICE


async def test_hunt_quest_ends_in_an_encounter(realm: Realm) -> None:
    hero = await mortal(realm, "Hunter", role=MortalRole.HUNTER, strength=90, agility=90)
    beast = await make(
        realm.session, "Great Wyrm", EntityType.SPECIES, SpeciesStats(danger=70, strength=10), world_id=realm.world.id, location_id=realm.region.id
    )
    ctx = context(realm.session, epoch=3)
    quest = await send_on_quest(ctx, hero.id, target_id=beast.id)
    assert quest.kind is HeroQuestKind.HUNT
    status = await resolve_quest(context(realm.session, epoch=4), hero.id)
    assert status is HeroQuestStatus.SUCCEEDED
    assert quest.ended_epoch == 4


async def test_vengeance_quest_kills_the_feud_enemy(realm: Realm) -> None:
    home = await settlement(realm, "Avengers")
    foes = await settlement(realm, "Foes")
    hero = await mortal(realm, "Avenger", location_id=home.id, role=MortalRole.HERO)
    victim = await mortal(realm, "Victim", location_id=foes.id)
    await link(realm.session, hero.id, home.id, BondKind.PROTECTS)
    await link(realm.session, victim.id, foes.id, BondKind.PROTECTS)
    first, second = sorted((home.id, foes.id))
    realm.session.add(CommunityRelationRow(entity_a_id=first, entity_b_id=second, value=-80, blood_feud_since_epoch=1))
    await realm.session.flush()
    ctx = context(realm.session, tuned(heroes={"quest_success_min_pct": 100}), epoch=3)
    quest = await send_on_quest(ctx, hero.id, kind=HeroQuestKind.VENGEANCE)
    assert quest.target_node_id == victim.id
    assert await resolve_quest(context(realm.session, ctx.rules, epoch=4), hero.id) is HeroQuestStatus.SUCCEEDED
    assert victim.status is EntityStatus.DEAD
    assert "heroes.quest_vengeance" in await chronicle_keys(realm.session)
