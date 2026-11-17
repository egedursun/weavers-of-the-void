from dataclasses import dataclass, field
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.sections import SECTION_STATES
from aerona.catalog.structure_sections import LAYOUTS, PartSpec
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.integrity import StructureDesignSectionRow, StructureSectionRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.integrity import Criticality, HarmForce, SectionHazard, SectionState
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import SectionRole, StructureSection
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

X = StructureSection
U = SectionRole
F = HarmForce
FLAMMABILITY: MappingProxyType[MaterialFamily, int] = total(
    MaterialFamily,
    {MaterialFamily.ORGANIC: 70, MaterialFamily.STONE: 10, MaterialFamily.METAL: 5, MaterialFamily.PRECIOUS: 5, MaterialFamily.EXOTIC: 30},
)
TALL = frozenset({X.TOWERS, X.SPIRE, X.DOME, X.UPPER_FLOORS, X.ROOF, X.KEEP, X.BEACON, X.SPINE})
FORCE_ROLES: MappingProxyType[HarmForce, MappingProxyType[SectionRole, int]] = total(
    HarmForce,
    {
        F.SIEGE: MappingProxyType({U.DEFENCE: 300, U.ENTRY: 300, U.SUPPORT: 50}),
        F.QUAKE: MappingProxyType({U.SUPPORT: 300}),
        F.FIRE: MappingProxyType({U.STORAGE: 200, U.SHELTER: 150, U.PRODUCTION: 150, U.KNOWLEDGE: 150}),
        F.FLOOD: MappingProxyType({U.SUPPORT: 200, U.WATER: 250, U.STORAGE: 150}),
        F.STORM: MappingProxyType({U.SHELTER: 200, U.DISPLAY: 150}),
        F.WAR: MappingProxyType({U.DEFENCE: 200, U.ENTRY: 200, U.STORAGE: 150, U.COMMAND: 150}),
        F.DECAY: MappingProxyType({}),
        F.DIVINE: MappingProxyType({U.WORSHIP: 200, U.DISPLAY: 150}),
        F.SABOTAGE: MappingProxyType({U.STORAGE: 200, U.SUPPORT: 150, U.POWER: 200, U.WATER: 150}),
        F.IMPACT: MappingProxyType({U.SUPPORT: 200, U.SHELTER: 150}),
    },
)
CHAIN_LIMIT = 8
EPSILON = 0.01


@dataclass
class StructureStrike:
    disabled: list[StructureSection] = field(default_factory=list)
    destroyed: list[StructureSection] = field(default_factory=list)
    collapsed: bool = False
    fire_spread: int = 0


def state_for(rules: Rules, condition: int) -> SectionState:
    table = rules.integrity
    if condition <= 0:
        return SectionState.DESTROYED
    if condition < table.disabled_at:
        return SectionState.DISABLED
    if condition < table.damaged_at:
        return SectionState.DAMAGED
    return SectionState.SOUND


async def sections_of(session: AsyncSession, structure_id: int) -> list[StructureSectionRow]:
    statement = select(StructureSectionRow).where(StructureSectionRow.structure_entity_id == structure_id)
    return list(await session.scalars(statement.order_by(StructureSectionRow.section)))


async def layout_for(
    session: AsyncSession, profile: StructureProfileRow
) -> tuple[list[PartSpec], dict[StructureSection, StructureDesignSectionRow], StructureDesignRow | None]:
    design = await session.get(StructureDesignRow, profile.design_id) if profile.design_id is not None else None
    overrides: dict[StructureSection, StructureDesignSectionRow] = {}
    if design is not None:
        rows = await session.scalars(select(StructureDesignSectionRow).where(StructureDesignSectionRow.design_id == design.id))
        overrides = {row.section: row for row in rows}
    return list(LAYOUTS[profile.kind]), overrides, design


async def flammability_of(session: AsyncSession, world_id: int | None, material: MaterialKind | None) -> int:
    if material is None:
        return FLAMMABILITY[MaterialFamily.STONE]
    props = (await MaterialBook.load(session)).props(world_id, material)
    return FLAMMABILITY[props.family] if props is not None else FLAMMABILITY[MaterialFamily.STONE]


async def ensure_sections(session: AsyncSession, work: EntityRow, profile: StructureProfileRow) -> list[StructureSectionRow]:
    found = await sections_of(session, work.id)
    if found:
        return found
    parts, overrides, design = await layout_for(session, profile)
    base = design.material if design is not None else None
    for part in parts:
        override = overrides.get(part.section)
        material = override.material if override is not None and override.material is not None else base
        row = StructureSectionRow(
            structure_entity_id=work.id,
            section=part.section,
            role=part.role,
            criticality=override.criticality if override is not None else part.criticality,
            share=override.share if override is not None else part.share,
            exposure=part.exposure,
            hazard=part.hazard,
            neighbours=[item.value for item in part.neighbours],
            condition=profile.condition,
            state=SectionState.SOUND,
            material=material,
            flammability=await flammability_of(session, work.world_id, material),
            locked=[],
        )
        session.add(row)
        found.append(row)
    for section, override in overrides.items():
        if section not in {part.section for part in parts}:
            row = StructureSectionRow(
                structure_entity_id=work.id,
                section=section,
                role=U.SHELTER,
                criticality=override.criticality,
                share=override.share,
                exposure=override.share,
                hazard=SectionHazard.NONE,
                neighbours=[],
                condition=profile.condition,
                state=SectionState.SOUND,
                material=override.material or base,
                flammability=await flammability_of(session, work.world_id, override.material or base),
                locked=[],
            )
            session.add(row)
            found.append(row)
    await session.flush()
    return found


