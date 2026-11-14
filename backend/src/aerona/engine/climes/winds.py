import math
from dataclasses import dataclass

from sqlalchemy import select

from aerona.cartography.biomes import Biome
from aerona.constants.units import PERCENT
from aerona.db.tables.climes import RegionWindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.climes import CirculationBand
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.industry import Pollutant
from aerona.engine.context import TickContext
from aerona.engine.industry.pollution import shift
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules

HIGHLANDS = (Biome.DRY_HILLS, Biome.WET_HILLS, Biome.MOUNTAINS, Biome.PEAKS)
OCTANTS = 8
EAST = 2
WEST = 6
NORTH = 0
BAND_FROM = {
    CirculationBand.TRADE: EAST,
    CirculationBand.WESTERLY: WEST,
    CirculationBand.POLAR: EAST,
    CirculationBand.SINGLE_CELL: NORTH,
    CirculationBand.TERMINATOR: EAST,
    CirculationBand.STILL: NORTH,
}


@dataclass
class WindTally:
    read: int = 0
    shadows: int = 0
    monsoons: int = 0
    upwellings: int = 0
    drifted: int = 0


def heading(octant: int) -> tuple[float, float]:
    angle = math.radians(octant * 360 / OCTANTS)
    return math.sin(angle), -math.cos(angle)


def band_of(rules: Rules, physics: WorldPhysicsRow | None, latitude: int) -> CirculationBand:
    table = rules.winds
    if physics is not None and physics.pressure <= 0:
        return CirculationBand.STILL
    if physics is not None and physics.tidally_locked:
        return CirculationBand.TERMINATOR
    if physics is not None and physics.rotation_hours > table.single_cell_hours:
        return CirculationBand.SINGLE_CELL
    reach = abs(latitude)
    if reach < table.trade_below:
        return CirculationBand.TRADE
    return CirculationBand.POLAR if reach > table.polar_above else CirculationBand.WESTERLY


def strength_of(rules: Rules, band: CirculationBand) -> int:
    table = rules.winds
    return {
        CirculationBand.TRADE: table.trade_strength,
        CirculationBand.WESTERLY: table.westerly_strength,
        CirculationBand.POLAR: table.polar_strength,
        CirculationBand.SINGLE_CELL: table.single_cell_strength,
        CirculationBand.TERMINATOR: table.terminator_strength,
        CirculationBand.STILL: 0,
    }[band]


def highland(rules: Rules, env: RegionEnvironmentRow | None) -> bool:
    if env is None:
        return False
    mix = list(env.biome_mix)
    return sum(mix[biome] for biome in HIGHLANDS if biome < len(mix)) >= rules.environment.terrain_dominant_share_pct


def toward(rules: Rules, positions: dict[int, tuple[float, float]], region: int, others: list[int], octant: int) -> list[int]:
    if region not in positions:
        return []
    x, y = positions[region]
    dx, dy = heading(octant)
    found: list[int] = []
    for other in others:
        if other not in positions:
            continue
        ox, oy = positions[other][0] - x, positions[other][1] - y
        length = math.hypot(ox, oy)
        if length > 0 and (ox * dx + oy * dy) / length * PERCENT >= rules.winds.upwind_cosine_pct:
            found.append(other)
    return found


async def keep_winds(ctx: TickContext, tally: WindTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    envs = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    physics = {row.world_id: row for row in await ctx.session.scalars(select(WorldPhysicsRow))}
    regions = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(sorted(envs))).order_by(EntityRow.id)))
    positions = {row.id: (row.map_x, row.map_y) for row in regions if row.map_x is not None and row.map_y is not None}
    winds = {row.region_entity_id: row for row in await ctx.session.scalars(select(RegionWindRow))}
    table = ctx.rules
    for region in regions:
        env = envs[region.id]
        if held(region.id):
            continue
        band = band_of(table, physics.get(env.world_id), env.latitude)
        octant = BAND_FROM[band]
        neighbours = atlas.neighbour_regions(region.id)
        upwind = toward(table, positions, region.id, neighbours, octant)
        downwind = toward(table, positions, region.id, neighbours, (octant + OCTANTS // 2) % OCTANTS)
        coastal = env.coast_kind is not CoastKind.NONE
        high = highland(table, env)
        reach = abs(env.latitude)
        values = {
            "band": band,
            "wind_from": octant,
            "strength": strength_of(table, band),
            "windward": high and (not upwind or any(envs[item].coast_kind is not CoastKind.NONE for item in upwind if item in envs)),
            "shadow": table.winds.shadow if not high and any(highland(table, envs.get(item)) for item in upwind) else 0,
            "monsoon": table.monsoons.strength if coastal and table.monsoons.lowest_latitude <= reach <= table.monsoons.highest_latitude else 0,
            "upwelling": coastal and bool(upwind) and not downwind,
        }
        row = winds.get(region.id)
        if row is None:
            row = RegionWindRow(region_entity_id=region.id, read_epoch=ctx.epoch, locked=[], **values)
            ctx.session.add(row)
            winds[region.id] = row
        else:
            for key, value in values.items():
                if key not in row.locked:
                    setattr(row, key, value)
            row.read_epoch = ctx.epoch
        tally.read += 1
        tally.shadows += int(row.shadow > 0)
        tally.monsoons += int(row.monsoon > 0)
        tally.upwellings += int(row.upwelling)
        if coastal and "current" not in env.locked:
            env.current = OceanCurrent.COLD if row.upwelling else OceanCurrent.WARM if not upwind else OceanCurrent.NONE
        if downwind and row.strength > 0:
            await drift_air(ctx, region.id, downwind[0], row.strength, tally)
    await ctx.session.flush()


async def drift_air(ctx: TickContext, source: int, sink: int, strength: int, tally: WindTally) -> None:
    there = await ctx.session.get(RegionPollutionRow, source)
    if there is None or there.air <= 0 or held(sink):
        return
    moved = there.air * ctx.rules.winds.pollution_drift_pct / PERCENT * strength / PERCENT
    if moved < 1:
        return
    downwind = await ctx.session.get(RegionPollutionRow, sink)
    if downwind is None:
        downwind = RegionPollutionRow(region_node_id=sink, air=0, water=0, soil=0, polluters={}, epoch=ctx.epoch, locked=[])
        ctx.session.add(downwind)
    taken = -shift(there, Pollutant.AIR, -moved)
    if taken > 0:
        shift(downwind, Pollutant.AIR, taken)
        tally.drifted += 1
