from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.evolution import FIRE_STAGE, STAGE_COVER, WET_LAND, WOODED, next_stage
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

MILD = 15
MILD_SPAN = 40
FUEL_EPOCHS = 10
STAGE_WORDS = {
    SuccessionStage.BARE: "bare ground",
    SuccessionStage.GRASSLAND: "grassland",
    SuccessionStage.SHRUBLAND: "shrubland",
    SuccessionStage.YOUNG_FOREST: "young forest",
    SuccessionStage.OLD_FOREST: "old forest",
    SuccessionStage.MARSH: "marsh",
    SuccessionStage.SWAMP_FOREST: "swamp forest",
}


@dataclass
class SuccessionTally:
    advanced: int = 0
    burned: int = 0
    cleared: int = 0


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
    table = ctx.rules.biome_succession
    for env in list(await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))):
        if held(env.entity_id, env.world_id) or "succession" in env.locked:
            continue
        rng = ctx.rng(f"succession.{env.entity_id}")
        if env.succession in FIRE_STAGE and env.rainfall < table.fire_rain and rng.chance(table.fire_pct * fuel(env, ctx.epoch)):
            burn_back(env, ctx.epoch)
            add_scar(env, ScarKind.BURNED, table.burn_scar)
            tally.burned += 1
            region = await ctx.session.get(EntityRow, env.entity_id)
            if region is not None:
                await note(
                    ctx, f"Fire swept the dry woods of {region.name}; {STAGE_WORDS[env.succession]} grows there now.", key="land.forest_fire", ids=[region.id]
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
        following = next_stage(env.succession, wet)
        if following is None or (not wet and STAGE_COVER[env.succession] >= env.base_forest and env.succession is not SuccessionStage.BARE):
            continue
        env.succession_progress = clamp_int(env.succession_progress + round_half_up(growth(ctx.rules, env)), 0, PERCENT)
        if env.succession_progress >= PERCENT:
            env.succession = following
            env.succession_progress = 0
            tally.advanced += 1
    await ctx.session.flush()
