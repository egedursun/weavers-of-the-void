from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import SpeakerCohortRow
from aerona.db.tables.discovery import NameExonymRow, TheoryProfileRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.tongues import DecipherWorkRow, DivineTongueRow, LanguagePolicyRow, ScriptRow, SoundChangeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.military import CaptiveFate
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.tongues import (
    LanguageModality,
    LanguagePolicy,
    LanguageStage,
    MorphologyType,
    ScriptChangeCause,
    SenseShift,
    SoundChangeCause,
    SoundChangeKind,
    SoundEnvironment,
    WordOrder,
    WordRegister,
)
from aerona.domain.models.entity_stats import BeastStats, LanguageStats, PolityStats
from aerona.domain.models.phonology import Phonology
from aerona.engine.context import TickContext
from aerona.engine.lore.language import understood
from aerona.engine.phases.language_death import language_death
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import add_flag, has_flag
from aerona.engine.tongues.decipher import DecipherTally, study
from aerona.engine.tongues.divine import give_tongue, knows, rite_factor, teach
from aerona.engine.tongues.grammar import distance, grammar_of, misread_factor, simplify
from aerona.engine.tongues.loans import adapt
from aerona.engine.tongues.meaning import DriftTally, lift_names, shift_word
from aerona.engine.tongues.modality import suited, telepathic, writable
from aerona.engine.tongues.pidgins import PidginTally, captive_pidgins, creolise, make_pidgin
from aerona.engine.tongues.policy import PolicyTally, choose_official, keep_policies, set_policy
from aerona.engine.tongues.scripts import ScriptTally, borrow, evolve, record_script
from aerona.engine.tongues.sounds import Change, SoundTally, acquire, add_change, apply_change, derive, inherit, reconstruct, rederive
from aerona.services.integrity.tongue_links import mend_tongue_links
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

VOWELS = frozenset("aeiou")


async def tongue(session: AsyncSession, world: CoreWorld, name: str = "Ostra", *, parent_id: int | None = None) -> EntityRow:
    language = await entity(session, name, EntityType.LANGUAGE, LanguageStats(spread=20, complexity=40, sacredness=0), world_id=world.world.id)
    await language_profile(session, language, parent_id)
    return language


def words(session: AsyncSession, language: EntityRow, *pairs: tuple[str, str]) -> None:
    for word, meaning in pairs:
        session.add(LexemeRow(language_entity_id=language.id, word=word, meaning=meaning, added_by_kind=ActorKind.ENGINE, epoch=1))


async def tuned(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "tongues", rules=tuned_rules(**namespaces))


def test_a_change_happens_only_where_its_environment_allows() -> None:
    lenition = Change(SoundChangeKind.LENITION, "t", "s", SoundEnvironment.BETWEEN_VOWELS)
    assert apply_change("Atar", lenition, VOWELS) == "Asar"
    assert apply_change("Tara", lenition, VOWELS) == "Tara"
    final = Change(SoundChangeKind.LOSS, "a", "", SoundEnvironment.FINAL)
    assert derive("Tara", [lenition, final], VOWELS) == "Tar"


async def test_a_decreed_change_rederives_every_word_but_spares_the_sacred_and_never_makes_two_words_one(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    language = await tongue(session, world)
    words(session, language, ("Kapa", "water"), ("Kaba", "stone"), ("Tapa", "hill"))
    session.add(
        LexemeRow(language_entity_id=language.id, word="Papa", meaning="the god", added_by_kind=ActorKind.ENGINE, epoch=1, register=WordRegister.SACRED)
    )
    await session.flush()
    await add_change(ctx, language.id, Change(SoundChangeKind.MERGER, "b", "p", SoundEnvironment.ANYWHERE), SoundChangeCause.DECREE)
    await add_change(ctx, language.id, Change(SoundChangeKind.SHIFT, "p", "f", SoundEnvironment.ANYWHERE), SoundChangeCause.DECREE)
    await rederive(ctx, language.id)
    forms = {row.meaning: (row.word, row.proto_word) for row in await session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language.id))}
    assert forms["water"] == ("Kafa", "Kapa")
    assert forms["stone"][0] == "Kaba"
    assert forms["hill"] == ("Tafa", "Tapa")
    assert forms["the god"][0] == "Papa"


