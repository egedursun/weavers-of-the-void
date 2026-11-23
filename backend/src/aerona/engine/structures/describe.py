from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.domain import GONE_STATES, STANDING_STATES, UNFINISHED_STATES
from aerona.core.grammar import agree, several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow, StructureStaffRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.structure import ConstructionState, ConstructionStatus
from aerona.engine.structures.profiles import resolved_of


def words(value: str) -> str:
    return value.replace("_", " ")


async def summary(session: AsyncSession, work: EntityRow, profile: StructureProfileRow) -> str:
    resolved = await resolved_of(session, profile)
    label = resolved.label.lower()
    if profile.construction_state in UNFINISHED_STATES:
        return f"{work.name} ({label}, being raised, {profile.progress}% done)"
    if profile.construction_state in GONE_STATES:
        gone = "a ruin" if profile.construction_state is ConstructionState.RUINED else spoken(profile.construction_state)
        return f"{work.name} ({label}, {gone})"
    state = "damaged, " if profile.construction_state is ConstructionState.DAMAGED else ""
    return f"{work.name} ({label} level {profile.level}, {state}working at {profile.effect_pct}%)"


async def structure_lines(session: AsyncSession, host: EntityRow) -> list[str]:
    rows = (
        await session.execute(
            select(EntityRow, StructureProfileRow)
            .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
            .where(StructureProfileRow.host_entity_id == host.id)
            .order_by(EntityRow.id)
        )
    ).all()
    return [await summary(session, work, profile) for work, profile in rows]


async def structure_detail(session: AsyncSession, work: EntityRow) -> list[str]:
    profile = await session.get(StructureProfileRow, work.id)
    if profile is None:
        return []
    resolved = await resolved_of(session, profile)
    lines = [f"it is {words(resolved.label.lower())} of the {spoken(resolved.group)} kind, level {profile.level}"]
    if profile.construction_state in STANDING_STATES:
        lines.append(f"it works at {profile.effect_pct}% (condition {profile.condition}, staffed {profile.staff_pct}%)")
    else:
        lines.append(f"it is {spoken(profile.construction_state)}, {profile.progress}% raised")
    construction = await session.scalar(
        select(ConstructionRow).where(ConstructionRow.structure_entity_id == work.id, ConstructionRow.status == ConstructionStatus.ACTIVE).limit(1)
    )
    if construction is not None:
        lines.append(
            f"{several(construction.workers, 'builder', 'builders')} {agree(construction.workers, 'works', 'work')} on it; "
            f"{construction.progress} of {construction.cost} labour is done"
        )
    staff = await session.scalar(select(StructureStaffRow).where(StructureStaffRow.structure_entity_id == work.id).limit(1))
    if staff is not None:
        lines.append(f"it needs {staff.required} {spoken(staff.social_class)}s and has {staff.allocated}")
    if profile.upkeep_coin or profile.upkeep_goods:
        lines.append(f"its upkeep is {profile.upkeep_coin} coin and {profile.upkeep_goods} {spoken(resolved.upkeep_commodity)} each age")
    son = await session.get(SonRow, profile.dedicated_son_id) if profile.dedicated_son_id is not None else None
    if son is not None:
        lines.append(f"it is dedicated to {son.name}{' and anchors that god' if profile.anchor else ''}")
    if profile.on_ley_line:
        lines.append("it stands on a ley line")
    return lines


async def structure_facts(session: AsyncSession, entity: EntityRow) -> list[str]:
    if entity.entity_type is EntityType.STRUCTURE:
        return await structure_detail(session, entity)
    if entity.entity_type in COMMUNITY_TYPES:
        found = await structure_lines(session, entity)
        return [f"works: {'; '.join(found)}"] if found else []
    return []
