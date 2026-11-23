from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.operations import STATION_SHARES
from aerona.catalog.vehicles import FRAMES
from aerona.catalog.wind_belts import BELTS
from aerona.constants.units import PERCENT
from aerona.db.tables.climes import RegionWindRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.operations import ShipCrewRow, ShipStateRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import CrewStation, PointOfSail, ShotKind
from aerona.domain.enums.vehicles import VehicleFrame, VehicleSection
from aerona.engine.climes.shifts import prevailing
from aerona.engine.context import TickContext
from aerona.engine.military.battle import stack_material
from aerona.engine.operations.crews import fitted_stations
from aerona.engine.operations.fields import keep
from aerona.engine.operations.limits import tonnage_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

OCTANTS = 8
HALF_TURN = 4
SOLID_LEVEL = 4
SHELL_LEVEL = 6
GUIDED_LEVEL = 7
ENERGY_LEVEL = 9
GRAPE_CREW_PCT = 130
GUIDED_FAMILIES = frozenset({EquipmentFamily.MISSILE_LAUNCHER, EquipmentFamily.ROCKET_LAUNCHER, EquipmentFamily.TORPEDO})
RITE_FAMILIES = frozenset({EquipmentFamily.FOCUS, EquipmentFamily.FOCUS_ARRAY})
P = PointOfSail
S = CrewStation


@dataclass
class Broadside:
    vessel: EntityRow
    row: VesselProfileRow
    state: ShipStateRow
    crew_at_start: int
    families: frozenset[EquipmentFamily] = frozenset()


@dataclass
class SailTally:
    legs: int = 0
    in_irons: int = 0
    tacks: int = 0
    broadsides: int = 0
    raked: int = 0
    fires: int = 0
    explosions: int = 0
    foundered: int = 0
    struck: int = 0
    prizes: int = 0


