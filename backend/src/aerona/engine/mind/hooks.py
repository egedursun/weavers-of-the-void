from collections.abc import Iterable

from sqlalchemy import select

from aerona.catalog.mind import COMMAND_SKILLS, HEALING_SKILLS, MELEE_SKILLS, MEMORIES, MISSILE_SKILLS
from aerona.catalog.thoughts import ATROCITIES
from aerona.constants.units import PERCENT
from aerona.db.repositories.chronicle import ChronicleRepository, incident_for
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import InjuryKind, InjuryState
from aerona.domain.enums.entity import COMMUNITY_TYPES, HERO_ROLES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.mind import ActKind, MemoryKind, SkillKind, ThoughtKind, TraitKind, TraitSource
from aerona.engine.body.treatment import exert
from aerona.engine.context import TickContext
from aerona.engine.intrigue.favours import owe
from aerona.engine.lore.taboos import violated
from aerona.engine.mind.book import load_holder, values_for
from aerona.engine.mind.ethics import conscience, ethic_reading
from aerona.engine.mind.memories import kin_of, remember
from aerona.engine.mind.skills import practise, practise_any
from aerona.engine.mind.thoughts import think
from aerona.engine.mind.traits import gain_trait
from aerona.engine.renown.currencies import on_act
from aerona.engine.renown.deeds import deed_seen

LOSS_KINDS = frozenset({InjuryKind.SEVERED, InjuryKind.GOUGED})
FIGHTING_ROLES = frozenset({*HERO_ROLES, MortalRole.CAPTAIN, MortalRole.BANDIT})
BATTLE_TRAITS = (TraitKind.BRAVE, TraitKind.CRAVEN)
MAIMED_TRAITS = (TraitKind.MELANCHOLIC, TraitKind.IRON_WILLED)
CAPTIVITY_TRAITS = (TraitKind.PARANOID,)
ACT_MEMORIES: dict[ActKind, MemoryKind] = {}
for _kind, _spec in MEMORIES.items():
    if _spec.act is not None:
        ACT_MEMORIES.setdefault(_spec.act, _kind)
COMMUNITY_KINDS = tuple(COMMUNITY_TYPES)


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
        if maimed:
            await judged(ctx, source_id, bearer_id, ActKind.MUTILATION)
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


async def fought(ctx: TickContext, fighter: EntityRow, *, commander: bool = False, survived: bool = True, won: bool | None = None) -> None:
    if not is_mortal(fighter):
        return
    if survived and won is not None:
        await think(ctx.session, ctx.rules, fighter.id, ThoughtKind.WON_BATTLE if won else ThoughtKind.DEFEATED, ctx.epoch)
    skills = ctx.rules.skills
    await exert(ctx, fighter)
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
        await exert(ctx, duellist)
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
    await judged(ctx, captor_id, captive_id, ActKind.TAKING_CAPTIVES)


async def freed(ctx: TickContext, captive: EntityRow, captor_id: int | None, rescuer_id: int | None = None) -> None:
    if not is_mortal(captive):
        return
    await gain_trait(
        ctx, captive.id, CAPTIVITY_TRAITS, ctx.rules.traits.captivity_chance, TraitSource.EXPERIENCE, source_node_id=captor_id, stream="captivity_trait"
    )
    if rescuer_id is not None and rescuer_id != captive.id:
        await owe(ctx, captive.id, rescuer_id, FavourOrigin.RESCUE, ctx.rules.intrigue.rescue_favour)
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
    await think(ctx.session, ctx.rules, patient_id, ThoughtKind.WAS_HEALED, ctx.epoch, subject_id=healer_id)
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


async def witnessed(
    ctx: TickContext, holder_id: int, subject_id: int, act: ActKind, *, base: int, note: str | None = None, victim_id: int | None = None
) -> int:
    if holder_id == subject_id:
        return 0
    values = await values_for(ctx.session, holder_id)
    reading = await ethic_reading(ctx.session, ctx.rules, holder_id, act, values, actor_id=subject_id, victim_id=victim_id)
    size = round(base * reading / PERCENT)
    if not size:
        return 0
    kind = MemoryKind.GOODWILL if size > 0 else ACT_MEMORIES.get(act, MemoryKind.ILL_WILL)
    await remember(ctx.session, ctx.rules, holder_id=holder_id, subject_id=subject_id, kind=kind, magnitude=size, epoch=ctx.epoch, note=note)
    await deed_seen(ctx, holder_id, subject_id, act, reading)
    await on_act(ctx, subject_id, act, reading, holder_id)
    return size


async def onlookers(ctx: TickContext, actor_id: int, victim_id: int) -> list[int]:
    victim = await ctx.session.get(EntityRow, victim_id)
    if victim is None or victim.location_id is None:
        return []
    statement = select(EntityRow.id).where(
        EntityRow.location_id == victim.location_id,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.entity_type.in_(COMMUNITY_KINDS),
        EntityRow.id.not_in([actor_id, victim_id]),
    )
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def horrified(ctx: TickContext, actor_id: int, victim_id: int) -> list[int]:
    victim = await ctx.session.get(EntityRow, victim_id)
    if victim is None or victim.location_id is None:
        return []
    statement = select(EntityRow.id).where(
        EntityRow.location_id == victim.location_id,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.id.not_in([actor_id, victim_id]),
    )
    witnesses = list(await ctx.session.scalars(statement.order_by(EntityRow.id)))
    for witness in witnesses:
        await think(ctx.session, ctx.rules, witness, ThoughtKind.WITNESSED_ATROCITY, ctx.epoch, subject_id=actor_id)
    return witnesses


async def judged(ctx: TickContext, actor_id: int, victim_id: int, act: ActKind, *, note: str | None = None) -> int:
    await violated(ctx, actor_id, act)
    base = ctx.rules.memory.witness_magnitude
    if not base:
        return 0
    moved = 0
    seen = await onlookers(ctx, actor_id, victim_id)
    for holder in seen:
        moved += abs(await witnessed(ctx, holder, actor_id, act, base=base, note=note, victim_id=victim_id))
    if act in ATROCITIES:
        moved += len(await horrified(ctx, actor_id, victim_id))
    await conscience(ctx, actor_id, act, victim_id)
    incident = incident_for(actor_id, ctx.epoch) or incident_for(victim_id, ctx.epoch)
    if incident is not None and seen:
        await ChronicleRepository(ctx.session).witness(incident, seen)
    return moved


async def converted(ctx: TickContext, convert_id: int, converter_id: int, *, note: str | None = None) -> int:
    if convert_id == converter_id:
        return 0
    size = ctx.rules.memory.conversion_magnitude
    await remember(
        ctx.session, ctx.rules, holder_id=convert_id, subject_id=converter_id, kind=MemoryKind.CONVERTED_ME, magnitude=size, epoch=ctx.epoch, note=note
    )
    return size


async def desecrated(ctx: TickContext, keeper_id: int, desecrator_id: int, *, note: str | None = None) -> int:
    if keeper_id == desecrator_id:
        return 0
    size = -ctx.rules.memory.outrage_magnitude
    await remember(
        ctx.session, ctx.rules, holder_id=keeper_id, subject_id=desecrator_id, kind=MemoryKind.DESECRATED_HOLY, magnitude=size, epoch=ctx.epoch, note=note
    )
    return size
