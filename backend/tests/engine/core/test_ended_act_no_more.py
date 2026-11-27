from bisect import bisect_right

from sqlalchemy import select

from aerona.catalog.incident_kinds.under_age import ACTING_ROLES
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.entity import ENDED_STATUSES
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 2
AGENCY = sorted(ACTING_ROLES - {IncidentRole.MAKER})
STEP_OPENED = "phase.%"


async def test_a_thing_that_ended_acts_in_no_later_step_except_through_what_it_did_before(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, EPOCHS, rules=eager(Rules()))
    async with database.read() as session:
        opened = (
            await session.execute(
                select(IncidentRow.id, IncidentRow.kind, IncidentRow.epoch).where(IncidentRow.kind.like(STEP_OPENED)).order_by(IncidentRow.id)
            )
        ).all()
        starts = [row[0] for row in opened]

        def step_of(incident: int, epoch: int) -> tuple[int, str]:
            at = bisect_right(starts, incident) - 1
            return (epoch, opened[at][1]) if at >= 0 else (epoch, "")

        ended = set(await session.scalars(select(EntityRow.id).where(EntityRow.status.in_(sorted(ENDED_STATUSES)))))
        ends: dict[int, tuple[int, int]] = {}
        for node, incident, epoch in await session.execute(
            select(StateChangeRow.node_id, StateChangeRow.incident_id, StateChangeRow.epoch).where(
                StateChangeRow.table_name == EntityRow.__tablename__,
                StateChangeRow.field == "status",
                StateChangeRow.after_text.in_(sorted(status.value for status in ENDED_STATUSES)),
                StateChangeRow.incident_id.is_not(None),
            )
        ):
            if node in ended and incident is not None and incident > ends.get(node, (0, 0))[0]:
                ends[node] = (incident, epoch)
        late: list[tuple[int, str, str]] = []
        for node, (end, epoch) in sorted(ends.items()):
            ending_step = step_of(end, epoch)
            rows = await session.execute(
                select(IncidentRow.id, IncidentRow.epoch, IncidentRow.cause_incident_id, IncidentRow.kind, IncidentParticipantRow.role)
                .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
                .where(IncidentParticipantRow.node_id == node, IncidentParticipantRow.role.in_(AGENCY), IncidentRow.id > end)
                .order_by(IncidentRow.id)
            )
            late.extend(
                (node, kind, str(role))
                for incident, act_epoch, cause, kind, role in rows
                if step_of(incident, act_epoch) != ending_step and (cause is None or cause > end)
            )
    assert late == [], f"ended things acting in a later step: {late[:30]}"
