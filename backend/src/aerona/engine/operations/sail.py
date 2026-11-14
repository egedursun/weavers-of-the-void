from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.operations import RAKED_SECTIONS, SHOT_TARGETS, STATION_SHARES
from aerona.catalog.vehicles import FRAMES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.operations import ShipCrewRow, ShipStateRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.military import VesselArmament
from aerona.domain.enums.operations import CrewStation, PointOfSail, ShotKind
from aerona.domain.enums.vehicles import VehicleFrame, VehicleSection
from aerona.engine.climes.shifts import prevailing
from aerona.engine.context import TickContext
from aerona.engine.military.battle import stack_material
from aerona.engine.operations.fields import keep
from aerona.engine.operations.limits import tonnage_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.vehicles.sections import design_sections, strike_vessel

OCTANTS = 8
HALF_TURN = 4
RAKING_GAP = 30
TINY = 1e-9
GRAPE_CREW_PCT = 130
ROWED = frozenset({VehicleFrame.GALLEY, VehicleFrame.LONGSHIP})
HULL_SECTIONS = frozenset({VehicleSection.HULL, VehicleSection.KEEL, VehicleSection.BOW, VehicleSection.STERN, VehicleSection.HOLD})
P = PointOfSail
S = CrewStation


@dataclass
class Broadside:
    vessel: EntityRow
    row: VesselProfileRow
    state: ShipStateRow
    crew_at_start: int


@dataclass
class Engagement:
    winner: EntityRow
    loser: EntityRow
    sunk: bool = False
    exploded: bool = False
    struck: bool = False
    hits: dict[int, int] = field(default_factory=dict)


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


async def oared(ctx: TickContext, row: VesselProfileRow) -> bool:
    if row.design_id is None:
        return row.frame in ROWED
    return VehicleSection.OARS in await design_sections(ctx.session, row.design_id)


async def crews_of(ctx: TickContext, vessel_id: int, row: VesselProfileRow) -> dict[CrewStation, ShipCrewRow]:
    found = {crew.station: crew for crew in await ctx.session.scalars(select(ShipCrewRow).where(ShipCrewRow.vessel_entity_id == vessel_id))}
    rowing = await oared(ctx, row)
    stations = [station for station in CrewStation if station is not S.ROWERS or rowing]
    weight = sum(STATION_SHARES[station] for station in stations)
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


async def set_sail(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, region_id: int | None, tally: SailTally) -> ShipStateRow:
    state = await ship_state(ctx, vessel.id)
    if held(vessel.id):
        return state
    table = ctx.rules.age_of_sail
    rng = ctx.rng(f"sail.{vessel.id}.{region_id}.{ctx.epoch}")
    steady = await prevailing(ctx.session, region_id)
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


def shot_for(shooter: Broadside, target: Broadside, shooter_speed: int, target_speed: int) -> ShotKind:
    if shooter.row.frame is VehicleFrame.FIRE_SHIP or VesselArmament.RITES.value in shooter.row.armament:
        return ShotKind.FIRE
    if target.row.crew * PERCENT > shooter.row.crew * GRAPE_CREW_PCT:
        return ShotKind.GRAPE
    if target_speed > shooter_speed:
        return ShotKind.CHAIN
    return ShotKind.ROUND


def aim(rng: SeededRandom, sections: list[VehicleSection], shot: ShotKind, raking: bool) -> VehicleSection | None:
    wanted = [section for section in sections if section in SHOT_TARGETS[shot] or (raking and section in RAKED_SECTIONS)]
    pool = wanted or sections
    return rng.pick(pool) if pool else None


