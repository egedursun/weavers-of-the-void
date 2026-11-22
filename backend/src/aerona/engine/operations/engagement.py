from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.engagement import MOVING_SECTIONS, SHIELDED, WATERBORNE, chain_of, reached
from aerona.catalog.equipment import FAMILIES
from aerona.catalog.life.operations import HOLED_SECTIONS
from aerona.catalog.operations import RAKED_SECTIONS, SHOT_TARGETS, SHOT_WEIGHT
from aerona.catalog.vehicles import FRAMES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.stored import stored_id
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.equipment import EquipmentModelRow
from aerona.db.tables.operations import ShipStateRow
from aerona.db.tables.vehicles import DesignMountRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.integrity import SectionState
from aerona.domain.enums.operations import CrewStation, PointOfSail, ShotKind
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepLocus, StepOutcome, StepState
from aerona.domain.enums.vehicles import MountKind, VehicleDomain, VehicleSection
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.military.battle import stack_material
from aerona.engine.operations.fields import keep
from aerona.engine.operations.sail import Broadside, SailTally, crews_of, modern_shot, rate_of_fire, ship_state, shot_for, speed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import StepDraft
from aerona.engine.technology.profiles import family_level
from aerona.engine.vehicles.sections import design_sections, mend_vessel_sections, strike_vessel, vessel_sections

TINY = 1e-9
RAKING_GAP = 30
CANNON_FAMILIES = frozenset({EquipmentFamily.CANNON, EquipmentFamily.CARRONADE, EquipmentFamily.BOMBARD})
RAMMING = frozenset({EquipmentFamily.RAM})
FALLEN = frozenset({SectionState.DESTROYED})
DOWN = frozenset({SectionState.DISABLED, SectionState.DESTROYED})
SAILED = frozenset({VehicleDomain.WATER, VehicleDomain.AMPHIBIOUS})


@dataclass(frozen=True)
class Weapon:
    mount: MountKind
    family: EquipmentFamily | None
    model_id: int | None
    model_node: int | None
    damage: DamageType
    count: int
    weight: float


@dataclass
class Party:
    vessel: EntityRow
    row: VesselProfileRow
    state: ShipStateRow
    crew_at_start: int
    weapons: list[Weapon]
    carried: list[VehicleSection]
    shielded: bool = False
    adrift: bool = False
    lost: bool = False
    crashed: bool = False
    grounded: bool = False
    jettisoned: bool = False
    hits_taken: int = 0


@dataclass
class Engagement:
    winner: EntityRow
    loser: EntityRow
    domain: VehicleDomain
    rounds: int
    end: StepOutcome
    sunk: bool = False
    exploded: bool = False
    struck: bool = False
    crashed: bool = False
    captured: bool = False
    escaped: bool = False
    hits: dict[int, int] = field(default_factory=dict)
    steps: list[StepDraft] = field(default_factory=list)


def domain_of(row: VesselProfileRow) -> VehicleDomain:
    return FRAMES[row.frame].domain


async def weapons_of(ctx: TickContext, row: VesselProfileRow) -> list[Weapon]:
    if row.design_id is None:
        return []
    mounts = list(
        await ctx.session.scalars(select(DesignMountRow).where(DesignMountRow.design_id == row.design_id).order_by(DesignMountRow.slot, DesignMountRow.id))
    )
    found: list[Weapon] = []
    for mount in mounts:
        model = await ctx.session.get(EquipmentModelRow, mount.model_id) if mount.model_id is not None else None
        if model is None or mount.count <= 0:
            continue
        spec = FAMILIES[model.family]
        weight = max(1, model.damage) * mount.count * max(1, model.rate)
        found.append(Weapon(mount.mount, model.family, model.id, model.entity_id, spec.damage_type, mount.count, float(weight)))
    return found


async def party(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow) -> Party:
    carried = sorted(await design_sections(ctx.session, row.design_id), key=lambda item: item.value) if row.design_id is not None else []
    return Party(vessel, row, await ship_state(ctx, vessel.id), row.crew, await weapons_of(ctx, row), carried)


