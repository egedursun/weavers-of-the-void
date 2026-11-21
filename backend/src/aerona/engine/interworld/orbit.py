from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import OrbitalControlRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.networks import OutageCause
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import touches
from aerona.engine.interworld.book import InterworldTally, orbit_of
from aerona.engine.made.control import cut_network
from aerona.engine.means.building import burn_structures
from aerona.engine.military.vessels import batter_fleet, fleet_bonus
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record
from aerona.engine.services.war import current_war

TENTHS = 1000
SOLDIERS_PER_POINT = 100
LOSER_DAMAGE = 0.3
GALE = 0.5


async def orbit_power(ctx: TickContext, army: EntityRow) -> int:
    return round_half_up(await fleet_bonus(ctx, army.id, None)) + (stat(army, "size") or 0) // SOLDIERS_PER_POINT


async def contest(ctx: TickContext, world_id: int, challenger: int, army: EntityRow, tally: InterworldTally) -> bool:
    row = await orbit_of(ctx.session, world_id)
    if row is not None and (held(row.holder_entity_id) or "holder_entity_id" in (row.locked or [])):
        return False
    attack = await orbit_power(ctx, army)
    defence = row.strength if row is not None and row.holder_entity_id != challenger else 0
    won = attack > 0 and ctx.rng(f"orbit.{world_id}.{challenger}.{ctx.epoch}").chance(PERCENT * attack / max(1, attack + defence))
    if not won:
        await batter_fleet(ctx, army.id, LOSER_DAMAGE, region_id=None)
        if row is not None:
            row.contested_by_entity_id = challenger
        return False
    loser = row.holder_entity_id if row is not None else None
    if row is None:
        row = OrbitalControlRow(world_id=world_id, holder_entity_id=challenger, locked=[])
        ctx.session.add(row)
    row.holder_entity_id, row.strength, row.contested_by_entity_id, row.since_epoch = challenger, clamp_int(attack, 0, PERCENT), None, ctx.epoch
    await ctx.session.flush()
    tally.orbits_won += 1
    await record(ctx, "war.orbit_won", roles={IncidentRole.ACTOR: challenger, IncidentRole.VICTIM: loser}, facts={"strength": row.strength}, world_id=world_id)
    if loser is not None and loser != challenger:
        tally.orbits_lost += 1
        await record(
            ctx, "war.orbit_lost", roles={IncidentRole.SUBJECT: loser, IncidentRole.ACTOR: challenger}, facts={"strength": row.strength}, world_id=world_id
        )
    return True


async def enemies_below(ctx: TickContext, row: OrbitalControlRow) -> list[EntityRow]:
    query = select(EntityRow).where(EntityRow.world_id == row.world_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
    found: list[EntityRow] = []
    for town in await ctx.session.scalars(query.order_by(EntityRow.id)):
        if not held(town.id) and await current_war(ctx.session, row.holder_entity_id, town.id) is not None:
            found.append(town)
    return found


async def bombard(ctx: TickContext, row: OrbitalControlRow, tally: InterworldTally) -> None:
    for town in await enemies_below(ctx, row):
        dead = round_half_up((stat(town, "population") or 0) * ctx.rules.interworld.bombard_harm_per_strength * row.strength / (TENTHS * PERCENT))
        if dead <= 0:
            continue
        shift_stat(town, "population", -dead)
        await burn_structures(ctx, town, GALE)
        tally.bombardments += 1
        await record(ctx, "war.bombardment", roles={IncidentRole.ACTOR: row.holder_entity_id, IncidentRole.VICTIM: town.id}, facts={"dead": dead})


async def blockade(ctx: TickContext, row: OrbitalControlRow) -> None:
    for route in await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.id)):
        if touches(route, row.world_id) and "toll_controller_entity_id" not in (route.locked or []):
            route.toll_controller_entity_id, route.toll_pct = row.holder_entity_id, max(route.toll_pct, ctx.rules.interworld.blockade_toll_pct)


async def cut_signals(ctx: TickContext, row: OrbitalControlRow) -> None:
    query = (
        select(NetworkProfileRow)
        .join(EntityRow, EntityRow.id == NetworkProfileRow.network_entity_id)
        .where(EntityRow.world_id == row.world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(NetworkProfileRow.network_entity_id)
    )
    for network in list(await ctx.session.scalars(query)):
        owner = network.owner_node_id
        if owner is None or held(network.network_entity_id) or await current_war(ctx.session, row.holder_entity_id, owner) is None:
            continue
        await cut_network(ctx, network.network_entity_id, OutageCause.WAR, 1, row.strength)


async def lift_blockade(ctx: TickContext, world_id: int, holder: int) -> None:
    for route in await ctx.session.scalars(select(RouteRow).where(RouteRow.toll_controller_entity_id == holder).order_by(RouteRow.id)):
        if touches(route, world_id) and "toll_controller_entity_id" not in (route.locked or []):
            route.toll_controller_entity_id, route.toll_pct = None, 0


async def tend_orbits(ctx: TickContext, tally: InterworldTally) -> None:
    for row in list(await ctx.session.scalars(select(OrbitalControlRow).order_by(OrbitalControlRow.id))):
        holder = await living_entity(ctx.session, row.holder_entity_id)
        if holder is None:
            await lift_blockade(ctx, row.world_id, row.holder_entity_id)
            await ctx.session.delete(row)
            continue
        if held(holder.id):
            continue
        await bombard(ctx, row, tally)
        await blockade(ctx, row)
        await cut_signals(ctx, row)
