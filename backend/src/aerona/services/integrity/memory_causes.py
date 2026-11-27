from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.write_guard import held


async def causes_without_their_subject(session: AsyncSession) -> list[int]:
    names_subject = select(IncidentParticipantRow.incident_id).where(
        IncidentParticipantRow.incident_id == MemoryRow.incident_id, IncidentParticipantRow.node_id == MemoryRow.subject_node_id
    )
    names_holder = select(IncidentParticipantRow.incident_id).where(
        IncidentParticipantRow.incident_id == MemoryRow.incident_id, IncidentParticipantRow.node_id == MemoryRow.holder_node_id
    )
    rows = await session.execute(
        select(MemoryRow.id, MemoryRow.holder_node_id)
        .where(MemoryRow.incident_id.is_not(None), MemoryRow.inherited_from_node_id.is_(None), ~(names_subject.exists() & names_holder.exists()))
        .order_by(MemoryRow.id)
    )
    return [memory_id for memory_id, holder in rows if not held(holder)]


async def unlink_cause(session: AsyncSession, memory_id: int) -> None:
    row = await session.get(MemoryRow, memory_id)
    if row is not None:
        row.incident_id = None
        row.step_id = None
