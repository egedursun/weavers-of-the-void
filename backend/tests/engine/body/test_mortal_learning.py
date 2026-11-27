from sqlalchemy import select

from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow, ConditionRow
from aerona.db.tables.culture import BookContentRow, LegendProfileRow
from aerona.db.tables.mind import MemoryRow, SkillRow, TraitRow
from aerona.db.tables.mortal import KindVariantRow, MortalProfileRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.mind import KindFamily, MemoryKind, Profession, SkillKind, SkillSource, TraitEffect, TraitKind, TraitSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats, KnowledgeStats, LanguageStats, LegendStats, MortalStats, StructureStats
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.state import refresh
from aerona.engine.cycles.breeding import born_sex
from aerona.engine.lore.legends import LEGEND_NOTE, remember_legend
from aerona.engine.mind.book import effect_of, set_skill
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.course import seed_mortal
from aerona.engine.mortal.learning import attend_lectures, best_profession, read_books, speak_tongues, tongue_level, watch_masters
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.primitives.queries import connect
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned

RULES = Rules()


async def test_speaking_a_tongue_builds_a_skill_in_that_tongue(realm: Realm) -> None:
    speaker = await mortal(realm, "Ivo")
    tongue = await make(realm.session, "Old Speech", EntityType.LANGUAGE, LanguageStats(), world_id=realm.world.id)
    await connect(realm.session, speaker.id, tongue.id, BondKind.SPEAKS, 1)
    ctx = context(realm.session, tuned(skills={"speak_xp": 500}))
    await speak_tongues(ctx, speaker)
    assert await tongue_level(realm.session, speaker.id, tongue.id) > 0


async def test_a_profession_is_the_best_bundle_and_masters_teach_by_example(realm: Realm) -> None:
    town = await settlement(realm, "Harrow")
    smith = await mortal(realm, "Brann", location_id=town.id)
    learner = await mortal(realm, "Cael", location_id=town.id)
    await set_skill(realm.session, smith.id, SkillKind.SMITHING, 80, epoch=1, source=SkillSource.PLAYER)
    await set_skill(realm.session, learner.id, SkillKind.SMITHING, 30, epoch=1, source=SkillSource.PLAYER)
    rows = {row.skill: row for row in await realm.session.scalars(select(SkillRow).where(SkillRow.holder_node_id == learner.id))}
    assert best_profession(RULES, rows) is Profession.SMITH
    ctx = context(realm.session, tuned(skills={"demonstration_xp": 500}))
    profile, _ = await ensure_profile(realm.session, learner.id, ctx.epoch)
    profile.profession = Profession.SMITH
    assert await watch_masters(ctx, learner, profile) > 0


async def test_a_teaching_master_lectures_at_a_school_and_nowhere_else(realm: Realm) -> None:
    town = await settlement(realm, "Lettermere")
    scholar = await mortal(realm, "Orsa", location_id=town.id)
    student = await mortal(realm, "Pell", location_id=town.id)
    await set_skill(realm.session, scholar.id, SkillKind.MEDICINE, 80, epoch=1, source=SkillSource.PLAYER)
    await set_skill(realm.session, scholar.id, SkillKind.TEACHING, 40, epoch=1, source=SkillSource.PLAYER)
    await set_skill(realm.session, student.id, SkillKind.MEDICINE, 20, epoch=1, source=SkillSource.PLAYER)
    ctx = context(realm.session, tuned(skills={"lecture_xp": 500}))
    profile, _ = await ensure_profile(realm.session, student.id, ctx.epoch)
    profile.profession = Profession.HEALER
    assert await attend_lectures(ctx, student, profile) == 0
    hall = await make(
        realm.session,
        "House of Letters",
        EntityType.STRUCTURE,
        StructureStats(splendor=10, durability=60, function=50),
        world_id=realm.world.id,
        location_id=town.id,
    )
    hall.engine_kind = EngineKind.SCHOOL
    await realm.session.flush()
    assert await attend_lectures(ctx, student, profile) > 0


async def test_a_book_teaches_its_branch(realm: Realm) -> None:
    reader = await mortal(realm, "Dara")
    lore = await make(realm.session, "Herb Lore", EntityType.KNOWLEDGE, KnowledgeStats(), world_id=realm.world.id, knowledge_branch=KnowledgeBranch.MEDICINE)
    book = await make(realm.session, "A Herbal", EntityType.ITEM, ItemStats(), world_id=realm.world.id)
    realm.session.add(BookContentRow(book_entity_id=book.id, knowledge_entity_id=lore.id, fidelity=100))
    await connect(realm.session, reader.id, book.id, BondKind.OWNS, 1)
    await realm.session.flush()
    ctx = context(realm.session, tuned(skills={"book_xp": 500}))
    assert await read_books(ctx, reader) > 0


async def test_a_distorted_legend_plants_a_betrayal_that_never_happened(realm: Realm) -> None:
    town = await settlement(realm, "Morrow")
    villain = await mortal(realm, "Ezra")
    legend = await make(realm.session, "The Turncoat", EntityType.LEGEND, LegendStats(), world_id=realm.world.id)
    row = LegendProfileRow(
        legend_entity_id=legend.id, archetype=LegendArchetype.BETRAYAL, credence=90, distortion=80, subject_node_id=villain.id, tellers=[town.id], locked=[]
    )
    realm.session.add(row)
    await realm.session.flush()
    ctx = context(realm.session, tuned(belief={"false_memory_chance": 100}))
    assert await remember_legend(ctx, legend, row) == 1
    planted = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == town.id, MemoryRow.subject_node_id == villain.id))
    assert planted is not None and planted.kind is MemoryKind.BETRAYED_ME and planted.note == LEGEND_NOTE


