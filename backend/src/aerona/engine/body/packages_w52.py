from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.body_plans import CHANGEABLE_PLANS
from aerona.catalog.effect_packages import PACKAGES, StageSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import BodyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import ChangeSign, CharmKind, PackageKind, Transmission
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.book import ensure_body
from aerona.engine.body.digits import replan
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record

UNKEPT_STATS = ("intellect", "charisma")
STIRRING = 50
SUBSTANCE_PLAN = BodyPlan.CONSTRUCT


@dataclass(frozen=True)
class Shape:
    fortune_sign: int | None = None
    fortune_strength: int | None = None
    transform_plan: BodyPlan | None = None
    transform_species_id: int | None = None
    transform_substance: MaterialKind | None = None
    transform_trigger: ChangeSign | None = None
    transform_mind_kept: bool | None = None
    charm_target_node_id: int | None = None
    charm_kind: CharmKind | None = None


async def source_plan(ctx: TickContext, source_id: int | None) -> BodyPlan | None:
    body = await ctx.session.get(BodyRow, source_id) if source_id is not None else None
    return body.plan if body is not None else None


async def shape_row(ctx: TickContext, row: AfflictionRow, shape: Shape | None) -> None:
    given = shape or Shape()
    table = ctx.rules.packages
    if row.package is PackageKind.FORTUNE:
        row.fortune_sign = given.fortune_sign or (-1 if row.transmission is Transmission.CURSE else 1)
        row.fortune_strength = given.fortune_strength if given.fortune_strength is not None else table.fortune_strength
    if row.package is PackageKind.TRANSFORMATION:
        row.transform_species_id = given.transform_species_id
        row.transform_substance = given.transform_substance
        chosen = given.transform_plan or await species_plan(ctx, given.transform_species_id) or await source_plan(ctx, row.source_node_id)
        if chosen is None and given.transform_substance is not None:
            chosen = SUBSTANCE_PLAN
        row.transform_plan = chosen or ctx.rng(f"transform.plan.{row.id}").pick(list(CHANGEABLE_PLANS))
        row.transform_trigger = given.transform_trigger or ChangeSign.NONE
        row.transform_mind_kept = True if given.transform_mind_kept is None else given.transform_mind_kept
    if row.package is PackageKind.CHARM:
        row.charm_target_node_id = given.charm_target_node_id or row.source_node_id
        row.charm_kind = given.charm_kind or CharmKind.LOVE
        row.charm_strength = table.charm_strength


async def species_plan(ctx: TickContext, species_id: int | None) -> BodyPlan | None:
    body = await ctx.session.get(BodyRow, species_id) if species_id is not None else None
    return body.plan if body is not None else None


async def meet_fortunes(ctx: TickContext, bearer: EntityRow, standing: AfflictionRow, sign: int, strength: int) -> None:
    if "fortune" in standing.locked:
        return
    total = (standing.fortune_sign or 1) * (standing.fortune_strength or 0) + sign * strength
    standing.fortune_sign = 1 if total >= 0 else -1
    standing.fortune_strength = min(PERCENT, abs(total))
    await record(
        ctx,
        "affliction.fortune_turned",
        roles={IncidentRole.PATIENT: bearer.id},
        facts={"lean": FortuneSourceKind.BLESSING if standing.fortune_sign > 0 else FortuneSourceKind.CURSE, "strength": standing.fortune_strength},
    )


