from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.body import ConditionRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mind import DreamRow, GriefRow, MemoryRow, ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.mind import (
    DreamKind,
    Emotion,
    Facet,
    GriefStage,
    MemoryKind,
    MoodState,
    NeedKind,
    ThoughtKind,
    TraitKind,
    ValueAxis,
    ValueHolder,
)
from aerona.engine.mind.book import ensure_mind_row, stored_values, traits_of, write_needs, write_values
from aerona.engine.mind.dreams import dream, visitations
from aerona.engine.mind.feelings import feel
from aerona.engine.mind.grief import GriefTally, advance, bereave
from aerona.engine.mind.memories import remember
from aerona.engine.mind.split import write_facets
from aerona.engine.mind.thoughts import need_importance, settle_mood, think
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.profile import ensure_profile
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal

RULES = Rules()


async def test_facets_sharpen_feelings_and_the_strongest_become_formative(realm: Realm) -> None:
    ctx = context(realm.session)
    calm = await mortal(realm, "Ivo")
    jumpy = await mortal(realm, "Neda")
    for one in (calm, jumpy):
        await ensure_mind_row(realm.session, one, ctx.epoch)
        await write_values(realm.session, ValueHolder.PERSONAL, one.id, {ValueAxis.MERCY: 0})
    await write_facets(realm.session, jumpy.id, {Facet.ANXIETY: 50, Facet.VULNERABILITY: 50})
    soft = await think(realm.session, RULES, calm.id, ThoughtKind.WAS_CAPTURED, ctx.epoch)
    sharp = await think(realm.session, RULES, jumpy.id, ThoughtKind.WAS_CAPTURED, ctx.epoch)
    assert soft is not None and sharp is not None and sharp.intensity > soft.intensity
    horror = await think(realm.session, RULES, calm.id, ThoughtKind.WITNESSED_ATROCITY, ctx.epoch, subject_id=jumpy.id)
    assert horror is not None and horror.memory_id is not None
    memory = await realm.session.get(MemoryRow, horror.memory_id)
    assert memory is not None and memory.kind is MemoryKind.FORMATIVE and memory.magnitude < 0
    assert (await stored_values(realm.session, ValueHolder.PERSONAL, calm.id))[ValueAxis.MERCY] == 8


async def test_feelings_sum_to_a_mood_that_the_god_can_hold(realm: Realm) -> None:
    ctx = context(realm.session)
    glad = await mortal(realm, "Pell")
    await ensure_mind_row(realm.session, glad, ctx.epoch)
    for kind in (ThoughtKind.MARRIED, ThoughtKind.CHILD_BORN, ThoughtKind.WON_BATTLE):
        await think(realm.session, RULES, glad.id, kind, ctx.epoch)
    assert await settle_mood(realm.session, RULES, glad, ctx.epoch) in {MoodState.ELATED, MoodState.CONTENT}
    profile, _ = await ensure_profile(realm.session, glad.id, ctx.epoch)
    profile.locked = ["mood"]
    profile.mood_score, profile.mood = -90, MoodState.BROKEN
    assert await settle_mood(realm.session, RULES, glad, ctx.epoch) is None
    assert profile.mood is MoodState.BROKEN


async def test_needs_matter_by_temperament_and_unmet_ones_darken_thoughts(realm: Realm) -> None:
    ctx = context(realm.session)
    scholar = await mortal(realm, "Ys")
    await ensure_mind_row(realm.session, scholar, ctx.epoch)
    await write_facets(realm.session, scholar.id, {Facet.CURIOSITY: 50})
    await write_values(realm.session, ValueHolder.PERSONAL, scholar.id, {ValueAxis.KNOWLEDGE: 80})
    assert need_importance(RULES, NeedKind.LEARNING, {Facet.CURIOSITY: 50}, {ValueAxis.KNOWLEDGE: 80}) > 140
    await write_needs(realm.session, scholar.id, {NeedKind.LEARNING: 5, NeedKind.SUSTENANCE: 95})
    await feel(ctx, scholar)
    kinds = set(await realm.session.scalars(select(ThoughtRow.kind).where(ThoughtRow.holder_node_id == scholar.id)))
    assert ThoughtKind.LEARNED_NOTHING in kinds