async def sound_share(ctx: TickContext, side: Party, domain: VehicleDomain) -> float:
    moving = [section for section in side.carried if section in MOVING_SECTIONS[domain]]
    if not moving:
        return 1.0
    states = await vessel_sections(ctx.session, side.vessel.id)
    working = sum(1 for section in moving if section not in states or states[section].state not in DOWN)
    return working / len(moving)


async def position_of(ctx: TickContext, side: Party, domain: VehicleDomain) -> float:
    table = ctx.rules.engagement
    if side.adrift or side.grounded:
        return 0.0
    base = float(speed_of(ctx, side.state)) if domain in SAILED else float(FRAMES[side.row.frame].speed)
    share = max(table.sound_share_floor_pct / PERCENT, await sound_share(ctx, side, domain))
    handling = 1 + side.row.seamanship * table.position_seamanship_pct / (PERCENT * PERCENT)
    return base * share * handling


def shot_sections(side: Party, target: Party, weapon: Weapon | None, raking: bool) -> list[VehicleSection]:
    if weapon is None or weapon.family in CANNON_FAMILIES:
        wanted = [section for section in target.carried if section in SHOT_TARGETS[side.state.shot] or (raking and section in RAKED_SECTIONS)]
        return wanted or target.carried
    if target.shielded and weapon.damage in SHIELDED and VehicleSection.WARD in target.carried:
        return [VehicleSection.WARD]
    return reached(weapon.damage, weapon.family, target.carried)


def instrument(weapon: Weapon | None) -> tuple[InstrumentKind, int | None, str | None]:
    if weapon is None:
        return InstrumentKind.VEHICLE, None, None
    return InstrumentKind.VEHICLE_WEAPON, weapon.model_node, weapon.family.value if weapon.family is not None else weapon.mount.value


def section_outcome(state: SectionState) -> StepOutcome:
    return {
        SectionState.SOUND: StepOutcome.GLANCED,
        SectionState.DAMAGED: StepOutcome.DAMAGED,
        SectionState.DISABLED: StepOutcome.DISABLED,
        SectionState.DESTROYED: StepOutcome.DESTROYED,
    }[state]


@dataclass
class Fight:
    ctx: TickContext
    domain: VehicleDomain
    sides: list[Party]
    weights: list[float]
    tally: SailTally
    steps: list[StepDraft] = field(default_factory=list)
    hits: dict[int, int] = field(default_factory=dict)

    def step(self, draft: StepDraft) -> int:
        self.steps.append(draft)
        return len(self.steps) - 1


