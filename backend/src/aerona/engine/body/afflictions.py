from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.effect_packages import PACKAGES, PackageSpec, StageSpec
from aerona.catalog.incident_kinds.body_lines import ONSET_STEPS
from aerona.catalog.life.body import POWER_CURE_SPELL_FORMS
from aerona.catalog.life_traits import MEMORY_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import SymbiontRow
from aerona.db.tables.made import AugmentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.affliction import ChangeSign, CureKind, PackageKind, Transmission, Visibility
from aerona.domain.enums.body import HarmCause, InjuryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.life_traits import MemoryKindTrait
from aerona.domain.enums.mind import ActKind, MemoryKind, ValueHolder
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.powers import PowerState
from aerona.domain.enums.records import StepAction, StepOutcome, StepState
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import HeroQuestStatus
from aerona.engine.body.book import ensure_body
from aerona.engine.body.conditions import end_condition, gain_condition
from aerona.engine.body.hits import Harm
from aerona.engine.body.packages_w52 import (
    Shape,
    bind_charm,
    broken_charm,
    change_body,
    fortune_turns,
    line_chance,
    meet_fortunes,
    pull_charm,
    restore_body,
    shape_row,
    trigger_came,
)
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import clamp_value, needs_of, stored_values, write_needs, write_values
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.folk import folk_of, present_among
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.queries import active_bonds, flags_by_entity, living_entity
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record

AFFLICTION_KEY = "afflictions"
STAGE_HOLD = "stage"
BEARER_TYPES = frozenset({EntityType.MORTAL, EntityType.BEAST})


def spec_of(row: AfflictionRow) -> PackageSpec:
    return PACKAGES[row.package]


def stage_of(row: AfflictionRow) -> StageSpec | None:
    stages = spec_of(row).stages
    return stages[row.stage - 1] if 1 <= row.stage <= len(stages) else None


def visible(row: AfflictionRow) -> bool:
    return spec_of(row).visibility is not Visibility.HIDDEN and row.stage > 0


async def active(session: AsyncSession, bearer_id: int) -> list[AfflictionRow]:
    rows = await session.scalars(
        select(AfflictionRow).where(AfflictionRow.bearer_node_id == bearer_id, AfflictionRow.cured_epoch.is_(None)).order_by(AfflictionRow.id)
    )
    return list(rows)


async def carriers(session: AsyncSession, packages: set[PackageKind]) -> dict[int, list[AfflictionRow]]:
    found: dict[int, list[AfflictionRow]] = {}
    for row in await session.scalars(select(AfflictionRow).where(AfflictionRow.cured_epoch.is_(None), AfflictionRow.package.in_(list(packages)))):
        found.setdefault(row.bearer_node_id, []).append(row)
    return found


async def ageless(session: AsyncSession, bearer_id: int) -> bool:
    return any((stage := stage_of(row)) is not None and stage.ageless for row in await active(session, bearer_id))


def bearable(bearer: EntityRow | None) -> bool:
    return bearer is not None and bearer.entity_type in BEARER_TYPES and bearer.status is EntityStatus.CANON


TRAIT_PREFIX = "trait."


