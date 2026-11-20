from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.mind import AttributeRow, CultureValueRow, FacetRow, IdeaRow, TraitRow
from aerona.domain.enums.mind import Attribute, Facet, IdeaKind, IdeaSource, IdeaState, SkillKind, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.engine.mind.book import add_trait, ensure_mind_row, stored_values, write_values
from aerona.engine.mind.ideas import Encounter, take_up, turn_over
from aerona.engine.mind.split import (
    attributes_of,
    effective_attributes,
    facets_of,
    seed_split,
    store_attributes,
    talent,
    temper_facets,
    weather_attributes,
    write_facets,
)
from aerona.engine.phases.mind import AXES_FIXUP, backfill_axes
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, people

RULES = Rules()
QUIET = replace(RULES, mind_split=replace(RULES.mind_split, seed_jitter=0, facet_jitter=0))


async def test_attributes_seed_from_stats_and_a_changed_stat_flows_back(realm: Realm) -> None:
    sage = await mortal(realm, "Ilse", intellect=80, strength=40)
    ctx = context(realm.session, QUIET)
    await ensure_mind_row(realm.session, sage, ctx.epoch)
    assert await seed_split(realm.session, QUIET, sage, ctx.rng("seed")) == 2
    attributes = await attributes_of(realm.session, sage.id)
    assert attributes[Attribute.ANALYTICAL_ABILITY] == 80 and attributes[Attribute.MEMORY] == 80
    assert attributes[Attribute.STRENGTH] == 40
    set_stats(sage, intellect=30)
    assert await weather_attributes(realm.session, QUIET, sage, ctx.epoch)
    moved = await attributes_of(realm.session, sage.id)
    assert moved[Attribute.ANALYTICAL_ABILITY] == 30 and moved[Attribute.MEMORY] == 30
    assert stat(sage, "intellect") == 30


async def test_a_marked_facet_becomes_a_trait_and_a_held_trait_pulls_its_facet(realm: Realm) -> None:
    seeker = await mortal(realm, "Brann")
    ctx = context(realm.session, QUIET)
    await ensure_mind_row(realm.session, seeker, ctx.epoch)
    await seed_split(realm.session, QUIET, seeker, ctx.rng("seed"))
    await write_facets(realm.session, seeker.id, {Facet.CURIOSITY: 45, Facet.PERSEVERANCE: 0})
    await add_trait(realm.session, seeker.id, TraitKind.STUBBORN, TraitSource.PLAYER, ctx.epoch)
    gained = await temper_facets(realm.session, QUIET, seeker, ctx.epoch)
    assert TraitKind.CURIOUS in gained
    row = await realm.session.get(TraitRow, (seeker.id, TraitKind.CURIOUS))
    assert row is not None and row.source is TraitSource.FACET
    assert (await facets_of(realm.session, seeker.id))[Facet.PERSEVERANCE] == QUIET.mind_split.trait_pull


async def test_governing_attributes_speed_learning() -> None:
    gifted = dict.fromkeys(Attribute, 90)
    clumsy = dict.fromkeys(Attribute, 10)
    assert talent(RULES, gifted, SkillKind.BLADE) > 1 > talent(RULES, clumsy, SkillKind.BLADE)


async def test_an_idea_costs_focus_while_it_incubates_then_settles_into_beliefs(realm: Realm) -> None:
    scholar = await mortal(realm, "Mirel")
    ctx = context(realm.session, QUIET)
    await ensure_mind_row(realm.session, scholar, ctx.epoch)
    await seed_split(realm.session, QUIET, scholar, ctx.rng("seed"))
    await write_values(realm.session, ValueHolder.PERSONAL, scholar.id, {ValueAxis.KNOWLEDGE: 40})
    before = await attributes_of(realm.session, scholar.id)
    row = await take_up(realm.session, scholar.id, Encounter(IdeaKind.RATIONALISM, IdeaSource.PLAYER, None), ctx.epoch, progress=99)
    assert row is not None
    focus = (await effective_attributes(realm.session, QUIET, scholar))[Attribute.FOCUS]
    assert focus < before[Attribute.FOCUS]
    tally = await turn_over(ctx, scholar, KnowledgeMap({}))
    assert tally.internalised == 1 and row.state is IdeaState.INTERNALISED
    values = await stored_values(realm.session, ValueHolder.PERSONAL, scholar.id)
    assert values[ValueAxis.KNOWLEDGE] == 60 and values[ValueAxis.SUPERSTITION] == -20
    assert (await attributes_of(realm.session, scholar.id))[Attribute.ANALYTICAL_ABILITY] == before[Attribute.ANALYTICAL_ABILITY] + 6


