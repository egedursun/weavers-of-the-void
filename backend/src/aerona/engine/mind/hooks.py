from collections.abc import Iterable

from aerona.catalog.mind import COMMAND_SKILLS, HEALING_SKILLS, MELEE_SKILLS, MISSILE_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import InjuryKind, InjuryState
from aerona.domain.enums.entity import HERO_ROLES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import ActKind, MemoryKind, SkillKind, TraitKind, TraitSource
from aerona.engine.context import TickContext
from aerona.engine.mind.book import load_holder, values_for
from aerona.engine.mind.memories import kin_of, remember
from aerona.engine.mind.skills import practise, practise_any
from aerona.engine.mind.space import value_reading
from aerona.engine.mind.traits import gain_trait

LOSS_KINDS = frozenset({InjuryKind.SEVERED, InjuryKind.GOUGED})
FIGHTING_ROLES = frozenset({*HERO_ROLES, MortalRole.CAPTAIN, MortalRole.BANDIT})
BATTLE_TRAITS = (TraitKind.BRAVE, TraitKind.CRAVEN)
MAIMED_TRAITS = (TraitKind.MELANCHOLIC, TraitKind.IRON_WILLED)
CAPTIVITY_TRAITS = (TraitKind.PARANOID,)
ACT_MEMORIES = {
    ActKind.EXECUTION: MemoryKind.KILLED_KIN,
    ActKind.BETRAYAL: MemoryKind.BETRAYED_ME,
    ActKind.OATHBREAKING: MemoryKind.BROKE_OATH,
    ActKind.CONQUEST: MemoryKind.CONQUERED_US,
}


def is_mortal(node: object) -> bool:
    return isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL


async def wound_memories(ctx: TickContext, bearer: object, source_id: int | None, rows: Iterable[InjuryRow], lost: int) -> None:
    items = [row for row in rows if row.state is not InjuryState.LETHAL]
    bearer_id = getattr(bearer, "id", None)
    if not isinstance(bearer_id, int) or not items:
        return
    maimed = any(row.kind in LOSS_KINDS for row in items)
    if source_id is not None and source_id != bearer_id and await load_holder(ctx.session, bearer_id) is not None:
        size = -max(1, round(lost * ctx.rules.memory.wound_memory_pct / PERCENT))
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=bearer_id,
            subject_id=source_id,
            kind=MemoryKind.MAIMED_ME if maimed else MemoryKind.HARMED_ME,
            magnitude=size,
            epoch=ctx.epoch,
        )
    if maimed and isinstance(bearer, EntityRow) and bearer.mortal_role in FIGHTING_ROLES:
        await gain_trait(
            ctx,
            bearer.id,
            MAIMED_TRAITS,
            ctx.rules.traits.maimed_chance,
            TraitSource.EXPERIENCE,
            values=await values_for(ctx.session, bearer.id),
            stream="maimed_trait",
        )


async def fought(ctx: TickContext, fighter: EntityRow, *, commander: bool = False, survived: bool = True) -> None:
    if not is_mortal(fighter):
        return
    skills = ctx.rules.skills
    await practise_any(ctx.session, ctx.rules, fighter.id, (*MELEE_SKILLS, *MISSILE_SKILLS), skills.battle_xp, epoch=ctx.epoch)
    if commander:
        await practise_any(ctx.session, ctx.rules, fighter.id, COMMAND_SKILLS, skills.command_xp, epoch=ctx.epoch)
    if survived:
        await gain_trait(
            ctx,
            fighter.id,
            BATTLE_TRAITS,
            ctx.rules.traits.battle_chance,
            TraitSource.EXPERIENCE,
            values=await values_for(ctx.session, fighter.id),
            stream="battle_trait",
        )


async def duelled(ctx: TickContext, duellist: object) -> None:
    if isinstance(duellist, EntityRow) and is_mortal(duellist):
        await practise_any(ctx.session, ctx.rules, duellist.id, MELEE_SKILLS, ctx.rules.skills.duel_xp, epoch=ctx.epoch)


async def taken_captive(ctx: TickContext, captive_id: int, captor_id: int) -> None:
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=captive_id,
        subject_id=captor_id,
        kind=MemoryKind.HELD_CAPTIVE,
        magnitude=-ctx.rules.memory.backfill_magnitude,
        epoch=ctx.epoch,
    )


async def freed(ctx: TickContext, captive: EntityRow, captor_id: int | None, rescuer_id: int | None = None) -> None:
    if not is_mortal(captive):
        return
    await gain_trait(
        ctx, captive.id, CAPTIVITY_TRAITS, ctx.rules.traits.captivity_chance, TraitSource.EXPERIENCE, source_node_id=captor_id, stream="captivity_trait"
    )
    if rescuer_id is not None and rescuer_id != captive.id:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=captive.id,
            subject_id=rescuer_id,
            kind=MemoryKind.FREED_US,
            magnitude=ctx.rules.memory.backfill_magnitude,
            epoch=ctx.epoch,
        )


async def healed(ctx: TickContext, healer_id: int, patient_id: int, *, saved: bool) -> None:
    await practise_any(ctx.session, ctx.rules, healer_id, HEALING_SKILLS, ctx.rules.skills.heal_xp, epoch=ctx.epoch)
    if saved:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=patient_id,
            subject_id=healer_id,
            kind=MemoryKind.SAVED_ME,
            magnitude=ctx.rules.memory.backfill_magnitude,
            epoch=ctx.epoch,
        )


async def failed_to_heal(ctx: TickContext, healer_id: int, patient: EntityRow) -> int:
    formed = 0
    mourners = [*await kin_of(ctx.session, patient.id)]
    if patient.status is EntityStatus.CANON:
        mourners.append(patient)
    for mourner in mourners:
        if mourner.id == healer_id:
            continue
        if await remember(
            ctx.session,
            ctx.rules,
            holder_id=mourner.id,
            subject_id=healer_id,
            kind=MemoryKind.FAILED_TO_HEAL,
            magnitude=-ctx.rules.memory.backfill_magnitude,
            epoch=ctx.epoch,
            note=patient.name,
        ):
            formed += 1
    return formed


async def practised(ctx: TickContext, node_id: int, skill: SkillKind, xp_rule: int) -> None:
    await practise(ctx.session, ctx.rules, node_id, skill, xp_rule, epoch=ctx.epoch)


async def practised_any(ctx: TickContext, node_id: int, skills: Iterable[SkillKind], xp_rule: int) -> None:
    await practise_any(ctx.session, ctx.rules, node_id, skills, xp_rule, epoch=ctx.epoch)


async def witnessed(ctx: TickContext, holder_id: int, subject_id: int, act: ActKind, *, base: int, note: str | None = None) -> int:
    if holder_id == subject_id:
        return 0
    reading = value_reading(await values_for(ctx.session, holder_id), act)
    size = round(base * reading / PERCENT)
    if not size:
        return 0
    kind = ACT_MEMORIES.get(act, MemoryKind.GOODWILL if size > 0 else MemoryKind.ILL_WILL)
    await remember(ctx.session, ctx.rules, holder_id=holder_id, subject_id=subject_id, kind=kind, magnitude=size, epoch=ctx.epoch, note=note)
    return size