def weight(force: HarmForce, row: StructureSectionRow) -> int:
    lift = FORCE_ROLES[force].get(row.role, PERCENT)
    if force is F.QUAKE and row.section in TALL:
        lift += PERCENT
    if force is F.FIRE:
        lift = lift * max(1, row.flammability) // (PERCENT // 2)
    return max(1, row.exposure * lift // PERCENT)


def overall(rows: list[StructureSectionRow]) -> int:
    shares = sum(row.share for row in rows)
    return round_half_up(sum(row.condition * row.share for row in rows) / shares) if shares else PERCENT


def broken(row: StructureSectionRow) -> bool:
    return row.state is SectionState.DESTROYED and row.criticality is Criticality.CRITICAL


def wound(rules: Rules, row: StructureSectionRow, loss: float, strike: StructureStrike) -> bool:
    if set(row.locked or []) & {"condition", "state"} or loss <= 0:
        return False
    before = row.state
    row.condition = clamp_int(row.condition - loss, 0, PERCENT)
    row.state = state_for(rules, row.condition)
    if row.state is before:
        return False
    if row.state is SectionState.DESTROYED:
        strike.destroyed.append(row.section)
    elif row.state is SectionState.DISABLED:
        strike.disabled.append(row.section)
    return True


def frozen(row: StructureSectionRow) -> bool:
    return bool(set(row.locked or []) & {"condition", "state"})


def spread_loss(rows: list[StructureSectionRow], weights: dict[StructureSection, int], loss: float) -> dict[StructureSection, float]:
    goal = loss * (sum(row.share for row in rows) or 1)
    amounts: dict[StructureSection, float] = {}
    open_rows = [row for row in rows if row.condition > 0 and row.share > 0 and not frozen(row)]
    while goal > EPSILON and open_rows:
        mass = sum(row.share * weights[row.section] for row in open_rows)
        if mass <= 0:
            break
        scale = goal / mass
        still: list[StructureSectionRow] = []
        for row in open_rows:
            room = row.condition - amounts.get(row.section, 0.0)
            want = scale * weights[row.section]
            taken = min(room, want)
            amounts[row.section] = amounts.get(row.section, 0.0) + taken
            goal -= taken * row.share
            if taken >= want:
                still.append(row)
        open_rows = still
    return amounts


def strike_rows(ctx: TickContext, rows: list[StructureSectionRow], loss: float, force: HarmForce, *, even: bool = False) -> StructureStrike:
    table = ctx.rules.integrity
    strike = StructureStrike()
    if not rows or loss <= 0:
        return strike
    weights = {row.section: 1 if even else weight(force, row) for row in rows}
    by_section = {row.section: row for row in rows}
    amounts = {row.section: float(loss) for row in rows} if even else spread_loss(rows, weights, loss)
    queue: list[tuple[StructureSectionRow, float]] = [(row, amounts.get(row.section, 0.0)) for row in rows]
    chained = 0
    while queue:
        row, amount = queue.pop(0)
        if not wound(ctx.rules, row, amount, strike):
            continue
        if chained >= CHAIN_LIMIT:
            continue
        for name in row.neighbours:
            neighbour = by_section.get(StructureSection(name))
            if neighbour is None or neighbour.state is SectionState.DESTROYED:
                continue
            if (force is F.FIRE or row.hazard is SectionHazard.FIRE) and row.state in {SectionState.DISABLED, SectionState.DESTROYED}:
                spread = amount * neighbour.flammability / PERCENT * table.fire_spread_pct / PERCENT
                if spread > 0:
                    strike.fire_spread += 1
                    queue.append((neighbour, spread))
                    chained += 1
            elif row.hazard in {SectionHazard.COLLAPSE, SectionHazard.EXPLOSION} and row.state is SectionState.DESTROYED:
                queue.append((neighbour, float(table.collapse_hit)))
                chained += 1
    foundation = next((row for row in rows if row.section in {X.FOUNDATION, X.SPINE, X.PIERS} and row.state is SectionState.DESTROYED), None)
    if foundation is not None and foundation.criticality is Criticality.CRITICAL:
        for row in rows:
            if row.state is not SectionState.DESTROYED and not set(row.locked or []) & {"condition", "state"}:
                row.condition = 0
                row.state = SectionState.DESTROYED
                strike.destroyed.append(row.section)
    strike.collapsed = any(broken(row) for row in rows)
    return strike


def working_share(rows: list[StructureSectionRow]) -> float:
    if not rows:
        return 1.0
    if any(broken(row) for row in rows):
        return 0.0
    shares = sum(row.share for row in rows)
    up = 0.0
    for row in rows:
        spec = SECTION_STATES[row.state]
        factor = (spec.minor_function_pct if row.criticality is Criticality.MINOR else spec.function_pct) / PERCENT
        up += row.share * factor
    return up / shares if shares else 1.0


async def integrity_share(session: AsyncSession, structure_id: int) -> float:
    return working_share(await sections_of(session, structure_id))


async def mend_sections(session: AsyncSession, rules: Rules, structure_id: int, amount: int, *, rebuild: bool) -> int:
    mended = 0
    for row in await sections_of(session, structure_id):
        if set(row.locked or []) & {"condition", "state"} or row.condition >= PERCENT:
            continue
        if row.state is SectionState.DESTROYED and not rebuild:
            continue
        row.condition = clamp_int(row.condition + amount, 0, PERCENT)
        row.state = state_for(rules, row.condition)
        mended += 1
    return mended


async def match_condition(session: AsyncSession, rules: Rules, structure_id: int, condition: int) -> None:
    for row in await sections_of(session, structure_id):
        if not set(row.locked or []) & {"condition", "state"}:
            row.condition = clamp_int(condition, 0, PERCENT)
            row.state = state_for(rules, row.condition)