async def test_an_idea_that_grates_against_beliefs_is_let_go(realm: Realm) -> None:
    mystic = await mortal(realm, "Oda")
    strict = replace(QUIET, ideas=replace(QUIET.ideas, reject_pct=100, encounter_pct=0))
    ctx = context(realm.session, strict)
    await ensure_mind_row(realm.session, mystic, ctx.epoch)
    await write_values(realm.session, ValueHolder.PERSONAL, mystic.id, {ValueAxis.KNOWLEDGE: -100, ValueAxis.SUPERSTITION: 100})
    await take_up(realm.session, mystic.id, Encounter(IdeaKind.RATIONALISM, IdeaSource.TEACHER, None), ctx.epoch)
    tally = await turn_over(ctx, mystic, KnowledgeMap({}))
    row = await realm.session.scalar(select(IdeaRow).where(IdeaRow.holder_node_id == mystic.id))
    assert tally.rejected == 1 and row is not None and row.state is IdeaState.REJECTED


async def test_old_cultures_gain_the_new_belief_axes_once(realm: Realm) -> None:
    folk = await people(realm, "Hallow")
    realm.session.add_all(CultureValueRow(entity_id=folk.id, axis=axis, value=value) for axis, value in {ValueAxis.HONOUR: 80, ValueAxis.KINSHIP: 60}.items())
    await realm.session.flush()
    ctx = context(realm.session)
    assert await backfill_axes(ctx) == 1
    values = await stored_values(realm.session, ValueHolder.CULTURE, folk.id)
    assert values[ValueAxis.TRUTH] > 0 and values[ValueAxis.LOYALTY] > 0 and values[ValueAxis.FAMILY] > 0
    assert await realm.session.get(AppliedFixupRow, AXES_FIXUP) is not None
    assert await backfill_axes(ctx) == 0


async def test_a_mind_touched_before_it_was_seeded_stays_whole_and_weathers(realm: Realm) -> None:
    hunter = await mortal(realm, "Teo", strength=60)
    ctx = context(realm.session, QUIET)
    await ensure_mind_row(realm.session, hunter, ctx.epoch)
    session = realm.session
    for row in [
        *await session.scalars(select(AttributeRow).where(AttributeRow.node_id == hunter.id)),
        *await session.scalars(select(FacetRow).where(FacetRow.node_id == hunter.id)),
    ]:
        await session.delete(row)
    await session.flush()
    session.add(AttributeRow(node_id=hunter.id, attribute=Attribute.ENDURANCE, value=65))
    await write_facets(session, hunter.id, {Facet.ANGER: 20})
    await session.flush()
    assert await seed_split(session, QUIET, hunter, ctx.rng("seed")) == 2
    attributes = await attributes_of(session, hunter.id)
    assert set(attributes) == set(Attribute) and attributes[Attribute.ENDURANCE] == 65
    assert len(await facets_of(session, hunter.id)) == len(Facet) and (await facets_of(session, hunter.id))[Facet.ANGER] == 20
    await store_attributes(session, hunter, {Attribute.EMPATHY: 70})
    await weather_attributes(session, QUIET, hunter, ctx.epoch)
    assert set(await attributes_of(session, hunter.id)) == set(Attribute)
