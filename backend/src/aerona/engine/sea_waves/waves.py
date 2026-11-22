from collections.abc import Awaitable, Callable
from typing import Any

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.sea_waves import WaveOrigin
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import FactInput, record
from aerona.engine.sea_waves.sea import open_coast, shape_pct, warned

Striker = Callable[[TickContext, EntityRow, Disaster, float], Awaitable[Any]]
ORIGIN_OF = total(
    Disaster,
    {
        Disaster.EARTHQUAKE: WaveOrigin.QUAKE,
        Disaster.VOLCANIC_QUAKE: WaveOrigin.QUAKE,
        Disaster.ERUPTION: WaveOrigin.ERUPTION,
        Disaster.STORM: WaveOrigin.STORM,
        Disaster.FLOOD: None,
        Disaster.PLAGUE: None,
        Disaster.DROUGHT: None,
    },
)
FULL_STRIKE = 500
SLIDE_STRENGTH = 1.5


def wave_chance(ctx: TickContext, origin: WaveOrigin, severity: float) -> float:
    table = ctx.rules.sea_waves
    if origin is WaveOrigin.STORM:
        return table.storm_surge_chance_pct * severity if severity * PERCENT >= table.storm_floor_pct else 0.0
    if origin is WaveOrigin.DIVINE:
        return PERCENT
    return table.quake_wave_chance_pct * severity


def region_of(atlas: RegionAtlas, target: EntityRow) -> int | None:
    return target.id if target.entity_type is EntityType.REGION else atlas.top_region(target.id)


async def salt(ctx: TickContext, row: SeaWaveCoastRow) -> None:
    ground = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
    if ground is None or "soil_fertility" in (ground.locked or []):
        return
    ground.soil_fertility = clamp_int(ground.soil_fertility - ctx.rules.sea_waves.salt_fertility, 0, PERCENT)
    row.salted = True
    await record(ctx, "land.coast_salted", roles={IncidentRole.PLACE: row.region_entity_id}, facts={"fertility": ground.soil_fertility})


async def strike_coast(ctx: TickContext, atlas: RegionAtlas, wave: SeaWaveRow, region_id: int, *, hops: int, strike: Striker) -> SeaWaveCoastRow | None:
    table = ctx.rules.sea_waves
    height = clamp_int((wave.strength - table.decay_per_hop * hops) * await shape_pct(ctx, region_id) // PERCENT, 0, PERCENT)
    region = await ctx.session.get(EntityRow, region_id)
    if region is None or height < table.floor or held(region_id):
        return None
    row = SeaWaveCoastRow(wave_id=wave.id, region_entity_id=region_id, height=height, delay=hops, warned=await warned(ctx, atlas, region_id), locked=[])
    ctx.session.add(row)
    severity = min(1.0, height * table.harm_per_height / FULL_STRIKE)
    if row.warned:
        severity *= 1 - table.warning_death_cut_pct / PERCENT
        await record(ctx, "land.wave_warned", roles={IncidentRole.PLACE: region_id}, facts={"height": height})
    impact = await strike(ctx, region, Disaster.FLOOD, severity)
    row.dead = len(getattr(impact, "dead", []))
    if height >= table.salt_height:
        await salt(ctx, row)
    return row


async def raise_wave(
    ctx: TickContext,
    origin_region: int,
    origin: WaveOrigin,
    severity: float,
    *,
    strike: Striker,
    cause: int | None = None,
    sure: bool = False,
    atlas: RegionAtlas | None = None,
) -> SeaWaveRow | None:
    atlas = atlas or await RegionAtlas.load(ctx.session)
    sea, coasts = await open_coast(ctx, atlas, origin_region)
    world = atlas.world_of(origin_region)
    if not coasts or world is None:
        return None
    if not sure and not ctx.rng(f"wave.{origin.value}.{origin_region}.{ctx.epoch}").chance(wave_chance(ctx, origin, severity)):
        return None
    wave = SeaWaveRow(
        world_id=world,
        origin=origin,
        origin_region_id=origin_region,
        sea_region_id=sea,
        strength=clamp_int(round(severity * PERCENT), 0, PERCENT),
        cause_node_id=cause,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(wave)
    await ctx.session.flush()
    struck = []
    for coast in coasts:
        hops = atlas.region_hops(origin_region, coast)
        row = await strike_coast(ctx, atlas, wave, coast, hops=hops if hops is not None else 0, strike=strike)
        if row is not None:
            struck.append(row)
    roles = {IncidentRole.PLACE: origin_region, IncidentRole.ACTOR: cause, IncidentRole.TARGET: [row.region_entity_id for row in struck]}
    facts: dict[str, FactInput] = {"origin": origin, "strength": wave.strength, "coasts": len(struck), "dead": sum(row.dead for row in struck)}
    await record(ctx, "land.sea_wave", roles=roles, facts=facts)
    return wave


async def wave_after(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: float, strike: Striker, *, origin: WaveOrigin | None = None) -> None:
    chosen = origin or ORIGIN_OF[disaster]
    if chosen is None:
        return
    if chosen is WaveOrigin.ERUPTION and ctx.rng(f"wave.slide.{target.id}.{ctx.epoch}").chance(ctx.rules.sea_waves.slide_pct):
        chosen, severity = WaveOrigin.SLIDE, min(1.0, severity * SLIDE_STRENGTH)
    atlas = await RegionAtlas.load(ctx.session)
    region = region_of(atlas, target)
    if region is not None:
        await raise_wave(ctx, region, chosen, severity, strike=strike, atlas=atlas)
