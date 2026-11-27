from collections import Counter

from sqlalchemy import select

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.repeats import REPEATED_KINDS
from aerona.db.session import Database
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos


async def test_no_happening_is_told_twice_alike_in_one_year(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, 1, rules=eager(Rules()))
    async with database.read() as session:
        incidents = (
            await session.execute(select(IncidentRow.id, IncidentRow.kind, IncidentRow.epoch, IncidentRow.year).where(IncidentRow.chronicle_id.is_not(None)))
        ).all()
        parts: dict[int, list[tuple[int, str]]] = {}
        for incident_id, member, role in await session.execute(
            select(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id, IncidentParticipantRow.role)
        ):
            parts.setdefault(incident_id, []).append((member, role.value))
        facts: dict[int, list[tuple[str, object]]] = {}
        for incident_id, key, number, enum_value, name, fact_node in await session.execute(
            select(
                IncidentFactRow.incident_id,
                IncidentFactRow.key,
                IncidentFactRow.number,
                IncidentFactRow.enum_value,
                IncidentFactRow.name,
                IncidentFactRow.node_id,
            )
        ):
            facts.setdefault(incident_id, []).append((key, number if number is not None else enum_value or name or fact_node))
    alike = Counter(
        (kind, epoch, year, tuple(sorted(parts.get(incident_id, []))), tuple(sorted(facts.get(incident_id, []), key=repr)))
        for incident_id, kind, epoch, year in incidents
        if INCIDENT_KINDS.get(kind) is not None and INCIDENT_KINDS[kind].told and not INCIDENT_KINDS[kind].repeatable
    )
    twice = sorted((key for key, count in alike.items() if count > 1), key=repr)
    assert twice == [], f"happenings told twice alike in one year: {twice[:40]}"


def test_every_kind_said_to_repeat_is_a_kind() -> None:
    assert sorted(REPEATED_KINDS - set(INCIDENT_KINDS)) == []
