from dataclasses import dataclass, replace

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorMoodInputRow, CreatorRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.creator import CreatorMoodAxis, CreatorMoodLabel, CreatorPassion
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.engine.divine.prayer_window import overdue_in_run
from aerona.engine.gods.worship import creator_node_id, creator_worshippers
from aerona.engine.lore.research import mean_spread
from aerona.engine.primitives.numbers import clamp_percent, decay_weight, saturating, scaled_cap
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

BATTLE_KINDS = frozenset({EngineKind.BATTLE, EngineKind.SIEGE})
NEW_LIFE_TYPES = frozenset({EntityType.PEOPLE, EntityType.MORTAL, EntityType.SETTLEMENT, EntityType.SPECIES})
BREAKDOWN_PRECISION = 2
HALF = 0.5


class MoodItem:
    WARS = "wars"
    GODLESS = "godless"
    REBEL_SONS = "rebel_sons"
    DOOMSDAY = "doomsday_clock"
    CONTENTMENT_SOOTHES = "contentment_soothes"
    CULT = "cult"
    NEW_LIFE = "new_life"
    ACTED = "the_god_acted"
    SHADOW_OF_ANGER = "shadow_of_anger"
    BATTLES = "battles"
    BLOOD = "blood_shed"
    LEAK = "leak"
    TEMPERAMENT = "temperament"
    STIR = "stir"
    PASSIONS = "passions"


@dataclass(frozen=True)
class MoodState:
    contentment: int
    anger: int
    interest: int
    loneliness: int
    temperament: int = 0


@dataclass(frozen=True)
class MoodInputs:
    wars: int
    godless: int
    communities: int
    rebels: int
    doom_clock: int
    cult: int
    new_life: int
    actions: int
    active_sons: int
    unanswered_weight: float
    battles: int = 0
    killings: int = 0
    mean_leak: float = 0.0
    temperament_roll: float = HALF
    anger_roll: float = HALF
    content_roll: float = HALF
    passions: tuple[CreatorPassion, ...] = ()
    discoveries: int = 0
    works: int = 0


@dataclass(frozen=True)
class MoodBreakdownItem:
    axis: CreatorMoodAxis
    item: str
    delta: float


@dataclass(frozen=True)
class MoodUpdate:
    state: MoodState
    breakdown: tuple[MoodBreakdownItem, ...]


def mood_of(creator: CreatorRow) -> MoodState:
    return MoodState(creator.mood_contentment, creator.mood_anger, creator.mood_interest, creator.mood_loneliness, creator.mood_temperament or 0)


def store_mood(creator: CreatorRow, state: MoodState) -> None:
    creator.mood_contentment = clamp_percent(state.contentment)
    creator.mood_anger = clamp_percent(state.anger)
    creator.mood_interest = clamp_percent(state.interest)
    creator.mood_loneliness = clamp_percent(state.loneliness)
    creator.mood_temperament = max(-PERCENT, min(PERCENT, state.temperament))


def mood_label(rules: Rules, state: MoodState) -> CreatorMoodLabel:
    creator = rules.creator
    if state.anger >= creator.label_wrathful:
        return CreatorMoodLabel.ANGRY
    if state.interest <= creator.label_silent:
        return CreatorMoodLabel.DISTANT
    if state.loneliness >= creator.label_lonely:
        return CreatorMoodLabel.LONELY
    if state.contentment >= creator.label_content:
        return CreatorMoodLabel.CONTENT
    if state.anger >= creator.label_restless:
        return CreatorMoodLabel.UNEASY
    return CreatorMoodLabel.SERENE


def swing(roll: float, width: int) -> float:
    return (roll * 2 - 1) * width


def passion_matches(rules: Rules, inputs: MoodInputs) -> float:
    calm = rules.creator.content_passion_half
    matches = {
        CreatorPassion.WAR: inputs.battles,
        CreatorPassion.CHAOS: inputs.wars + inputs.killings,
        CreatorPassion.ORDER: max(0, calm - inputs.wars),
        CreatorPassion.CREATION: inputs.new_life,
        CreatorPassion.KNOWLEDGE: inputs.discoveries,
        CreatorPassion.BEAUTY: inputs.works,
        CreatorPassion.MERCY: max(0, calm - inputs.killings),
        CreatorPassion.SILENCE: max(0, calm - inputs.actions),
    }
    return float(sum(matches[passion] for passion in inputs.passions))


