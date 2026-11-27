from sqlalchemy import exists, select
from sqlalchemy.orm import aliased

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext


async def told_this_epoch(
    ctx: TickContext,
    key: str,
    subject: int,
    role: IncidentRole,
    *,
    fact: str | None = None,
    value: str | None = None,
    other: tuple[int, IncidentRole] | None = None,
) -> bool:
    statement = (
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == key, IncidentRow.epoch == ctx.epoch, IncidentParticipantRow.node_id == subject, IncidentParticipantRow.role == role)
    )
    if fact is not None:
        told = (IncidentFactRow.enum_value == value) | (IncidentFactRow.name == value)
        statement = statement.where(exists().where(IncidentFactRow.incident_id == IncidentRow.id, IncidentFactRow.key == fact, told))
    if other is not None:
        partner = aliased(IncidentParticipantRow)
        statement = statement.where(exists().where(partner.incident_id == IncidentRow.id, partner.node_id == other[0], partner.role == other[1]))
    return await ctx.session.scalar(statement.limit(1)) is not None
