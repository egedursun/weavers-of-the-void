from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.sections import SECTION_STATES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.vehicles import DesignSectionRow, VehicleGroupRow, VehicleGroupSectionRow, VesselSectionRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import DesignComponentKind
from aerona.domain.enums.integrity import Criticality, SectionHazard, SectionState
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus, StepOutcome, StepState
from aerona.domain.enums.vehicles import VehicleSection
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import StepDraft

ORDER = (SectionState.SOUND, SectionState.DAMAGED, SectionState.DISABLED, SectionState.DESTROYED)
LOST_HAZARDS = frozenset({SectionHazard.EXPLOSION, SectionHazard.CRASH})
CHAIN_LIMIT = 6


@dataclass
class StrikeResult:
    lost: int = 0
    crew_lost_pct: int = 0
    steps: list[StepDraft] = field(default_factory=list)
    hazards: list[SectionHazard] = field(default_factory=list)


HAZARD_STEPS = {
    SectionHazard.FIRE: (StepAction.IGNITE, StepState.BURNING),
    SectionHazard.EXPLOSION: (StepAction.EXPLODE, StepState.DISABLED),
    SectionHazard.FLOODING: (StepAction.FLOOD, StepState.FLOODING),
    SectionHazard.BREACH: (StepAction.VENT, StepState.BREACHED),
    SectionHazard.CRASH: (StepAction.CRASH, StepState.GROUNDED),
    SectionHazard.PANIC: (StepAction.ROUT, StepState.ROUTED),
    SectionHazard.COLLAPSE: (StepAction.COLLAPSE, StepState.DISABLED),
}
STATE_OUTCOMES = {
    SectionState.SOUND: StepOutcome.GLANCED,
    SectionState.DAMAGED: StepOutcome.DAMAGED,
    SectionState.DISABLED: StepOutcome.DISABLED,
    SectionState.DESTROYED: StepOutcome.DESTROYED,
}


def step(state: SectionState) -> SectionState:
    return ORDER[min(len(ORDER) - 1, ORDER.index(state) + 1)]


async def design_sections(session: AsyncSession, design_id: int) -> dict[VehicleSection, DesignSectionRow]:
    rows = await session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id == design_id))
    return {row.section: row for row in rows}


async def group_sections(session: AsyncSession, group_id: int) -> dict[VehicleSection, VehicleGroupSectionRow]:
    rows = await session.scalars(select(VehicleGroupSectionRow).where(VehicleGroupSectionRow.group_id == group_id))
    return {row.section: row for row in rows}


async def vessel_sections(session: AsyncSession, vessel_id: int) -> dict[VehicleSection, VesselSectionRow]:
    rows = await session.scalars(select(VesselSectionRow).where(VesselSectionRow.vessel_entity_id == vessel_id))
    return {row.section: row for row in rows}


def pick_section(rng: SeededRandom, sections: dict[VehicleSection, DesignSectionRow]) -> DesignSectionRow | None:
    pool = [row for row in sorted(sections.values(), key=lambda item: item.section.value) if row.exposure > 0]
    if not pool:
        return None
    roll = rng.below(sum(row.exposure for row in pool))
    for row in pool:
        roll -= row.exposure
        if roll < 0:
            return row
    return pool[-1]


def deflected(ctx: TickContext, rng: SeededRandom, section: DesignSectionRow) -> bool:
    return rng.chance(round_half_up(section.armour * PERCENT / max(1, ctx.rules.vehicles.deflect_pct)))


def tier(row: VehicleGroupSectionRow, state: SectionState) -> int:
    column = SECTION_STATES[state].tier
    return int(getattr(row, column)) if column is not None else 0


def shift_tier(row: VehicleGroupSectionRow, state: SectionState, amount: int) -> None:
    column = SECTION_STATES[state].tier
    if column is not None:
        setattr(row, column, max(0, int(getattr(row, column)) + amount))


def struck_state(rng: SeededRandom, group: VehicleGroupRow, row: VehicleGroupSectionRow) -> SectionState:
    sound = max(0, group.count - row.damaged - row.disabled - row.destroyed)
    pool = [(SectionState.SOUND, sound), (SectionState.DAMAGED, row.damaged), (SectionState.DISABLED, row.disabled)]
    weight = sum(amount for _, amount in pool)
    if weight <= 0:
        return SectionState.DESTROYED
    roll = rng.below(weight)
    for state, amount in pool:
        roll -= amount
        if roll < 0:
            return state
    return SectionState.SOUND


