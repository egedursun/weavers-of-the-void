from collections import Counter

from sqlalchemy import exists, or_, select

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentTermRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.engine.pipeline import simulate
from aerona.engine.recording.bands import quantity_field
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 1


async def test_every_number_an_engine_step_changes_says_why_unless_its_kind_sets_it_outright(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, EPOCHS, rules=eager(Rules()))
    explained = or_(
        exists().where(StateChangeTermRow.change_id == StateChangeRow.id),
        exists().where(IncidentTermRow.incident_id == StateChangeRow.incident_id),
    )
    async with database.read() as session:
        rows = (
            await session.execute(
                select(IncidentRow.kind, StateChangeRow.table_name, StateChangeRow.field)
                .join(IncidentRow, IncidentRow.id == StateChangeRow.incident_id)
                .where(
                    StateChangeRow.actor_kind == ActorKind.ENGINE,
                    StateChangeRow.operation == LedgerOperation.UPDATE,
                    or_(StateChangeRow.before_number.is_not(None), StateChangeRow.after_number.is_not(None)),
                    ~explained,
                )
            )
        ).all()
    unexplained = Counter(
        f"{kind}: {table}.{field}"
        for kind, table, field in rows
        if quantity_field(table, field) and (not (spec := INCIDENT_KINDS.get(kind)) or not spec.direct)
    )
    assert not unexplained, "Numbers changed with no terms:\n" + "\n".join(f"{count}x {line}" for line, count in unexplained.most_common(40))


def test_a_link_to_another_record_is_not_a_quantity_that_needs_terms() -> None:
    assert not quantity_field("structure_profiles", "design_id")
    assert quantity_field("entities", "power_level")