async def fire_broadside(ctx: TickContext, shooter: Broadside, target: Broadside, index: int, tally: SailTally, *, weight: float = 1.0) -> int:
    table = ctx.rules.age_of_sail
    crews = await crews_of(ctx, shooter.vessel.id, shooter.row)
    keep(shooter.state, "rate_of_fire", rate_of_fire(ctx, shooter.row, crews))
    mine, theirs = speed_of(ctx, shooter.state), speed_of(ctx, target.state)
    keep(shooter.state, "shot", shot_for(shooter, target, mine, theirs))
    raking = target.state.point_of_sail is P.IN_IRONS or mine - theirs >= RAKING_GAP
    hits = max(1, round((table.base_hits + shooter.state.rate_of_fire // table.rate_hits_per) * weight))
    if raking:
        hits = hits * table.raking_pct // PERCENT
        keep(target.state, "raked", target.state.raked + 1)
        tally.raked += 1
    sections = sorted(await design_sections(ctx.session, target.row.design_id), key=lambda item: item.value) if target.row.design_id is not None else []
    rng = ctx.rng(f"broadside.{shooter.vessel.id}.{target.vessel.id}.{ctx.epoch}.{index}")
    flammable = stack_material(target.row.hull_material).family is MaterialFamily.ORGANIC
    for _ in range(hits):
        section = aim(rng, sections, shooter.state.shot, raking)
        if section is not None:
            await strike_vessel(ctx, target.vessel, target.row, section, 1)
        elif "condition" not in target.row.locked:
            target.row.condition = clamp_int(target.row.condition - ctx.rules.vehicles.section_hit, 0, PERCENT)
        if shooter.state.shot is ShotKind.ROUND and (section is None or section in HULL_SECTIONS):
            keep(target.state, "leak", clamp_int(target.state.leak + table.leak_per_hit, 0, PERCENT))
        elif shooter.state.shot is ShotKind.GRAPE and "crew" not in target.row.locked:
            target.row.crew = max(0, target.row.crew - max(1, target.row.crew * table.grape_crew_pct // PERCENT))
        elif shooter.state.shot is ShotKind.FIRE:
            spread = table.fire_spread_pct if flammable else PERCENT
            keep(target.state, "fire", clamp_int(target.state.fire + table.fire_per_hit * spread // PERCENT, 0, PERCENT))
            tally.fires += 1
    tally.broadsides += 1
    return hits


async def damage_control(ctx: TickContext, side: Broadside) -> None:
    table = ctx.rules.age_of_sail
    crews = await crews_of(ctx, side.vessel.id, side.row)
    riggers = crews.get(S.RIGGERS)
    pumps = table.pumping * (1 + (riggers.count if riggers is not None else 0) // max(1, FRAMES[side.row.frame].crew // 4))
    keep(side.state, "leak", clamp_int(side.state.leak - pumps, 0, PERCENT))
    keep(side.state, "fire", clamp_int(side.state.fire - table.fire_fought, 0, PERCENT))


async def doomed(ctx: TickContext, side: Broadside, index: int, tally: SailTally) -> tuple[bool, bool]:
    table = ctx.rules.age_of_sail
    if side.state.leak >= table.founder_leak:
        tally.foundered += 1
        return True, False
    if (
        side.state.magazine
        and side.state.fire >= table.magazine_fire
        and ctx.rng(f"magazine.{side.vessel.id}.{ctx.epoch}.{index}").chance(table.magazine_chance)
    ):
        keep(side.state, "magazine", False)
        tally.explosions += 1
        return True, True
    return False, False


def strikes(ctx: TickContext, side: Broadside) -> bool:
    table = ctx.rules.age_of_sail
    thinned = side.row.crew * PERCENT < side.crew_at_start * table.strike_crew_pct
    return thinned or side.row.condition < table.strike_condition


async def engage(
    ctx: TickContext, first: tuple[EntityRow, VesselProfileRow], second: tuple[EntityRow, VesselProfileRow], powers: tuple[float, float], tally: SailTally
) -> Engagement:
    sides = [Broadside(vessel, row, await ship_state(ctx, vessel.id), row.crew) for vessel, row in (first, second)]
    strongest = max(*powers, TINY)
    weights = [power / strongest for power in powers]
    weaker = 0 if powers[0] < powers[1] else 1
    hits = {side.vessel.id: 0 for side in sides}
    for index in range(ctx.rules.age_of_sail.rounds):
        for position, (shooter, target) in enumerate(((sides[0], sides[1]), (sides[1], sides[0]))):
            if held(target.vessel.id):
                continue
            hits[target.vessel.id] += await fire_broadside(ctx, shooter, target, index, tally, weight=weights[position])
        doomed_now: list[tuple[int, bool]] = []
        for position, side in enumerate(sides):
            await damage_control(ctx, side)
            sunk, exploded = await doomed(ctx, side, index, tally)
            if sunk:
                doomed_now.append((position, exploded))
        if doomed_now:
            position, exploded = next((item for item in doomed_now if item[0] == weaker), doomed_now[0])
            return Engagement(sides[1 - position].vessel, sides[position].vessel, sunk=True, exploded=exploded, hits=hits)
        broken = [position for position, side in enumerate(sides) if strikes(ctx, side) and not held(side.vessel.id)]
        if broken:
            position = weaker if weaker in broken else broken[0]
            keep(sides[position].state, "struck", True)
            tally.struck += 1
            return Engagement(sides[1 - position].vessel, sides[position].vessel, struck=True, hits=hits)
    winner, loser = (sides[0], sides[1]) if powers[0] >= powers[1] else (sides[1], sides[0])
    return Engagement(winner.vessel, loser.vessel, hits=hits)


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
