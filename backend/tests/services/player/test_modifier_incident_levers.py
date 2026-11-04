import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.modifier import IncidentRole, ModifierOp, ModifierSource
from aerona.services.player import incidents, modifiers
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def test_a_modifier_of_any_source_is_forged_edited_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    region = world.region.id
    outcome = await modifiers.create_modifier(
        scope, modifiers.CreateModifier(node_id=region, key="fertility", op=ModifierOp.MULTIPLY, magnitude=1.2, source_kind=ModifierSource.WEATHER, epochs=3)
    )
    row = await session.get(ModifierRow, outcome.created_ids[0])
    assert row is not None and row.held and row.source_kind is ModifierSource.WEATHER and row.end_epoch is not None
    await modifiers.edit_modifier(scope, modifiers.EditModifier(modifier_id=row.id, magnitude=1.4, stacking_group="storm", endless=True))
    assert (row.magnitude, row.stacking_group, row.end_epoch) == (1.4, "storm", None)
    await modifiers.release_modifier(scope, modifiers.HoldModifier(modifier_id=row.id))
    assert not row.held
    await modifiers.hold_modifier(scope, modifiers.HoldModifier(modifier_id=row.id))
    assert row.held
    with pytest.raises(ValidationFailedError):
        await modifiers.create_modifier(scope, modifiers.CreateModifier(node_id=region, key="population", op=ModifierOp.ADD, magnitude=5))
    with pytest.raises(ValidationFailedError):
        await modifiers.create_modifier(
            scope, modifiers.CreateModifier(node_id=region, key="fertility", op=ModifierOp.ADD, magnitude=5, source_kind=ModifierSource.PIN)
        )


async def test_an_incident_is_written_rewritten_linked_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    region = world.region.id
    first = await incidents.create_incident(
        scope, incidents.CreateIncident(text="The river rose.", magnitude=40, participants=[incidents.Participant(node_id=region, role=IncidentRole.PLACE)])
    )
    root = first.created_ids[0]
    second = await incidents.create_incident(
        scope,
        incidents.CreateIncident(text="The town fled.", cause_incident_id=root, participants=[incidents.Participant(node_id=region, role=IncidentRole.TARGET)]),
    )
    child = second.created_ids[0]
    row = await session.get(IncidentRow, child)
    assert row is not None and row.cause_incident_id == root and row.kind == incidents.PLAYER_KIND
    await incidents.edit_incident(scope, incidents.EditIncident(incident_id=child, text="The town fled north.", magnitude=70))
    chronicle = await session.get(ChronicleRow, row.chronicle_id)
    assert chronicle is not None and chronicle.text == "The town fled north." and row.magnitude == 70
    await incidents.set_incident_roles(
        scope, incidents.SetIncidentRoles(incident_id=child, participants=[incidents.Participant(node_id=region, role=IncidentRole.ACTOR)])
    )
    roles = list(await session.scalars(select(IncidentParticipantRow.role).where(IncidentParticipantRow.incident_id == child)))
    assert roles == [IncidentRole.ACTOR]
    with pytest.raises(ValidationFailedError):
        await incidents.link_cause(scope, incidents.LinkCause(incident_id=root, cause_incident_id=child))
    await incidents.unlink_cause(scope, incidents.IncidentRef(incident_id=child))
    assert row.cause_incident_id is None
    await incidents.link_cause(scope, incidents.LinkCause(incident_id=child, cause_incident_id=root))
    await incidents.delete_incident(scope, incidents.IncidentRef(incident_id=root))
    await session.flush()
    assert await session.get(IncidentRow, root) is None
    assert row.cause_incident_id is None
