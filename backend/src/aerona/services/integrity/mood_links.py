from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.feeling_spread.moods import emotion_of
from aerona.engine.recording.render import render_incident

PLACE_MOODS = {"mood.spread": "mood.spread_household", "mood.faded": "mood.faded_household"}


def proper(feelings: dict[str, int]) -> dict[str, int]:
    return {key: max(0, min(PERCENT, int(value))) for key, value in feelings.items() if emotion_of(key) is not None}


async def odd_moods(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(FeelingSpreadRow).order_by(FeelingSpreadRow.id))
    return [
        row.id
        for row in rows
        if proper(dict(row.feelings or {})) != dict(row.feelings or {}) or (row.settlement_entity_id is None) == (row.household_id is None)
    ]


async def mend_mood(session: AsyncSession, key: int) -> None:
    row = await session.get(FeelingSpreadRow, key)
    if row is None:
        return
    if (row.settlement_entity_id is None) == (row.household_id is None):
        await session.delete(row)
        return
    row.feelings = proper(dict(row.feelings or {}))
    top = max(row.feelings.items(), key=lambda item: (item[1], item[0]), default=None)
    row.leading = emotion_of(top[0]) if top is not None else None


async def stray_mood_lines(session: AsyncSession) -> list[int]:
    towns = select(EntityRow.id).where(EntityRow.entity_type == EntityType.SETTLEMENT)
    query = (
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind.in_(sorted(PLACE_MOODS)), IncidentParticipantRow.role == IncidentRole.SUBJECT, IncidentParticipantRow.node_id.not_in(towns))
    )
    return sorted(set(await session.scalars(query)))


async def strike_line(session: AsyncSession, incident: IncidentRow) -> None:
    if incident.chronicle_id is not None:
        await session.execute(delete(ChronicleRow).where(ChronicleRow.id == incident.chronicle_id))
    await session.execute(delete(IncidentRow).where(IncidentRow.id == incident.id))


async def told_facts(session: AsyncSession, incident_id: int) -> dict[str, object]:
    found: dict[str, object] = {}
    for fact in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id).order_by(IncidentFactRow.id)):
        if fact.enum_name == Emotion.__name__ and fact.enum_value is not None:
            found[fact.key] = Emotion(fact.enum_value)
        elif fact.number is not None:
            found[fact.key] = int(fact.number) if float(fact.number).is_integer() else fact.number
        elif fact.name is not None:
            found[fact.key] = fact.name
    return found


async def retell_mood_line(session: AsyncSession, incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    if incident is None or incident.kind not in PLACE_MOODS:
        return
    subject = await session.scalar(
        select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident_id, IncidentParticipantRow.role == IncidentRole.SUBJECT)
    )
    household = await session.get(HouseholdRow, subject.node_id) if subject is not None else None
    head = await session.get(EntityRow, household.head_node_id) if household is not None and household.head_node_id is not None else None
    if subject is None or household is None or head is None or head.entity_type is not EntityType.MORTAL:
        await strike_line(session, incident)
        return
    kind = PLACE_MOODS[incident.kind]
    await session.delete(subject)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=incident_id, node_id=head.id, role=IncidentRole.SUBJECT, position=subject.position))
    home = await session.get(EntityRow, household.settlement_node_id) if household.settlement_node_id is not None else None
    incident.kind = kind
    incident.place_entity_id = home.id if home is not None else incident.place_entity_id
    facts = await told_facts(session, incident_id)
    line = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
    if line is not None:
        line.template_key = kind
        line.text = render_incident(INCIDENT_KINDS[kind], {IncidentRole.SUBJECT: [head.name]}, facts)
        await session.execute(delete(ChronicleEntityRow).where(ChronicleEntityRow.chronicle_id == line.id))
        session.add(ChronicleEntityRow(chronicle_id=line.id, entity_id=head.id, position=0))
    await session.flush()
