from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmos import CreatorMoodInputRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.creator import CreatorMoodAxis, CreatorMoodLabel, CreatorSignKind
from aerona.domain.enums.entity import EntityFlag, EntityType, MortalRole
from aerona.engine.gods.mood import MoodInputs, MoodItem, MoodState, compute_mood_update, gather_mood_inputs, mood_label, unanswered_prayer_weight
from aerona.engine.gods.queries import worship_targets
from aerona.engine.gods.worship import creator_faith, creator_worshippers, cult_effect_from_faith
from aerona.engine.phases.creator_mood import PHASES, creator_mood
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.primitives.numbers import saturating
from aerona.rules.registry import Rules
from aerona.services.gods.creator_mood import answer_mortal_prayer, read_mood, set_mood, trigger_sign
from tests.engine.gods.factories import GodsWorld, bond, chronicle_keys, make_context, make_entity, make_son

QUIET = MoodInputs(wars=0, godless=0, communities=0, rebels=0, doom_clock=0, cult=0, new_life=0, actions=0, active_sons=5, unanswered_weight=0.0)


def test_saturating_reaches_half_cap_at_half() -> None:
    assert saturating(10, 10, 8) == pytest.approx(4.0)
    assert saturating(0, 10, 8) == 0.0


def test_mood_label_first_match(rules: Rules) -> None:
    assert mood_label(rules, MoodState(contentment=90, anger=80, interest=50, loneliness=10)) is CreatorMoodLabel.ANGRY
    assert mood_label(rules, MoodState(contentment=90, anger=10, interest=10, loneliness=10)) is CreatorMoodLabel.DISTANT
    assert mood_label(rules, MoodState(contentment=90, anger=10, interest=50, loneliness=80)) is CreatorMoodLabel.LONELY
    assert mood_label(rules, MoodState(contentment=90, anger=10, interest=50, loneliness=10)) is CreatorMoodLabel.CONTENT
    assert mood_label(rules, MoodState(contentment=10, anger=50, interest=50, loneliness=10)) is CreatorMoodLabel.UNEASY
    assert mood_label(rules, MoodState(contentment=10, anger=10, interest=50, loneliness=10)) is CreatorMoodLabel.SERENE


def test_mood_update_decays_and_opposes(rules: Rules) -> None:
    update = compute_mood_update(rules, MoodState(contentment=60, anger=40, interest=60, loneliness=30), QUIET)
    creator = rules.creator
    assert update.state.anger == round(40 * creator.wrath_keep_pct / 100 - 60 * creator.mood_opposition_pct / 100)
    assert update.state.interest == round(60 * creator.attention_keep_pct / 100)
    assert update.state.loneliness == round(30 * creator.loneliness_keep_pct / 100 + creator.loneliness_no_cult)
    items = {(item.axis, item.item) for item in update.breakdown}
    assert (CreatorMoodAxis.ANGER, MoodItem.CONTENTMENT_SOOTHES) in items
    assert (CreatorMoodAxis.CONTENTMENT, MoodItem.SHADOW_OF_ANGER) in items
    assert all(item.delta != 0 for item in update.breakdown)


def test_unanswered_prayers_are_capped(rules: Rules) -> None:
    calm = MoodState(contentment=50, anger=20, interest=60, loneliness=0)
    flooded = compute_mood_update(rules, calm, replace(QUIET, cult=1, unanswered_weight=500.0))
    assert flooded.state.loneliness == rules.creator.loneliness_unanswered_cap - rules.creator.loneliness_cult_relief


def test_actions_raise_interest_and_contentment(rules: Rules) -> None:
    base = MoodState(contentment=50, anger=0, interest=10, loneliness=0)
    idle = compute_mood_update(rules, base, QUIET)
    busy = compute_mood_update(rules, base, replace(QUIET, actions=20))
    assert busy.state.interest - idle.state.interest == rules.creator.attention_action_cap
    assert busy.state.contentment - idle.state.contentment == rules.creator.content_action


async def test_unanswered_window_decays(session: AsyncSession, world: GodsWorld) -> None:
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    for epoch in (1, 5, 9, 10):
        session.add(MessageRow(epoch=epoch, sender_node_id=mortal.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="hear me"))
    await session.flush()
    count, weight = await unanswered_prayer_weight(session, world.creator.id, 10, 8, 50)
    assert count == 2
    assert weight == pytest.approx(0.5 + 0.5**5)


async def test_a_prayer_of_the_epoch_just_lived_weighs_nothing_until_the_creator_could_answer(session: AsyncSession, world: GodsWorld) -> None:
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    session.add(MessageRow(epoch=10, sender_node_id=mortal.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="hear me"))
    await session.flush()
    assert await unanswered_prayer_weight(session, world.creator.id, 10, 8, 50) == (0, 0.0)
    count, weight = await unanswered_prayer_weight(session, world.creator.id, 11, 8, 50)
    assert count == 1 and weight == pytest.approx(0.5)


