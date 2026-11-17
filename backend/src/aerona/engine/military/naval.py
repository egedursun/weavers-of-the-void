from dataclasses import dataclass, field

from aerona.constants.units import PERCENT
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.context import TickContext
from aerona.engine.military.logistics import March
from aerona.engine.military.units import stacks_of
from aerona.engine.military.vessels import batter_fleet, fleet_bonus, fleet_of, renown_fleet
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.vehicles.fleet import AIRBORNE, NAVAL, afloat, batter_groups, readings

STORMS = frozenset({WeatherKind.STORM, WeatherKind.MAGIC_STORM, WeatherKind.BLIZZARD, WeatherKind.SANDSTORM})
WINDY = frozenset({WeatherKind.STORM, WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
SEAMANSHIP_LEVELS = 3


@dataclass
class SeaFight:
    winner: March
    loser: March
    sunk: dict[int, int]
    steps: list[StepDraft] = field(default_factory=list)


async def crew_quality(ctx: TickContext, army_id: int) -> float:
    crews = [row for row in await stacks_of(ctx.session, army_id) if row.kind is UnitKind.NAVAL_CREW and row.count > 0]
    if not crews:
        return 0.5
    soldiers = sum(row.count for row in crews)
    return sum(row.count * row.quality / (PERCENT // 2) * (0.5 + row.morale / PERCENT) for row in crews) / soldiers


async def fleet_power(ctx: TickContext, army_id: int, weather: WeatherKind | None) -> float:
    table = ctx.rules.naval
    power = 0.0
    for reading in await readings(ctx.session, army_id):
        if reading.design.domain not in NAVAL:
            continue
        fire = reading.firepower * (table.fire_wind_pct / PERCENT if weather in WINDY and reading.design.frame is VehicleFrame.FIRE_SHIP else 1.0)
        boarding = reading.troops * table.boarding_pct / PERCENT
        ramming = reading.design.structure * reading.group.count * table.ram_pct / PERCENT / 10
        power += fire + boarding + ramming
    return power * await crew_quality(ctx, army_id)


async def sea_battle(ctx: TickContext, marches: list[March], weather: WeatherKind | None, slot: str) -> SeaFight | None:
    present = [await afloat(ctx.session, march.army.id) or bool(await fleet_of(ctx, march.army.id)) for march in marches]
    if not all(present):
        return None
    bonuses = [await fleet_bonus(ctx, march.army.id, weather) for march in marches]
    favour = [await ctx.hook_factor(march.owner.id, DomainHook.NAVAL_MIGHT) for march in marches]
    powers = [
        (await fleet_power(ctx, march.army.id, weather) + bonuses[index]) * favour[index] * (0.8 + ctx.rng(f"sea.{slot}.{index}").below(40) / PERCENT)
        for index, march in enumerate(marches)
    ]
    winner, loser = (0, 1) if powers[0] >= powers[1] else (1, 0)
    ratio = powers[loser] / max(1.0, powers[winner])
    loser_share = min(0.6, 0.15 + (1 - ratio) / 2)
    winner_share = 0.1 * ratio
    lost_loser, _, loser_steps = await batter_groups(ctx, marches[loser].army.id, loser_share, f"sea.{slot}", NAVAL)
    lost_winner, _, winner_steps = await batter_groups(ctx, marches[winner].army.id, winner_share, f"sea.{slot}", NAVAL)
    marches[winner].profile.blockade_entity_id = marches[loser].owner.id
    marches[loser].profile.blockade_entity_id = None
    await batter_fleet(ctx, marches[loser].army.id, loser_share, region_id=marches[loser].profile.region_entity_id)
    await batter_fleet(ctx, marches[winner].army.id, winner_share, region_id=marches[winner].profile.region_entity_id)
    await renown_fleet(ctx, marches[winner].army.id)
    sunk = {marches[loser].army.id: lost_loser, marches[winner].army.id: lost_winner}
    return SeaFight(marches[winner], marches[loser], sunk, [*loser_steps, *winner_steps])


async def weather_the_storm(ctx: TickContext, march: March, weather: WeatherKind | None, knowledge: KnowledgeMap) -> int:
    if weather not in STORMS:
        return 0
    table = ctx.rules.naval
    skill = min(SEAMANSHIP_LEVELS, knowledge.level(march.owner.id, KnowledgeBranch.SEAFARING))
    lost, _, sea_steps = await batter_groups(
        ctx, march.army.id, table.storm_sink_pct / PERCENT * (1 - skill / SEAMANSHIP_LEVELS), f"storm.{march.army.id}", NAVAL
    )
    flown, _, sky_steps = await batter_groups(ctx, march.army.id, table.sky_storm_pct / PERCENT, f"sky_storm.{march.army.id}", AIRBORNE)
    if sea_steps or sky_steps:
        await record(
            ctx,
            "war.fleet_storm",
            roles={IncidentRole.SUBJECT: march.army.id, IncidentRole.OWNER: march.owner.id},
            facts={"weather": weather, "lost": lost + flown},
            steps=[*sea_steps, *sky_steps],
            place=march.profile.region_entity_id,
        )
    return lost + flown
