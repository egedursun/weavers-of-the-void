import pytest
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityFlagRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.society import ReverenceRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import CultStats, LanguageStats, TraditionStats
from aerona.engine.phases.culture_exchange import cultural_exchange, knowledge_diffusion, order_cultural_contact
from aerona.engine.phases.religion_spread import godlessness, religion_spread, schism_root, schisms
from aerona.engine.primitives.faith import dominance_multiplier
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, bonded, chronicle_keys, context, knowledge, link, make, named, natural_law, people, son, tuned

RULES = Rules()


def test_dominance_multiplier_falls_after_threshold() -> None:
    threshold = RULES.religion.dominant_god_threshold_pct
    assert dominance_multiplier(RULES, threshold) == 1.0
    assert dominance_multiplier(RULES, 100) == 0.0
    assert 0 < dominance_multiplier(RULES, (threshold + 100) / 2) < 1


def test_schism_root_strips_suffixes() -> None:
    assert schism_root("Ember Schismatics Schismatics II") == "Ember"
    assert schism_root("Ember") == "Ember"


async def test_knowledge_and_language_diffuse_along_trade(realm: Realm) -> None:
    teacher = await people(realm, "Scribes")
    learner = await people(realm, "Herders")
    letters = await knowledge(realm, "Letters", KnowledgeBranch.WRITING)
    tongue = await make(realm.session, "Old Tongue", EntityType.LANGUAGE, LanguageStats(spread=10), world_id=realm.world.id)
    await link(realm.session, teacher.id, letters.id, BondKind.KNOWS)
    await link(realm.session, teacher.id, tongue.id, BondKind.SPEAKS)
    await link(realm.session, teacher.id, learner.id, BondKind.TRADES_WITH)
    await natural_law(realm, "One Speech", NaturalLaw.ONE_LANGUAGE)
    ctx = context(realm.session, tuned(knowledge={"diffusion_chance": 100, "language_spread_chance": 100}))
    await knowledge_diffusion(ctx)
    assert await bonded(realm.session, learner.id, letters.id, BondKind.KNOWS)
    assert await bonded(realm.session, learner.id, tongue.id, BondKind.SPEAKS)
    assert stat(letters, "spread") == 20 + RULES.intervention_effects.knowledge_spread_gain


async def test_cultural_contact_passes_words_traditions_knowledge_and_gods(realm: Realm) -> None:
    giver = await people(realm, "Givers")
    taker = await people(realm, "Takers")
    giver_tongue = await make(realm.session, "Giver Tongue", EntityType.LANGUAGE, LanguageStats(), world_id=realm.world.id)
    taker_tongue = await make(realm.session, "Taker Tongue", EntityType.LANGUAGE, LanguageStats(), world_id=realm.world.id)
    await link(realm.session, giver.id, giver_tongue.id, BondKind.SPEAKS)
    await link(realm.session, taker.id, taker_tongue.id, BondKind.SPEAKS)
    realm.session.add(LexemeRow(language_entity_id=giver_tongue.id, word="aru", meaning="river", added_by_kind=ActorKind.ENGINE, epoch=1))
    feast = await make(realm.session, "Feast of Ash", EntityType.TRADITION, TraditionStats(spread=10), world_id=realm.world.id)
    await link(realm.session, giver.id, feast.id, BondKind.CELEBRATES)
    lore = await knowledge(realm, "Stars", KnowledgeBranch.ASTRONOMY)
    await link(realm.session, giver.id, lore.id, BondKind.KNOWS)
    old_god = await son(realm.session, "Old", realm.world.id)
    new_god = await son(realm.session, "New", realm.world.id)
    await link(realm.session, giver.id, new_god.id, BondKind.WORSHIPS)
    await link(realm.session, taker.id, old_god.id, BondKind.WORSHIPS)
    rules = tuned(culture={"trade_loanword_pct": 100, "trade_tradition_pct": 100, "trade_knowledge_pct": 100, "trade_god_pct": 100})
    count = await order_cultural_contact(context(realm.session, rules), giver.id, taker.id)
    assert count == 4
    words = list(await realm.session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == taker_tongue.id)))
    assert words == ["aru"]
    assert await bonded(realm.session, taker.id, feast.id, BondKind.CELEBRATES)
    assert await bonded(realm.session, taker.id, lore.id, BondKind.KNOWS)
    assert await realm.session.get(ReverenceRow, (taker.id, new_god.id)) is not None
    assert await bonded(realm.session, taker.id, old_god.id, BondKind.WORSHIPS)
    with pytest.raises(ValidationFailedError):
        await order_cultural_contact(context(realm.session), giver.id, giver.id)


