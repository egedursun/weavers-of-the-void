from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.orm import aliased

from aerona.db.session import Database
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentStepRow
from aerona.domain.models.moment import Moment
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from aerona.services.integrity.record_links import ahead_of_births
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 2


def moment_of(year: int | None, season: int | None, day: int | None, hour: int | None) -> Moment | None:
    return Moment(year, season, day, hour) if year is not None else None


async def test_no_happening_is_earlier_than_its_cause_and_no_step_earlier_than_the_one_before(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, EPOCHS, rules=eager(Rules()))
    cause = aliased(IncidentRow)
    async with database.read() as session:
        pairs = (
            await session.execute(
                select(
                    IncidentRow.id,
                    IncidentRow.kind,
                    IncidentRow.year,
                    IncidentRow.season,
                    IncidentRow.day,
                    IncidentRow.hour,
                    cause.year,
                    cause.season,
                    cause.day,
                    cause.hour,
                ).join(cause, cause.id == IncidentRow.cause_incident_id)
            )
        ).all()
        steps = (
            await session.execute(
                select(
                    IncidentStepRow.incident_id,
                    IncidentStepRow.position,
                    IncidentStepRow.year,
                    IncidentStepRow.season,
                    IncidentStepRow.day,
                    IncidentStepRow.hour,
                )
            )
        ).all()
        years = (
            await session.execute(select(IncidentRow.kind, IncidentRow.year, ChronicleRow.year).join(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id))
        ).all()
    early = []
    for incident_id, kind, *rest in pairs:
        own, before = moment_of(*rest[:4]), moment_of(*rest[4:])
        if own is None or (before is not None and own.before(before)):
            early.append(f"{kind} #{incident_id} at {own} before its cause at {before}")
    ordered: dict[int, list[tuple[int, Moment | None]]] = {}
    for incident_id, position, *moment in steps:
        ordered.setdefault(incident_id, []).append((position, moment_of(*moment)))
    for incident_id, rows in ordered.items():
        moments = [moment for _, moment in sorted(rows, key=lambda row: row[0])]
        if any(moment is None for moment in moments) or any(later.before(earlier) for earlier, later in pairwise(moments) if earlier and later):
            early.append(f"the steps of #{incident_id} go back in time")
    told = [f"{kind}: incident year {year} but line year {line}" for kind, year, line in years if year != line]
    async with database.read() as session:
        unborn = await ahead_of_births(session)
    assert early == []
    assert told == []
    assert unborn == [], f"happenings earlier than the first record of someone in them: {unborn[:20]}"