async def lose_crew(fight: Fight, side: Party, pct: int, parent: int, round_index: int) -> int:
    lost_total = 0
    if pct <= 0 or held(side.vessel.id):
        return 0
    crews = await crews_of(fight.ctx, side.vessel.id, side.row)
    for station in CrewStation:
        crew = crews.get(station)
        if crew is None or crew.count <= 0 or "count" in crew.locked:
            continue
        lost = max(1, crew.count * pct // PERCENT)
        crew.count -= lost
        lost_total += lost
        fight.step(
            StepDraft(
                StepAction.DIE,
                target=side.vessel.id,
                round=round_index,
                parent=parent,
                amount=lost,
                unit=FactUnit.PEOPLE,
                outcome=StepOutcome.KILLED,
                record_table="ship_crews",
                record_key=f"{side.vessel.id}:{station.value}",
            )
        )
    if "crew" not in side.row.locked:
        side.row.crew = max(0, side.row.crew - lost_total)
    return lost_total


async def chain(fight: Fight, side: Party, section: VehicleSection, round_index: int) -> None:
    spec = chain_of(section, fight.domain)
    if spec is None:
        return
    table, sail = fight.ctx.rules.engagement, fight.ctx.rules.age_of_sail
    states = ((side.vessel.id, spec.state),) if spec.state is not None else ()
    index = fight.step(
        StepDraft(
            spec.action,
            actor=side.vessel.id,
            round=round_index,
            locus_kind=StepLocus.VEHICLE_SECTION,
            locus_key=section.value,
            locus_node=side.vessel.id,
            states=states,
        )
    )
    if spec.action is StepAction.EXPLODE:
        side.lost = True
        fight.tally.explosions += 1
    elif spec.action is StepAction.CRASH:
        if fight.ctx.rng(f"engagement.fall.{side.vessel.id}.{fight.ctx.epoch}.{round_index}").chance(table.fall_lost_pct):
            side.lost = True
            side.crashed = True
        else:
            side.grounded = True
    elif spec.action is StepAction.FLOOD:
        keep(side.state, "leak", clamp_int(side.state.leak + table.flooding_leak, 0, PERCENT))
    elif spec.action is StepAction.VENT:
        await lose_crew(fight, side, table.venting_crew_pct if spec.state is StepState.DEPRESSURISED else table.breach_crew_pct, index, round_index)
    elif spec.action in {StepAction.LOSE_POWER, StepAction.DRIFT}:
        side.adrift = True
        await run_aground(fight, side, round_index)
    elif spec.action is StepAction.LOSE_SHIELD:
        side.shielded = False
    elif spec.action is StepAction.IGNITE:
        keep(side.state, "fire", clamp_int(side.state.fire + sail.fire_per_hit, 0, PERCENT))


async def run_aground(fight: Fight, side: Party, round_index: int) -> None:
    if fight.domain not in WATERBORNE or fight.domain is VehicleDomain.UNDERWATER:
        return
    land = await fight.ctx.session.get(RegionEnvironmentRow, side.row.region_entity_id) if side.row.region_entity_id is not None else None
    coastal = land is not None and land.coast_kind is not CoastKind.NONE
    if coastal and fight.ctx.rng(f"engagement.aground.{side.vessel.id}.{fight.ctx.epoch}.{round_index}").chance(fight.ctx.rules.engagement.adrift_aground_pct):
        side.grounded = True
        fight.step(
            StepDraft(StepAction.DRIFT, actor=side.vessel.id, round=round_index, locus_kind=StepLocus.SEA, states=((side.vessel.id, StepState.AGROUND),))
        )


async def land(fight: Fight, shooter: Party, target: Party, *, weapon: Weapon | None, section: VehicleSection, round_index: int, rng: SeededRandom) -> None:
    kind, node, key = instrument(weapon)
    damage = weapon.damage if weapon is not None else DamageType.BALLISTIC
    if target.shielded and damage in SHIELDED and rng.chance(fight.ctx.rules.engagement.shield_absorb_pct):
        fight.step(
            StepDraft(
                StepAction.FIRE,
                actor=shooter.vessel.id,
                target=target.vessel.id,
                round=round_index,
                instrument_kind=kind,
                instrument_node=node,
                instrument_key=key,
                locus_kind=StepLocus.VEHICLE_SECTION,
                locus_key=VehicleSection.WARD.value,
                locus_node=target.vessel.id,
                damage_type=damage,
                amount=1,
                unit=FactUnit.COUNT,
                outcome=StepOutcome.ABSORBED,
            )
        )
        return
    after = await strike_vessel(fight.ctx, target.vessel, target.row, section, 1)
    target.hits_taken += 1
    fight.step(
        StepDraft(
            StepAction.FIRE,
            actor=shooter.vessel.id,
            target=target.vessel.id,
            round=round_index,
            instrument_kind=kind,
            instrument_node=node,
            instrument_key=key,
            locus_kind=StepLocus.VEHICLE_SECTION,
            locus_key=section.value,
            locus_node=target.vessel.id,
            damage_type=damage,
            amount=1,
            unit=FactUnit.COUNT,
            outcome=section_outcome(after),
            record_table="vessel_sections",
            record_key=f"{target.vessel.id}:{section.value}",
        )
    )
    if after in FALLEN:
        await chain(fight, target, section, round_index)


def hull_hit(fight: Fight, shooter: Party, target: Party, weapon: Weapon | None, round_index: int) -> None:
    worn = fight.ctx.rules.vehicles.section_hit
    if "condition" not in target.row.locked:
        target.row.condition = clamp_int(target.row.condition - worn, 0, PERCENT)
    kind, node, key = instrument(weapon)
    fight.step(
        StepDraft(
            StepAction.FIRE,
            actor=shooter.vessel.id,
            target=target.vessel.id,
            round=round_index,
            instrument_kind=kind,
            instrument_node=node,
            instrument_key=key,
            damage_type=weapon.damage if weapon is not None else None,
            amount=worn,
            unit=FactUnit.PERCENT,
            outcome=StepOutcome.DAMAGED,
            record_table="vessel_profiles",
            record_key=str(target.vessel.id),
        )
    )


async def volley(fight: Fight, position: int, round_index: int, *, holds: bool) -> int:
    ctx = fight.ctx
    table, sail = ctx.rules.engagement, ctx.rules.age_of_sail
    shooter, target = fight.sides[position], fight.sides[1 - position]
    crews = await crews_of(ctx, shooter.vessel.id, shooter.row)
    keep(shooter.state, "rate_of_fire", rate_of_fire(ctx, shooter.row, crews))
    raking = False
    if fight.domain in SAILED:
        mine, theirs = speed_of(ctx, shooter.state), speed_of(ctx, target.state)
        level = await family_level(ctx.session, shooter.vessel.affiliated_entity_id, TechFamily.WARFARE)
        keep(
            shooter.state,
            "shot",
            modern_shot(broadside_of(shooter), broadside_of(target), level, target.carried)
            or shot_for(broadside_of(shooter), broadside_of(target), mine, theirs),
        )
        raking = target.state.point_of_sail is PointOfSail.IN_IRONS or mine - theirs >= RAKING_GAP
    base = (sail.base_hits + shooter.state.rate_of_fire // sail.rate_hits_per) * fight.weights[position] * SHOT_WEIGHT[shooter.state.shot] / PERCENT
    if raking:
        base = base * sail.raking_pct / PERCENT
        keep(target.state, "raked", target.state.raked + 1)
        fight.tally.raked += 1
    elif holds and fight.domain not in SAILED:
        base = base * table.position_hits_pct / PERCENT
    hits = max(1, round(base))
    rng = ctx.rng(f"broadside.{shooter.vessel.id}.{target.vessel.id}.{ctx.epoch}.{round_index}")
    weapons = [weapon for weapon in shooter.weapons if weapon.family not in RAMMING]
    total = sum(weapon.weight for weapon in weapons)
    flammable = stack_material(target.row.hull_material).family is MaterialFamily.ORGANIC
    landed = 0
    for _ in range(hits):
        weapon = pick_weapon(rng, weapons, total)
        pool = shot_sections(shooter, target, weapon, raking)
        if not pool:
            hull_hit(fight, shooter, target, weapon, round_index)
            landed += 1
            continue
        section = rng.pick(pool)
        await land(fight, shooter, target, weapon=weapon, section=section, round_index=round_index, rng=rng)
        landed += 1
        if weapon is None or weapon.family in CANNON_FAMILIES:
            await shot_effect(fight, shooter, target, section=section, flammable=flammable, round_index=round_index)
        if target.lost:
            break
    fight.tally.broadsides += 1
    fight.hits[target.vessel.id] = fight.hits.get(target.vessel.id, 0) + landed
    return landed


def pick_weapon(rng: SeededRandom, weapons: list[Weapon], total: float) -> Weapon | None:
    if not weapons or total <= 0:
        return None
    roll = rng.uniform(0, total)
    for weapon in weapons:
        roll -= weapon.weight
        if roll <= 0:
            return weapon
    return weapons[-1]


async def shot_effect(fight: Fight, shooter: Party, target: Party, *, section: VehicleSection, flammable: bool, round_index: int) -> None:
    sail = fight.ctx.rules.age_of_sail
    if shooter.state.shot is ShotKind.ROUND and section in HOLED_SECTIONS:
        keep(target.state, "leak", clamp_int(target.state.leak + sail.leak_per_hit, 0, PERCENT))
    elif shooter.state.shot is ShotKind.GRAPE and "crew" not in target.row.locked:
        target.row.crew = max(0, target.row.crew - max(1, target.row.crew * sail.grape_crew_pct // PERCENT))
    elif shooter.state.shot is ShotKind.FIRE:
        spread = sail.fire_spread_pct if flammable else PERCENT
        keep(target.state, "fire", clamp_int(target.state.fire + sail.fire_per_hit * spread // PERCENT, 0, PERCENT))
        fight.tally.fires += 1
        fight.step(
            StepDraft(StepAction.IGNITE, actor=shooter.vessel.id, target=target.vessel.id, round=round_index, states=((target.vessel.id, StepState.BURNING),))
        )


def broadside_of(side: Party) -> Broadside:
    return Broadside(side.vessel, side.row, side.state, side.crew_at_start, frozenset(weapon.family for weapon in side.weapons if weapon.family is not None))


async def opening(fight: Fight) -> None:
    for side in fight.sides:
        if VehicleSection.WARD in side.carried and not held(side.vessel.id):
            states = await vessel_sections(fight.ctx.session, side.vessel.id)
            ward = states.get(VehicleSection.WARD)
            if ward is None or ward.state not in DOWN:
                side.shielded = True
                fight.step(StepDraft(StepAction.RAISE_SHIELD, actor=side.vessel.id, round=0, states=((side.vessel.id, StepState.SHIELDED),)))
        bays = sum(weapon.count for weapon in side.weapons if weapon.mount is MountKind.BAY)
        if bays:
            fight.step(StepDraft(StepAction.LAUNCH_CRAFT, actor=side.vessel.id, round=0, amount=bays, unit=FactUnit.COUNT))
            position = fight.sides.index(side)
            fight.weights[position] *= 1 + bays * fight.ctx.rules.engagement.craft_hits_pct / PERCENT


async def manoeuvre(fight: Fight, round_index: int) -> int | None:
    readings = [await position_of(fight.ctx, side, fight.domain) for side in fight.sides]
    for side, reading in zip(fight.sides, readings, strict=True):
        fight.step(
            StepDraft(
                StepAction.MANOEUVRE, actor=side.vessel.id, round=round_index, amount=round(reading), unit=FactUnit.SPEED, locus_kind=locus_for(fight.domain)
            )
        )
    if abs(readings[0] - readings[1]) <= TINY:
        return None
    holder = 0 if readings[0] > readings[1] else 1
    fight.step(
        StepDraft(
            StepAction.TAKE_POSITION,
            actor=fight.sides[holder].vessel.id,
            target=fight.sides[1 - holder].vessel.id,
            round=round_index,
            locus_kind=locus_for(fight.domain),
            outcome=StepOutcome.SUCCESS,
        )
    )
    return holder


def locus_for(domain: VehicleDomain) -> StepLocus:
    return {
        VehicleDomain.LAND: StepLocus.REGION,
        VehicleDomain.WATER: StepLocus.SEA,
        VehicleDomain.UNDERWATER: StepLocus.SEA,
        VehicleDomain.AMPHIBIOUS: StepLocus.SEA,
        VehicleDomain.AIR: StepLocus.SKY,
        VehicleDomain.GAS_GIANT: StepLocus.SKY,
        VehicleDomain.SPACE: StepLocus.ORBIT,
        VehicleDomain.UNDERGROUND: StepLocus.REGION,
        VehicleDomain.PLANAR: StepLocus.REALM,
    }[domain]


async def ram(fight: Fight, position: int, round_index: int) -> None:
    shooter, target = fight.sides[position], fight.sides[1 - position]
    rams = [weapon for weapon in shooter.weapons if weapon.family in RAMMING or weapon.mount is MountKind.RAM]
    if not rams or held(target.vessel.id):
        return
    table = fight.ctx.rules.engagement
    weapon = rams[0]
    kind, node, key = instrument(weapon)
    rng = fight.ctx.rng(f"engagement.ram.{shooter.vessel.id}.{target.vessel.id}.{fight.ctx.epoch}")
    index = fight.step(
        StepDraft(
            StepAction.RAM,
            actor=shooter.vessel.id,
            target=target.vessel.id,
            round=round_index,
            instrument_kind=kind,
            instrument_node=node,
            instrument_key=key,
            amount=table.ram_hits,
            unit=FactUnit.COUNT,
            outcome=StepOutcome.SUCCESS,
        )
    )
    for _ in range(table.ram_hits):
        pool = reached(weapon.damage, weapon.family, target.carried)
        if not pool:
            break
        await land(fight, shooter, target, weapon=weapon, section=rng.pick(pool), round_index=round_index, rng=rng)
    if table.ram_recoil and VehicleSection.BOW in shooter.carried and not held(shooter.vessel.id):
        await strike_vessel(fight.ctx, shooter.vessel, shooter.row, VehicleSection.BOW, table.ram_recoil)
        fight.step(
            StepDraft(
                StepAction.RAM,
                actor=shooter.vessel.id,
                round=round_index,
                parent=index,
                locus_kind=StepLocus.VEHICLE_SECTION,
                locus_key=VehicleSection.BOW.value,
                locus_node=shooter.vessel.id,
                amount=table.ram_recoil,
                unit=FactUnit.COUNT,
                outcome=StepOutcome.DAMAGED,
            )
        )


async def damage_control(fight: Fight, side: Party, round_index: int) -> None:
    ctx = fight.ctx
    sail, table = ctx.rules.age_of_sail, ctx.rules.engagement
    if held(side.vessel.id):
        return
    crews = await crews_of(ctx, side.vessel.id, side.row)
    riggers = crews.get(CrewStation.RIGGERS)
    hands = riggers.count if riggers is not None else 0
    if side.state.leak >= table.jettison_leak and not side.jettisoned:
        side.jettisoned = True
        keep(side.state, "leak", clamp_int(side.state.leak - table.jettison_relief, 0, PERCENT))
        fight.step(StepDraft(StepAction.JETTISON, actor=side.vessel.id, round=round_index, amount=table.jettison_relief, unit=FactUnit.PERCENT))
    if side.state.leak > 0:
        pumped = min(side.state.leak, sail.pumping * (1 + hands // max(1, FRAMES[side.row.frame].crew // 4)))
        keep(side.state, "leak", clamp_int(side.state.leak - pumped, 0, PERCENT))
        fight.step(
            StepDraft(
                StepAction.PUMP,
                actor=side.vessel.id,
                round=round_index,
                amount=pumped,
                unit=FactUnit.PERCENT,
                states=((side.vessel.id, StepState.FLOODING),) if side.state.leak else (),
            )
        )
    if side.state.fire > 0:
        fought = min(side.state.fire, sail.fire_fought)
        keep(side.state, "fire", clamp_int(side.state.fire - fought, 0, PERCENT))
        fight.step(StepDraft(StepAction.EXTINGUISH, actor=side.vessel.id, round=round_index, amount=fought, unit=FactUnit.PERCENT))
    if hands > 0 and side.hits_taken > 0:
        mended = await mend_vessel_sections(ctx.session, side.vessel.id, sail.pumping)
        if mended:
            fight.step(StepDraft(StepAction.REPAIR_UNDERWAY, actor=side.vessel.id, round=round_index, amount=mended, unit=FactUnit.COUNT))


async def doomed(fight: Fight, side: Party, round_index: int) -> tuple[bool, bool]:
    ctx, sail = fight.ctx, fight.ctx.rules.age_of_sail
    if side.lost:
        return True, not side.crashed
    if side.state.leak >= sail.founder_leak and fight.domain in WATERBORNE:
        fight.tally.foundered += 1
        fight.step(StepDraft(StepAction.SINK, actor=side.vessel.id, round=round_index, outcome=StepOutcome.DESTROYED))
        return True, False
    if (
        side.state.magazine
        and side.state.fire >= sail.magazine_fire
        and ctx.rng(f"magazine.{side.vessel.id}.{ctx.epoch}.{round_index}").chance(sail.magazine_chance)
    ):
        keep(side.state, "magazine", False)
        fight.tally.explosions += 1
        fight.step(
            StepDraft(
                StepAction.EXPLODE,
                actor=side.vessel.id,
                round=round_index,
                locus_kind=StepLocus.VEHICLE_SECTION,
                locus_key=VehicleSection.MAGAZINE.value,
                locus_node=side.vessel.id,
                outcome=StepOutcome.DESTROYED,
            )
        )
        return True, True
    return False, False


def strikes(fight: Fight, side: Party) -> bool:
    sail = fight.ctx.rules.age_of_sail
    thinned = side.row.crew * PERCENT < side.crew_at_start * sail.strike_crew_pct
    return thinned or side.row.condition < sail.strike_condition or side.grounded


async def officer_of(ctx: TickContext, side: Party) -> EntityRow | None:
    return await living_entity(ctx.session, side.row.captain_entity_id) if side.row.captain_entity_id is not None else None


async def board(fight: Fight, attacker: int, round_index: int) -> bool:
    ctx, table = fight.ctx, fight.ctx.rules.engagement
    boarder, defender = fight.sides[attacker], fight.sides[1 - attacker]
    crews = await crews_of(ctx, boarder.vessel.id, boarder.row)
    theirs = await crews_of(ctx, defender.vessel.id, defender.row)
    marines = crews.get(CrewStation.MARINES)
    if marines is None or held(defender.vessel.id) or marines.count * PERCENT < defender.row.crew * table.board_marines_pct:
        return False
    index = fight.step(
        StepDraft(StepAction.BOARD, actor=boarder.vessel.id, target=defender.vessel.id, round=round_index, amount=marines.count, unit=FactUnit.PEOPLE)
    )
    guard = theirs.get(CrewStation.MARINES)
    attackers = marines.count
    defenders = max(guard.count if guard is not None else 0, defender.row.crew // 4)
    leader, foe = await officer_of(ctx, boarder), await officer_of(ctx, defender)
    if leader is not None and foe is not None:
        await officers(fight, leader, foe, index, round_index)
    for close in range(table.board_rounds):
        if attackers <= 0 or defenders <= 0:
            break
        attacker_loss = (
            max(1, defenders * table.board_loss_pct // PERCENT) if defenders > attackers // 2 else max(0, defenders * table.board_loss_pct // (2 * PERCENT))
        )
        defender_loss = max(1, attackers * table.board_loss_pct // PERCENT)
        attackers, defenders = max(0, attackers - attacker_loss), max(0, defenders - defender_loss)
        fight.step(
            StepDraft(
                StepAction.STRIKE,
                actor=boarder.vessel.id,
                target=defender.vessel.id,
                round=close + 1,
                parent=index,
                amount=defender_loss,
                unit=FactUnit.PEOPLE,
                outcome=StepOutcome.KILLED,
            )
        )
        fight.step(
            StepDraft(
                StepAction.STRIKE,
                actor=defender.vessel.id,
                target=boarder.vessel.id,
                round=close + 1,
                parent=index,
                amount=attacker_loss,
                unit=FactUnit.PEOPLE,
                outcome=StepOutcome.KILLED,
            )
        )
    if "count" not in marines.locked:
        marines.count = attackers
    if guard is not None and "count" not in guard.locked:
        guard.count = min(guard.count, defenders)
    taken = defenders <= 0 or attackers > defenders * 2
    if taken:
        fight.step(
            StepDraft(
                StepAction.YIELD,
                actor=defender.vessel.id,
                round=table.board_rounds,
                parent=index,
                outcome=StepOutcome.CAPTURED,
                states=((defender.vessel.id, StepState.CAPTURED),),
            )
        )
    else:
        fight.step(
            StepDraft(StepAction.REPEL, actor=defender.vessel.id, target=boarder.vessel.id, round=table.board_rounds, parent=index, outcome=StepOutcome.SUCCESS)
        )
    return taken


async def officers(fight: Fight, leader: EntityRow, foe: EntityRow, parent: int, round_index: int) -> None:
    ctx, table = fight.ctx, fight.ctx.rules.engagement
    rng = ctx.rng(f"engagement.officers.{leader.id}.{foe.id}.{ctx.epoch}")
    fight.step(StepDraft(StepAction.CLOSE, actor=leader.id, target=foe.id, round=round_index, parent=parent))
    striker, struck = (leader, foe) if rng.chance(50) else (foe, leader)
    parried = rng.chance(40)
    if parried:
        fight.step(StepDraft(StepAction.PARRY, actor=struck.id, target=striker.id, round=round_index, parent=parent, outcome=StepOutcome.PARRIED))
        return
    injury: str | None = None
    if not held(struck.id):
        harm = Harm(
            table.officer_wound, HarmCause.BATTLE, "struck down in a boarding", damage_type=DamageType.CUT, source_node_id=striker.id, killer_id=striker.id
        )
        wounding = await apply_hits(ctx, struck, harm, lethal=False)
        if wounding.injuries:
            injury = str(await stored_id(ctx.session, wounding.injuries[0]))
    fight.step(
        StepDraft(
            StepAction.STRIKE,
            actor=striker.id,
            target=struck.id,
            round=round_index,
            parent=parent,
            instrument_kind=InstrumentKind.BODY,
            damage_type=DamageType.CUT,
            amount=table.officer_wound,
            unit=FactUnit.HP,
            outcome=StepOutcome.WOUNDED if injury is not None else StepOutcome.GLANCED,
            record_table="injuries" if injury is not None else None,
            record_key=injury,
        )
    )


async def engage(
    ctx: TickContext, first: tuple[EntityRow, VesselProfileRow], second: tuple[EntityRow, VesselProfileRow], powers: tuple[float, float], tally: SailTally
) -> Engagement:
    sides = [await party(ctx, *first), await party(ctx, *second)]
    domain = domain_of(first[1])
    strongest = max(*powers, TINY)
    fight = Fight(ctx, domain, sides, [power / strongest for power in powers], tally)
    weaker = 0 if powers[0] < powers[1] else 1
    await opening(fight)
    rounds = ctx.rules.age_of_sail.rounds
    held_position: int | None = None
    for index in range(rounds):
        round_index = index + 1
        held_position = await manoeuvre(fight, round_index)
        if index == 0 and held_position is not None:
            await ram(fight, held_position, round_index)
        for position in (0, 1):
            if held(sides[1 - position].vessel.id) or sides[position].lost:
                continue
            await volley(fight, position, round_index, holds=held_position == position)
        lost: list[tuple[int, bool]] = []
        for position, side in enumerate(sides):
            await damage_control(fight, side, round_index)
            sunk, exploded = await doomed(fight, side, round_index)
            if sunk:
                lost.append((position, exploded))
        if lost:
            position, exploded = next((item for item in lost if item[0] == weaker), lost[0])
            crashed = sides[position].crashed
            end = StepOutcome.DESTROYED
            return Engagement(
                sides[1 - position].vessel,
                sides[position].vessel,
                domain,
                round_index,
                end,
                sunk=True,
                exploded=exploded,
                crashed=crashed,
                hits=fight.hits,
                steps=fight.steps,
            )
        broken = [position for position, side in enumerate(sides) if strikes(fight, side) and not held(side.vessel.id)]
        if broken:
            position = weaker if weaker in broken else broken[0]
            if await board(fight, 1 - position, round_index):
                return Engagement(
                    sides[1 - position].vessel,
                    sides[position].vessel,
                    domain,
                    round_index,
                    StepOutcome.CAPTURED,
                    struck=True,
                    captured=True,
                    hits=fight.hits,
                    steps=fight.steps,
                )
            keep(sides[position].state, "struck", True)
            tally.struck += 1
            fight.step(
                StepDraft(
                    StepAction.STRIKE_COLOURS,
                    actor=sides[position].vessel.id,
                    round=round_index,
                    outcome=StepOutcome.YIELDED,
                    states=((sides[position].vessel.id, StepState.YIELDED),),
                )
            )
            return Engagement(
                sides[1 - position].vessel, sides[position].vessel, domain, round_index, StepOutcome.YIELDED, struck=True, hits=fight.hits, steps=fight.steps
            )
    readings = [await position_of(ctx, side, domain) for side in sides]
    stronger = 1 - weaker
    if readings[weaker] * PERCENT >= readings[stronger] * ctx.rules.engagement.escape_position_pct and readings[weaker] > 0:
        fight.step(
            StepDraft(
                StepAction.ESCAPE,
                actor=sides[weaker].vessel.id,
                target=sides[stronger].vessel.id,
                round=rounds,
                locus_kind=locus_for(domain),
                outcome=StepOutcome.ESCAPED,
            )
        )
        return Engagement(sides[stronger].vessel, sides[weaker].vessel, domain, rounds, StepOutcome.ESCAPED, escaped=True, hits=fight.hits, steps=fight.steps)
    winner, loser = (sides[0], sides[1]) if powers[0] >= powers[1] else (sides[1], sides[0])
    return Engagement(winner.vessel, loser.vessel, domain, rounds, StepOutcome.DAMAGED, hits=fight.hits, steps=fight.steps)