def compute_mood_update(rules: Rules, state: MoodState, inputs: MoodInputs) -> MoodUpdate:
    creator = rules.creator
    war_cap = max(1, scaled_cap(rules.diplomacy.world_war_cap, rules.diplomacy.cap_community_divisor, inputs.communities))
    threshold = max(1, rules.balance.apocalypse_threshold)
    godless_share = inputs.godless / inputs.communities * PERCENT if inputs.communities else 0.0
    temperament = round(state.temperament * creator.temperament_keep_pct / PERCENT + swing(inputs.temperament_roll, creator.temperament_wave))
    anger_items = [
        (MoodItem.WARS, saturating(inputs.wars / war_cap * PERCENT, creator.wrath_war_half_pct, creator.wrath_war_max)),
        (MoodItem.BATTLES, saturating(inputs.battles, creator.wrath_battle_half, creator.wrath_battle_max)),
        (MoodItem.BLOOD, saturating(inputs.killings, creator.wrath_blood_half, creator.wrath_blood_max)),
        (MoodItem.LEAK, saturating(inputs.mean_leak, creator.wrath_leak_half, creator.wrath_leak_max)),
        (MoodItem.TEMPERAMENT, float(temperament)),
        (MoodItem.STIR, swing(inputs.anger_roll, creator.mood_jitter)),
        (MoodItem.GODLESS, saturating(godless_share, creator.wrath_godless_half_pct, creator.wrath_godless_max)),
        (MoodItem.REBEL_SONS, saturating(inputs.rebels, creator.wrath_rebel_half, creator.wrath_rebel_max)),
        (MoodItem.DOOMSDAY, inputs.doom_clock / threshold * PERCENT / creator.wrath_apocalypse_divisor),
        (MoodItem.CONTENTMENT_SOOTHES, -state.contentment * creator.mood_opposition_pct / PERCENT),
    ]
    content_items = [
        (MoodItem.CULT, saturating(inputs.cult, creator.content_cult_half, creator.content_cult_max)),
        (MoodItem.NEW_LIFE, saturating(inputs.new_life, creator.content_new_life_half, creator.content_new_life_max)),
        (MoodItem.ACTED, float(creator.content_action) if inputs.actions else 0.0),
        (MoodItem.PASSIONS, saturating(passion_matches(rules, inputs), creator.content_passion_half, creator.content_passion_max) if inputs.passions else 0.0),
        (MoodItem.SHADOW_OF_ANGER, -state.anger * creator.mood_opposition_pct / PERCENT),
        (MoodItem.TEMPERAMENT, -temperament * creator.temperament_content_pct / PERCENT),
        (MoodItem.STIR, swing(inputs.content_roll, creator.mood_jitter)),
    ]
    anger = clamp_percent(state.anger * creator.wrath_keep_pct / PERCENT + sum(delta for _, delta in anger_items))
    contentment = clamp_percent(state.contentment * creator.content_keep_pct / PERCENT + sum(delta for _, delta in content_items))
    interest = clamp_percent(
        state.interest * creator.attention_keep_pct / PERCENT + min(creator.attention_action_cap, inputs.actions * creator.attention_per_action)
    )
    loneliness_terms = (
        (creator.loneliness_few_sons if inputs.active_sons < creator.loneliness_son_threshold else 0)
        + (-creator.loneliness_cult_relief if inputs.cult else creator.loneliness_no_cult)
        + min(float(creator.loneliness_unanswered_cap), inputs.unanswered_weight)
    )
    loneliness = clamp_percent(state.loneliness * creator.loneliness_keep_pct / PERCENT + loneliness_terms)
    breakdown = tuple(
        MoodBreakdownItem(axis, item, round(delta, BREAKDOWN_PRECISION))
        for axis, items in ((CreatorMoodAxis.ANGER, anger_items), (CreatorMoodAxis.CONTENTMENT, content_items))
        for item, delta in items
        if round(delta, BREAKDOWN_PRECISION) != 0
    )
    return MoodUpdate(replace(state, anger=anger, contentment=contentment, interest=interest, loneliness=loneliness, temperament=temperament), breakdown)


