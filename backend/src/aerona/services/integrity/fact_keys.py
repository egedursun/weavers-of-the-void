from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentFactRow

DECLARED = {key: frozenset(fact.key for fact in spec.facts) for key, spec in INCIDENT_KINDS.items()}


async def facts_beyond_their_kind(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(IncidentRow.id, IncidentRow.kind, IncidentFactRow.key)
        .join(IncidentFactRow, IncidentFactRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind.in_(sorted(DECLARED)))
        .order_by(IncidentRow.id)
    )
    found: list[int] = []
    for incident_id, kind, key in rows:
        if key not in DECLARED[kind] and (not found or found[-1] != incident_id):
            found.append(incident_id)
    return found


async def drop_undeclared_facts(session: AsyncSession, incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    if incident is None or incident.kind not in DECLARED:
        return
    await session.execute(
        delete(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id, IncidentFactRow.key.not_in(sorted(DECLARED[incident.kind])))
    )
