from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ages import EcoTransformationRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import LongPlanKind, LongPlanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record

AIMS = (("moisture", "target_moisture"), ("forest_cover", "target_forest"), ("soil_fertility", "target_fertility"))
TEMPERATE = 50


@dataclass
class EcologyTally:
    begun: int = 0
    regions: int = 0
    resisted: int = 0
    sabotaged: int = 0


async def regions_of(ctx: TickContext, target_id: int | None) -> list[RegionEnvironmentRow]:
    if target_id is None:
        return []
    region = await ctx.session.get(RegionEnvironmentRow, target_id)
    if region is not None:
        return [region]
    rows = await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == target_id).order_by(RegionEnvironmentRow.entity_id))
    return list(rows)


async def work_of(ctx: TickContext, plan: LongPlanRow) -> EcoTransformationRow:
    row = await ctx.session.get(EcoTransformationRow, plan.id)
    if row is None:
        row = EcoTransformationRow(plan_id=plan.id, last_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


def pull_against(region: RegionEnvironmentRow) -> int:
    heat = abs(region.temperature - TEMPERATE)
    dryness = max(0, TEMPERATE - region.rainfall)
    return clamp_int(heat + dryness, 0, PERCENT)


def step_toward(current: int, target: int, step: int) -> int:
    if current < target:
        return min(target, current + step)
    return max(target, current - step)


async def remake(ctx: TickContext, row: EcoTransformationRow, region: RegionEnvironmentRow, tally: EcologyTally) -> bool:
    table = ctx.rules.eco_transformations
    resistance = pull_against(region)
    kept = round_half_up(table.step * (PERCENT - resistance * table.resistance_pct // PERCENT) / PERCENT)
    if kept < table.step:
        tally.resisted += 1
    moved = False
    for column, aim in AIMS:
        if column in region.locked:
            continue
        current = getattr(region, column)
        target = getattr(row, aim)
        new = step_toward(current, target, kept)
        if new != current:
            setattr(region, column, new)
            moved = True
    if "resistance" not in row.locked:
        row.resistance = resistance
    return moved


async def lands_of(ctx: TickContext, target_id: int | None) -> list[int]:
    target = await ctx.session.get(EntityRow, target_id) if target_id is not None else None
    if target is not None and target.entity_type is EntityType.REGION:
        return [target.id]
    rows = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.REGION, EntityRow.world_id == target_id, EntityRow.status == EntityStatus.CANON)
    )
    return list(rows)


async def dependents(ctx: TickContext, region_ids: list[int], plan: LongPlanRow) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(region_ids))
        .order_by(EntityRow.id)
    )
    return [town for town in list(rows) if plan.holder_node_id not in (await people_id_of(ctx.session, town), town.id) and not held(town.id)]


def step_away(current: int, target: int, step: int) -> int:
    if current < target:
        return clamp_int(current - step, 0, PERCENT)
    if current > target:
        return clamp_int(current + step, 0, PERCENT)
    return current


async def set_back(ctx: TickContext, plan: LongPlanRow, row: EcoTransformationRow) -> None:
    table = ctx.rules.eco_transformations
    plan.progress = max(0, plan.progress - table.sabotage_loss)
    if "sabotage" not in row.locked:
        row.sabotage += 1
    for region in await regions_of(ctx, plan.target_node_id):
        if held(region.entity_id):
            continue
        for column, aim in AIMS:
            if column not in region.locked:
                setattr(region, column, step_away(getattr(region, column), getattr(row, aim), table.step))


async def sabotage(ctx: TickContext, plan: LongPlanRow, row: EcoTransformationRow, region_ids: list[int], tally: EcologyTally) -> None:
    table = ctx.rules.eco_transformations
    towns = await dependents(ctx, region_ids, plan)
    if not towns or "progress" in plan.locked or not ctx.rng(f"eco.sabotage.{plan.id}.{ctx.epoch}").chance(table.sabotage_chance):
        return
    await set_back(ctx, plan, row)
    tally.sabotaged += 1
    await record(
        ctx,
        "plans.eco_sabotage",
        roles={IncidentRole.ACTOR: towns[0].id, IncidentRole.TARGET: plan.holder_node_id},
        facts={"plan": plan.name, "lost": ctx.rules.eco_transformations.sabotage_loss, "chance": table.sabotage_chance},
        place=towns[0].id,
    )


async def keep_transformations(ctx: TickContext, tally: EcologyTally) -> None:
    plans = await ctx.session.scalars(
        select(LongPlanRow)
        .where(LongPlanRow.kind == LongPlanKind.ECOLOGICAL_TRANSFORMATION, LongPlanRow.status == LongPlanStatus.ACTIVE)
        .order_by(LongPlanRow.id)
    )
    for plan in list(plans):
        if held(plan.holder_node_id):
            continue
        known = await ctx.session.get(EcoTransformationRow, plan.id) is not None
        row = await work_of(ctx, plan)
        tally.begun += not known
        regions = [region for region in await regions_of(ctx, plan.target_node_id) if not held(region.entity_id)]
        changed = 0
        for region in regions:
            if await remake(ctx, row, region, tally):
                changed += 1
        tally.regions += changed
        if "regions_changed" not in row.locked:
            row.regions_changed += changed
        row.last_epoch = ctx.epoch
        await sabotage(ctx, plan, row, await lands_of(ctx, plan.target_node_id), tally)
    await ctx.session.flush()