async def test_trade_route_exchange_is_capped(realm: Realm) -> None:
    first = await people(realm, "North")
    second = await people(realm, "South")
    lore = await knowledge(realm, "Irrigation", KnowledgeBranch.AGRICULTURE)
    await link(realm.session, first.id, lore.id, BondKind.KNOWS)
    await link(realm.session, second.id, lore.id, BondKind.KNOWS)
    await link(realm.session, first.id, second.id, BondKind.TRADES_WITH)
    ctx = context(realm.session, tuned(culture={"exchange_chance": 100, "exchange_cap": 0}))
    await cultural_exchange(ctx)
    assert ctx.environment.stats.counters["test.exchanges"] == 0


async def test_schism_splits_a_zealous_cult(realm: Realm) -> None:
    patron = await son(realm.session, "Patron", realm.world.id, charisma=40)
    rival = await son(realm.session, "Rival", realm.world.id, charisma=90)
    cult = await make(
        realm.session, "Ember Cult", EntityType.CULT, CultStats(followers=5000, zeal=90, influence=50), world_id=realm.world.id, location_id=realm.region.id
    )
    await link(realm.session, cult.id, patron.id, BondKind.WORSHIPS)
    ctx = context(realm.session, tuned(religion={"schism_zealous_chance": 100}), epoch=10)
    await schisms(ctx)
    sects = [item for item in await named(realm.session, EntityType.CULT) if item.id != cult.id]
    assert len(sects) == 1
    assert sects[0].name == "Ember Cult Schismatics"
    assert await bonded(realm.session, sects[0].id, rival.id, BondKind.WORSHIPS)
    assert await bonded(realm.session, sects[0].id, cult.id, BondKind.ENEMY)
    assert stat(cult, "followers") == 5000 - 1500


async def test_weak_faith_turns_godless(realm: Realm) -> None:
    doubters = await people(realm, "Doubters", piety=5)
    ctx = context(realm.session, tuned(religion={"godlessness_chance": 100}))
    await godlessness(ctx)
    flag = await realm.session.get(EntityFlagRow, (doubters.id, EntityFlag.GODLESS))
    assert flag is not None
    assert "religion.godless" in await chronicle_keys(realm.session)


async def test_preaching_converts_and_syncretism_adds_reverence(realm: Realm) -> None:
    preacher_god = await son(realm.session, "Preacher", realm.world.id, fame=500)
    old_god = await son(realm.session, "Elder", realm.world.id)
    cult = await make(
        realm.session, "Bright Sermon", EntityType.CULT, CultStats(followers=4000, influence=90), world_id=realm.world.id, location_id=realm.region.id
    )
    await link(realm.session, cult.id, preacher_god.id, BondKind.WORSHIPS)
    seekers = await people(realm, "Seekers")
    believers = await people(realm, "Believers")
    await link(realm.session, believers.id, old_god.id, BondKind.WORSHIPS)
    rules = tuned(religion={"conversion_chance_cap": 100, "preach_base_pct": 100, "syncretism_pct": 100, "dominant_god_threshold_pct": 100})
    await religion_spread(context(realm.session, rules))
    assert await bonded(realm.session, seekers.id, preacher_god.id, BondKind.WORSHIPS)
    assert await realm.session.get(ReverenceRow, (believers.id, preacher_god.id)) is not None
    keys = await chronicle_keys(realm.session)
    assert "religion.conversion" in keys
    assert "religion.syncretism" in keys
