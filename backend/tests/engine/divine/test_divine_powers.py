from sqlalchemy import select

from aerona.core.errors import ConflictError
from aerona.db.repositories.cosmos import CosmosRepository, CreatorDraft
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import BreachPointRow, CouncilRulingRow, CreatorTabooRow, GodGoalRow, NaturalLawProfileRow, OuterBeingProfileRow, WorldAttentionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import (
    BargainGain,
    BargainPrice,
    CouncilMotion,
    DivineWoundKind,
    GodGoalKind,
    LawException,
    LawScope,
    OuterHunger,
    SonPunishment,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.models.entity_stats import CultStats, LanguageStats, OuterBeingStats
from aerona.domain.models.profiles import GodDepth
from aerona.engine.cosmos.actions import BargainTerms, bargain_with_outer
from aerona.engine.cosmos.duels import son_duel
from aerona.engine.divine import control
from aerona.engine.divine.creator import autonomy, target_for, tend_attention, type_taboos
from aerona.engine.divine.decrees import outlawed_schools, truce_in_force
from aerona.engine.divine.foreign import old_god_doctrine, pact_between, pantheon_leagues, seal_pact
from aerona.engine.divine.goals import aim_text
from aerona.engine.divine.laws import binds, tend_laws
from aerona.engine.divine.outer import outer_feeding, seed_void_tenets, void_rites
from aerona.engine.divine.rulings import Motion, enforce_rulings, engine_council, engine_votes
from aerona.engine.divine.taboos import taboo_broken
from aerona.engine.divine.wounds import open_wounds
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.services.conflict import foreign_god_war
from tests.engine.divine.pantheon import foreign, god, worship
from tests.engine.society.factories import Realm, context, make, mortal, natural_law, settlement


async def creator_of(realm: Realm) -> CreatorRow:
    found = await realm.session.scalar(select(CreatorRow).limit(1))
    if found is not None:
        return found
    return await CosmosRepository(realm.session).create_creator(
        CreatorDraft(name="Aeron", essence=500, mood_contentment=50, mood_anger=20, mood_interest=60, mood_loneliness=30)
    )


async def test_breaking_a_taboo_angers_the_creator_and_prose_taboos_become_typed(realm: Realm) -> None:
    creator = await creator_of(realm)
    ctx = context(realm.session)
    await control.set_taboo(ctx, ActKind.TORTURE, 80)
    anger = creator.mood_anger
    breaker = await mortal(realm, "Vask")
    assert await taboo_broken(ctx, breaker.id, ActKind.TORTURE)
    row = await realm.session.get(CreatorTabooRow, ActKind.TORTURE)
    assert row is not None and row.broken == 1 and row.last_breaker_node_id == breaker.id and creator.mood_anger > anger
    assert not await taboo_broken(ctx, breaker.id, ActKind.THEFT)
    creator.depth = GodDepth(taboos=("No slaves shall be kept",), epoch=0)
    assert await type_taboos(ctx) == 1
    assert await realm.session.get(CreatorTabooRow, ActKind.SLAVERY) is not None


async def test_a_world_far_from_the_eye_frees_its_sons(realm: Realm) -> None:
    creator = await creator_of(realm)
    creator.mood_interest = 0
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    ctx = context(realm.session)
    realm.session.add(WorldAttentionRow(world_id=realm.world.id, attention=5, watched=False, locked=[]))
    await realm.session.flush()
    await tend_attention(ctx)
    assert await autonomy(ctx, sea) == ctx.rules.creator.far_eye_rebel_pct
    await control.set_attention(ctx, realm.world.id, {"attention": 90}, [])
    assert await autonomy(ctx, sea) == 0


async def test_foreign_gods_league_and_a_pact_bars_war(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await foreign(realm.session, realm, "Ussamar", Domain.DEATH, stance=-80)
    second = await foreign(realm.session, realm, "Kethra", Domain.PLAGUE, stance=-80)
    for holder, subject in ((first, second), (second, first)):
        realm.session.add(
            RelationshipRow(holder_node_id=holder.id, subject_node_id=subject.id, friendship=60, kinds=[], since_epoch=1, last_epoch=1, locked=[])
        )
    await realm.session.flush()
    assert await pantheon_leagues(ctx) == 1
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    await seal_pact(ctx, sea, first)
    assert await pact_between(ctx, sea.id, first.id) is not None
    try:
        await foreign_god_war(ctx, sea.id, first.id)
    except ConflictError as error:
        assert "pact" in error.message
    else:
        raise AssertionError("a pact did not stop the war")


async def test_an_old_god_seeds_a_native_faith_with_its_domains(realm: Realm) -> None:
    old = await foreign(realm.session, realm, "Ussamar", Domain.WAR)
    town = await settlement(realm, "Embercourt")
    await worship(realm, town, old.id)
    assert await old_god_doctrine(context(realm.session)) == 1
    cult = await realm.session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.subtype == "old_faith"))
    assert cult is not None
    assert list(await realm.session.scalars(select(CultTenetRow).where(CultTenetRow.cult_entity_id == cult.id)))


