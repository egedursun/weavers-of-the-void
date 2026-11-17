from dataclasses import replace
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.units import UnitSpec
from aerona.catalog.vehicles import FRAMES, FrameSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.vehicles import VehicleGroupRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import CivilizationTier
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.vehicles import VehicleDomain, VehicleFamily, VehicleFrame, VehicleSize, VehicleStatus
from aerona.engine.collective.designs import draw_design
from aerona.engine.context import TickContext
from aerona.engine.cosmos.tiers import tier_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import StepDraft
from aerona.engine.vehicles.groups import GroupReading, groups_of, move_vehicles, read, salvage, take_prizes
from aerona.engine.vehicles.sections import strike_group
from aerona.rules.registry import Rules

D = VehicleDomain
Y = VehicleFamily
SIEGE = frozenset({Y.RAM, Y.TOWER, Y.THROWER})
LAND_DOMAINS = frozenset({D.LAND, D.UNDERGROUND, D.AMPHIBIOUS})
ROLE_DOMAINS: MappingProxyType[UnitKind, frozenset[VehicleDomain]] = MappingProxyType(
    {
        UnitKind.NAVAL_CREW: frozenset({D.WATER, D.UNDERWATER, D.AMPHIBIOUS}),
        UnitKind.SKY_CREW: frozenset({D.AIR}),
        UnitKind.VOID_CREW: frozenset({D.SPACE, D.GAS_GIANT, D.PLANAR}),
        UnitKind.VEHICLE_CREW: LAND_DOMAINS,
        UnitKind.SIEGE_CREW: frozenset({D.LAND}),
        UnitKind.ARTILLERY_CREW: frozenset({D.LAND}),
        UnitKind.CHARIOTS: frozenset({D.LAND}),
        UnitKind.MECHANISED_INFANTRY: LAND_DOMAINS,
        UnitKind.PILOTS: frozenset({D.AIR}),
        UnitKind.DROP_TROOPS: frozenset({D.SPACE, D.AIR}),
    }
)
ROLE_FAMILIES: MappingProxyType[UnitKind, frozenset[VehicleFamily]] = MappingProxyType(
    {
        UnitKind.NAVAL_CREW: frozenset({Y.BOAT, Y.GALLEY, Y.SAILING_SHIP, Y.STEAM_SHIP, Y.SUBMARINE, Y.LIVING}),
        UnitKind.SKY_CREW: frozenset({Y.BALLOON, Y.AIRSHIP, Y.AIRCRAFT, Y.ROTORCRAFT, Y.CONSTRUCT}),
        UnitKind.VOID_CREW: frozenset({Y.SPACECRAFT, Y.AIRSHIP}),
        UnitKind.VEHICLE_CREW: frozenset({Y.WAGON, Y.MOTOR, Y.TRACKED, Y.WALKER, Y.CONSTRUCT, Y.MOUNT, Y.RAIL, Y.BURROWER}),
        UnitKind.SIEGE_CREW: SIEGE,
        UnitKind.ARTILLERY_CREW: frozenset({Y.GUN}),
        UnitKind.CHARIOTS: frozenset({Y.CHARIOT}),
        UnitKind.MECHANISED_INFANTRY: frozenset({Y.MOTOR, Y.TRACKED}),
        UnitKind.PILOTS: frozenset({Y.AIRCRAFT, Y.ROTORCRAFT}),
        UnitKind.DROP_TROOPS: frozenset({Y.SPACECRAFT, Y.ROTORCRAFT}),
    }
)
CREW_ROLES = frozenset(ROLE_DOMAINS)
NAVAL = ROLE_DOMAINS[UnitKind.NAVAL_CREW]
AIRBORNE = ROLE_DOMAINS[UnitKind.SKY_CREW]


UNRIDDEN = frozenset({VehicleFrame.RIDING_MOUNT, VehicleFrame.PACK_MOUNT})


def fits(role: UnitKind, spec: FrameSpec) -> bool:
    if role is UnitKind.VEHICLE_CREW and spec.frame in UNRIDDEN:
        return False
    return spec.domain in ROLE_DOMAINS.get(role, frozenset()) and spec.family in ROLE_FAMILIES.get(role, frozenset())


def fighting_worth(spec: FrameSpec) -> int:
    return spec.structure + spec.armour + spec.slots * 20 + spec.speed // 2 + spec.troops // 4


SIZE_ORDER = tuple(VehicleSize)


