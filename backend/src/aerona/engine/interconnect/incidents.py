from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow

CHAIN_ARROW = " → "


@dataclass(frozen=True)
class Chain:
    incident_ids: tuple[int, ...]
    texts: tuple[str, ...]

    @property
    def line(self) -> str:
        return CHAIN_ARROW.join(self.texts)


async def _incidents(session: AsyncSession, epoch: int | None) -> dict[int, IncidentRow]:
    statement = select(IncidentRow)
    if epoch is not None:
        statement = statement.where(IncidentRow.epoch == epoch)
    return {row.id: row for row in await session.scalars(statement.order_by(IncidentRow.id))}


async def _texts(session: AsyncSession, rows: dict[int, IncidentRow]) -> dict[int, str]:
    chronicle_ids = [row.chronicle_id for row in rows.values() if row.chronicle_id is not None]
    texts = {row.id: row.text for row in await session.scalars(select(ChronicleRow).where(ChronicleRow.id.in_(chronicle_ids)))} if chronicle_ids else {}
    return {incident_id: texts.get(row.chronicle_id or 0, row.kind) for incident_id, row in rows.items()}


async def chain_to(session: AsyncSession, incident_id: int, depth: int) -> Chain:
    path: list[int] = []
    current: int | None = incident_id
    rows: dict[int, IncidentRow] = {}
    while current is not None and current not in path and len(path) < depth:
        row = await session.get(IncidentRow, current)
        if row is None:
            break
        rows[row.id] = row
        path.append(row.id)
        current = row.cause_incident_id
    texts = await _texts(session, rows)
    ordered = tuple(reversed(path))
    return Chain(ordered, tuple(texts[item] for item in ordered))


async def chains_in(session: AsyncSession, epoch: int, minimum: int, depth: int) -> list[Chain]:
    rows = await _incidents(session, epoch)
    causes = {row.cause_incident_id for row in rows.values() if row.cause_incident_id is not None}
    leaves = [row.id for row in rows.values() if row.id not in causes and row.cause_incident_id is not None]
    chains = [await chain_to(session, leaf, depth) for leaf in leaves]
    return [chain for chain in chains if len(chain.incident_ids) >= minimum]


async def recent_chain(session: AsyncSession, node_id: int, depth: int) -> Chain | None:
    latest = await session.scalar(
        select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == node_id).order_by(IncidentParticipantRow.incident_id.desc()).limit(1)
    )
    if latest is None:
        return None
    chain = await chain_to(session, latest, depth)
    return chain if len(chain.incident_ids) > 1 else None


async def causality_graph(session: AsyncSession, node_id: int) -> dict[int, list[int]]:
    own = list(await session.scalars(select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == node_id)))
    graph: dict[int, list[int]] = defaultdict(list)
    for incident_id in own:
        row = await session.get(IncidentRow, incident_id)
        if row is not None and row.cause_incident_id is not None:
            graph[row.cause_incident_id].append(row.id)
    return dict(graph)


async def last_incident(session: AsyncSession, node_id: int, templates: tuple[str, ...]) -> IncidentRow | None:
    if not templates:
        return None
    statement = (
        select(IncidentRow)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentParticipantRow.node_id == node_id, or_(*(IncidentRow.kind.startswith(template) for template in templates)))
        .order_by(IncidentRow.id.desc())
        .limit(1)
    )
    found: IncidentRow | None = await session.scalar(statement)
    return found
