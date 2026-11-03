from aerona.db.tables.entities import EntityFlagRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.models.entity_stats import PlaceStats, StructureStats
from aerona.engine.phases.dark_ages import dark_age_status, dark_ages, drift_spread, spread_target
from aerona.engine.phases.society_economy import set_class_shares
from aerona.engine.phases.wonders import wonders
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import set_relation
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, bonded, chronicle_keys, context, knowledge, link, make, people, settlement, son, tuned

RULES = Rules()


async def test_spread_drifts_toward_knowers(realm: Realm) -> None:
    lore = await knowledge(realm, "Herbs", KnowledgeBranch.MEDICINE, spread=10)
    settings = RULES.knowledge
    assert spread_target(RULES, 3, lost=False) == min(100, settings.spread_base + 3 * settings.spread_per_knower)
    assert spread_target(RULES, 3, lost=True) == 0
    assert drift_spread(RULES, lore, 9, lost=False) == 10 + settings.spread_step
    assert drift_spread(RULES, lore, 0, lost=True) == 10


async def test_devastated_communities_forget_and_knowledge_gets_lost(realm: Realm) -> None:
    ruined = await people(realm, "Ruined", prosperity=1)
    lore = await knowledge(realm, "Bronze", KnowledgeBranch.METALLURGY)
    await link(realm.session, ruined.id, lore.id, BondKind.KNOWS)
    ctx = context(realm.session, tuned(knowledge={"dark_age_forget_chance": 100}))
    status = await dark_age_status(realm.session, ctx.rules, ctx.epoch, ruined.id)
    assert status.devastated and not status.protected
    await dark_ages(ctx)
    assert not await bonded(realm.session, ruined.id, lore.id, BondKind.KNOWS)
    assert await realm.session.get(EntityFlagRow, (lore.id, EntityFlag.LOST)) is not None
    keys = await chronicle_keys(realm.session)
    assert "dark_ages.forgotten" in keys
    assert "dark_ages.lost" in keys


async def test_scribes_protect_and_rediscover(realm: Realm) -> None:
    learned = await people(realm, "Learned", prosperity=1)
    ctx = context(realm.session, tuned(knowledge={"dark_age_forget_protected_chance": 0, "relic_decipher_chance": 100}))
    await set_class_shares(ctx, learned.id, {SocialClass.SCRIBE: 60.0, SocialClass.FARMER: 40.0})
    assert (await dark_age_status(realm.session, ctx.rules, ctx.epoch, learned.id)).protected
    lore = await knowledge(realm, "Star Charts", KnowledgeBranch.ASTRONOMY)
    realm.session.add(EntityFlagRow(entity_id=lore.id, flag=EntityFlag.LOST, epoch=1))
    ruin = await make(realm.session, "Broken Tower", EntityType.PLACE, PlaceStats(), world_id=realm.world.id, location_id=realm.region.id)
    realm.session.add(EntityFlagRow(entity_id=ruin.id, flag=EntityFlag.RUIN, epoch=1))
    await realm.session.flush()
    await dark_ages(ctx)
    assert await bonded(realm.session, learned.id, lore.id, BondKind.KNOWS)
    assert await realm.session.get(EntityFlagRow, (lore.id, EntityFlag.LOST)) is None
    assert "dark_ages.rediscovered" in await chronicle_keys(realm.session)


async def test_wonders_reward_owners_and_stir_envy(realm: Realm) -> None:
    owner = await settlement(realm, "Marvel", prosperity=40)
    rival = await settlement(realm, "Envy")
    god = await son(realm.session, "Builder", realm.world.id)
    await link(realm.session, owner.id, god.id, BondKind.WORSHIPS)
    tower = await make(realm.session, "Sky Tower", EntityType.STRUCTURE, StructureStats(splendor=95), world_id=realm.world.id, location_id=owner.id)
    first, second = sorted((owner.id, rival.id))
    await set_relation(context(realm.session), first, second, -90, "old hatred")
    ctx = context(realm.session, tuned(wonders={"envy_war_chance": 100}))
    await wonders(ctx)
    assert await realm.session.get(EntityFlagRow, (tower.id, EntityFlag.WONDER)) is not None
    assert stat(owner, "prosperity") == 40 + RULES.wonders.prosperity
    assert god.fame == RULES.wonders.renown
    assert await bonded(realm.session, rival.id, owner.id, BondKind.ENEMY)
    relation = await realm.session.get(CommunityRelationRow, (first, second))
    assert relation is not None and relation.value == -90 - RULES.wonders.envy_relation_loss