async def test_remembered_deeds_and_weddings_become_thoughts(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await mortal(realm, "Ama")
    second = await mortal(realm, "Bo")
    await ensure_mind_row(realm.session, first, ctx.epoch)
    await remember(realm.session, RULES, holder_id=first.id, subject_id=second.id, kind=MemoryKind.SAVED_ME, magnitude=40, epoch=ctx.epoch)
    await marry(realm.session, first, second, ctx.epoch)
    await feel(ctx, first)
    kinds = set(await realm.session.scalars(select(ThoughtRow.kind).where(ThoughtRow.holder_node_id == first.id)))
    assert {ThoughtKind.WAS_SAVED, ThoughtKind.MARRIED} <= kinds


async def test_a_spouse_mourns_and_a_grief_that_will_not_heal_leaves_melancholy(realm: Realm) -> None:
    hard = replace(RULES, grief=replace(RULES.grief, complicated_pct=100, shock_epochs=1, mourning_epochs=1))
    ctx = context(realm.session, hard)
    widow = await mortal(realm, "Ula")
    lost = await mortal(realm, "Ren")
    await ensure_mind_row(realm.session, widow, ctx.epoch)
    await marry(realm.session, widow, lost, ctx.epoch)
    assert await bereave(ctx, lost, None) == 1
    grief = await realm.session.scalar(select(GriefRow).where(GriefRow.mourner_node_id == widow.id))
    assert grief is not None and grief.stage is GriefStage.SHOCK
    tally = GriefTally()
    await advance(context(realm.session, hard, epoch=ctx.epoch + 1), widow, tally)
    assert grief.stage is GriefStage.MOURNING
    await advance(context(realm.session, hard, epoch=ctx.epoch + 3), widow, tally)
    assert grief.stage is GriefStage.COMPLICATED and TraitKind.MELANCHOLIC in await traits_of(realm.session, widow.id)


async def test_nightmares_recur_into_a_condition_and_god_messages_become_visitations(realm: Realm) -> None:
    rules = replace(RULES, dreams=replace(RULES.dreams, dream_pct=100, recurring_after=2, reading_pct=0, longing_weight=0, shared_weight=0))
    haunted = await mortal(realm, "Kas")
    foe = await mortal(realm, "Mor")
    ctx = context(realm.session, rules)
    await ensure_mind_row(realm.session, haunted, ctx.epoch)
    for epoch in (ctx.epoch, ctx.epoch + 1, ctx.epoch + 2):
        await remember(realm.session, rules, holder_id=haunted.id, subject_id=foe.id, kind=MemoryKind.FORMATIVE, magnitude=-90, epoch=epoch, merge=False)
    nightmares = 0
    for epoch in range(ctx.epoch, ctx.epoch + 4):
        row = await dream(context(realm.session, rules, epoch=epoch), haunted)
        nightmares += 1 if row is not None and row.kind is DreamKind.NIGHTMARE else 0
    assert nightmares >= 2
    assert await realm.session.scalar(select(ConditionRow.id).where(ConditionRow.bearer_node_id == haunted.id, ConditionRow.kind == ConditionKind.NIGHTMARES))
    profile = await realm.session.get(MortalProfileRow, haunted.id)
    assert profile is not None and profile.stress > 0
    realm.session.add(MessageRow(epoch=ctx.epoch, sender_node_id=foe.id, recipient_node_id=haunted.id, intent=MessageIntent.DREAM, text="Come north."))
    await realm.session.flush()
    assert await visitations(ctx) == 1
    visit = await realm.session.scalar(select(DreamRow).where(DreamRow.dreamer_node_id == haunted.id, DreamRow.kind == DreamKind.VISITATION))
    assert visit is not None and visit.sender_node_id == foe.id
    awe = await realm.session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == haunted.id, ThoughtRow.kind == ThoughtKind.RECEIVED_VISITATION))
    assert awe is not None and awe.emotion is Emotion.AWE
