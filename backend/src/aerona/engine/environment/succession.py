from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.evolution import ADVANCE, FIRE_STAGE, STAGE_COVER, WET_LAND, WOODED, next_stage, path_of
from aerona.catalog.soils import SOILS
from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.environment import CoastKind, ScarKind, SoilKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus
from aerona.engine.context import TickContext
from aerona.engine.ecology.keystones import dispersal, services_by_region
from aerona.engine.environment.book import add_scar
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

MILD = 15
MILD_SPAN = 40
FUEL_EPOCHS = 10


@dataclass
class SuccessionTally:
    advanced: int = 0
    burned: int = 0
    cleared: int = 0


ACID_SOIL = 70


def stage_path(ground: RegionEnvironmentRow) -> tuple[SuccessionStage, ...]:
    wet = ground.base_wetland >= WET_LAND or ground.wetland >= WET_LAND
    return path_of(ground.succession, wet=wet, poor=SOILS[ground.soil].acidity >= ACID_SOIL, dune=ground.coast_kind is CoastKind.BEACH)


def growth(rules: Rules, env: RegionEnvironmentRow) -> float:
    mild = max(0.0, 1 - abs(env.temperature - MILD) / MILD_SPAN)
    wet = min(1.0, env.rainfall / (PERCENT / 2))
    fertile = min(1.5, env.soil_fertility / (PERCENT / 2))
    worked = 1 - env.farmed / PERCENT
    return rules.biome_succession.rate * mild * wet * fertile * worked


def burn_back(env: RegionEnvironmentRow, epoch: int) -> bool:
    if "succession" in env.locked or env.succession not in FIRE_STAGE:
        return False
    env.succession = FIRE_STAGE[env.succession]
    env.succession_progress = 0
    env.burned_epoch = epoch
    return True


def fuel(env: RegionEnvironmentRow, epoch: int) -> float:
    since = epoch - env.burned_epoch if env.burned_epoch is not None else FUEL_EPOCHS
    return min(1.0, since / FUEL_EPOCHS)


async def grow_lands(ctx: TickContext, tally: SuccessionTally) -> None:
    services = await services_by_region(ctx.session)
    table = ctx.rules.biome_succession
    for env in list(await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))):
        if held(env.entity_id, env.world_id) or "succession" in env.locked:
            continue
        rng = ctx.rng(f"succession.{env.entity_id}")
        chance = table.fire_pct * fuel(env, ctx.epoch)
        if env.succession in FIRE_STAGE and env.rainfall < table.fire_rain and rng.chance(chance):
            burn_back(env, ctx.epoch)
            add_scar(env, ScarKind.BURNED, table.burn_scar)
            tally.burned += 1
            await record(
                ctx,
                "land.forest_fire",
                roles={IncidentRole.PLACE: env.entity_id},
                facts={"stage": env.succession, "scar": table.burn_scar, "chance": chance},
                place=env.entity_id,
                world_id=env.world_id,
                steps=(
                    StepDraft(StepAction.BEGIN, locus_kind=StepLocus.REGION, locus_node=env.entity_id),
                    StepDraft(StepAction.BURN_LAND, locus_kind=StepLocus.REGION, locus_node=env.entity_id, amount=table.burn_scar, unit=FactUnit.PERCENT),
                    StepDraft(StepAction.END, locus_kind=StepLocus.REGION, locus_node=env.entity_id),
                ),
            )
            continue
        if env.succession in WOODED and env.farmed > 0 and rng.chance(table.slash_pct * env.farmed / PERCENT):
            env.succession = SuccessionStage.GRASSLAND
            env.succession_progress = 0
            env.burned_epoch = ctx.epoch
            tally.cleared += 1
            continue
        if env.succession is SuccessionStage.GRASSLAND and env.grazed >= table.grazing_hold:
            continue
        wet = env.base_wetland >= WET_LAND or env.wetland >= WET_LAND
        poor = SOILS[env.soil].acidity >= ACID_SOIL
        dune = env.coast_kind is CoastKind.BEACH
        following = next_stage(env.succession, wet, poor=poor, dune=dune)
        if following is None or (not wet and STAGE_COVER[env.succession] >= env.base_forest and env.succession is not SuccessionStage.BARE):
            continue
        pace = growth(ctx.rules, env) / ADVANCE[env.succession](ctx.rules) * dispersal(ctx.rules, services.get(env.entity_id))
        env.succession_progress = clamp_int(env.succession_progress + round_half_up(pace), 0, PERCENT)
        if env.succession is SuccessionStage.BOG and env.succession_progress >= PERCENT and "soil" not in env.locked:
            env.soil = SoilKind.PEAT
        if env.succession_progress >= PERCENT:
            before, env.succession = env.succession, following
            env.succession_progress = 0
            tally.advanced += 1
            await record(
                ctx, "succession.advanced", roles={IncidentRole.PLACE: env.entity_id}, facts={"before": before, "stage": following}, place=env.entity_id
            )
    await ctx.session.flush()
