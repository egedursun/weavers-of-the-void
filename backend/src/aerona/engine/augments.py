from sqlalchemy import select

from aerona.catalog.life_traits import MIND_UPKEEP_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import AugmentEffectRow, AugmentRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import MindUpkeepTrait
from aerona.domain.enums.made import AugmentKind, AugmentMake, AugmentSlot, EffectTarget, MadeMindStance
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.minds import MindUpkeep
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.research import techniques_of
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.mind.book import skill_level
from aerona.engine.minds.continuity import law_for
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record

BEARER_TYPES = frozenset({EntityType.MORTAL, EntityType.BEAST, EntityType.SPIRIT, EntityType.COSMIC_BEING})
SELF_KEPT = having(MIND_UPKEEP_TRAITS, MindUpkeepTrait.SELF_KEPT)
REJECTING = frozenset({MadeMindStance.ABOMINATION})


async def bearer(ctx: TickContext, node_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None or entity.status is not EntityStatus.CANON or entity.entity_type not in BEARER_TYPES:
        raise ValidationFailedError("Only a living being with a body can bear an augment.")
    return entity


async def install(
    ctx: TickContext,
    bearer_id: int,
    *,
    slot: AugmentSlot,
    part: BodyPart | None,
    kind: AugmentKind,
    make: AugmentMake,
    quality: int,
    surgeon_id: int | None,
    effects: list[tuple[EffectTarget, str, int]],
    forced: bool = False,
) -> AugmentRow:
    being = await bearer(ctx, bearer_id)
    if not forced and await law_for(ctx, being, LawKind.AUGMENT_LAW, "level") == "banned":
        raise ValidationFailedError("The law here forbids augmenting a body.")
    if slot is AugmentSlot.PART and part is None:
        raise ValidationFailedError("An augment of a body part names the part.")
    skill = await skill_level(ctx.session, surgeon_id, SkillKind.SURGERY) if surgeon_id is not None else 0
    table = ctx.rules.augments
    integration = clamp_percent(table.base_integration + round_half_up(skill * table.skill_pct / PERCENT) + (quality - PERCENT // 2) // 2)
    row = AugmentRow(
        bearer_node_id=being.id,
        slot=slot,
        part=part,
        kind=kind,
        make=make,
        quality=clamp_percent(quality),
        upkeep=MindUpkeep.MAINTENANCE if make is AugmentMake.MADE else MindUpkeep.VIS if make is AugmentMake.RITE_BOUND else MindUpkeep.FOOD,
        integration=integration,
        strain=0,
        installed_by_node_id=surgeon_id,
        installed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    for target, key, amount in effects:
        ctx.session.add(AugmentEffectRow(augment_id=row.id, target=target, target_key=key, amount=amount, locked=[]))
    await ctx.session.flush()
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.PATIENT: being.id, IncidentRole.HEALER: surgeon_id}
    facts: dict[str, FactInput] = {"slot": slot, "kind": kind, "make": make, "quality": row.quality, "integration": integration}
    if part is not None:
        facts["part"] = part
    steps = (
        StepDraft(
            StepAction.OPERATE,
            actor=surgeon_id,
            target=being.id,
            locus_kind=StepLocus.BODY_PART if part else StepLocus.NONE,
            locus_key=part.value if part else None,
            outcome=StepOutcome.SUCCESS,
        ),
    )
    await record(ctx, "augment.installed", roles=roles, facts=facts, steps=steps)
    return row


async def remove(ctx: TickContext, augment_id: int) -> int:
    row = await ctx.session.get(AugmentRow, augment_id)
    if row is None:
        raise ValidationFailedError("No such augment.")
    being = await ctx.session.get(EntityRow, row.bearer_node_id)
    if row.kind is AugmentKind.REPLACEMENT and being is not None and not held(being.id) and stat_or(being, "hp", 0):
        set_stats(being, hp=max(0, stat_or(being, "hp", 0) - ctx.rules.augments.removal_harm))
    bearer_id = row.bearer_node_id
    facts: dict[str, FactInput] = {"slot": row.slot, "kind": row.kind, "make": row.make}
    await ctx.session.delete(row)
    await ctx.session.flush()
    await record(ctx, "augment.removed", roles={IncidentRole.PATIENT: bearer_id}, facts=facts)
    return bearer_id


async def doctrine_rejects(ctx: TickContext, being: EntityRow) -> bool:
    doctrine = await doctrine_here(ctx.session, being)
    return doctrine is not None and doctrine.augment_stance in REJECTING


async def strain_of(ctx: TickContext, being: EntityRow, row: AugmentRow, count: int) -> int:
    table = ctx.rules.augments
    strain = max(0, table.integration_floor - row.integration) * table.poor_integration_pct // PERCENT
    if count > table.many_augments:
        strain += (count - table.many_augments) * table.per_extra
    if await doctrine_rejects(ctx, being):
        strain += table.doctrine_strain
    return clamp_percent(strain)


async def keep_one(ctx: TickContext, being: EntityRow, row: AugmentRow, count: int) -> None:
    table = ctx.rules.augments
    paid = row.upkeep in SELF_KEPT or await points_of(ctx.session, being) >= table.upkeep_wealth
    if not paid and "integration" not in row.locked:
        row.integration = clamp_percent(row.integration - table.unpaid_loss)
    if "strain" not in row.locked:
        row.strain = await strain_of(ctx, being, row, count)
    if row.strain >= table.stress_at and being.entity_type is EntityType.MORTAL:
        await add_stress(ctx.session, being.id, row.strain * table.stress_pct / PERCENT, ctx.epoch)
    if row.integration <= table.rejection_at and ctx.rng(f"augment.reject.{row.id}.{ctx.epoch}").chance(table.rejection_chance):
        rejected: dict[str, FactInput] = {"slot": row.slot, "kind": row.kind, "integration": row.integration, "strain": row.strain}
        await record(ctx, "augment.rejected", roles={IncidentRole.PATIENT: being.id}, facts=rejected)
        await ctx.session.delete(row)


@reads("table.augment_effects", "table.augments", "table.cult_doctrines", "table.entities", "table.mortal_profiles")
@writes("table.augments", "table.mortal_profiles")
async def keep_augments(ctx: TickContext) -> None:
    rows = list(await ctx.session.scalars(select(AugmentRow).order_by(AugmentRow.bearer_node_id, AugmentRow.id)))
    counts: dict[int, int] = {}
    for row in rows:
        counts[row.bearer_node_id] = counts.get(row.bearer_node_id, 0) + 1
    for row in rows:
        being = await ctx.session.get(EntityRow, row.bearer_node_id)
        if being is None or being.status is not EntityStatus.CANON or held(being.id):
            continue
        await keep_one(ctx, being, row, counts[row.bearer_node_id])
        ctx.count("augments_kept")
    await ctx.session.flush()


async def best_skill(ctx: TickContext, being_id: int) -> SkillKind | None:
    query = select(SkillRow.skill).where(SkillRow.holder_node_id == being_id).order_by(SkillRow.level.desc(), SkillRow.skill)
    return await ctx.session.scalar(query.limit(1))


async def enhancement_effects(ctx: TickContext, being_id: int) -> list[tuple[EffectTarget, str, int]]:
    skill = await best_skill(ctx, being_id)
    return [(EffectTarget.SKILL, skill.value, ctx.rules.augments.enhance_lift)] if skill is not None else []


async def make_known(ctx: TickContext, being: EntityRow) -> AugmentMake | None:
    place = being.location_id
    if await knows(ctx.session, being.id, KnowledgeBranch.MAGIC):
        return AugmentMake.RITE_BOUND
    if await knows(ctx.session, being.id, KnowledgeBranch.BIOMANCY):
        return AugmentMake.GROWN
    if place is not None and Technique.COMPUTATION in await techniques_of(ctx.session, place):
        return AugmentMake.MADE
    return None


async def surgeon_near(ctx: TickContext, being: EntityRow) -> int | None:
    here = await present_among(ctx.session, [being.location_id])
    query = select(SkillRow.holder_node_id).join(EntityRow, EntityRow.id == SkillRow.holder_node_id).where(here, SkillRow.skill == SkillKind.SURGERY)
    return await ctx.session.scalar(query.order_by(SkillRow.level.desc(), SkillRow.holder_node_id).limit(1))


async def seek_enhancements(ctx: TickContext) -> int:
    table = ctx.rules.augments
    enhanced = select(AugmentRow.bearer_node_id).where(AugmentRow.kind == AugmentKind.ENHANCEMENT)
    wealthy = select(MortalProfileRow.entity_id).where(MortalProfileRow.wealth >= table.enhance_wealth)
    query = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(enhanced), EntityRow.id.in_(wealthy)
    )
    sought = 0
    for being in list(await ctx.session.scalars(query.order_by(EntityRow.id))):
        if held(being.id):
            continue
        make = await make_known(ctx, being)
        effects = await enhancement_effects(ctx, being.id)
        if make is None or not effects:
            continue
        try:
            await install(
                ctx,
                being.id,
                slot=AugmentSlot.WHOLE_BODY,
                part=None,
                kind=AugmentKind.ENHANCEMENT,
                make=make,
                quality=PERCENT // 2,
                surgeon_id=await surgeon_near(ctx, being),
                effects=effects,
            )
        except ValidationFailedError:
            continue
        await shift_points(ctx.session, being, -table.enhance_cost)
        sought += 1
    return sought
