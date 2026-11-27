import json

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules
from aerona.services.integrity.chronicle_retell import retelling
from tests.engine.core.factories import CoreWorld, mortal

OLD_TEXT = "Parar called Wapnar out over honour honour."


async def called_out(session: AsyncSession, world: CoreWorld) -> tuple[ChronicleRow, NodeRow]:
    ctx = await manual_context(session, "retell", Rules())
    caller, called = await mortal(session, "Parar", world, world.regions[0].id), await mortal(session, "Wapnar", world, world.regions[0].id)
    recorded = await record(ctx, "duel.honour", roles={IncidentRole.ACTOR: caller.id, IncidentRole.TARGET: called.id}, facts={"grievance": 4})
    await session.flush()
    assert recorded is not None
    incident = await session.get(IncidentRow, recorded.incident_id)
    assert incident is not None and incident.chronicle_id is not None
    line = await session.get(ChronicleRow, incident.chronicle_id)
    node = await session.get(NodeRow, called.id)
    assert line is not None and node is not None
    return line, node


async def test_a_line_told_by_an_old_template_is_told_again_with_the_name_it_had_then(session: AsyncSession, world: CoreWorld) -> None:
    line, called = await called_out(session, world)
    told = line.text
    line.text = OLD_TEXT
    session.add(
        StateChangeRow(
            epoch=world.cosmos.epoch + 1,
            table_name="nodes",
            row_key=json.dumps({"id": called.id}),
            node_id=called.id,
            operation=LedgerOperation.UPDATE,
            field="name",
            before_text="Wapnar",
            after_text="Cenju",
            actor_kind=ActorKind.ENGINE,
        )
    )
    called.name = "Cenju"
    await session.flush()
    first = await retelling(session)
    assert first.changed >= 1
    assert line.text == told
    assert "Wapnar" in line.text and "Cenju" not in line.text
    assert (await retelling(session)).kinds == 0


async def test_a_line_written_by_hand_is_never_told_again(session: AsyncSession, world: CoreWorld) -> None:
    line, _ = await called_out(session, world)
    line.text, line.author_account_id, line.author_name = OLD_TEXT, 1, "Keeper"
    await session.flush()
    await retelling(session)
    assert line.text == OLD_TEXT


async def test_a_line_naming_a_record_a_repair_renamed_is_told_with_its_new_name(session: AsyncSession, world: CoreWorld) -> None:
    line, called = await called_out(session, world)
    await retelling(session)
    session.add(
        StateChangeRow(
            epoch=world.cosmos.epoch,
            table_name="nodes",
            row_key=json.dumps({"id": called.id}),
            node_id=called.id,
            operation=LedgerOperation.UPDATE,
            field="name",
            before_text="Wapnar",
            after_text="Wapnar Keel",
            actor_kind=ActorKind.SYSTEM,
        )
    )
    called.name = "Wapnar Keel"
    await session.flush()
    assert (await retelling(session)).changed == 1
    assert "Wapnar Keel" in line.text
    assert (await retelling(session)).changed == 0
