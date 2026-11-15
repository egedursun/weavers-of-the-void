from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import several
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.prehistory import PrehistoryEventRow, PrehistoryRow
from aerona.domain.enums.prehistory import PrehistoryState


def label(value: str) -> str:
    return value.replace("_", " ")


async def happening_text(session: AsyncSession, event: PrehistoryEventRow) -> str | None:
    incident = await session.get(IncidentRow, event.incident_id) if event.incident_id is not None else None
    line = await session.get(ChronicleRow, incident.chronicle_id) if incident is not None and incident.chronicle_id is not None else None
    if line is not None:
        return line.text
    subject = await session.get(NodeRow, event.subject_node_id) if event.subject_node_id is not None else None
    return subject.name if subject is not None else None


async def prehistory_digests(session: AsyncSession, epoch: int) -> list[str]:
    rows = await session.scalars(
        select(PrehistoryRow).where(PrehistoryRow.state == PrehistoryState.DONE, PrehistoryRow.birth_epoch >= epoch - 1).order_by(PrehistoryRow.world_id)
    )
    lines: list[str] = []
    for row in list(rows):
        world = await session.get(WorldRow, row.world_id)
        statement = select(PrehistoryEventRow).where(PrehistoryEventRow.world_id == row.world_id)
        events = await session.scalars(statement.order_by(PrehistoryEventRow.round, PrehistoryEventRow.magnitude.desc()))
        told = [text for event in list(events) if (text := await happening_text(session, event)) is not None]
        if world is None or not told:
            continue
        header = f"{world.name}, {label(row.kind.value)} prehistory, {several(row.rounds_done, 'epoch', 'epochs')}, {label(row.source.value)}"
        lines.append(f"{header}: " + " | ".join(told))
    return lines