def largest_size(rules: Rules, tier: int) -> int:
    caps = rules.vehicles
    return (caps.tribe_size, caps.city_state_size, caps.realm_size, caps.empire_size, caps.interstellar_size, caps.cosmic_size)[
        min(max(tier, CivilizationTier.TRIBE), CivilizationTier.COSMIC_POWER)
    ]


def least_tier(rules: Rules, size: VehicleSize) -> int | None:
    need = SIZE_ORDER.index(size)
    return next((int(tier) for tier in CivilizationTier if largest_size(rules, tier) >= need), None)


def opened(spec: FrameSpec, knowledge: KnowledgeMap, owner: EntityRow, rules: Rules) -> bool:
    if spec.branch is not None and knowledge.level(owner.id, spec.branch) < spec.level:
        return False
    return SIZE_ORDER.index(spec.size) <= largest_size(rules, tier_of(owner))


def best_frame(knowledge: KnowledgeMap, owner: EntityRow, role: UnitKind, rules: Rules) -> VehicleFrame | None:
    found = [spec for spec in FRAMES.values() if fits(role, spec) and opened(spec, knowledge, owner, rules)]
    return max(found, key=lambda spec: (fighting_worth(spec), spec.frame.value)).frame if found else None


async def role_design(ctx: TickContext, owner: EntityRow, role: UnitKind, knowledge: KnowledgeMap) -> DesignRow | None:
    statement = select(DesignRow).where(DesignRow.owner_entity_id == owner.id, DesignRow.obsolete.is_(False), DesignRow.frame.is_not(None))
    for design in await ctx.session.scalars(statement.order_by(DesignRow.epoch.desc(), DesignRow.id.desc())):
        if design.frame is not None and fits(role, FRAMES[design.frame]):
            return design
    frame = best_frame(knowledge, owner, role, ctx.rules)
    if frame is None or held(owner.id):
        return None
    return await draw_design(ctx, owner, frame, knowledge=knowledge)


async def readings(session: AsyncSession, holder_id: int) -> list[GroupReading]:
    found = []
    for group in await groups_of(session, holder_id):
        reading = await read(session, group)
        if reading is not None:
            found.append(reading)
    return found


def serving(reading: GroupReading, role: UnitKind) -> bool:
    return reading.design.frame is not None and fits(role, FRAMES[reading.design.frame])