async def test_cult_faith_and_effect(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    assert await worship_creator(session, people, 2, "vow")
    assert not await worship_creator(session, people, 2, "vow")
    await worship_creator(session, mortal, 2, "vow")
    faith = await creator_faith(session, rules)
    expected = 6000 / rules.creator.cult_population_per_faith * 0.6 + rules.creator.cult_faith_per_mortal
    assert faith == round(expected)
    effect = cult_effect_from_faith(rules, 100)
    assert effect.essence == 100 // rules.creator.cult_faith_per_essence
    assert effect.doom_pushback == min(rules.creator.cult_apocalypse_push_cap, 100 // rules.creator.cult_faith_per_apocalypse_push)
    assert {entity.id for entity in await creator_worshippers(session)} == {people.id, mortal.id}


async def test_worship_creator_replaces_son_patron(session: AsyncSession, world: GodsWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)

    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    await worship_creator(session, people, 2, "vow")

    assert await worship_targets(session, people.id) == [world.creator.id]


async def test_phase_runs_wrath_sign_and_stores_breakdown(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = replace(rules, creator=replace(rules.creator, wrath_sign_chance=100, wrath_keep_pct=100, mood_opposition_pct=0))
    world.creator.mood_anger = 95
    people = await make_entity(session, "Sinners", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)

    await EntityRepository(session).add_flag(people.id, EntityFlag.GODLESS, 1)
    ctx = make_context(session, tuned, epoch=3, phase="creator_mood")
    await creator_mood(ctx)
    keys = await chronicle_keys(session)
    assert any(key.startswith("gods.mood.wrath") for key in keys)
    assert world.creator.mood_anger < 95
    stored = list(await session.scalars(select(CreatorMoodInputRow)))
    assert stored and all(row.epoch == 3 for row in stored)
    assert PHASES[0].name == "creator_mood"


async def test_lonely_creator_dreams_to_seer(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = replace(rules, creator=replace(rules.creator, loneliness_sign_chance=100, loneliness_keep_pct=100))
    world.creator.mood_loneliness = 90
    seer = await make_entity(session, "Oracle", EntityType.MORTAL, world_id=world.world.id, mortal_role=MortalRole.SEER)
    await make_entity(session, "Farmer", EntityType.MORTAL, world_id=world.world.id)
    await creator_mood(make_context(session, tuned, epoch=3, phase="creator_mood"))
    dreams = list(await session.scalars(select(MessageRow).where(MessageRow.intent == MessageIntent.DREAM)))
    assert [dream.recipient_node_id for dream in dreams] == [seer.id]
    assert dreams[0].text == god_lines.LONELY_DREAM


async def test_estranged_community_turns(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = replace(rules, creator=replace(rules.creator, estranged_turn_chance=100))
    people = await make_entity(session, "Lost", EntityType.PEOPLE, world_id=world.world.id)

    await EntityRepository(session).add_flag(people.id, EntityFlag.GODLESS, 1)
    await creator_mood(make_context(session, tuned, epoch=3, phase="creator_mood"))
    assert "gods.mood.estranged_turn" in await chronicle_keys(session)
    assert not await EntityRepository(session).has_flag(people.id, EntityFlag.GODLESS)


async def test_inputs_count_wars_and_godless(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    people = await make_entity(session, "Lost", EntityType.PEOPLE, world_id=world.world.id)

    await EntityRepository(session).add_flag(people.id, EntityFlag.GODLESS, 1)
    inputs = await gather_mood_inputs(session, rules, 1, 30)
    assert inputs.godless == 1
    assert inputs.communities == 1
    assert inputs.new_life == 1
    assert inputs.doom_clock == 30


async def test_manual_mood_and_signs(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    view = await set_mood(session, rules, MoodState(contentment=10, anger=99, interest=50, loneliness=20))
    assert view.label is CreatorMoodLabel.ANGRY
    assert view.breakdown == ()
    target = await make_entity(session, "Ash Plain", EntityType.REGION, world_id=world.world.id)
    struck = await trigger_sign(session, rules, CreatorSignKind.WRATH, target.id)
    assert struck is not None and struck.id == target.id
    mood = await read_mood(session, rules)
    assert mood.state.anger == 99 - rules.creator.wrath_discharge


async def test_answer_mortal_prayer(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    message = MessageRow(epoch=2, sender_node_id=people.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="rain")
    session.add(message)
    await session.flush()
    before = world.creator.essence
    await answer_mortal_prayer(session, rules, message.id, "Rain will come.", 9)
    assert message.answered
    assert world.creator.essence == before - 9
    assert people.stats.model_dump()["piety"] == 60 + rules.creator.prayer_faith_gain
    assert people.stats.model_dump()["prosperity"] == 50 + 3
    assert people.id in {entity.id for entity in await creator_worshippers(session)}
