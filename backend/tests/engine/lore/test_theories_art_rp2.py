from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import ArtworkProfileRow, HolderLevelRow, ItemProfileRow, LanguageIntelligibilityRow
from aerona.db.tables.discovery import (
    ArtFormPractitionerRow,
    ArtFormProfileRow,
    EpithetRow,
    NameExonymRow,
    NameMeaningRow,
    ParadigmShiftRow,
    TheoryAdherentRow,
    TheoryAnomalyRow,
    TheoryProfileRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import TreatyBreachRow
from aerona.db.tables.renown import DeedRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.culture import ArtMedium, ItemClass
from aerona.domain.enums.discovery import AnomalyKind, ArtDiscipline, TheoryDomain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ArtworkStats, ItemStats, LanguageStats
from aerona.engine.lore import art_forms, names, theories, theory_control
from aerona.engine.lore.truth import branch_factor, ruling, theory_factor, truth_factor
from aerona.engine.polity.accords import Clause, sign
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm
from tests.engine.warfare.factories import bond, make, make_ctx
from tests.tools.factories import make_entity

RULES = Rules()


def tuned(namespace: str, **values: int) -> Rules:
    return replace(RULES, **{namespace: replace(getattr(RULES, namespace), **values)})


async def town(session: AsyncSession, realm: Realm, name: str) -> EntityRow:
    return await make(session, name, EntityType.SETTLEMENT, realm.world.id, location_id=realm.region.id, population=4000, prosperity=50, wealth=50)


async def tongue(session: AsyncSession, realm: Realm, name: str, speaker: EntityRow, words: dict[str, str]) -> EntityRow:
    language = await make_entity(session, name, EntityType.LANGUAGE, world_id=realm.world.id, stats=LanguageStats())
    await bond(session, speaker.id, language.id, BondKind.SPEAKS)
    for word, meaning in words.items():
        session.add(
            LexemeRow(language_entity_id=language.id, word=word, meaning=meaning, part_of_speech=PartOfSpeech.NOUN, added_by_kind=ActorKind.ENGINE, epoch=1)
        )
    await session.flush()
    return language


async def test_a_false_ruling_theory_harms_meets_anomalies_and_falls_to_a_truer_rival(session: AsyncSession, realm: Realm) -> None:
    rules = tuned("theories", anomaly_pct=100, contest_margin=0)
    ctx = make_ctx(session, rules)
    home = await town(session, realm, "Quill Town")
    false = await theories.create_theory(ctx, home, TheoryDomain.MEDICINE, "The Cold Account", "Sickness follows the cold.", correctness=0)
    true = await theories.create_theory(ctx, home, TheoryDomain.MEDICINE, "The Seed Account", "Sickness passes by contact.", correctness=100)
    ruling_now = await ruling(session, home.id, TheoryDomain.MEDICINE)
    assert ruling_now is not None and ruling_now.theory_entity_id == false.id
    assert await theory_factor(session, rules, home.id, TheoryDomain.MEDICINE) == truth_factor(rules, 0) < 1
    assert await branch_factor(session, rules, home.id, KnowledgeBranch.MEDICINE) < 1
    profile = await session.get_one(TheoryProfileRow, false.id)
    profile.explanatory_power = 0
    assert await theories.meet_anomalies(ctx) >= 1
    assert await session.scalar(select(TheoryAnomalyRow).where(TheoryAnomalyRow.theory_entity_id == false.id)) is not None
    assert await theories.contests(ctx) == 1
    after = await ruling(session, home.id, TheoryDomain.MEDICINE)
    assert after is not None and after.theory_entity_id == true.id
    shift = await session.scalar(select(ParadigmShiftRow).where(ParadigmShiftRow.community_entity_id == home.id))
    assert shift is not None and shift.old_theory_id == false.id and shift.new_theory_id == true.id


async def test_learned_scholars_found_a_theory_and_the_god_controls_it(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session, tuned("theories", found_pct=100, found_level=1))
    home = await town(session, realm, "Star Town")
    session.add(
        HolderLevelRow(
            holder_entity_id=home.id, branch=KnowledgeBranch.ASTRONOMY, level=2, practitioners=1, progress=0, secret=False, updated_epoch=1, locked=[]
        )
    )
    await session.flush()
    assert await theories.found_theories(ctx) >= 1
    founded = await ruling(session, home.id, TheoryDomain.COSMOLOGY)
    assert founded is not None
    other = await town(session, realm, "Far Town")
    row = await theory_control.set_adherent(ctx, founded.theory_entity_id, other.id, strength=60, orthodox=True, present=True)
    assert row is not None and row.orthodox and set(row.locked) == {"strength", "orthodox"}
    await theory_control.add_anomaly(ctx, founded.theory_entity_id, AnomalyKind.OBSERVATION, 2, other.id)
    revealed = await theory_control.reveal_truth(ctx, founded.theory_entity_id, home.id)
    assert revealed.correctness == 100 and "correctness" in revealed.locked
    assert await theory_control.set_adherent(ctx, founded.theory_entity_id, other.id, strength=0, orthodox=False, present=False) is None
    assert await session.get(TheoryAdherentRow, (founded.theory_entity_id, other.id)) is None


async def test_an_art_form_spreads_loses_mastery_across_tongues_lends_artworks_quality_and_is_lost(session: AsyncSession, realm: Realm) -> None:
    rules = tuned("art_forms", spread_pct=100, decline_epochs=1)
    ctx = make_ctx(session, rules)
    home = await town(session, realm, "Song Town")
    partner = await town(session, realm, "Dune Town")
    await tongue(session, realm, "Aru", home, {})
    await tongue(session, realm, "Bel", partner, {})
    await bond(session, home.id, partner.id, BondKind.TRADES_WITH)
    poet = await make(session, "Ila Sor", EntityType.MORTAL, realm.world.id, location_id=home.id)
    form = await art_forms.found_form(ctx, home, ArtDiscipline.POETRY, "The Long Verse", founder=poet, parents=[], structure={"metre": "long"})
    profile = await session.get_one(ArtFormProfileRow, form.id)
    assert profile.language_entity_id is not None
    assert await art_forms.spread(ctx) >= 1
    carried = await session.get(ArtFormPractitionerRow, (form.id, partner.id))
    source = await session.get_one(ArtFormPractitionerRow, (form.id, home.id))
    assert carried is not None and carried.mastery < source.mastery // 2 + 1
    work = await make_entity(session, "The First Verse", EntityType.ARTWORK, world_id=realm.world.id, stats=ArtworkStats(renown=10))
    session.add(ArtworkProfileRow(artwork_entity_id=work.id, medium=ArtMedium.EPIC_POEM, author_entity_id=poet.id, quality=50, locked=[]))
    await session.flush()
    assert await art_forms.credit_artworks(ctx) == 1
    artwork = await session.get_one(ArtworkProfileRow, work.id)
    assert artwork.art_form_entity_id == form.id and artwork.quality > 50
    lone = await art_forms.found_form(ctx, home, ArtDiscipline.DANCE, "The Quiet Step", founder=None, parents=[], structure={})
    for row in list(await session.scalars(select(ArtFormPractitionerRow).where(ArtFormPractitionerRow.art_form_entity_id == lone.id))):
        await session.delete(row)
    lone_profile = await session.get_one(ArtFormProfileRow, lone.id)
    lone_profile.updated_epoch = 0
    await session.flush()
    counts = await art_forms.tend_forms(ctx)
    assert counts["art_forms_lost"] >= 1 and lone.status is EntityStatus.DESTROYED


async def test_names_take_meanings_and_foreign_forms_and_the_renowned_earn_epithets(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    home = await make(session, "Ravenford", EntityType.SETTLEMENT, realm.world.id, location_id=realm.region.id, population=4000)
    partner = await town(session, realm, "Dawn Town")
    await bond(session, home.id, partner.id, BondKind.TRADES_WITH)
    await tongue(session, realm, "Cor", home, {"raven": "black bird", "ford": "river crossing"})
    await tongue(session, realm, "Dal", partner, {"kra": "black bird"})
    await names.give_meanings(ctx)
    meaning = await session.get(NameMeaningRow, home.id)
    assert meaning is not None and meaning.morphemes == ["raven", "ford"] and meaning.gloss == "black bird-river crossing"
    assert await names.give_exonyms(ctx) >= 1
    exonym = await session.scalar(select(NameExonymRow).where(NameExonymRow.node_id == home.id))
    assert exonym is not None and exonym.form.lower().startswith("kra")
    hero = await make(session, "Tov Ash", EntityType.MORTAL, realm.world.id, location_id=home.id)
    profile = await session.get(MortalProfileRow, hero.id)
    if profile is None:
        session.add(MortalProfileRow(entity_id=hero.id, renown=90))
    else:
        profile.renown = 90
    session.add(DeedRow(doer_node_id=hero.id, axis=ReputationAxis.HEROISM, magnitude=50, epoch=1, locked=[]))
    await session.flush()
    assert await names.give_epithets(ctx) == 1
    epithet = await session.get(EpithetRow, hero.id)
    assert epithet is not None and epithet.deed == "heroism"


async def test_a_treaty_between_tongues_that_share_nothing_is_misread(session: AsyncSession, realm: Realm) -> None:
    rules = tuned("name_meanings", misread_pct=100)
    ctx = make_ctx(session, replace(rules, interpreters=replace(rules.interpreters, barrier_floor_pct=0)))
    first = await town(session, realm, "East Town")
    second = await town(session, realm, "West Town")
    await tongue(session, realm, "Eo", first, {"sun": "sun"})
    other = await tongue(session, realm, "Wu", second, {"mor": "moon"})
    own = await session.scalar(select(LexemeRow.language_entity_id).where(LexemeRow.word == "sun"))
    assert own is not None
    low, high = sorted((own, other.id))
    session.add(LanguageIntelligibilityRow(first_entity_id=low, second_entity_id=high, value=0, epoch=1, locked=[]))
    await session.flush()
    treaty = await sign(
        ctx,
        TreatyKind.TRADE_PACT,
        [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.TRADE_RIGHTS, first.id, second.id)],
        witnessed=False,
    )
    assert await names.misreadings(ctx) == 1
    breach = await session.scalar(select(TreatyBreachRow).where(TreatyBreachRow.treaty_entity_id == treaty.id))
    assert breach is not None and breach.breaker_node_id is None


async def test_a_theory_passes_with_its_founding_book_and_is_dropped_when_no_one_holds_it(session: AsyncSession, realm: Realm) -> None:
    ctx = make_ctx(session)
    home = await town(session, realm, "Scroll Town")
    reader = await town(session, realm, "Reader Town")
    book = await make_entity(session, "The Account Written", EntityType.ITEM, world_id=realm.world.id, stats=ItemStats())
    session.add(ItemProfileRow(item_entity_id=book.id, item_class=ItemClass.BOOK, condition=100, locked=[]))
    await bond(session, home.id, book.id, BondKind.OWNS)
    theory = await theories.create_theory(ctx, home, TheoryDomain.HISTORY, "The Long Memory", "The past repeats.", correctness=60)
    profile = await session.get_one(TheoryProfileRow, theory.id)
    assert profile.founding_book_id == book.id
    await bond(session, reader.id, book.id, BondKind.OWNS)
    assert await theories.read_theories(ctx) == 1
    held_row = await session.get_one(TheoryAdherentRow, (theory.id, reader.id))
    held_row.strength = 0
    assert await theories.abandon(ctx) == 1
    assert await session.get(TheoryAdherentRow, (theory.id, reader.id)) is None