async def change_body(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    if row.transform_plan is None:
        return
    body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
    if body.plan is not row.transform_plan:
        row.transform_from_plan = row.transform_from_plan or body.plan
        replan(body, row.transform_plan)
    if not row.transform_mind_kept:
        cut = {key: -min(stat(bearer, key) or 0, ctx.rules.packages.unkept_mind_pct) for key in UNKEPT_STATS if stat(bearer, key) is not None}
        set_stats(bearer, **{key: (stat(bearer, key) or 0) + delta for key, delta in cut.items()})
        row.applied = {**row.applied, **cut}
    await record(
        ctx,
        "affliction.transformed",
        roles={IncidentRole.PATIENT: bearer.id},
        facts={"plan": row.transform_plan, "trigger": row.transform_trigger or ChangeSign.NONE, "mind_kept": 1 if row.transform_mind_kept else 0},
    )


async def restore_body(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    if row.transform_from_plan is None:
        return
    body = await ctx.session.get(BodyRow, bearer.id)
    if body is not None and "plan" not in body.locked:
        replan(body, row.transform_from_plan)
    row.transform_from_plan = None


async def trigger_came(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, moon_bright: bool) -> bool:
    trigger = row.transform_trigger or ChangeSign.NONE
    if trigger is ChangeSign.SEASON:
        return True
    if trigger is ChangeSign.SKY_EVENT:
        return moon_bright
    if trigger is ChangeSign.EMOTION:
        stirred = await ctx.session.scalar(
            select(ThoughtRow.id).where(ThoughtRow.holder_node_id == bearer.id, ThoughtRow.epoch == ctx.epoch, ThoughtRow.intensity >= STIRRING).limit(1)
        )
        return stirred is not None
    return False


async def bind_charm(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> None:
    target = await living_entity(ctx.session, row.charm_target_node_id) if row.charm_target_node_id is not None else None
    if target is None:
        return
    kind = row.charm_kind or CharmKind.LOVE
    if kind is CharmKind.OBEDIENCE:
        await connect(ctx.session, target.id, bearer.id, BondKind.COMMANDS, ctx.epoch, description="charmed to obey")
    elif kind is CharmKind.DEVOTION and target.entity_type is not EntityType.MORTAL:
        await connect(ctx.session, bearer.id, target.id, BondKind.WORSHIPS, ctx.epoch, description="charmed to devotion")
    else:
        await connect(ctx.session, bearer.id, target.id, BondKind.LOVES, ctx.epoch, description="charmed")
    await record(ctx, "affliction.charmed", roles={IncidentRole.PATIENT: bearer.id, IncidentRole.TARGET: target.id}, facts={"charm": kind})


async def pull_charm(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, stage: StageSpec) -> bool:
    table = ctx.rules.packages
    strength = row.charm_strength or 0
    if row.charm_target_node_id is not None and strength > 0:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=bearer.id,
            subject_id=row.charm_target_node_id,
            kind=MemoryKind.GOODWILL,
            magnitude=table.charm_pull * strength / PERCENT,
            epoch=ctx.epoch,
            note="a compelled warmth",
        )
    if stage.fades and "charm_strength" not in row.locked:
        row.charm_strength = table.charm_strength if await renewed(ctx, bearer, row) else max(0, strength - table.charm_fade)
    return (row.charm_strength or 0) <= 0


async def renewed(ctx: TickContext, bearer: EntityRow, row: AfflictionRow) -> bool:
    source = row.source_node_id
    charmer = await living_entity(ctx.session, source) if source is not None and source != bearer.id and not held(source) else None
    cost = ctx.rules.packages.charm_renew_cost
    if charmer is None or not await take_coin(ctx.session, ctx.rules, charmer, cost):
        return False
    await record(
        ctx,
        "affliction.charm_renewed",
        roles={IncidentRole.PATIENT: bearer.id, IncidentRole.ACTOR: charmer.id},
        facts={"charm": row.charm_kind or CharmKind.LOVE, "cost": cost},
    )
    return True


async def broken_charm(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, *, found: bool) -> None:
    await record(
        ctx,
        "affliction.charm_broken",
        roles={IncidentRole.PATIENT: bearer.id, IncidentRole.ACTOR: row.source_node_id},
        facts={"charm": row.charm_kind or CharmKind.LOVE, "found": 1 if found else 0},
    )
    if found and row.source_node_id is not None and row.source_node_id != bearer.id:
        await remember(
            ctx.session, ctx.rules, holder_id=bearer.id, subject_id=row.source_node_id, kind=MemoryKind.BETRAYED_ME, magnitude=-PERCENT // 2, epoch=ctx.epoch
        )


async def fortune_turns(ctx: TickContext, bearer: EntityRow, row: AfflictionRow, stage: StageSpec) -> None:
    sign = row.fortune_sign or 1
    strength = row.fortune_strength if row.fortune_strength is not None else ctx.rules.packages.fortune_strength
    amount = round(sign * strength * ctx.rules.packages.fortune_roll_pct / PERCENT * (0.5 if stage.fades else 1.0))
    kind = FortuneSourceKind.BLESSING if sign > 0 else FortuneSourceKind.CURSE
    await shift_fortune(ctx, bearer.id, amount, kind, row.source_node_id, epochs=1)


def line_chance(ctx: TickContext, package: PackageKind) -> int:
    line = PACKAGES[package].line
    return line(ctx.rules) if line is not None else ctx.rules.effect_packages.birth_pct