async def lose_vehicle(session: AsyncSession, group: VehicleGroupRow, result: StrikeResult) -> None:
    if group.count <= 0:
        return
    group.count -= 1
    group.crewed = min(group.crewed, group.count)
    result.lost += 1
    result.steps.append(
        StepDraft(
            StepAction.BREAK,
            target=group.holder_node_id,
            amount=1,
            unit=FactUnit.COUNT,
            outcome=StepOutcome.DESTROYED,
            record_table="vehicle_groups",
            record_key=str(group.id),
        )
    )
    for row in (await group_sections(session, group.id)).values():
        overflow = row.damaged + row.disabled + row.destroyed - group.count
        for state in (SectionState.DESTROYED, SectionState.DISABLED, SectionState.DAMAGED):
            if overflow <= 0:
                break
            cut = min(overflow, tier(row, state))
            shift_tier(row, state, -cut)
            overflow -= cut


@dataclass
class Strike:
    group: VehicleGroupRow
    sections: dict[VehicleSection, DesignSectionRow]
    states: dict[VehicleSection, VehicleGroupSectionRow]
    rng: SeededRandom
    result: StrikeResult
    queue: list[tuple[DesignSectionRow | None, int]] = field(default_factory=list)
    chained: int = 0


def state_row(ctx: TickContext, strike: Strike, section: DesignSectionRow) -> VehicleGroupSectionRow:
    row = strike.states.get(section.section)
    if row is None:
        row = VehicleGroupSectionRow(group_id=strike.group.id, section=section.section, damaged=0, disabled=0, destroyed=0, locked=[])
        ctx.session.add(row)
        strike.states[section.section] = row
    return row


def chain(ctx: TickContext, strike: Strike, section: DesignSectionRow, after: SectionState) -> bool:
    strike.result.hazards.append(section.hazard)
    action, state = HAZARD_STEPS.get(section.hazard, (StepAction.BREAK, StepState.DISABLED))
    holder = strike.group.holder_node_id
    strike.result.steps.append(
        StepDraft(
            action,
            target=holder,
            locus_kind=StepLocus.VEHICLE_SECTION,
            locus_key=section.section.value,
            record_table="vehicle_groups",
            record_key=str(strike.group.id),
            states=((holder, state),) if holder is not None else (),
        )
    )
    spread, fatal = hazard(ctx, strike.rng, section, after)
    if section.hazard is SectionHazard.BREACH:
        strike.result.crew_lost_pct = min(PERCENT, strike.result.crew_lost_pct + ctx.rules.vehicles.breach_crew_pct)
    for neighbour in section.neighbours if spread > 0 and strike.chained < CHAIN_LIMIT else ():
        found = strike.sections.get(VehicleSection(neighbour))
        if found is not None:
            strike.queue.append((found, spread))
            strike.chained += 1
    return fatal


async def land_hit(ctx: TickContext, strike: Strike, section: DesignSectionRow) -> None:
    row = state_row(ctx, strike, section)
    if set(row.locked or []) & {"damaged", "disabled", "destroyed"}:
        return
    before = struck_state(strike.rng, strike.group, row)
    after = step(before)
    shift_tier(row, before, -1)
    shift_tier(row, after, 1)
    strike.result.steps.append(
        StepDraft(
            StepAction.FIRE,
            target=strike.group.holder_node_id,
            locus_kind=StepLocus.VEHICLE_SECTION,
            locus_key=section.section.value,
            amount=1,
            unit=FactUnit.COUNT,
            outcome=STATE_OUTCOMES[after],
            record_table="vehicle_group_sections",
            record_key=f"{strike.group.id}:{section.section.value}",
        )
    )
    fatal = after is SectionState.DESTROYED and section.criticality is Criticality.CRITICAL
    if after in {SectionState.DISABLED, SectionState.DESTROYED} and section.hazard is not SectionHazard.NONE:
        fatal = chain(ctx, strike, section, after) or fatal
    if fatal:
        shift_tier(row, SectionState.DESTROYED, -1)
        await lose_vehicle(ctx.session, strike.group, strike.result)


async def strike_group(ctx: TickContext, group: VehicleGroupRow, hits: int, slot: str) -> StrikeResult:
    result = StrikeResult()
    if hits <= 0 or group.count <= 0 or held(group.holder_node_id) or "count" in (group.locked or []):
        return result
    strike = Strike(
        group=group,
        sections=await design_sections(ctx.session, group.design_id),
        states=await group_sections(ctx.session, group.id),
        rng=ctx.rng(f"vehicle_strike.{group.id}.{slot}.{ctx.epoch}"),
        result=result,
        queue=[(None, hits)],
    )
    while strike.queue and group.count > 0:
        target, amount = strike.queue.pop(0)
        for _ in range(min(amount, group.count * 3)):
            section = target or pick_section(strike.rng, strike.sections)
            if section is None or group.count <= 0:
                break
            if target is None and deflected(ctx, strike.rng, section):
                continue
            await land_hit(ctx, strike, section)
    return result


