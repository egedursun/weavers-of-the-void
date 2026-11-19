from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.nature_kinds50 import SPACE_WEATHER
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.tables.space_weather import SpaceWeatherEventRow, StarActivityRow, WorldFieldRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.networks import OutageCause
from aerona.domain.enums.space_weather import SpaceWeatherKind
from aerona.domain.enums.world import Atmosphere, SkyEventKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.made.control import cut_network
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.rules.registry import Rules

AIR_SHIELDING: dict[Atmosphere, int] = {Atmosphere.NONE: 0, Atmosphere.THIN: 25, Atmosphere.NORMAL: 50, Atmosphere.DENSE: 75, Atmosphere.TOXIC: 60}
STORM_KINDS = tuple(kind for kind, spec in SPACE_WEATHER.items() if spec.from_star and kind is not SpaceWeatherKind.FLARE)
TENTHS = 10
PEAK = 50
COMMUNITIES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
SHELTERS = frozenset({EntityType.SETTLEMENT, EntityType.STRUCTURE})


@dataclass(frozen=True)
class Strike:
    star_id: int | None
    kind: SpaceWeatherKind
    strength: int


@dataclass
class SpaceWeatherTally:
    events: int = 0
    outages: int = 0
    harmed: int = 0
    reversals: int = 0
    omens: int = 0


def shield_of(rules: Rules, world: WorldRow, field: WorldFieldRow) -> int:
    table = rules.space_weather
    shielding = field.shielding - (table.reversal_shield_loss if field.reversal_left > 0 else 0)
    strength = clamp_int(world.magnetism + field.shift, 0, PERCENT)
    return clamp_int(strength * table.shield_per_field_point + max(0, shielding) * table.shield_per_air_point, 0, PERCENT * 2)


