from dataclasses import dataclass
from math import sqrt

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ages import FormationHistoryRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.physics import ImpactEventRow, StarPhysicsRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import FormationZone, GiantMigration
from aerona.domain.enums.cosmography import WorldAge
from aerona.domain.enums.physics import ImpactBody, ImpactOutcome
from aerona.domain.enums.world import WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import GAS_WORLDS, planet_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int

DIVINE_WORLDS = frozenset({WorldType.GODS_PALACE, WorldType.DREAM, WorldType.VOID_POCKET, WorldType.GENERATION_SHIP})
TENTHS = 10
ANCIENT = 1
ZONE_WATER = {FormationZone.INNER: 15, FormationZone.SNOW_LINE: 50, FormationZone.OUTER: 80}
ZONE_CORE = {FormationZone.INNER: 35, FormationZone.SNOW_LINE: 25, FormationZone.OUTER: 10}
ZONE_ICE = {FormationZone.INNER: 2, FormationZone.SNOW_LINE: 20, FormationZone.OUTER: 55}
AGE_BOMBARDMENT = {WorldAge.YOUNG: 80, WorldAge.MATURE: 40, WorldAge.OLD: 25, WorldAge.DYING: 20}


@dataclass
class FormationTally:
    formed: int = 0
    shaped: int = 0
    craters: int = 0


async def snow_line(ctx: TickContext, world: WorldRow) -> float:
    physics = await ctx.session.get(StarPhysicsRow, world.star_id) if world.star_id is not None else None
    luminosity = physics.luminosity if physics is not None else 1.0
    return ctx.rules.formation.snow_line_tenths / TENTHS * sqrt(max(luminosity, 0.0001))


def zone_for(ctx: TickContext, orbit: float, line: float) -> FormationZone:
    table = ctx.rules.formation
    if orbit < line * table.inner_share / PERCENT:
        return FormationZone.INNER
    if orbit <= line * table.outer_share / PERCENT:
        return FormationZone.SNOW_LINE
    return FormationZone.OUTER


def migration_for(ctx: TickContext, world: WorldRow) -> GiantMigration:
    table = ctx.rules.formation
    roll = ctx.rng(f"formation.migration.{world.star_id or world.id}").integer(1, PERCENT)
    if roll <= table.inward_chance:
        return GiantMigration.INWARD
    if roll <= table.inward_chance + table.outward_chance:
        return GiantMigration.OUTWARD
    return GiantMigration.NONE


def water_of(ctx: TickContext, zone: FormationZone, migration: GiantMigration) -> int:
    table = ctx.rules.formation
    water = ZONE_WATER[zone]
    if zone is FormationZone.INNER and migration is GiantMigration.INWARD:
        water += table.migration_water
    if zone is FormationZone.INNER and migration is GiantMigration.OUTWARD:
        water -= table.migration_water // 2
    return clamp_int(water, 0, PERCENT)


async def history_of(ctx: TickContext, world: WorldRow, physics: WorldPhysicsRow | None, *, fresh: bool) -> FormationHistoryRow:
    table = ctx.rules.formation
    rng = ctx.rng(f"formation.{world.id}")
    host = await planet_of(ctx.session, world)
    zone = zone_for(ctx, host.orbit, await snow_line(ctx, host))
    migration = migration_for(ctx, host)
    bombardment = clamp_int(AGE_BOMBARDMENT.get(world.age_stage, 40) + rng.integer(-10, 10), 0, PERCENT)
    row = FormationHistoryRow(
        world_id=world.id,
        zone=zone,
        migration=migration,
        bombardment=bombardment,
        craters=bombardment // max(1, table.bombardment_per_crater),
        formed_epoch=ctx.epoch,
        locked=[],
    )
    if fresh or physics is None:
        row.core_share = clamp_int(ZONE_CORE[zone] + rng.integer(-5, 5), 0, PERCENT)
        row.water_delivered = water_of(ctx, zone, migration)
        row.mantle_heat = clamp_int(table.mantle_heat_base + row.core_share // 2 - (PERCENT - bombardment) // 4 + rng.integer(-5, 5), 0, PERCENT)
        row.exotic_delivered = clamp_int(bombardment * table.exotic_pct // PERCENT, 0, PERCENT)
    else:
        row.core_share = clamp_int(physics.iron, 0, PERCENT)
        row.water_delivered = clamp_int(physics.hydrosphere, 0, PERCENT)
        row.mantle_heat = clamp_int(physics.tectonics, 0, PERCENT)
        row.exotic_delivered = clamp_int(physics.exotic, 0, PERCENT)
    return row


def take(physics: WorldPhysicsRow, key: str, value: int) -> None:
    if key not in physics.locked:
        setattr(physics, key, value)


async def shape(ctx: TickContext, world: WorldRow, physics: WorldPhysicsRow, row: FormationHistoryRow) -> None:
    gas = world.world_type in GAS_WORLDS
    take(physics, "iron", row.core_share if not gas else min(physics.iron, row.core_share))
    take(physics, "ice", max(physics.ice, ZONE_ICE[row.zone]))
    if not gas:
        take(physics, "hydrosphere", row.water_delivered)
        take(physics, "tectonics", row.mantle_heat)
        take(physics, "volcanism", clamp_int(row.mantle_heat * 2 // 3, 0, PERCENT))
    take(physics, "exotic", max(physics.exotic, row.exotic_delivered))
    if "magnetism" not in world.locked:
        world.magnetism = clamp_int(row.core_share * 2, 0, PERCENT)
    row.shaped = True


async def mark_craters(ctx: TickContext, world: WorldRow, row: FormationHistoryRow, tally: FormationTally) -> None:
    for number in range(min(row.craters, ctx.rules.formation.recorded_craters)):
        body = ImpactBody.COMET if row.zone is FormationZone.OUTER or number % 2 else ImpactBody.ASTEROID
        ctx.session.add(
            ImpactEventRow(
                world_id=world.id,
                body=body,
                size=clamp_int(row.bombardment - number * 10, 1, PERCENT),
                due_epoch=ANCIENT,
                outcome=ImpactOutcome.STRUCK,
                text=f"An impact of the bombardment that shaped {world.name} in its youth.",
                locked=[],
            )
        )
        tally.craters += 1


async def form_worlds(ctx: TickContext, tally: FormationTally) -> None:
    known = set(await ctx.session.scalars(select(FormationHistoryRow.world_id)))
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if world.id in known or held(world.id) or world.world_type in DIVINE_WORLDS:
            continue
        physics = await ctx.session.get(WorldPhysicsRow, world.id)
        fresh = world.created_epoch >= ctx.epoch - 1
        row = await history_of(ctx, world, physics, fresh=fresh)
        ctx.session.add(row)
        if fresh and physics is not None:
            await shape(ctx, world, physics, row)
            tally.shaped += 1
            await note(ctx, f"{world.name} took its shape from the disc and the bombardment of its youth.", key="formation.shaped", world_id=world.id)
        await mark_craters(ctx, world, row, tally)
        tally.formed += 1
    await ctx.session.flush()
