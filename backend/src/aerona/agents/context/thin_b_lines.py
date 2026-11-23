from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.intrigue import BELIEF_SOURCE_LABELS
from aerona.core.grammar import spoken
from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.society_depth import MobilityEventRow
from aerona.db.tables.storyteller_depth import RegionalTensionRow, SubsystemTensionRow
from aerona.engine.demography.wills import heirs_of_will, will_of

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
    found = [f"household form: {spoken(household.form)}"]
    dwelling = await session.scalar(select(DwellingRow).where(DwellingRow.household_id == household.id))
    if dwelling is not None:
        kind = await session.get(DwellingKindRow, dwelling.dwelling_kind_id) if dwelling.dwelling_kind_id is not None else None
        if kind is not None:
            found.append(f"home: {kind.name.lower()}")
        found.append(f"home held as: {spoken(dwelling.tenure)}")
        found.append(f"home heated by: {spoken(dwelling.heating) if dwelling.heating is not None else 'nothing'}")
        found.append(f"home lit by: {spoken(dwelling.light) if dwelling.light is not None else 'nothing'}")
        found.append(f"members per hundred rooms: {dwelling.crowding}")
    return found


async def will_lines(session: AsyncSession, me_id: int) -> list[str]:
    will = await will_of(session, me_id)
    if will is None:
        return []
    heirs = await heirs_of_will(session, will.id)
    named = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_([line.heir_node_id for line in heirs])))}
    shares = ", ".join(f"{named.get(line.heir_node_id, 'someone')} {line.share}%" for line in heirs)
    return [f"your will (made in epoch {will.made_epoch}) leaves what you own to: {shares}"]


async def class_change_lines(session: AsyncSession, me_id: int) -> list[str]:
    rows = await session.scalars(
        select(MobilityEventRow)
        .where(MobilityEventRow.mortal_entity_id == me_id)
        .order_by(MobilityEventRow.epoch.desc(), MobilityEventRow.id.desc())
        .limit(FEW)
    )
    return [f"your standing changed in epoch {row.epoch}: {spoken(row.event)}" for row in rows]


async def mortal_depth_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    return [
        *await home_lines(session, me.id),
        *await will_lines(session, me.id),
        *await class_change_lines(session, me.id),
        *await trust_lines(session, me.id),
        *await tension_lines(session, me.world_id),
    ]


async def son_depth_lines(session: AsyncSession, son_id: int, world_id: int | None) -> list[str]:
    return [*await trust_lines(session, son_id), *await tension_lines(session, world_id)]