async def test_a_dialect_shares_its_parents_early_changes_and_scholars_rebuild_the_dead_parent(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, sound_changes={"reconstruct_pct": 100, "reconstruct_skill": 10})
    parent = await tongue(session, world, "Elder")
    words(session, parent, ("Amar", "sun"))
    await session.flush()
    await add_change(ctx, parent.id, Change(SoundChangeKind.SHIFT, "m", "n", SoundEnvironment.ANYWHERE), SoundChangeCause.DRIFT)
    first, second = await tongue(session, world, "Lower", parent_id=parent.id), await tongue(session, world, "Upper", parent_id=parent.id)
    for child in (first, second):
        words(session, child, ("Amar", "sun"))
        await session.flush()
        await inherit(ctx, parent.id, child.id)
        await rederive(ctx, child.id)
    inherited = await session.scalar(select(SoundChangeRow).where(SoundChangeRow.language_entity_id == first.id))
    assert inherited is not None
    assert inherited.cause is SoundChangeCause.INHERITED
    await session.execute(delete(LexemeRow).where(LexemeRow.language_entity_id == parent.id))
    await add_flag(session, parent.id, EntityFlag.DEAD_LANGUAGE, 1)
    town = await settlement(session, "Brin", world, world.regions[0])
    await bond(session, town.id, first.id, BondKind.SPEAKS)
    scholar = await mortal(session, "Ilo", world, town.id)
    session.add(SkillRow(holder_node_id=scholar.id, skill=SkillKind.LANGUAGES, level=50, peak=50, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    tally = SoundTally()
    await reconstruct(ctx, tally)
    rebuilt = await session.scalar(select(LexemeRow).where(LexemeRow.language_entity_id == parent.id))
    assert rebuilt is not None
    assert rebuilt.meaning == "sun"
    assert rebuilt.word == "Amar"
    assert tally.reconstructed == 1


async def test_distant_grammars_are_misread_more_and_contact_tongues_are_born_simple(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    one, other = await tongue(session, world, "One"), await tongue(session, world, "Other")
    first, second = await grammar_of(session, one.id), await grammar_of(session, other.id)
    assert first is not None and second is not None
    first.word_order, first.morphology, first.cases = WordOrder.SOV, MorphologyType.POLYSYNTHETIC, 12
    second.word_order, second.morphology, second.cases = WordOrder.VOS, MorphologyType.ISOLATING, 0
    assert distance(first, second) > 0
    assert await misread_factor(session, ctx.rules, {one.id}, {other.id}) > 1
    assert await misread_factor(session, ctx.rules, {one.id}, {one.id}) == 1
    simple = await simplify(session, ctx.rules, one.id, ctx.epoch)
    assert simple is not None
    assert (simple.morphology, simple.cases) == (MorphologyType.ISOLATING, ctx.rules.grammar.creole_cases)


def test_a_loanword_takes_the_sounds_of_the_tongue_that_borrows_it() -> None:
    phonology = Phonology(vowels=("a", "i"), consonants=("k", "t", "r"), syllable_patterns=("CV",), min_syllables=1, max_syllables=3)
    assert adapt("Bolu", phonology) == "Kiki"


async def test_a_word_takes_in_another_meaning_and_the_name_of_a_dreaded_beast_is_veiled(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, semantic_drift={"drift_pct": 100, "taboo_pct": 100, "taboo_terror": 50})
    town = await settlement(session, "Hollow", world, world.regions[0])
    language = await tongue(session, world, "Hollowish")
    await bond(session, town.id, language.id, BondKind.SPEAKS)
    words(session, language, ("Ama", "water"), ("Bena", "stone"), ("Cori", "hill"))
    await entity(session, "Graw", EntityType.BEAST, BeastStats(terror=90), world_id=world.world.id, location_id=world.regions[0].id)
    await session.flush()
    tally = DriftTally()
    shifted = await shift_word(ctx, language, tally)
    assert shifted is None or shifted.shift in {SenseShift.BROADENED, SenseShift.NARROWED, SenseShift.PEJORATIVE, SenseShift.AMELIORATIVE}
    await lift_names(ctx, tally)
    assert tally.veiled >= 1
    veiled = await session.scalar(select(NameExonymRow).where(NameExonymRow.language_entity_id == language.id))
    assert veiled is not None
    old = await session.scalar(select(LexemeRow).where(LexemeRow.language_entity_id == language.id, LexemeRow.register == WordRegister.SACRED))
    assert old is not None
    assert old.word == "Graw"


async def test_a_veiled_name_already_in_the_tongue_keeps_its_one_word(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, semantic_drift={"drift_pct": 0, "taboo_pct": 100, "taboo_terror": 50})
    town = await settlement(session, "Hollow", world, world.regions[0])
    language = await tongue(session, world, "Hollowish")
    await bond(session, town.id, language.id, BondKind.SPEAKS)
    words(session, language, ("Ama", "water"), ("Bena", "stone"), ("Graw", "the beast of the hills"))
    await entity(session, "Graw", EntityType.BEAST, BeastStats(terror=90), world_id=world.world.id, location_id=world.regions[0].id)
    await session.flush()
    tally = DriftTally()
    await lift_names(ctx, tally)
    assert tally.veiled >= 1
    named = list(await session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language.id, LexemeRow.word_key == "graw")))
    assert len(named) == 1


async def test_a_merchant_tongue_wears_its_script_simpler_and_an_unwritten_one_borrows(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, script_evolution={"evolve_pct": 100, "merchant_share": 0, "borrow_pct": 100})
    writer = await tongue(session, world, "Scribal")
    profile = await language_profile(session, writer)
    current = await record_script(ctx, writer, profile, WritingSystem.PICTOGRAPHIC, cause=ScriptChangeCause.INVENTION)
    tally = ScriptTally()
    evolved = await evolve(ctx, writer, profile, tally)
    assert evolved is not None
    assert (evolved.system, evolved.parent_script_id, evolved.cause) == (WritingSystem.LOGOGRAPHIC, current.id, ScriptChangeCause.SIMPLIFICATION)
    town = await settlement(session, "Mart", world, world.regions[0])
    unwritten = await tongue(session, world, "Plain")
    await bond(session, town.id, unwritten.id, BondKind.SPEAKS)
    session.add(SpeakerCohortRow(community_entity_id=town.id, language_entity_id=writer.id, kind=SpeakerKind.SECOND, share=40, since_epoch=1, locked=[]))
    await session.flush()
    borrowed = await borrow(ctx, unwritten, await language_profile(session, unwritten), tally)
    assert borrowed is not None
    assert borrowed.cause is ScriptChangeCause.BORROWING
    assert borrowed.signs == evolved.signs + ctx.rules.script_evolution.borrowed_signs


async def test_scholars_decipher_a_dead_script_and_misreadings_become_a_false_theory(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, decipherment={"error_pct": 100, "legend_errors": 1, "base": 60})
    dead = await tongue(session, world, "Lost")
    await add_flag(session, dead.id, EntityFlag.DEAD_LANGUAGE, 1)
    await add_flag(session, dead.id, EntityFlag.DECIPHERABLE, 1)
    scholar = await mortal(session, "Vesh", world, world.regions[0].id)
    session.add(SkillRow(holder_node_id=scholar.id, skill=SkillKind.LANGUAGES, level=50, peak=50, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    tally = DecipherTally()
    work = await study(ctx, dead, scholar, tally)
    assert 0 < work.progress < 100
    assert work.errors == 1
    theory = await session.scalar(select(TheoryProfileRow).where(TheoryProfileRow.founder_entity_id == scholar.id))
    assert theory is not None
    await study(ctx, dead, scholar, tally)
    assert not await has_flag(session, dead.id, EntityFlag.DECIPHERABLE)
    assert tally.deciphered == 1


async def test_traders_with_no_shared_tongue_make_a_pidgin_and_children_make_it_a_creole(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, pidgins={"creole_after": 0, "native_share": 10})
    first, second = await settlement(session, "Aport", world, world.regions[0]), await settlement(session, "Bport", world, world.regions[1])
    one, other = await tongue(session, world, "Aish"), await tongue(session, world, "Bish")
    await bond(session, first.id, one.id, BondKind.SPEAKS)
    await bond(session, second.id, other.id, BondKind.SPEAKS)
    words(session, one, ("Ala", "boat"))
    words(session, other, ("Bel", "salt"))
    await session.flush()
    pidgin = await make_pidgin(ctx, first, second)
    assert pidgin is not None
    profile = await session.get(LanguageProfileRow, pidgin.id)
    assert profile is not None
    assert profile.stage is LanguageStage.PIDGIN
    assert await creolise(ctx, pidgin, profile, PidginTally())
    assert {profile.stage} == {LanguageStage.CREOLE}


async def test_a_realm_makes_its_tongue_official_and_suppression_costs_its_speakers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, language_policy={"official_pct": 100})
    realm = await entity(session, "Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    town = await settlement(session, "Hold", world, world.regions[0])
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id, joined_epoch=1, locked=[]))
    await bond(session, town.id, world.language.id, BondKind.SPEAKS)
    minority = await tongue(session, world, "Minor")
    session.add(SpeakerCohortRow(community_entity_id=town.id, language_entity_id=minority.id, kind=SpeakerKind.SECOND, share=50, since_epoch=1, locked=[]))
    await session.flush()
    tally = PolicyTally()
    official = await choose_official(ctx, realm, tally)
    assert official is not None
    assert (official.policy, official.language_entity_id) == (LanguagePolicy.OFFICIAL, world.language.id)
    await set_policy(ctx, realm.id, minority.id, LanguagePolicy.SUPPRESSED, 100)
    await keep_policies(ctx, tally)
    cohort = await session.get(SpeakerCohortRow, (town.id, minority.id, SpeakerKind.SECOND))
    assert cohort is not None
    assert cohort.share == 50 - ctx.rules.language_policy.suppress_loss
    assert tally.suppressed >= 1


async def test_thought_crosses_every_barrier_between_telepaths_and_cannot_be_written(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    one, other = await tongue(session, world, "Mindone"), await tongue(session, world, "Mindtwo")
    for language in (one, other):
        profile = await language_profile(session, language)
        profile.modality = LanguageModality.TELEPATHIC
    await session.flush()
    assert await telepathic(session, {one.id})
    first, second = await settlement(session, "Ka", world, world.regions[0]), await settlement(session, "Ke", world, world.regions[1])
    assert await understood(session, ctx.rules, (first.id, second.id), ({one.id}, {other.id}), ctx.epoch) == 1.0
    assert not await writable(session, one.id)
    assert suited(frozenset()) is LanguageModality.TELEPATHIC


async def test_a_son_is_given_its_sacred_tongue_and_a_mortal_who_learns_it_casts_stronger(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row = await give_tongue(ctx, world.son)
    assert row is not None
    profile = await session.get(LanguageProfileRow, row.language_entity_id)
    assert profile is not None
    assert profile.stage is LanguageStage.DIVINE
    priest = await mortal(session, "Ora", world, world.regions[0].id)
    assert await teach(ctx, world.son.id, priest)
    assert await knows(session, priest.id, row.language_entity_id)
    assert await rite_factor(session, ctx.rules.divine_tongues.rite_pct, priest.id, world.son.id) > 1


async def test_tongue_links_to_vanished_holders_and_fallen_gods_are_mended(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    row = await give_tongue(ctx, world.son)
    assert row is not None
    realm = await entity(session, "Fallen Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    await set_policy(ctx, realm.id, world.language.id, LanguagePolicy.OFFICIAL, 50)
    session.add(DecipherWorkRow(language_entity_id=world.language.id, progress=10, locked=[]))
    realm.status, realm.end_epoch = EntityStatus.DEAD, ctx.epoch
    world.son.status, world.son.death_epoch = SonStatus.DEAD, ctx.epoch
    await session.flush()
    assert await mend_tongue_links(session) >= 2
    assert await session.get(LanguagePolicyRow, (realm.id, world.language.id, LanguagePolicy.OFFICIAL)) is None
    assert await session.get(DivineTongueRow, world.son.id) is None
    assert await session.scalar(select(ScriptRow)) is None


async def test_a_sacred_tongue_and_a_tongue_spoken_only_as_a_second_tongue_do_not_die(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "sacred")
    row = await give_tongue(ctx, world.son)
    assert row is not None
    trade = await tongue(session, world, "Tradewords")
    town = await settlement(session, "Quay", world, world.regions[0])
    session.add(SpeakerCohortRow(community_entity_id=town.id, language_entity_id=trade.id, kind=SpeakerKind.SECOND, share=30, since_epoch=1, locked=[]))
    for language_id in (row.language_entity_id, trade.id):
        found = await session.get(EntityRow, language_id)
        assert found is not None
        found.birth_epoch = 0
    world.cosmos.epoch = 40
    await session.flush()
    await language_death(await manual_context(session, "death"))
    assert not await has_flag(session, row.language_entity_id, EntityFlag.DEAD_LANGUAGE)
    assert not await has_flag(session, trade.id, EntityFlag.DEAD_LANGUAGE)


async def test_a_tongue_does_not_take_the_same_change_twice(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    lender, borrower = await tongue(session, world, "Lender"), await tongue(session, world, "Borrower")
    change = Change(SoundChangeKind.SHIFT, "k", "g", SoundEnvironment.ANYWHERE)
    await add_change(ctx, lender.id, change, SoundChangeCause.DRIFT)
    await add_change(ctx, borrower.id, change, SoundChangeCause.PRESTIGE)
    ctx_sure = await tuned(session, sound_changes={"base_pct": 100, "prestige_gap": 0})
    town = await settlement(session, "Twin", world, world.regions[0])
    await bond(session, town.id, borrower.id, BondKind.SPEAKS)
    session.add(SpeakerCohortRow(community_entity_id=town.id, language_entity_id=lender.id, kind=SpeakerKind.SECOND, share=30, since_epoch=1, locked=[]))
    await session.flush()
    await acquire(ctx_sure, borrower, SoundTally())
    same = await session.scalars(select(SoundChangeRow).where(SoundChangeRow.language_entity_id == borrower.id, SoundChangeRow.source == "k"))
    assert len(list(same)) == 1


async def test_captors_and_the_captives_they_hold_make_a_pidgin(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, pidgins={"contact_pct": 100})
    captor = await settlement(session, "Keep", world, world.regions[0])
    own, theirs = await tongue(session, world, "Keepish"), await tongue(session, world, "Farish")
    await bond(session, captor.id, own.id, BondKind.SPEAKS)
    words(session, own, ("Kel", "gate"))
    words(session, theirs, ("Fen", "field"))
    session.add(CaptiveCohortRow(captor_entity_id=captor.id, language_entity_id=theirs.id, count=40, fate=CaptiveFate.ENSLAVED, since_epoch=1))
    await session.flush()
    tally = PidginTally()
    await captive_pidgins(ctx, tally)
    assert tally.born == 1
    cohort = await session.scalar(
        select(SpeakerCohortRow).where(SpeakerCohortRow.community_entity_id == captor.id, SpeakerCohortRow.kind == SpeakerKind.SECOND)
    )
    assert cohort is not None
