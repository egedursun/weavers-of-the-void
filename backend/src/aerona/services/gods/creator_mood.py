from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import CreatorMoodInputRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.creator import CreatorMoodLabel, CreatorSignKind
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import Publisher
from aerona.engine.gods.mood import MoodState, last_breakdown, mood_label, mood_of, store_breakdown, store_mood
from aerona.engine.gods.signs import grace_sign, lonely_dream, silence, wrath_sign
from aerona.engine.gods.stats import Trait, add_trait, set_trait, trait
from aerona.engine.gods.worship import CultEffect, creator_worshippers, cult_effect
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent
from aerona.rules.registry import Rules
from aerona.services.gods.context import record_action, require, require_creator

PRAYER_STAT_TRAITS = (Trait.PROSPERITY, Trait.FERTILITY, Trait.DEFENSE, Trait.HP)


@dataclass(frozen=True)
class MoodView:
    state: MoodState
    label: CreatorMoodLabel
    breakdown: tuple[CreatorMoodInputRow, ...]


@dataclass(frozen=True)
class CultView:
    members: tuple[EntityRow, ...]
    effect: CultEffect


async def read_mood(session: AsyncSession, rules: Rules) -> MoodView:
    state = mood_of(await require_creator(session))
    return MoodView(state, mood_label(rules, state), tuple(await last_breakdown(session)))


async def set_mood(session: AsyncSession, rules: Rules, state: MoodState) -> MoodView:
    ctx = await manual_context(session, "set_mood", rules)
    creator = await require_creator(session)
    store_mood(creator, state)
    await store_breakdown(session, ctx.epoch, ())
    await record_action(ctx, ActionKind.EDIT_CREATOR, creator.id)
    return await read_mood(session, rules)


async def read_cult(session: AsyncSession, rules: Rules) -> CultView:
    return CultView(tuple(await creator_worshippers(session)), await cult_effect(session, rules))


async def trigger_sign(
    session: AsyncSession, rules: Rules, kind: CreatorSignKind, target_id: int | None = None, publish: Publisher | None = None
) -> EntityRow | None:
    ctx = await manual_context(session, f"sign.{kind.value}", rules, publish)
    creator = await require_creator(session)
    target = require(await session.get(EntityRow, target_id), "record") if target_id is not None else None
    if target is not None and target.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{target.name} is not in the world.")
    if kind is CreatorSignKind.WRATH:
        result = await wrath_sign(ctx, creator, target)
        action = ActionKind.DISASTER
    elif kind is CreatorSignKind.GRACE:
        result = await grace_sign(ctx, creator, target)
        action = ActionKind.MIRACLE
    elif kind is CreatorSignKind.SILENCE:
        await silence(ctx, creator, announce=True)
        result = None
        action = ActionKind.OTHER
    else:
        result = await lonely_dream(ctx, creator, target)
        action = ActionKind.DREAM
    if kind is not CreatorSignKind.SILENCE and result is None:
        raise ValidationFailedError("There is no place or mortal for this sign to reach.")
    await record_action(ctx, action, result.id if result is not None else None)
    return result


async def answer_mortal_prayer(session: AsyncSession, rules: Rules, message_id: int, text: str, essence_given: int) -> EntityRow:
    ctx = await manual_context(session, "answer_prayer", rules)
    creator = await require_creator(session)
    message = require(await session.get(MessageRow, message_id), "prayer")
    if message.recipient_node_id != creator.id or message.answered:
        raise ValidationFailedError("This prayer is not waiting for an answer.")
    if not 0 <= essence_given <= rules.god_actions.prayer_essence_cap:
        raise ValidationFailedError(f"A prayer can receive at most {rules.god_actions.prayer_essence_cap} essence (world rule god_actions.prayer_essence_cap).")
    entity = await session.get(EntityRow, message.sender_node_id)
    if entity is None:
        raise ValidationFailedError("The one who prayed no longer exists.")
    if essence_given:
        if creator.essence < essence_given:
            raise ValidationFailedError(f"This needs {essence_given} divine essence; you have {creator.essence}.")
        creator.essence -= essence_given
    if trait(entity, Trait.PIETY) is not None:
        add_trait(entity, Trait.PIETY, rules.creator.prayer_faith_gain)
    if essence_given:
        bonus = round(essence_given / rules.creator.prayer_essence_per_stat)
        for key in PRAYER_STAT_TRAITS:
            current = trait(entity, key)
            if current is not None:
                ceiling = rules.limits.hp_cap if key is Trait.HP else None
                set_trait(entity, key, min(ceiling, current + bonus) if ceiling is not None else current + bonus)
    await worship_creator(session, entity, ctx.epoch, god_lines.PRAYER_ANSWERED_VOW)
    if text.strip():
        session.add(MessageRow(epoch=ctx.epoch, sender_node_id=creator.id, recipient_node_id=entity.id, intent=MessageIntent.DREAM, text=text.strip()))
    creator.mood_loneliness = clamp_percent(creator.mood_loneliness - rules.creator.prayer_loneliness_relief)
    creator.mood_contentment = clamp_percent(creator.mood_contentment + rules.creator.prayer_contentment)
    message.answered = True
    message.is_read = True
    message.answered_epoch = ctx.epoch
    message.answer_essence = essence_given
    await ctx.chronicle(
        ChronicleKind.CREATOR_HAND,
        god_lines.PRAYER_ANSWERED.render(creator=creator.name, entity=entity.name, grace=god_lines.PRAYER_GRACE if essence_given else ""),
        template_key=god_lines.PRAYER_ANSWERED.key,
        entity_ids=[entity.id],
    )
    await record_action(ctx, ActionKind.ANSWER_PRAYER, entity.id, essence_given)
    return entity
