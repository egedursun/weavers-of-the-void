from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import AugmentEffectRow, AugmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import AugmentKind, AugmentMake, AugmentSlot, EffectTarget, MadeMindStance
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.minds import MindUpkeep
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.mind.book import skill_level
from aerona.engine.minds.continuity import law_for
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record

BEARER_TYPES = frozenset({EntityType.MORTAL, EntityType.BEAST, EntityType.SPIRIT, EntityType.COSMIC_BEING})
SELF_KEPT = frozenset({MindUpkeep.NONE, MindUpkeep.FOOD})
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
