from sqlalchemy import select

from aerona.catalog.evolution import STAGE_COVER, WET_LAND
from aerona.catalog.scars import SCARS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import ScarKind, SoilKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world import ClimateEra
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

WARMING_ERAS = frozenset({ClimateEra.WARMING})
LOOSE_SOILS = frozenset({SoilKind.SAND, SoilKind.SILT})


async def crack_structures(ctx: TickContext, ground: RegionEnvironmentRow) -> int:
    harm = ctx.rules.soils.cracking_harm
    built = (
        select(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(EntityRow.location_id == ground.entity_id, EntityRow.status == EntityStatus.CANON)
    )
    cracked = 0
    for row in await ctx.session.scalars(built.order_by(StructureProfileRow.structure_entity_id)):
        if held(row.structure_entity_id) or "condition" in (row.locked or []):
            continue
        row.condition = clamp_int(row.condition - harm, 0, PERCENT)
        cracked += 1
    return cracked


async def erode_silt(ctx: TickContext, ground: RegionEnvironmentRow) -> bool:
    if ground.cleared <= 0 or not ctx.rng(f"silt.{ground.entity_id}").chance(ctx.rules.soils.silt_erosion_pct * ground.cleared // PERCENT):
        return False
    add_scar(ground, ScarKind.ERODED, ground.cleared // 2)
    await record(
        ctx, "soil.eroded", roles={IncidentRole.PLACE: ground.entity_id}, facts={"soil": ground.soil, "depth": ground.cleared // 2}, place=ground.entity_id
    )
    return True


async def thaw(ctx: TickContext, ground: RegionEnvironmentRow, era: ClimateEra | None) -> bool:
    if era not in WARMING_ERAS or "soil" in ground.locked or not ctx.rng(f"thaw.{ground.entity_id}").chance(ctx.rules.soils.permafrost_thaw_pct):
        return False
    ground.soil = SoilKind.GLEY
    await record(ctx, "soil.thawed", roles={IncidentRole.PLACE: ground.entity_id}, facts={"soil": SoilKind.PERMAFROST}, place=ground.entity_id)
    return True


def scar_once(ground: RegionEnvironmentRow, kind: ScarKind, depth: int) -> bool:
    if depth <= 0 or f"scar.{kind.value}" in ground.locked or ground.scars.get(kind.value, 0) >= depth:
        return False
    add_scar(ground, kind, depth - ground.scars.get(kind.value, 0))
    return True


async def scar_by_use(ctx: TickContext, ground: RegionEnvironmentRow) -> list[ScarKind]:
    table = ctx.rules.scars
    made: list[ScarKind] = []
    if (
        ground.base_forest >= ctx.rules.environment.forest_terrain_pct
        and ground.cleared >= table.deforest_cleared
        and scar_once(ground, ScarKind.DEFORESTED, ground.cleared)
    ):
        made.append(ScarKind.DEFORESTED)
    if (
        ground.base_wetland >= WET_LAND
        and ground.wetland <= table.drained_wetland
        and scar_once(ground, ScarKind.DRAINED, ground.base_wetland - ground.wetland)
    ):
        made.append(ScarKind.DRAINED)
    if ground.grazed >= table.overgrazed_grazed and scar_once(ground, ScarKind.OVERGRAZED, ground.grazed - table.overgrazed_grazed + 1):
        made.append(ScarKind.OVERGRAZED)
    loose = ground.soil in LOOSE_SOILS and ground.cleared > 0 and ground.grazed > 0
    if loose and ctx.rng(f"erode.{ground.entity_id}").chance(table.erosion_clearing_pct) and scar_once(ground, ScarKind.ERODED, ground.cleared // 2):
        made.append(ScarKind.ERODED)
    pollution = await ctx.session.get(RegionPollutionRow, ground.entity_id)
    worst = max(pollution.air, pollution.water, pollution.soil) if pollution is not None else 0
    if worst >= table.pollution_poison_threshold and scar_once(ground, ScarKind.POISONED, worst - table.pollution_poison_threshold + 1):
        made.append(ScarKind.POISONED)
    for kind in made:
        await record(
            ctx,
            "scar.made",
            roles={IncidentRole.PLACE: ground.entity_id},
            facts={"scar": kind, "depth": ground.scars.get(kind.value, 0)},
            place=ground.entity_id,
        )
    return made


async def hold_back(ctx: TickContext, ground: RegionEnvironmentRow) -> SuccessionStage | None:
    if "succession" in ground.locked:
        return None
    deep = [(depth, key) for key, depth in sorted(ground.scars.items()) if depth >= ctx.rules.scars.reset_depth and SCARS[ScarKind(key)].resets_to is not None]
    if not deep:
        return None
    _, key = max(deep)
    stage = SCARS[ScarKind(key)].resets_to
    if stage is None or stage is ground.succession or STAGE_COVER[stage] >= STAGE_COVER[ground.succession]:
        return None
    before = ground.succession
    ground.succession = stage
    ground.succession_progress = 0
    await record(
        ctx,
        "succession.reset",
        roles={IncidentRole.PLACE: ground.entity_id},
        facts={"scar": ScarKind(key), "stage": stage, "before": before},
        place=ground.entity_id,
    )
    return stage


def wash_bare(rules: Rules, ground: RegionEnvironmentRow) -> int:
    bare = ground.scars.get(ScarKind.DEFORESTED.value, 0)
    if bare <= 0 or "erosion" in ground.locked:
        return 0
    added = round_half_up(bare * rules.scars.deforested_erosion_pct / PERCENT)
    ground.erosion = clamp_int(ground.erosion + added, 0, PERCENT)
    return added


async def live_soils(ctx: TickContext, ground: RegionEnvironmentRow, era: ClimateEra | None) -> None:
    if held(ground.entity_id):
        return
    await scar_by_use(ctx, ground)
    wash_bare(ctx.rules, ground)
    await hold_back(ctx, ground)
    if ground.soil is SoilKind.CRACKING_CLAY:
        await crack_structures(ctx, ground)
    elif ground.soil is SoilKind.SILT:
        await erode_silt(ctx, ground)
    elif ground.soil is SoilKind.PERMAFROST:
        await thaw(ctx, ground, era)
