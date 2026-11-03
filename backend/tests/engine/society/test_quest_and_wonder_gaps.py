from aerona.core.errors import ValidationFailedError
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.war import HeroQuestKind, HeroQuestStatus
from aerona.domain.models.entity_stats import ItemStats, StructureStats
from aerona.engine.phases.heroes import resolve_quest, send_on_quest
from aerona.engine.phases.wonders import wonders
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import set_relation
from tests.engine.society.factories import Realm, bonded, chronicle_keys, context, link, make, mortal, people, settlement, tuned


async def test_thread_quest_is_offered_for_an_open_story_and_reveals_the_truth(realm: Realm) -> None:
    home = await settlement(realm, "Keep")
    elder = await people(realm, "Elders")
    hero = await mortal(realm, "Seeker", location_id=home.id, role=MortalRole.HERO)
    await link(realm.session, hero.id, home.id, BondKind.PROTECTS)
    thread = ThreadRow(epoch=1, text="A rumour of a buried bell.", status=ThreadStatus.OPEN)
    realm.session.add(thread)
    await realm.session.flush()
    realm.session.add_all(
        [
            ThreadLinkRow(thread_id=thread.id, entity_id=home.id, role=ThreadLinkRole.RELATED, epoch=1),
            ThreadLinkRow(thread_id=thread.id, entity_id=elder.id, role=ThreadLinkRole.RELATED, epoch=1),
        ]
    )
    await realm.session.flush()
    ctx = context(realm.session, epoch=3)
    quest = await send_on_quest(ctx, hero.id, kind=HeroQuestKind.THREAD)
    assert quest.kind is HeroQuestKind.THREAD and quest.thread_id == thread.id
    assert await bonded(realm.session, hero.id, quest.target_node_id or 0, BondKind.PURSUES)
    status = await resolve_quest(context(realm.session, epoch=4), hero.id, succeed=True)
    assert status is HeroQuestStatus.SUCCEEDED
    assert not await bonded(realm.session, hero.id, quest.target_node_id or 0, BondKind.PURSUES)
    keys = await chronicle_keys(realm.session)
    assert "heroes.quest_start" in keys and "heroes.quest_thread" in keys
    assert stat(hero, "charisma") == 50 + ctx.rules.heroes.quest_charisma_gain


async def test_no_thread_quest_exists_without_an_open_thread(realm: Realm) -> None:
    home = await settlement(realm, "Keep")
    hero = await mortal(realm, "Seeker", location_id=home.id, role=MortalRole.HERO)
    await link(realm.session, hero.id, home.id, BondKind.PROTECTS)
    assert await _offered(realm, hero.id, HeroQuestKind.THREAD) is False


async def _offered(realm: Realm, hero_id: int, kind: HeroQuestKind) -> bool:
    try:
        await send_on_quest(context(realm.session, epoch=3), hero_id, kind=kind)
    except ValidationFailedError:
        return False
    return True


async def test_relic_quest_targets_an_ownerless_item_and_the_hero_takes_it_up(realm: Realm) -> None:
    hero = await mortal(realm, "Finder", role=MortalRole.HERO)
    relic = await make(realm.session, "Lost Crown", EntityType.ITEM, ItemStats(damage=10, might=20), world_id=realm.world.id, location_id=realm.region.id)
    quest = await send_on_quest(context(realm.session, epoch=3), hero.id, kind=HeroQuestKind.RELIC)
    assert quest.target_node_id == relic.id
    status = await resolve_quest(context(realm.session, epoch=4), hero.id, succeed=True)
    assert status is HeroQuestStatus.SUCCEEDED
    assert await bonded(realm.session, hero.id, relic.id, BondKind.OWNS)
    assert not await bonded(realm.session, hero.id, relic.id, BondKind.PURSUES)
    assert "heroes.quest_relic" in await chronicle_keys(realm.session)


async def test_owned_item_is_not_a_relic_quest_target(realm: Realm) -> None:
    hero = await mortal(realm, "Finder", role=MortalRole.HERO)
    holder = await mortal(realm, "Holder")
    relic = await make(realm.session, "Held Crown", EntityType.ITEM, ItemStats(damage=10), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, holder.id, relic.id, BondKind.OWNS)
    assert await _offered(realm, hero.id, HeroQuestKind.RELIC) is False


async def envy_scene(realm: Realm) -> tuple[int, int]:
    owner = await settlement(realm, "Marvel", prosperity=40)
    rival = await settlement(realm, "Envy")
    await make(realm.session, "Sky Tower", EntityType.STRUCTURE, StructureStats(splendor=95), world_id=realm.world.id, location_id=owner.id)
    first, second = sorted((owner.id, rival.id))
    await set_relation(context(realm.session), first, second, -90, "old hatred")
    return owner.id, rival.id


async def test_envious_neighbour_declares_war_over_a_wonder(realm: Realm) -> None:
    owner, rival = await envy_scene(realm)
    await wonders(context(realm.session, tuned(wonders={"envy_war_chance": 100})))
    assert await bonded(realm.session, rival, owner, BondKind.ENEMY)
    keys = await chronicle_keys(realm.session)
    assert "wonders.promoted" in keys and "wonders.envy_war" in keys


async def test_envy_without_the_war_chance_only_sours_relations(realm: Realm) -> None:
    owner, rival = await envy_scene(realm)
    await wonders(context(realm.session, tuned(wonders={"envy_war_chance": 0})))
    assert not await bonded(realm.session, rival, owner, BondKind.ENEMY)
    assert "wonders.envy_war" not in await chronicle_keys(realm.session)