async def test_council_rulings_bind_the_gods_and_lapse(realm: Realm) -> None:
    ctx = context(realm.session)
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    war = await god(realm, "Kerr", Domain.WAR, Domain.BLOOD)
    truce, _ = await control.decree(ctx, CouncilMotion.COSMIC_TRUCE)
    assert await truce_in_force(ctx)
    try:
        await son_duel(ctx, sea, war, Stat.STRENGTH, "old feud")
    except ConflictError:
        pass
    else:
        raise AssertionError("the truce let a duel happen")
    await control.decree(ctx, CouncilMotion.OUTLAW_RITE, school=MagicSchool.BLOOD)
    assert MagicSchool.BLOOD in await outlawed_schools(ctx)
    _, lines = await control.decree(ctx, CouncilMotion.PUNISH_SON, target_id=war.id, punishment=SonPunishment.EXILE)
    assert war.status is SonStatus.EXILED and lines
    truce.until_epoch = ctx.epoch
    await enforce_rulings(ctx)
    assert not truce.active


async def test_the_engine_council_weighs_votes_and_lays_down_a_ruling(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    rebel = await god(realm, "Varr", Domain.LIES, Domain.SHADOW)
    rebel.rebel = True
    third = await god(realm, "Pell", Domain.LIFE, Domain.LOVE)
    ctx = context(realm.session)
    votes = await engine_votes(ctx, [sea, rebel, third], Motion(CouncilMotion.PUNISH_SON, target_node_id=rebel.id, punishment=SonPunishment.CHAIN))
    assert votes[rebel.id] is False
    held = await engine_council(ctx)
    assert held is not None and held.minutes.decision == CouncilMotion.PUNISH_SON.value
    if held.passed:
        assert await realm.session.scalar(select(CouncilRulingRow).where(CouncilRulingRow.motion == CouncilMotion.PUNISH_SON)) is not None


async def test_natural_laws_take_scope_upkeep_contest_and_exceptions(realm: Realm) -> None:
    ctx = context(realm.session)
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    life = await natural_law(realm, "Deathless", NaturalLaw.IMMORTALITY)
    life.creator_son_id = sea.id
    short = await natural_law(realm, "Brief", NaturalLaw.SHORT_LIFE)
    await realm.session.flush()
    await tend_laws(ctx)
    first = await realm.session.get(NaturalLawProfileRow, life.id)
    second = await realm.session.get(NaturalLawProfileRow, short.id)
    assert first is not None and second is not None and first.author_node_id == sea.id
    assert first.contested and second.contested
    assert not (await LawBook.load(realm.session)).has(NaturalLaw.IMMORTALITY, realm.world.id)
    await control.edit_law(ctx, short.id, {"strength": 10}, [])
    await tend_laws(ctx)
    assert not first.contested and second.stability < ctx.rules.natural_laws.start_stability
    await control.edit_law(ctx, life.id, {"exception": LawException.HEROES.value, "scope": LawScope.COSMOS.value}, [])
    hero = await mortal(realm, "Dask", role=MortalRole.HERO)
    farmer = await mortal(realm, "Lim")
    fresh = context(realm.session)
    assert not await binds(fresh, NaturalLaw.IMMORTALITY, hero)
    assert await binds(fresh, NaturalLaw.IMMORTALITY, farmer)


async def test_an_unkept_law_weakens_and_is_unmade(realm: Realm) -> None:
    ctx = context(realm.session)
    law = await natural_law(realm, "Bounty", NaturalLaw.BOUNTY)
    await tend_laws(ctx)
    row = await realm.session.get(NaturalLawProfileRow, law.id)
    assert row is not None
    row.author_node_id, row.stability, row.strength = None, 0, 5
    await tend_laws(ctx)
    assert law.status is EntityStatus.DESTROYED


async def test_an_outer_being_feeds_on_its_hunger_opens_breaches_and_its_cult_serves_it(realm: Realm) -> None:
    being = await make(realm.session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=60, interest=80, influence=20), world_id=realm.world.id)
    realm.session.add(OuterBeingProfileRow(outer_entity_id=being.id, hunger=OuterHunger.NAMES, locked=[]))
    language = await make(realm.session, "Old Tongue", EntityType.LANGUAGE, LanguageStats(), world_id=realm.world.id)
    for word in ("ka", "ro", "mi"):
        realm.session.add(LexemeRow(language_entity_id=language.id, word=word, meaning=word, added_by_kind=ActorKind.ENGINE, epoch=1))
    await realm.session.flush()
    ctx = context(realm.session)
    assert await outer_feeding(ctx) > 0
    profile = await realm.session.get(OuterBeingProfileRow, being.id)
    assert profile is not None and profile.fed > 0 and profile.reach >= 2
    assert list(await realm.session.scalars(select(BreachPointRow).where(BreachPointRow.outer_entity_id == being.id)))
    cult = await make(realm.session, "Listeners", EntityType.CULT, CultStats(followers=100), world_id=realm.world.id)
    assert await seed_void_tenets(ctx, cult) == 3
    assert TenetKind.VOID_COMMUNION in set(await realm.session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult.id)))
    await void_rites(ctx)