def hazard(ctx: TickContext, rng: SeededRandom, section: DesignSectionRow, after: SectionState) -> tuple[int, bool]:
    table = ctx.rules.vehicles
    gone = after is SectionState.DESTROYED
    outcomes = {
        SectionHazard.FIRE: (1 if rng.chance(table.fire_spread_pct) else 0, False),
        SectionHazard.EXPLOSION: (table.explosion_hits if gone else 0, gone),
        SectionHazard.FLOODING: (1 if rng.chance(table.flood_spread_pct) else 0, False),
        SectionHazard.BREACH: (1, False),
        SectionHazard.CRASH: (0, gone or rng.chance(table.crash_pct)),
        SectionHazard.PANIC: (0, rng.chance(table.panic_pct)),
    }
    return outcomes.get(section.hazard, (0, False))


async def function_share(session: AsyncSession, group: VehicleGroupRow, function: DesignComponentKind) -> float:
    if group.count <= 0:
        return 0.0
    sections = [row for row in (await design_sections(session, group.design_id)).values() if row.function is function]
    if not sections:
        return 1.0
    states = await group_sections(session, group.id)
    shares = []
    for section in sections:
        row = states.get(section.section)
        if row is None:
            shares.append(1.0)
            continue
        down = row.disabled + row.destroyed if section.criticality is not Criticality.MINOR else (row.disabled + row.destroyed) / 2
        shares.append(max(0.0, 1 - (down + row.damaged / 4) / group.count))
    return sum(shares) / len(shares)


async def strike_vessel(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, section: VehicleSection, hits: int) -> SectionState:
    states = await vessel_sections(ctx.session, vessel.id)
    current = states.get(section)
    if held(vessel.id) or hits <= 0:
        return current.state if current is not None else SectionState.SOUND
    if current is None:
        current = VesselSectionRow(vessel_entity_id=vessel.id, section=section, state=SectionState.SOUND, condition=PERCENT, locked=[])
        ctx.session.add(current)
    if set(current.locked or []) & {"state", "condition"}:
        return current.state
    for _ in range(hits):
        current.condition = clamp_int(current.condition - ctx.rules.vehicles.section_hit, 0, PERCENT)
        current.state = step(current.state)
    designed = await design_sections(ctx.session, row.design_id) if row.design_id is not None else {}
    spec = designed.get(section)
    if spec is not None and "condition" not in row.locked:
        row.condition = clamp_int(row.condition - round_half_up(spec.share * hits * ctx.rules.vehicles.section_hit / PERCENT), 0, PERCENT)
        if current.state is SectionState.DESTROYED and (spec.criticality is Criticality.CRITICAL or spec.hazard in LOST_HAZARDS):
            row.condition = 0
        elif current.state in {SectionState.DISABLED, SectionState.DESTROYED} and spec.criticality is Criticality.MAJOR and "status" not in row.locked:
            row.status = VesselStatus.DAMAGED
    return current.state


async def mend_vessel_sections(session: AsyncSession, vessel_id: int, amount: int) -> int:
    mended = 0
    for row in (await vessel_sections(session, vessel_id)).values():
        if set(row.locked or []) & {"state", "condition"} or row.state is SectionState.SOUND:
            continue
        row.condition = clamp_int(row.condition + amount, 0, PERCENT)
        if row.state is not SectionState.DESTROYED and row.condition >= PERCENT // 2:
            row.state = SectionState.SOUND if row.condition >= PERCENT * 3 // 4 else SectionState.DAMAGED
        mended += 1
    return mended


async def batter_vessel(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, hits: int, slot: str) -> list[tuple[DesignSectionRow, SectionState]]:
    if row.design_id is None or hits <= 0 or held(vessel.id):
        return []
    sections = await design_sections(ctx.session, row.design_id)
    rng = ctx.rng(f"vessel_strike.{vessel.id}.{slot}.{ctx.epoch}")
    found = []
    for _ in range(hits):
        section = pick_section(rng, sections)
        if section is None:
            break
        if deflected(ctx, rng, section):
            continue
        found.append((section, await strike_vessel(ctx, vessel, row, section.section, 1)))
    return found
