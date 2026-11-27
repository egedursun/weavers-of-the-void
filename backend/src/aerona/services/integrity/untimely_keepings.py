from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.recording.render import render_incident

KEPT = "tradition.kept"
UNTIMELY = "tradition.kept_untimely"
CLOSED = "tradition.slot_closed"


def paired_notes() -> Select[int, int]:
    product = aliased(IncidentParticipantRow)
    place = aliased(IncidentParticipantRow)
    subject = aliased(IncidentParticipantRow)
    actor = aliased(IncidentParticipantRow)
    note = aliased(IncidentRow)
    return (
        select(IncidentRow.id, note.id)
        .join(product, (product.incident_id == IncidentRow.id) & (product.role == IncidentRole.PRODUCT))
        .join(place, (place.incident_id == IncidentRow.id) & (place.role == IncidentRole.PLACE))
        .join(note, (note.kind == CLOSED) & (note.epoch == IncidentRow.epoch))
        .join(subject, (subject.incident_id == note.id) & (subject.role == IncidentRole.SUBJECT) & (subject.node_id == product.node_id))
        .join(actor, (actor.incident_id == note.id) & (actor.role == IncidentRole.ACTOR) & (actor.node_id == place.node_id))
        .where(IncidentRow.kind == KEPT)
    )


async def keepings_told_as_timely(session: AsyncSession) -> list[int]:
    return list(dict.fromkeys(kept for kept, _ in await session.execute(paired_notes().order_by(IncidentRow.id))))


async def tell_keeping_out_of_time(session: AsyncSession, incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    if incident is None or incident.kind != KEPT:
        return
    note = await session.scalar(select(paired_notes().where(IncidentRow.id == incident_id).subquery().c[1]).limit(1))
    if note is None:
        return
    incident.kind = UNTIMELY
    incident.cause_incident_id = incident.cause_incident_id or note
    line = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
    if line is None:
        return
    names: dict[IncidentRole, list[str]] = {}
    for role, name in await session.execute(
        select(IncidentParticipantRow.role, EntityRow.name)
        .join(EntityRow, EntityRow.id == IncidentParticipantRow.node_id)
        .where(IncidentParticipantRow.incident_id == incident_id)
        .order_by(IncidentParticipantRow.position)
    ):
        names.setdefault(role, []).append(name)
    facts: dict[str, object] = {}
    for fact in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id).order_by(IncidentFactRow.id)):
        if fact.key == "function" and fact.enum_value is not None:
            facts[fact.key] = TraditionFunction(fact.enum_value)
        elif fact.number is not None:
            facts[fact.key] = round(fact.number)
    line.template_key = UNTIMELY
    line.text = render_incident(INCIDENT_KINDS[UNTIMELY], names, facts)