async def test_an_outer_bargain_pays_its_typed_price_at_once(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    being = await make(realm.session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=40, influence=40), world_id=realm.world.id)
    ctx = context(realm.session)
    might = sea.might
    await bargain_with_outer(ctx, sea.id, being.id, "a road", BargainTerms(BargainGain.MIGHT, BargainPrice.DOMAIN, Domain.STORM))
    assert sea.might > might
    wounds = await open_wounds(realm.session, sea.id, DivineWoundKind.SEVERED_DOMAIN)
    assert [row.domain for row in wounds] == [Domain.STORM]
    world = await realm.session.get(WorldRow, realm.world.id)
    assert world is not None


async def test_the_creator_s_love_of_knowledge_falls_on_more_than_one_scholar(realm: Realm) -> None:
    town = await settlement(realm, "Ardun")
    for index in range(6):
        await mortal(realm, f"Sage {index}", location_id=town.id, role=MortalRole.SAGE)
    chosen = set()
    for epoch in range(1, 13):
        found = await target_for(context(realm.session, epoch=epoch), CreatorPassion.KNOWLEDGE)
        assert found is not None
        chosen.add(found.id)
    assert len(chosen) > 1


async def test_every_aim_reads_as_a_plain_purpose(realm: Realm) -> None:
    town = await settlement(realm, "Ardun")
    for kind in GodGoalKind:
        bare = await aim_text(realm.session, GodGoalRow(kind=kind))
        aimed = await aim_text(realm.session, GodGoalRow(kind=kind, target_node_id=town.id))
        assert "(" not in bare + aimed and bare[0].islower() and aimed[0].islower()
    spread = await aim_text(realm.session, GodGoalRow(kind=GodGoalKind.SPREAD_DOMAIN, domain=Domain.TRADE, world_id=realm.world.id))
    assert spread == f"spread the domain of trade across {realm.world.name}"
