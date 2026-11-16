from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.intrigue import BELIEF_SOURCE_LABELS
from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.storyteller_depth import RegionalTensionRow, SubsystemTensionRow

FEW = 5


def words(key: str) -> str:
    return key.replace("_", " ")


async def trust_lines(session: AsyncSession, holder_id: int) -> list[str]:
    rows = await session.scalars(select(SourceTrustRow).where(SourceTrustRow.holder_node_id == holder_id).order_by(SourceTrustRow.trust.desc()).limit(FEW))
    return [f"trust in {BELIEF_SOURCE_LABELS[row.source].lower()}: {row.trust}/100" for row in rows]


async def tension_lines(session: AsyncSession, world_id: int | None) -> list[str]:
    if world_id is None:
        return []
    found: list[str] = []
    regions = await session.scalars(
        select(RegionalTensionRow).where(RegionalTensionRow.world_id == world_id).order_by(RegionalTensionRow.tension.desc()).limit(FEW)
    )
    for row in regions:
        region = await session.get(EntityRow, row.region_entity_id)
        if region is not None:
            found.append(f"tension in {region.name}: {row.tension}/100{', in crisis' if row.crisis else ''}")
    parts = await session.scalars(
        select(SubsystemTensionRow).where(SubsystemTensionRow.world_id == world_id).order_by(SubsystemTensionRow.tension.desc()).limit(FEW)
    )
    found.extend(f"tension in {words(row.subsystem)}: {row.tension}/100" for row in parts)
    return found


async def home_lines(session: AsyncSession, member_id: int) -> list[str]:
    member = await session.get(HouseholdMemberRow, member_id)
    household = await session.get(HouseholdRow, member.household_id) if member is not None else None
    if household is None:
        return []
    found = [f"household form: {words(household.form.value)}"]
    dwelling = await session.scalar(select(DwellingRow).where(DwellingRow.household_id == household.id))
    if dwelling is not None:
        found.append(f"home held as: {words(dwelling.tenure.value)}")
        found.append(f"home heated by: {words(dwelling.heating.value) if dwelling.heating is not None else 'nothing'}")
        found.append(f"home lit by: {words(dwelling.light.value) if dwelling.light is not None else 'nothing'}")
        found.append(f"members per hundred rooms: {dwelling.crowding}")
    return found


async def mortal_depth_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    return [*await home_lines(session, me.id), *await trust_lines(session, me.id), *await tension_lines(session, me.world_id)]


async def son_depth_lines(session: AsyncSession, son_id: int, world_id: int | None) -> list[str]:
    return [*await trust_lines(session, son_id), *await tension_lines(session, world_id)]