async def revert(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    deltas = {key: delta for key, delta in row.applied.items() if not key.startswith(TRAIT_PREFIX)}
    if deltas:
        set_stats(bearer, **{key: max(0, min(PERCENT, (stat(bearer, key) or 0) - delta)) for key, delta in deltas.items()})
    granted = {key.removeprefix(TRAIT_PREFIX) for key in row.applied if key.startswith(TRAIT_PREFIX)}
    if granted:
        body = await ctx.session.get(BodyRow, bearer.id)
        if body is not None:
            body.traits = [trait for trait in body.traits if trait not in granted]
    row.applied = {}
    stage = stage_of(row)
    if stage is not None and stage.condition is not None:
        await end_condition(ctx, bearer, stage.condition, announce=False)
    if stage is not None and stage.changes_body:
        await restore_body(ctx, bearer, row)


async def enter_stage(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, number: int) -> None:
    await revert(ctx, bearer, row)
    row.stage = number
    row.stage_since_epoch = ctx.epoch
    stage = stage_of(row)
    if stage is None:
        return
    if stage.condition is not None:
        await gain_condition(ctx, bearer, stage.condition, HarmCause.CURSE, severity=stage.severity, source_node_id=row.source_node_id, announce=False)
    applied = {key: delta for key, delta in stage.stats.items() if stat(bearer, key) is not None}
    if applied:
        set_stats(bearer, **{key: max(0, min(PERCENT, (stat(bearer, key) or 0) + delta)) for key, delta in applied.items()})
    if stage.grants:
        body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
        fresh = sorted(trait.value for trait in stage.grants if trait.value not in body.traits)
        body.traits = sorted({*body.traits, *fresh})
        applied |= {f"{TRAIT_PREFIX}{trait}": 1 for trait in fresh}
    row.applied = applied
    if stage.changes_body:
        await change_body(ctx, bearer, row)
    if stage.lucky:
        await fortune_turns(ctx, bearer, row, stage)
    if stage.values:
        values = dict(await stored_values(ctx.session, ValueHolder.PERSONAL, bearer.id))
        for axis, delta in stage.values.items():
            values[axis] = clamp_value(values.get(axis, 0) + delta)
        await write_values(ctx.session, ValueHolder.PERSONAL, bearer.id, values)
    if stage.fears_source and row.source_node_id is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=bearer.id,
            subject_id=row.source_node_id,
            kind=MemoryKind.DREADS,
            magnitude=ctx.rules.effect_packages.fear_magnitude,
            epoch=ctx.epoch,
        )