async def test_a_legend_swells_a_true_memory(realm: Realm) -> None:
    town = await settlement(realm, "Fenmoor")
    hero = await mortal(realm, "Fara")
    legend = await make(realm.session, "The Saviour", EntityType.LEGEND, LegendStats(), world_id=realm.world.id)
    held = await remember(realm.session, RULES, holder_id=town.id, subject_id=hero.id, kind=MemoryKind.SAVED_ME, magnitude=20, epoch=1)
    row = LegendProfileRow(
        legend_entity_id=legend.id, archetype=LegendArchetype.HERO_QUEST, credence=10, distortion=100, subject_node_id=hero.id, tellers=[town.id], locked=[]
    )
    realm.session.add(row)
    await realm.session.flush()
    await remember_legend(context(realm.session), legend, row)
    await remember_legend(context(realm.session), legend, row)
    memories = list(await realm.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == town.id, MemoryRow.subject_node_id == hero.id)))
    assert held is not None and held.magnitude == 20 and held.note is None and held.event_entity_id is None
    told = [memory for memory in memories if memory.event_entity_id == legend.id]
    assert len(told) == 1 and told[0].note == LEGEND_NOTE and told[0].kind is MemoryKind.SAVED_ME
    assert sum(memory.magnitude for memory in memories) > 20


async def test_a_merged_memory_keeps_the_reason_it_was_first_remembered_for(realm: Realm) -> None:
    town = await settlement(realm, "Wexford")
    courtier = await mortal(realm, "Ilse")
    first = await remember(
        realm.session, RULES, holder_id=town.id, subject_id=courtier.id, kind=MemoryKind.GOODWILL, magnitude=10, epoch=1, note="first reason"
    )
    again = await remember(realm.session, RULES, holder_id=town.id, subject_id=courtier.id, kind=MemoryKind.GOODWILL, magnitude=5, epoch=1, note="later reason")
    assert first is not None and again is first
    assert first.note == "first reason" and first.magnitude == 15


async def test_a_world_made_trait_kind_scales_its_effects(realm: Realm) -> None:
    bold = await mortal(realm, "Gorm")
    variant = KindVariantRow(family=KindFamily.TRAIT, base=TraitKind.AMBITIOUS.value, name="Burning ambition", strength_pct=200, learning_pct=100, locked=[])
    realm.session.add(variant)
    await realm.session.flush()
    realm.session.add(TraitRow(node_id=bold.id, trait=TraitKind.AMBITIOUS, source=TraitSource.PLAYER, epoch=1))
    await realm.session.flush()
    plain = {effect: await effect_of(realm.session, bold.id, effect) for effect in TraitEffect}
    trait = await realm.session.get(TraitRow, (bold.id, TraitKind.AMBITIOUS))
    assert trait is not None
    trait.variant_id = variant.id
    await realm.session.flush()
    scaled = {effect: await effect_of(realm.session, bold.id, effect) for effect in TraitEffect}
    assert any(abs(scaled[effect]) > abs(plain[effect]) for effect in TraitEffect if plain[effect])


async def test_a_world_made_condition_kind_weighs_heavier(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await mortal(realm, "Hal")
    second = await mortal(realm, "Ilo")
    for bearer in (first, second):
        await gain_condition(ctx, bearer, ConditionKind.MELANCHOLY, HarmCause.PLAYER, severity=2)
    variant = KindVariantRow(family=KindFamily.CONDITION, base=ConditionKind.MELANCHOLY.value, name="Black bile", strength_pct=300, learning_pct=100, locked=[])
    realm.session.add(variant)
    await realm.session.flush()
    row = await realm.session.scalar(select(ConditionRow).where(ConditionRow.bearer_node_id == second.id))
    assert row is not None
    row.variant_id = variant.id
    await refresh(realm.session, RULES, first, ctx.epoch)
    await refresh(realm.session, RULES, second, ctx.epoch)
    plain = await realm.session.get(BodyRow, first.id)
    heavy = await realm.session.get(BodyRow, second.id)
    assert plain is not None and heavy is not None and heavy.command < plain.command


async def test_other_sex_is_never_seeded_unless_the_world_allows_it(realm: Realm) -> None:
    ctx = context(realm.session)
    mortals = [await mortal(realm, f"Seed{index}") for index in range(40)]
    for item in mortals:
        await seed_mortal(ctx, item)
    sexes = {item.stats.sex for item in mortals if isinstance(item.stats, MortalStats)}
    assert sexes <= {SexKind.BEARER.value, SexKind.BEGETTER.value}
    assert len(sexes) == 2
    rng = SeededRandom.for_epoch(1, 1, "sex")
    assert {born_sex(RULES, ReproductiveSystem.TWO_SEX, rng) for _ in range(200)} <= {SexKind.BEARER, SexKind.BEGETTER}
    open_world = tuned(fertility={"both_sex_pct": 100.0})
    assert born_sex(open_world, ReproductiveSystem.TWO_SEX, rng) is SexKind.BOTH
    assert born_sex(RULES, ReproductiveSystem.AMBISEXUAL, rng) is SexKind.BOTH
    profiles = list(await realm.session.scalars(select(MortalProfileRow)))
    assert len(profiles) == len(mortals)
