from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.culture import (
    LanguageIntelligibilityRow,
    LanguageRegisterRow,
    SpeakerCohortRow,
    TraditionEffectRow,
    TraditionParticipationRow,
    TraditionProfileRow,
)
from aerona.domain.enums.culture import LanguageRegister, SpeakerKind, TraditionEffectKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.lore import traditions
from aerona.engine.polity.control import lock
from aerona.engine.primitives.queries import living_entity

HOLDERS = frozenset({*COMMUNITY_TYPES, EntityType.CULT, EntityType.POLITY})
EFFECT_LIMIT = PERCENT
TARGETS = {
    TraditionEffectKind.VALUE: frozenset(axis.value for axis in ValueAxis),
    TraditionEffectKind.SATISFACTION: frozenset({"", *(item.value for item in SocialClass)}),
}


async def living_language(ctx: TickContext, language_id: int) -> None:
    language = await living_entity(ctx.session, language_id)
    if language is None or language.entity_type is not EntityType.LANGUAGE:
        raise NotFoundError("No such living language.")


async def set_register(ctx: TickContext, holder_id: int, register: LanguageRegister, language_id: int | None, *, hold: bool) -> LanguageRegisterRow | None:
    holder = await living_entity(ctx.session, holder_id)
    if holder is None or holder.entity_type not in HOLDERS:
        raise NotFoundError("No such living people, settlement, faith or realm.")
    row = await ctx.session.get(LanguageRegisterRow, (holder_id, register))
    if language_id is None:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    await living_language(ctx, language_id)
    if row is None:
        row = LanguageRegisterRow(holder_entity_id=holder_id, register=register, language_entity_id=language_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.language_entity_id, row.since_epoch = language_id, ctx.epoch
    row.locked = lock(row.locked, "language_entity_id") if hold else [item for item in row.locked if item != "language_entity_id"]
    await ctx.session.flush()
    return row


def released(locked: list[str], key: str) -> list[str]:
    return [item for item in locked if item != key]


async def release_intelligibility(ctx: TickContext, first: int, second: int) -> LanguageIntelligibilityRow:
    low, high = sorted((first, second))
    row = await ctx.session.get(LanguageIntelligibilityRow, (low, high))
    if row is None:
        raise NotFoundError("Those tongues have not yet been measured against each other.")
    row.locked = released(row.locked, "value")
    await ctx.session.flush()
    return row


async def release_speakers(ctx: TickContext, community_id: int, language_id: int, kind: SpeakerKind) -> SpeakerCohortRow:
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, kind))
    if row is None:
        raise NotFoundError("No one there speaks it that way.")
    row.locked = released(row.locked, "share")
    await ctx.session.flush()
    return row


async def release_participation(ctx: TickContext, tradition_id: int, community_id: int) -> TraditionParticipationRow:
    row = await ctx.session.get(TraditionParticipationRow, (tradition_id, community_id))
    if row is None:
        raise NotFoundError("That community does not keep it.")
    row.locked = released(row.locked, "participation")
    await ctx.session.flush()
    return row


async def tradition_profile(ctx: TickContext, tradition_id: int) -> TraditionProfileRow:
    tradition = await living_entity(ctx.session, tradition_id)
    if tradition is None or tradition.entity_type is not EntityType.TRADITION:
        raise NotFoundError("No such living tradition.")
    return await traditions.profile_of(ctx, tradition)


async def set_tradition_effect(ctx: TickContext, tradition_id: int, effect: TraditionEffectKind, target: str, magnitude: int) -> TraditionEffectRow | None:
    row = await tradition_profile(ctx, tradition_id)
    await traditions.seed_effects(ctx, row)
    allowed = TARGETS.get(effect, frozenset({""}))
    if target not in allowed:
        raise ValidationFailedError(f"{target or 'Nothing'} is not something {effect.value.replace('_', ' ')} can aim at.")
    found = await ctx.session.get(TraditionEffectRow, (tradition_id, effect, target))
    if magnitude == 0:
        if found is not None:
            await ctx.session.delete(found)
            await ctx.session.flush()
        return None
    if not -EFFECT_LIMIT <= magnitude <= EFFECT_LIMIT:
        raise ValidationFailedError(f"Strength runs from -{EFFECT_LIMIT} to {EFFECT_LIMIT}.")
    if found is None:
        found = TraditionEffectRow(tradition_entity_id=tradition_id, effect=effect, target=target, magnitude=magnitude)
        ctx.session.add(found)
    found.magnitude = magnitude
    await ctx.session.flush()
    return found


async def reseed_tradition(ctx: TickContext, tradition_id: int) -> int:
    row = await tradition_profile(ctx, tradition_id)
    await traditions.apply_custom_kind(ctx, row)
    return await traditions.seed_effects(ctx, row, replace=True)