async def outfit_army(ctx: TickContext, army: EntityRow, owner: EntityRow, rows: list[ArmyUnitRow], knowledge: KnowledgeMap) -> int:
    if held(army.id) or held(owner.id):
        return 0
    moved = 0
    for stack in rows:
        if stack.kind not in CREW_ROLES or stack.count <= 0:
            continue
        design = await role_design(ctx, owner, stack.kind, knowledge)
        if design is None:
            continue
        crew = max(1, design.crew)
        need = -(-stack.count // crew)
        have = sum(reading.group.count for reading in await readings(ctx.session, army.id) if serving(reading, stack.kind))
        for park in await groups_of(ctx.session, owner.id):
            if have >= need:
                break
            park_design = await ctx.session.get(DesignRow, park.design_id)
            if park_design is None or park_design.frame is None or not fits(stack.kind, FRAMES[park_design.frame]):
                continue
            got = await move_vehicles(ctx.session, park, army.id, need - have, epoch=ctx.epoch)
            have += got
            moved += got
        for reading in await readings(ctx.session, army.id):
            if serving(reading, stack.kind) and "crewed" not in (reading.group.locked or []):
                reading.group.crewed = min(reading.group.count, stack.count // max(1, reading.design.crew))
    return moved


async def army_pace(session: AsyncSession, army_id: int, domains: frozenset[VehicleDomain] = LAND_DOMAINS) -> int | None:
    paces = [reading.pace for reading in await readings(session, army_id) if reading.design.domain in domains]
    return min(paces) if paces else None


async def carried_troops(session: AsyncSession, army_id: int, domains: frozenset[VehicleDomain]) -> int:
    return sum(reading.troops for reading in await readings(session, army_id) if reading.design.domain in domains)


async def crew_specs(session: AsyncSession, rows: list[ArmyUnitRow], specs: dict[int, UnitSpec]) -> dict[int, UnitSpec]:
    if not any(row.kind in CREW_ROLES for row in rows):
        return {}
    army_ids = {row.army_entity_id for row in rows}
    groups: list[GroupReading] = []
    for army_id in sorted(army_ids):
        groups.extend(await readings(session, army_id))
    found: dict[int, UnitSpec] = {}
    for row in rows:
        if row.kind not in CREW_ROLES or row.count <= 0 or row.id not in specs:
            continue
        mine = [reading for reading in groups if reading.group.holder_node_id == row.army_entity_id and serving(reading, row.kind)]
        if not mine:
            continue
        spec = specs[row.id]
        fire = sum(reading.firepower for reading in mine) / max(1, row.count)
        armour = max(reading.armour for reading in mine)
        bulk = sum(reading.design.structure * reading.group.count for reading in mine) / max(1, row.count)
        found[row.id] = replace(
            spec,
            missile=clamp_int(spec.missile + round_half_up(fire), 0, PERCENT),
            defence=clamp_int(spec.defence + armour // 2, 0, PERCENT),
            mass=spec.mass + round_half_up(bulk),
            speed=min(spec.speed, *(reading.pace for reading in mine)) if any(reading.pace for reading in mine) else spec.speed,
            flying=spec.flying or any(reading.design.domain in AIRBORNE for reading in mine),
        )
    return found


async def batter_groups(
    ctx: TickContext, army_id: int, share: float, slot: str, domains: frozenset[VehicleDomain] | None = None
) -> tuple[int, list[VehicleGroupRow], list[StepDraft]]:
    lost = 0
    struck: list[VehicleGroupRow] = []
    steps: list[StepDraft] = []
    for reading in await readings(ctx.session, army_id):
        if domains is not None and reading.design.domain not in domains:
            continue
        hits = round_half_up(reading.group.count * share * ctx.rules.vehicles.battle_hits_pct / PERCENT)
        if hits <= 0 and share > 0:
            hits = 1
        result = await strike_group(ctx, reading.group, hits, slot)
        lost += result.lost
        steps.extend(result.steps)
        if reading.group.status is not VehicleStatus.WRECKED and "status" not in (reading.group.locked or []):
            reading.group.status = VehicleStatus.ENGAGED
        struck.append(reading.group)
    return lost, struck, steps


async def after_battle(
    ctx: TickContext, loser_ids: list[int], winner_ids: list[int], shares: tuple[float, float], victor_id: int | None
) -> tuple[dict[str, int], list[StepDraft]]:
    loser_share, winner_share = shares
    found = {"vehicles_lost": 0, "salvaged": 0, "prizes": 0}
    steps: list[StepDraft] = []
    for army_id in loser_ids:
        lost, struck, landed = await batter_groups(ctx, army_id, loser_share, f"battle.{army_id}")
        steps.extend(landed)
        found["vehicles_lost"] += lost
        for group in struck:
            found["salvaged"] += await salvage(ctx, group, lost, victor_id)
            found["prizes"] += await take_prizes(ctx, group, victor_id)
    for army_id in winner_ids:
        lost, _, landed = await batter_groups(ctx, army_id, winner_share, f"battle.{army_id}")
        steps.extend(landed)
        found["vehicles_lost"] += lost
    return found, steps


async def afloat(session: AsyncSession, army_id: int) -> bool:
    return any(reading.design.domain in NAVAL for reading in await readings(session, army_id))


async def siege_power(session: AsyncSession, army_id: int) -> float:
    fire = sum(reading.firepower for reading in await readings(session, army_id) if reading.design.family in SIEGE or reading.design.family is Y.GUN)
    return 1 + fire / (PERCENT * 2)


async def pace_pct(session: AsyncSession, rules: Rules, army_id: int, soldiers: int) -> int:
    land = LAND_DOMAINS
    pace = await army_pace(session, army_id, land)
    if pace is None:
        return PERCENT
    ratio = round_half_up(pace * PERCENT / max(1, rules.vehicles.walk_pace))
    riding = await carried_troops(session, army_id, land) >= soldiers > 0
    return clamp_int(ratio if riding else min(PERCENT, ratio), PERCENT // 4, PERCENT * 2)


async def land_cargo(session: AsyncSession, holder_id: int) -> int:
    return sum(reading.cargo for reading in await readings(session, holder_id) if reading.design.domain in LAND_DOMAINS)


async def borne_baggage(session: AsyncSession, rules: Rules, army_id: int) -> int:
    return await land_cargo(session, army_id) // max(1, rules.vehicles.cargo_per_baggage)
