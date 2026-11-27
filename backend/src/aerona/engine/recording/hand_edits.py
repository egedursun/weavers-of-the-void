from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.modifier import IncidentRole

EDITED_FIELDS_FACT = "fields"
RECORD_EDITED_KIND = "player.canon.edited"
FOREIGN_GOD_EDITED_KIND = "player.foreign_god.edited"
EPOCH_EDITED_KIND = "player.canon.epoch_edited"
EDITED_EPOCH_FACT = "epoch"


def field_names(text: str | None) -> set[str]:
    return {field.strip() for field in (text or "").split(",") if field.strip()}


async def written_by_hand(session: AsyncSession, kind: str, role: IncidentRole, node_id: int | None = None) -> dict[int, set[str]]:
    statement = (
        select(IncidentParticipantRow.node_id, IncidentFactRow.name)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .join(IncidentFactRow, IncidentFactRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == kind, IncidentParticipantRow.role == role, IncidentFactRow.key == EDITED_FIELDS_FACT)
        .order_by(IncidentRow.id)
    )
    if node_id is not None:
        statement = statement.where(IncidentParticipantRow.node_id == node_id)
    written: dict[int, set[str]] = defaultdict(set)
    for holder, fields in await session.execute(statement):
        written[int(holder)] |= field_names(fields)
    return dict(written)


async def epochs_written_by_hand(session: AsyncSession) -> dict[int, set[str]]:
    edits = select(IncidentRow.id).where(IncidentRow.kind == EPOCH_EDITED_KIND)
    statement = select(IncidentFactRow.incident_id, IncidentFactRow.key, IncidentFactRow.number, IncidentFactRow.name).where(
        IncidentFactRow.incident_id.in_(edits), IncidentFactRow.key.in_([EDITED_EPOCH_FACT, EDITED_FIELDS_FACT])
    )
    epochs: dict[int, int] = {}
    fields: dict[int, set[str]] = defaultdict(set)
    for incident_id, key, number, name in await session.execute(statement.order_by(IncidentFactRow.id)):
        if key == EDITED_EPOCH_FACT and number is not None:
            epochs[incident_id] = int(number)
        elif key == EDITED_FIELDS_FACT:
            fields[incident_id] |= field_names(name)
    written: dict[int, set[str]] = defaultdict(set)
    for incident_id, epoch in epochs.items():
        written[epoch] |= fields.get(incident_id, set())
    return dict(written)