async def ship_state(ctx: TickContext, vessel_id: int) -> ShipStateRow:
    row = await ctx.session.get(ShipStateRow, vessel_id)
    if row is None:
        row = ShipStateRow(vessel_entity_id=vessel_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def crews_of(ctx: TickContext, vessel_id: int, row: VesselProfileRow) -> dict[CrewStation, ShipCrewRow]:
    found = {crew.station: crew for crew in await ctx.session.scalars(select(ShipCrewRow).where(ShipCrewRow.vessel_entity_id == vessel_id))}
    stations = await fitted_stations(ctx.session, vessel_id, row)
    weight = max(1, sum(STATION_SHARES[station] for station in stations))
    for station in stations:
        if station in found:
            continue
        crew = ShipCrewRow(vessel_entity_id=vessel_id, station=station, count=row.crew * STATION_SHARES[station] // weight, skill=row.seamanship, locked=[])
        ctx.session.add(crew)
        found[station] = crew
    await ctx.session.flush()
    return found


def angle(heading: int, wind: int) -> int:
    gap = abs(heading - wind) % OCTANTS
    return min(gap, OCTANTS - gap)


def point_for(gap: int) -> PointOfSail:
    if gap == 0:
        return P.IN_IRONS
    if gap == 1:
        return P.CLOSE_HAULED
    if gap >= HALF_TURN:
        return P.RUNNING
    return P.REACHING


def speed_of(ctx: TickContext, state: ShipStateRow) -> int:
    table = ctx.rules.age_of_sail
    return {
        P.IN_IRONS: table.irons_speed_pct,
        P.CLOSE_HAULED: table.close_hauled_pct,
        P.REACHING: table.reaching_pct,
        P.RUNNING: table.running_pct,
        P.UNDER_OARS: table.oars_pct * (PERCENT - state.rower_fatigue // 2) // PERCENT,
    }[state.point_of_sail]


async def becalmed(ctx: TickContext, vessel: EntityRow, region_id: int | None, unlucky: bool) -> bool:
    wind = await ctx.session.get(RegionWindRow, region_id) if region_id is not None else None
    if wind is None or not unlucky or not BELTS[wind.band].calm:
        return False
    await record(ctx, "voyage.becalmed", roles={IncidentRole.SUBJECT: vessel.id, IncidentRole.PLACE: region_id}, facts={"band": wind.band}, place=region_id)
    return True


async def set_sail(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, region_id: int | None, tally: SailTally) -> ShipStateRow:
    state = await ship_state(ctx, vessel.id)
    if held(vessel.id):
        return state
    table = ctx.rules.age_of_sail
    rng = ctx.rng(f"sail.{vessel.id}.{'adrift' if region_id is None else region_id}.{ctx.epoch}")
    steady = await prevailing(ctx.session, region_id)
    if await becalmed(ctx, vessel, region_id, rng.chance(ctx.rules.winds.becalmed_pct)):
        keep(state, "point_of_sail", P.IN_IRONS)
        tally.legs += 1
        tally.in_irons += 1
        state.updated_epoch = ctx.epoch
        return state
    keep(state, "wind_from", steady if steady is not None and rng.chance(ctx.rules.winds.sail_steady_pct) else rng.below(OCTANTS))
    keep(state, "heading", rng.below(OCTANTS))
    gap = angle(state.heading, state.wind_from)
    crews = await crews_of(ctx, vessel.id, row)
    rowers = crews.get(S.ROWERS)
    if rowers is not None and rowers.count > 0 and gap <= 1:
        keep(state, "point_of_sail", P.UNDER_OARS)
        keep(state, "rower_fatigue", clamp_int(state.rower_fatigue + table.rower_fatigue, 0, PERCENT))
    else:
        if gap == 0 and rng.chance(table.tack_chance + row.seamanship // 2):
            keep(state, "heading", (state.heading + 2) % OCTANTS)
            keep(state, "tacks", state.tacks + 1)
            tally.tacks += 1
            gap = angle(state.heading, state.wind_from)
        keep(state, "point_of_sail", point_for(gap))
        keep(state, "rower_fatigue", clamp_int(state.rower_fatigue - table.rower_rest, 0, PERCENT))
    tally.legs += 1
    tally.in_irons += state.point_of_sail is P.IN_IRONS
    state.updated_epoch = ctx.epoch
    return state


def rate_of_fire(ctx: TickContext, row: VesselProfileRow, crews: dict[CrewStation, ShipCrewRow]) -> int:
    gunners = crews.get(S.GUNNERS)
    officers = crews.get(S.OFFICERS)
    if gunners is None:
        return 0
    manned = FRAMES[row.frame].crew * STATION_SHARES[S.GUNNERS] // PERCENT
    served = min(PERCENT, gunners.count * PERCENT // max(1, manned))
    command = officers.skill * ctx.rules.age_of_sail.officer_reload_pct // PERCENT if officers is not None and officers.count > 0 else 0
    return clamp_int(gunners.skill * served // PERCENT + command, 0, PERCENT)


def modern_shot(shooter: Broadside, target: Broadside, level: int, sections: list[VehicleSection]) -> ShotKind | None:
    if level >= ENERGY_LEVEL:
        return ShotKind.ENERGY
    if level >= GUIDED_LEVEL and shooter.families & GUIDED_FAMILIES:
        return ShotKind.GUIDED
    if level >= SHELL_LEVEL:
        if VehicleSection.ARMOUR_PLATING in sections:
            return ShotKind.PIERCING
        if target.row.crew * PERCENT > shooter.row.crew * GRAPE_CREW_PCT:
            return ShotKind.SPREAD
        return ShotKind.INCENDIARY if stack_material(target.row.hull_material).family is MaterialFamily.ORGANIC else ShotKind.EXPLOSIVE
    return ShotKind.SOLID if level >= SOLID_LEVEL else None


def shot_for(shooter: Broadside, target: Broadside, shooter_speed: int, target_speed: int) -> ShotKind:
    if shooter.row.frame is VehicleFrame.FIRE_SHIP or shooter.families & RITE_FAMILIES:
        return ShotKind.FIRE
    if target.row.crew * PERCENT > shooter.row.crew * GRAPE_CREW_PCT:
        return ShotKind.GRAPE
    if target_speed > shooter_speed:
        return ShotKind.CHAIN
    return ShotKind.ROUND


async def take_prize(ctx: TickContext, captor_row: VesselProfileRow, prize: EntityRow, prize_row: VesselProfileRow, captor_owner: EntityRow | None) -> int:
    table = ctx.rules.age_of_sail
    state = await ship_state(ctx, prize.id)
    crew = captor_row.crew * table.prize_crew_pct // PERCENT
    if "crew" not in captor_row.locked:
        captor_row.crew = max(0, captor_row.crew - crew)
    if "crew" not in prize_row.locked:
        prize_row.crew = crew
    money = tonnage_of(prize_row) * table.prize_money_per_ton
    keep(state, "prize_of_entity_id", captor_owner.id if captor_owner is not None else None)
    keep(state, "prize_crew", crew)
    keep(state, "prize_money", money)
    keep(state, "struck", False)
    keep(state, "fire", 0)
    if captor_owner is not None and "fleet_army_entity_id" not in prize_row.locked:
        prize_row.fleet_army_entity_id = captor_row.fleet_army_entity_id
        prize_row.crew_community_entity_id = captor_owner.id
    for station_row in await ctx.session.scalars(select(ShipCrewRow).where(ShipCrewRow.vessel_entity_id == prize.id)):
        keep(station_row, "count", crew * STATION_SHARES[station_row.station] // PERCENT)
    return money