async def unanswered_prayer_weight(session: AsyncSession, recipient_id: int, epoch: int, window: int, keep_pct: float) -> tuple[int, float]:
    statement = select(MessageRow.epoch).where(
        MessageRow.recipient_node_id == recipient_id,
        overdue_in_run(epoch),
        MessageRow.intent != MessageIntent.CHAT,
        MessageRow.epoch > epoch - window,
    )
    epochs = list(await session.scalars(statement))
    return len(epochs), sum(decay_weight(keep_pct, epoch - sent) for sent in epochs)


async def creator_action_count(session: AsyncSession, epoch: int) -> int:
    statement = select(func.count(ActionRecordRow.id)).where(ActionRecordRow.epoch == epoch, ActionRecordRow.actor_kind == ActorKind.CREATOR)
    return int(await session.scalar(statement) or 0)


async def gather_mood_inputs(session: AsyncSession, rules: Rules, old_epoch: int, doom_clock: int) -> MoodInputs:
    community_filter = (EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    communities = int(await session.scalar(select(func.count(EntityRow.id)).where(*community_filter)) or 0)
    godless_statement = (
        select(func.count(EntityRow.id))
        .join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id)
        .where(*community_filter, EntityFlagRow.flag == EntityFlag.GODLESS)
    )
    godless = int(await session.scalar(godless_statement) or 0)
    rebels = int(await session.scalar(select(func.count(SonRow.id)).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD)) or 0)
    active = int(await session.scalar(select(func.count(SonRow.id)).where(SonRow.status == SonStatus.ACTIVE)) or 0)
    new_life_statement = select(func.count(EntityRow.id)).where(
        EntityRow.birth_epoch == old_epoch, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(NEW_LIFE_TYPES))
    )
    new_life = int(await session.scalar(new_life_statement) or 0)
    creator_id = await creator_node_id(session)
    weight = 0.0
    if creator_id is not None:
        _, weight = await unanswered_prayer_weight(
            session, creator_id, old_epoch, rules.creator.unanswered_window_epochs, rules.creator.unanswered_decay_keep_pct
        )
    battles = int(
        await session.scalar(select(func.count(EntityRow.id)).where(EntityRow.birth_epoch == old_epoch, EntityRow.engine_kind.in_(list(BATTLE_KINDS)))) or 0
    )
    killings = int(await session.scalar(select(func.count(BondRow.id)).where(BondRow.kind == BondKind.KILLED, BondRow.epoch == old_epoch)) or 0)
    leak = float(await session.scalar(select(func.avg(WorldRow.leakage))) or 0.0)
    born = select(func.count(EntityRow.id)).where(EntityRow.birth_epoch == old_epoch, EntityRow.status == EntityStatus.CANON)
    discoveries = int(await session.scalar(born.where(EntityRow.entity_type == EntityType.KNOWLEDGE)) or 0)
    discoveries += round(await mean_spread(session) * rules.creator.spread_interest_pct / PERCENT)
    works = int(await session.scalar(born.where(EntityRow.entity_type.in_([EntityType.ARTWORK, EntityType.STRUCTURE]))) or 0)
    creator_row = await session.scalar(select(CreatorRow).limit(1))
    return MoodInputs(
        passions=tuple(creator_row.passions) if creator_row is not None else (),
        discoveries=discoveries,
        works=works,
        battles=battles,
        killings=killings,
        mean_leak=leak,
        wars=await ongoing_war_count(session),
        godless=godless,
        communities=communities,
        rebels=rebels,
        doom_clock=doom_clock,
        cult=len(await creator_worshippers(session)),
        new_life=new_life,
        actions=await creator_action_count(session, old_epoch),
        active_sons=active,
        unanswered_weight=weight,
    )


async def store_breakdown(session: AsyncSession, epoch: int, breakdown: tuple[MoodBreakdownItem, ...]) -> None:
    await session.execute(delete(CreatorMoodInputRow))
    session.add_all(CreatorMoodInputRow(epoch=epoch, axis=item.axis, item=item.item, delta=item.delta) for item in breakdown)
    await session.flush()


async def last_breakdown(session: AsyncSession) -> list[CreatorMoodInputRow]:
    return list(await session.scalars(select(CreatorMoodInputRow).order_by(CreatorMoodInputRow.id)))