def dose_through(rules: Rules, world: WorldRow, field: WorldFieldRow, strength: int) -> int:
    return clamp_int(strength * 2 - shield_of(rules, world, field) // 2, 0, PERCENT)


async def field_of(ctx: TickContext, world: WorldRow) -> WorldFieldRow:
    row = await ctx.session.get(WorldFieldRow, world.id)
    if row is None:
        row = WorldFieldRow(world_id=world.id, shielding=AIR_SHIELDING[world.atmosphere], locked=[])
        ctx.session.add(row)
    return row


async def activity_of(ctx: TickContext, star: StarRow) -> StarActivityRow:
    row = await ctx.session.get(StarActivityRow, star.id)
    if row is None:
        row = StarActivityRow(
            star_id=star.id,
            cycle_years=ctx.rules.space_weather.cycle_years,
            flare_rate=clamp_int(PERCENT - star.stability, 0, PERCENT),
            storm_rate=clamp_int(star.radiation, 0, PERCENT),
            wind=clamp_int((star.brightness + star.radiation) // 2, 0, PERCENT),
            locked=[],
        )
        ctx.session.add(row)
    return row


def turn_cycle(ctx: TickContext, row: StarActivityRow) -> None:
    if "phase" in row.locked:
        return
    step = round_half_up(PERCENT * ctx.rules.space_weather.years_per_epoch / max(1, row.cycle_years))
    row.phase = (row.phase + step) % PERCENT


def activity(row: StarActivityRow) -> int:
    return PERCENT - abs(row.phase - PEAK) * 2


async def strike(ctx: TickContext, world: WorldRow, field: WorldFieldRow, blow: Strike, tally: SpaceWeatherTally) -> None:
    table = ctx.rules.space_weather
    kind, strength = blow.kind, blow.strength
    dose = dose_through(ctx.rules, world, field, strength)
    ctx.session.add(SpaceWeatherEventRow(star_id=blow.star_id, world_id=world.id, kind=kind, strength=strength, dose=dose, epoch=ctx.epoch, locked=[]))
    tally.events += 1
    with explaining_alone():
        term("space_weather.dose", dose, source_node_id=world.id)
        if "surface_dose" not in field.locked:
            field.surface_dose = max(field.surface_dose, dose)
        if "aurora_reach" not in field.locked:
            reach = clamp_int(strength * table.aurora_per_strength - shield_of(ctx.rules, world, field) // 4, 0, PERCENT)
            field.aurora_reach = max(field.aurora_reach, reach)
    if kind is SpaceWeatherKind.FLARE:
        await record(
            ctx,
            "sky.flare",
            roles={IncidentRole.SUBJECT: world.id},
            facts={"event": SkyEventKind.FLARE, "lasting": 1, "strength": strength, "dose": dose},
            world_id=world.id,
        )
    else:
        await record(ctx, f"sky.{kind.value}", roles={IncidentRole.SUBJECT: world.id}, facts={"strength": strength, "dose": dose}, world_id=world.id)
    if field.aurora_reach >= PEAK:
        await record(ctx, "sky.aurora_spread", roles={IncidentRole.SUBJECT: world.id}, facts={"reach": field.aurora_reach}, world_id=world.id)
        await read_omen(ctx, world, field.aurora_reach, tally)
    if dose >= table.outage_threshold:
        await fail_signals(ctx, world, dose, tally)
        await harm_the_exposed(ctx, world, dose, tally)
    if dose >= table.crop_dose:
        await stress_harvests(ctx, world)


async def fail_signals(ctx: TickContext, world: WorldRow, dose: int, tally: SpaceWeatherTally) -> None:
    networks = list(
        await ctx.session.scalars(
            select(NetworkProfileRow.network_entity_id)
            .join(EntityRow, EntityRow.id == NetworkProfileRow.network_entity_id)
            .where(EntityRow.world_id == world.id, EntityRow.status == EntityStatus.CANON)
            .order_by(NetworkProfileRow.network_entity_id)
        )
    )
    cut = [network for network in networks if not held(network)]
    for network in cut:
        await cut_network(ctx, network, OutageCause.FLARE, 1, dose)
    tally.outages += len(cut)
    await record(
        ctx, "sky.outage", roles={IncidentRole.SUBJECT: world.id, IncidentRole.VICTIM: cut}, facts={"dose": dose, "networks": len(cut)}, world_id=world.id
    )


async def harm_the_exposed(ctx: TickContext, world: WorldRow, dose: int, tally: SpaceWeatherTally) -> None:
    table = ctx.rules.space_weather
    amount = (dose - table.outage_threshold) // TENTHS * table.dose_harm_per_point
    if amount <= 0:
        return
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal in list(mortals):
        place = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
        if held(mortal.id) or (place is not None and place.entity_type in SHELTERS):
            continue
        await apply_hits(ctx, mortal, Harm(amount, HarmCause.RADIATION, "struck by a storm from the sky"), lethal=False)
        tally.harmed += 1


async def stress_harvests(ctx: TickContext, world: WorldRow) -> None:
    loss = ctx.rules.space_weather.crop_loss
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        if not held(town.id):
            with explaining_alone():
                term("space_weather.harvest", -loss, source_node_id=world.id)
                shift_stat(town, "prosperity", -loss, low=0, high=PERCENT)


async def read_omen(ctx: TickContext, world: WorldRow, strength: int, tally: SpaceWeatherTally) -> None:
    piety = ctx.rules.space_weather.omen_piety
    if piety <= 0:
        return
    readers = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.world_id == world.id, EntityRow.entity_type.in_(COMMUNITIES), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for community in list(readers):
        if not held(community.id):
            with explaining_alone():
                term("space_weather.omen", piety, source_node_id=world.id)
                shift_stat(community, "piety", piety, low=0, high=PERCENT)
            tally.omens += 1


async def maybe_reverse(ctx: TickContext, world: WorldRow, field: WorldFieldRow, tally: SpaceWeatherTally) -> None:
    table = ctx.rules.space_weather
    if field.reversal_left > 0:
        if "reversal_left" not in field.locked:
            field.reversal_left -= 1
        return
    if "reversal_epoch" in field.locked or not ctx.rng(seed_of("field.reversal", world.id, ctx.epoch)).chance(table.reversal_chance_per_epoch_pct):
        return
    field.reversal_epoch = ctx.epoch
    field.reversal_left = table.epochs(table.reversal_years)
    tally.reversals += 1
    await strike(ctx, world, field, Strike(None, SpaceWeatherKind.FIELD_REVERSAL, table.reversal_shield_loss), tally)
    await read_omen(ctx, world, table.reversal_shield_loss, tally)


def ease_shift(field: WorldFieldRow) -> None:
    if field.shift_left <= 0 or "shift_left" in field.locked:
        return
    field.shift_left -= 1
    if field.shift_left == 0 and "shift" not in field.locked:
        field.shift = 0


def settle_compass(rules: Rules, world: WorldRow, field: WorldFieldRow) -> None:
    if "compass_error" in field.locked:
        return
    weakness = PERCENT - clamp_int(world.magnetism + field.shift, 0, PERCENT) + (rules.space_weather.reversal_shield_loss if field.reversal_left > 0 else 0)
    field.compass_error = clamp_int(max(field.surface_dose, weakness // 2), 0, PERCENT)


async def weather_world(ctx: TickContext, world: WorldRow, tally: SpaceWeatherTally) -> None:
    table = ctx.rules.space_weather
    field = await field_of(ctx, world)
    if "surface_dose" not in field.locked:
        field.surface_dose = 0
    if "aurora_reach" not in field.locked:
        field.aurora_reach = clamp_int(PERCENT - world.magnetism, 0, PERCENT) // 4
    await maybe_reverse(ctx, world, field, tally)
    ease_shift(field)
    star = await ctx.session.get(StarRow, world.star_id) if world.star_id is not None else None
    rng = ctx.rng(seed_of("space_weather", world.id, ctx.epoch))
    if star is not None:
        row = await activity_of(ctx, star)
        level = activity(row)
        if rng.chance(table.flare_base_pct * row.flare_rate * level * 4 / PERCENT / PERCENT):
            strength = clamp_int(star.radiation * level // PERCENT + row.flare_rate // 2, 0, PERCENT)
            await strike(ctx, world, field, Strike(star.id, SpaceWeatherKind.FLARE, strength), tally)
        if rng.chance(table.storm_base_pct * row.storm_rate * level * 4 / PERCENT / PERCENT):
            kind = STORM_KINDS[rng.below(len(STORM_KINDS))]
            strength = clamp_int(row.wind * level // PERCENT + row.storm_rate // 2, 0, PERCENT)
            await strike(ctx, world, field, Strike(star.id, kind, strength), tally)
    if rng.chance(table.burst_base_pct):
        await strike(ctx, world, field, Strike(None, SpaceWeatherKind.COSMIC_RAY_BURST, PEAK + rng.below(PEAK)), tally)
    settle_compass(ctx.rules, world, field)


async def keep_space_weather(ctx: TickContext, tally: SpaceWeatherTally) -> None:
    for star in list(await ctx.session.scalars(select(StarRow).order_by(StarRow.id))):
        if not held(star.id):
            turn_cycle(ctx, await activity_of(ctx, star))
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if not held(world.id):
            await weather_world(ctx, world, tally)
    await ctx.session.flush()