async def afflict(
    ctx: TickContext,
    bearer: EntityRow | None,
    package: PackageKind,
    transmission: Transmission,
    *,
    source_node_id: int | None = None,
    shape: Shape | None = None,
) -> AfflictionRow | None:
    if bearer is None or not bearable(bearer) or blocked(bearer.id, AFFLICTION_KEY):
        return None
    for row in await active(ctx.session, bearer.id):
        if row.package is package:
            if package is PackageKind.FORTUNE:
                sign = (shape.fortune_sign if shape is not None else None) or (-1 if transmission is Transmission.CURSE else 1)
                strength = shape.fortune_strength if shape is not None and shape.fortune_strength is not None else ctx.rules.packages.fortune_strength
                await meet_fortunes(ctx, bearer, row, sign, strength)
            return row
    spec = PACKAGES[package]
    row = AfflictionRow(
        bearer_node_id=bearer.id,
        package=package,
        stage=0,
        since_epoch=ctx.epoch,
        stage_since_epoch=ctx.epoch,
        transmission=transmission,
        source_node_id=source_node_id,
        applied={},
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await shape_row(ctx, row, shape)
    if package is PackageKind.CHARM:
        await bind_charm(ctx, bearer, row)
    if spec.onset <= 0:
        await enter_stage(ctx, bearer, row, 1)
    if spec.visibility is not Visibility.HIDDEN:
        roles: dict[IncidentRole, RoleValue] = {IncidentRole.PATIENT: bearer.id, IncidentRole.ACTOR: source_node_id}
        steps = onset_steps(bearer.id, row, source_node_id)
        await record(ctx, f"affliction.{package.value}", roles=roles, facts={"package": package, "transmission": transmission}, steps=steps)
    return row


def onset_steps(bearer_id: int, row: AfflictionRow, source_node_id: int | None) -> tuple[StepDraft, ...]:
    if row.package not in ONSET_STEPS:
        return ()
    states = ((bearer_id, StepState.POSSESSED),) if row.package is PackageKind.POSSESSION else ()
    return (affliction_step(ONSET_STEPS[row.package], row, source_node_id, bearer_id, states=states),)


def affliction_step(action: StepAction, row: AfflictionRow, actor: int | None, bearer_id: int, *, states: tuple[tuple[int, StepState], ...] = ()) -> StepDraft:
    return StepDraft(
        action,
        actor=actor,
        target=bearer_id,
        outcome=StepOutcome.SUCCESS,
        record_table=AfflictionRow.__tablename__,
        record_key=str(row.id),
        states=states,
    )


def cure_steps(bearer_id: int, row: AfflictionRow, how: CureKind | None) -> tuple[StepDraft, ...]:
    recovered = affliction_step(StepAction.RECOVER, row, None, bearer_id)
    if how is CureKind.MEDICINE:
        return (affliction_step(StepAction.TREAT, row, None, bearer_id), recovered)
    return (recovered,)


async def cure(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, how: CureKind | None) -> None:
    await revert(ctx, bearer, row)
    await restore_body(ctx, bearer, row)
    row.cured_epoch = ctx.epoch
    if row.package is PackageKind.CHARM:
        await broken_charm(ctx, bearer, row, found=how is not None and how is not CureKind.TIME)
    spec = spec_of(row)
    if spec.visibility is not Visibility.HIDDEN or how is not None:
        facts: dict[str, FactInput] = {"package": row.package, "stage": row.stage}
        if how is not None:
            facts["cure"] = how
        key = "affliction.cured_by" if how is not None else "affliction.cured"
        await record(ctx, key, roles={IncidentRole.PATIENT: bearer.id}, facts=facts, steps=cure_steps(bearer.id, row, how))


async def medicine_of(ctx: TickContext, bearer: EntityRow) -> int:
    holders = [bearer.id, *([bearer.location_id] if bearer.location_id is not None else [])]
    return max((levels.get(KnowledgeBranch.MEDICINE, 0) for levels in (await known_levels(ctx.session, holders)).values()), default=0)


async def neighbours(ctx: TickContext, bearer: EntityRow) -> list[EntityRow]:
    if bearer.location_id is None:
        return []
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(
            await present_among(ctx.session, [bearer.location_id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != bearer.id,
        )
        .order_by(EntityRow.id)
    )
    return list(rows)


async def has_role_near(ctx: TickContext, bearer: EntityRow, role: MortalRole) -> bool:
    return any(item.mortal_role is role for item in await neighbours(ctx, bearer))


async def quested(ctx: TickContext, bearer: EntityRow, since: int) -> bool:
    found = await ctx.session.scalar(
        select(HeroQuestRow.id).where(HeroQuestRow.target_node_id == bearer.id, HeroQuestRow.status == HeroQuestStatus.SUCCEEDED).limit(1)
    )
    return found is not None and since <= ctx.epoch


WIDER_CURES: Handlers[CureKind, Callable[[TickContext, EntityRow], Awaitable[bool]]] = Handlers(CureKind)


@WIDER_CURES.on(CureKind.DIVINE)
async def divine_cure(ctx: TickContext, bearer: EntityRow) -> bool:
    patron = await living_patron(ctx.session, bearer)
    return patron is not None and bool(await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[bearer.id], targets=[patron.id]))


@WIDER_CURES.on(CureKind.POWER)
async def power_cure(ctx: TickContext, bearer: EntityRow) -> bool:
    near = [item.id for item in await neighbours(ctx, bearer)]
    found = await ctx.session.scalar(
        select(PowerRow.id).where(PowerRow.holder_node_id.in_(near), PowerRow.form.in_(POWER_CURE_SPELL_FORMS), PowerRow.state == PowerState.ACTIVE).limit(1)
    )
    return found is not None


@WIDER_CURES.on(CureKind.SYMBIONT)
async def symbiont_cure(ctx: TickContext, bearer: EntityRow) -> bool:
    return await ctx.session.scalar(select(SymbiontRow.id).where(SymbiontRow.host_node_id == bearer.id).limit(1)) is not None


@WIDER_CURES.on(CureKind.TRANSFER)
async def transfer_cure(ctx: TickContext, bearer: EntityRow) -> bool:
    mind = await ctx.session.get(MindProfileRow, bearer.id)
    return mind is not None and mind.seat is not MindSeat.BODY


@WIDER_CURES.on(CureKind.AUGMENT)
async def augment_cure(ctx: TickContext, bearer: EntityRow) -> bool:
    return await ctx.session.scalar(select(AugmentRow.id).where(AugmentRow.bearer_node_id == bearer.id).limit(1)) is not None


async def try_cures(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> CureKind | None:
    table = ctx.rules.effect_packages
    spec = spec_of(row)
    rng = ctx.rng(f"cure.{row.id}")
    final = row.stage >= len(spec.stages)
    if CureKind.TIME in spec.cures and final and ctx.epoch - row.stage_since_epoch >= table.time_epochs:
        return CureKind.TIME
    if CureKind.QUEST in spec.cures and await quested(ctx, bearer, row.since_epoch):
        return CureKind.QUEST
    healed = await medicine_of(ctx, bearer) >= spec.cure_level and await has_role_near(ctx, bearer, MortalRole.HEALER)
    if CureKind.MEDICINE in spec.cures and healed and rng.chance(table.medicine_pct):
        return CureKind.MEDICINE
    if CureKind.RITE in spec.cures and await has_role_near(ctx, bearer, MortalRole.PRIEST) and rng.chance(table.rite_pct):
        return CureKind.RITE
    return await other_cures(ctx, bearer, spec, rng)


async def other_cures(ctx: TickContext, bearer: EntityRow, spec: PackageSpec, rng: SeededRandom) -> CureKind | None:
    table = ctx.rules.effect_packages
    herbal = bearer.location_id is not None and await knows_technique(ctx, bearer.location_id, Technique.HERBALISM)
    if CureKind.TECHNIQUE in spec.cures and herbal and rng.chance(table.technique_pct):
        return CureKind.TECHNIQUE
    for kind, cured in WIDER_CURES.items():
        if kind in spec.cures and await cured(ctx, bearer) and rng.chance(table.wider_cure_pct):
            return kind
    return None


async def knows_technique(ctx: TickContext, holder_id: int, technique: Technique) -> bool:
    found = await ctx.session.scalar(
        select(HolderTechniqueRow.holder_entity_id).where(HolderTechniqueRow.holder_entity_id == holder_id, HolderTechniqueRow.technique == technique).limit(1)
    )
    return found is not None


async def first_moon(ctx: TickContext, world_id: int | None) -> EntityRow | None:
    if world_id is None:
        return None
    found: EntityRow | None = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.world_id == world_id,
            EntityRow.entity_type == EntityType.CELESTIAL,
            EntityRow.domain == Domain.MOON,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def sunlit(ctx: TickContext, world_id: int | None) -> bool:
    world = await ctx.session.get(WorldRow, world_id) if world_id is not None else None
    return world is not None and world.star_id is not None


async def join_outer_cult(ctx: TickContext, bearer: EntityRow) -> None:
    cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    for cult_id in sorted(cults):
        cult = await living_entity(ctx.session, cult_id)
        if cult is not None and cult.world_id == bearer.world_id:
            await BondRepository(ctx.session).connect(BondDraft(bearer.id, cult.id, BondKind.MEMBER_OF, ctx.epoch, "claimed by the void"))
            return


async def moon_rampage(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    table = ctx.rules.effect_packages
    rng = ctx.rng(f"affliction.{row.id}.moon")
    moon = await first_moon(ctx, bearer.world_id)
    brightness = (stat_or(moon, "brightness", PERCENT // 2)) if moon is not None else 0
    victims = await neighbours(ctx, bearer)
    if moon is None or not victims or not rng.chance(table.rampage_pct * brightness / PERCENT):
        return
    harm = Harm(table.rampage_harm, HarmCause.MONSTER, "torn apart under the moon", source_node_id=bearer.id, killer_id=bearer.id, kind=InjuryKind.BITE)
    await apply_hits(ctx, rng.pick(victims), harm)


async def feed(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    table = ctx.rules.effect_packages
    rng = ctx.rng(f"affliction.{row.id}.feed")
    victims = await neighbours(ctx, bearer)
    if not victims:
        return
    victim = rng.pick(victims)
    harm = Harm(table.feed_harm, HarmCause.MONSTER, "drained of blood", source_node_id=bearer.id, killer_id=bearer.id, kind=InjuryKind.BITE)
    await apply_hits(ctx, victim, harm)
    await judged(ctx, bearer.id, victim.id, ActKind.EATING_SAPIENTS)
    if rng.chance(table.blood_pct):
        await afflict(ctx, victim, PackageKind.VAMPIRISM, Transmission.BLOOD, source_node_id=bearer.id)


async def stage_effects(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, stage: StageSpec) -> None:
    table = ctx.rules.effect_packages
    if stage.sanity_loss and bearer.sanity is not None:
        bearer.sanity = max(0, bearer.sanity - stage.sanity_loss)
    if stage.needs or stage.quenches:
        needs = dict(await needs_of(ctx.session, bearer.id))
        for need in stage.needs:
            needs[need] = max(0, needs.get(need, PERCENT) - table.need_pressure)
        for need in stage.quenches:
            needs[need] = PERCENT
        await write_needs(ctx.session, bearer.id, needs)
    if stage.sunlight_harm and await sunlit(ctx, bearer.world_id):
        await apply_hits(ctx, bearer, Harm(table.sunlight_harm, HarmCause.CURSE, "burned away by the sun"), lethal=True)
    if stage.transforms:
        await moon_rampage(ctx, bearer, row)
    if row.package is PackageKind.VAMPIRISM and stage.ageless:
        await feed(ctx, bearer, row)
    if stage.recruits:
        await join_outer_cult(ctx, bearer)
    await package_turns(ctx, bearer, row, stage)
    if Transmission.CONTACT in spec_of(row).contagion:
        rng = ctx.rng(f"affliction.{row.id}.contact")
        for other in await neighbours(ctx, bearer):
            if rng.chance(table.contact_pct):
                await afflict(ctx, other, row.package, Transmission.CONTACT, source_node_id=bearer.id)


async def package_turns(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, stage: StageSpec) -> None:
    if stage.lucky and row.stage_since_epoch != ctx.epoch:
        await fortune_turns(ctx, bearer, row, stage)
    if stage.binds and await pull_charm(ctx, bearer, row, stage):
        await cure(ctx, bearer, row, CureKind.TIME)
        return
    if row.package is PackageKind.TRANSFORMATION:
        await transformation_turns(ctx, bearer, row)


async def transformation_turns(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    if STAGE_HOLD in row.locked:
        return
    if row.stage == 1 and (row.transform_trigger or ChangeSign.NONE) is ChangeSign.NONE:
        row.stage_since_epoch = ctx.epoch
        return
    moon = await first_moon(ctx, bearer.world_id)
    bright = moon is not None and stat_or(moon, "brightness", PERCENT // 2) >= PERCENT // 2
    recurs = ctx.rng(f"transform.recur.{row.id}.{ctx.epoch}").chance(ctx.rules.packages.transform_recur_pct)
    if row.stage == len(spec_of(row).stages) and await trigger_came(ctx, bearer, row, bright) and recurs:
        await enter_stage(ctx, bearer, row, 1)


async def spread_by_bite(ctx: TickContext) -> int:
    biting = {kind for kind, spec in PACKAGES.items() if Transmission.BITE in spec.contagion}
    bearers = await carriers(ctx.session, biting)
    if not bearers:
        return 0
    spread = 0
    bites = await ctx.session.scalars(
        select(InjuryRow).where(InjuryRow.epoch == ctx.epoch, InjuryRow.kind == InjuryKind.BITE, InjuryRow.cause_node_id.in_(list(bearers)))
    )
    for bite in bites:
        victim = await living_entity(ctx.session, bite.bearer_node_id)
        for carried in bearers.get(bite.cause_node_id or 0, []):
            passes = victim is not None and ctx.rng(f"bite.{bite.id}.{carried.package.value}").chance(ctx.rules.effect_packages.bite_pct)
            if passes and await afflict(ctx, victim, carried.package, Transmission.BITE, source_node_id=carried.bearer_node_id) is not None:
                spread += 1
    return spread


async def inherit(ctx: TickContext, child: EntityRow, parents: list[int]) -> int:
    hereditary = {kind for kind, spec in PACKAGES.items() if spec.hereditary}
    gained = 0
    for parent_id in parents:
        for row in await active(ctx.session, parent_id):
            passes = row.package in hereditary and ctx.rng(f"inherit.{child.id}.{row.package.value}").chance(line_chance(ctx, row.package))
            shape = Shape(fortune_sign=row.fortune_sign, fortune_strength=row.fortune_strength)
            if passes and await afflict(ctx, child, row.package, Transmission.BIRTH, source_node_id=row.source_node_id, shape=shape) is not None:
                gained += 1
    return gained


async def desecrator_of(ctx: TickContext, node_id: int) -> EntityRow | None:
    found = await living_entity(ctx.session, node_id)
    if found is not None and found.entity_type is EntityType.MORTAL:
        return found
    if found is None:
        return None
    soldier: EntityRow | None = await ctx.session.scalar(
        select(EntityRow)
        .where(await folk_of(ctx.session, found), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    return soldier


async def desecration_curse(ctx: TickContext, shrine: EntityRow, desecrator_id: int) -> AfflictionRow | None:
    god_id = await shrine_god(ctx, shrine)
    god = await ctx.session.get(SonRow, god_id) if god_id is not None else None
    if god is None:
        return None
    if not ctx.rng(f"desecration.{shrine.id}.{desecrator_id}").chance(ctx.rules.effect_packages.desecration_pct):
        return None
    package = vengeance_package(ctx, god)
    return await afflict(ctx, await desecrator_of(ctx, desecrator_id), package, Transmission.CURSE, source_node_id=god.id)


def vengeance_package(ctx: TickContext, god: SonRow) -> PackageKind:
    domains = ".".join(sorted(domain.value for domain in (god.domain_primary, god.domain_secondary) if domain is not None))
    return ctx.rng(f"vengeance.{god.id}.{domains}").pick(sorted(PackageKind, key=lambda kind: kind.value))


async def shrine_god(ctx: TickContext, shrine: EntityRow) -> int | None:
    profile = await ctx.session.get(StructureProfileRow, shrine.id)
    if profile is not None and profile.dedicated_son_id is not None:
        return profile.dedicated_son_id
    bond: int | None = await ctx.session.scalar(
        select(BondRow.target_node_id).where(BondRow.source_node_id == shrine.id, BondRow.kind == BondKind.WORSHIPS).order_by(BondRow.id).limit(1)
    )
    return bond


async def blood_curse(ctx: TickContext, god: SonRow, target: EntityRow) -> AfflictionRow | None:
    if Domain.BLOOD not in (god.domain_primary, god.domain_secondary) or target.entity_type is not EntityType.MORTAL:
        return None
    if not ctx.rng(f"blood_curse.{god.id}.{target.id}").chance(ctx.rules.effect_packages.blood_curse_pct):
        return None
    return await afflict(ctx, target, PackageKind.VAMPIRISM, Transmission.CURSE, source_node_id=god.id)


TRAUMA_KINDS = having(MEMORY_KIND_TRAITS, MemoryKindTrait.TRAUMA_KINDS)


async def traumatise(ctx: TickContext) -> int:
    table = ctx.rules.effect_packages
    found = 0
    rows = await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.epoch == ctx.epoch, MemoryRow.kind.in_(list(TRAUMA_KINDS)), MemoryRow.magnitude <= -table.trauma_magnitude)
    )
    for memory in rows:
        holder = await living_entity(ctx.session, memory.holder_node_id)
        if holder is None or holder.entity_type is not EntityType.MORTAL or (stat_or(holder, "willpower", PERCENT // 2)) >= table.trauma_willpower:
            continue
        if await afflict(ctx, holder, PackageKind.TRAUMA, Transmission.EXPERIENCE, source_node_id=memory.subject_node_id) is not None:
            found += 1
    return found


async def progress(ctx: TickContext) -> dict[str, int]:
    counts = {"advanced": 0, "cured": 0, "spread": await spread_by_bite(ctx), "traumatised": await traumatise(ctx)}
    rows = list(await ctx.session.scalars(select(AfflictionRow).where(AfflictionRow.cured_epoch.is_(None)).order_by(AfflictionRow.id)))
    for row in rows:
        bearer = await living_entity(ctx.session, row.bearer_node_id)
        if bearer is None or frozen(bearer.id):
            continue
        spec = spec_of(row)
        held = STAGE_HOLD in row.locked
        if not held and row.stage == 0 and ctx.epoch - row.since_epoch >= spec.onset:
            await enter_stage(ctx, bearer, row, 1)
            counts["advanced"] += 1
        stage = stage_of(row)
        if not held and stage is not None and stage.epochs is not None and ctx.epoch - row.stage_since_epoch >= stage.epochs and row.stage < len(spec.stages):
            await enter_stage(ctx, bearer, row, row.stage + 1)
            counts["advanced"] += 1
            stage = stage_of(row)
        if stage is not None:
            await stage_effects(ctx, bearer, row, stage)
        how = await try_cures(ctx, bearer, row) if row.stage > 0 else None
        if how is not None:
            await cure(ctx, bearer, row, how)
            counts["cured"] += 1
    return counts
