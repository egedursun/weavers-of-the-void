from dataclasses import dataclass

from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.db.tables.military import ArmyUnitRow
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.military import UnitFamily, UnitKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.military.logistics import March
from aerona.engine.military.units import stacks_of, sync
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up

SKY = frozenset({UnitKind.SKYSHIPS, UnitKind.SKY_MOUNTS})
STORMS = frozenset({WeatherKind.STORM, WeatherKind.MAGIC_STORM, WeatherKind.BLIZZARD, WeatherKind.SANDSTORM})
WINDY = frozenset({WeatherKind.STORM, WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
SEAMANSHIP_LEVELS = 3


@dataclass
class SeaFight:
    winner: March
    loser: March
    sunk: dict[int, int]


def ships(rows: list[ArmyUnitRow]) -> list[ArmyUnitRow]:
    return [row for row in rows if row.count > 0 and UNITS[row.kind].family is UnitFamily.NAVAL and row.kind not in SKY]


def flyers(rows: list[ArmyUnitRow]) -> list[ArmyUnitRow]:
    return [row for row in rows if row.count > 0 and row.kind in SKY]


def fleet_power(ctx: TickContext, rows: list[ArmyUnitRow], weather: WeatherKind | None) -> float:
    table = ctx.rules.naval
    total = 0.0
    for row in ships(rows):
        spec = UNITS[row.kind]
        power = spec.melee * table.boarding_pct / PERCENT + spec.mass * table.ram_pct / PERCENT + spec.missile
        if row.kind is UnitKind.FIRE_SHIPS and weather in WINDY:
            power *= table.fire_wind_pct / PERCENT
        total += row.count * power * row.quality / (PERCENT // 2) * (0.5 + row.morale / PERCENT)
    return total


def sink(rows: list[ArmyUnitRow], share: float) -> int:
    lost = 0
    for row in rows:
        part = min(row.count, round_half_up(row.count * share))
        row.count -= part
        lost += part
    return lost


async def sea_battle(ctx: TickContext, marches: list[March], weather: WeatherKind | None, slot: str) -> SeaFight | None:
    fleets = [await stacks_of(ctx.session, march.army.id) for march in marches]
    if not all(ships(rows) for rows in fleets):
        return None
    powers = [fleet_power(ctx, rows, weather) * (0.8 + ctx.rng(f"sea.{slot}.{index}").below(40) / PERCENT) for index, rows in enumerate(fleets)]
    first_wins = powers[0] >= powers[1]
    winner, loser = (0, 1) if first_wins else (1, 0)
    ratio = powers[loser] / max(1.0, powers[winner])
    sunk = {
        marches[loser].army.id: sink(ships(fleets[loser]), min(0.6, 0.15 + (1 - ratio) / 2)),
        marches[winner].army.id: sink(ships(fleets[winner]), 0.1 * ratio),
    }
    for march, rows in zip(marches, fleets, strict=True):
        sync(march.army, rows, ctx.rules)
    marches[winner].profile.blockade_entity_id = marches[loser].owner.id
    marches[loser].profile.blockade_entity_id = None
    return SeaFight(marches[winner], marches[loser], sunk)


async def weather_the_storm(ctx: TickContext, march: March, weather: WeatherKind | None, knowledge: KnowledgeMap) -> int:
    if weather not in STORMS:
        return 0
    table = ctx.rules.naval
    rows = await stacks_of(ctx.session, march.army.id)
    skill = min(SEAMANSHIP_LEVELS, knowledge.level(march.owner.id, KnowledgeBranch.SEAFARING))
    lost = sink(ships(rows), table.storm_sink_pct / PERCENT * (1 - skill / SEAMANSHIP_LEVELS))
    lost += sink(flyers(rows), table.sky_storm_pct / PERCENT)
    if lost:
        sync(march.army, rows, ctx.rules)
    return lost
