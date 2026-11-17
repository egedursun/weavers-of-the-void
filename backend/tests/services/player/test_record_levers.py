import json

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactUnit, FactValue, ProcessGroup, StepAction, StepOutcome, StepState, WitnessMode
from aerona.services.player import incidents, record_levers
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def written(scope: PlayerScope, world: PlayerWorld) -> IncidentRow:
    outcome = await incidents.create_incident(
        scope,
        incidents.CreateIncident(
            text="A god set down a happening.", season=1, day=3, participants=[incidents.Participant(node_id=world.region.id, role=IncidentRole.ACTOR)]
        ),
    )
    row = await scope.session.get(IncidentRow, outcome.created_ids[0])
    assert row is not None and (row.season, row.day) == (1, 3)
    return row


async def test_a_fact_of_a_happening_is_set_down_rewritten_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    incident = await written(scope, world)
    made = await record_levers.add_fact(scope, record_levers.AddFact(incident_id=incident.id, key="amount", number=12, unit=FactUnit.COUNT))
    fact = await session.get(IncidentFactRow, made.created_ids[0])
    assert fact is not None and (fact.number, fact.unit) == (12, FactUnit.COUNT)
    await record_levers.edit_fact(scope, record_levers.EditFact(incident_fact_id=fact.id, node_id=world.region.id))
    assert (fact.node_id, fact.number, fact.unit) == (world.region.id, None, None)
    with pytest.raises(ValidationError):
        record_levers.AddFact(incident_id=incident.id, key="amount", number=1, name="Wren")
    await record_levers.delete_fact(scope, record_levers.FactRef(incident_fact_id=fact.id))
    await session.flush()
    assert await session.get(IncidentFactRow, fact.id) is None


def test_a_catalogued_kind_keeps_only_the_facts_it_declares_in_their_own_type_and_unit() -> None:
    spec = IncidentKindSpec(
        key="trade.sold",
        group=ProcessGroup.EXCHANGE,
        template="{seller} sold.",
        facts=(FactSpec("price", FactValue.NUMBER, FactUnit.COIN), FactSpec("good", FactValue.ENUM, enum=StepOutcome)),
    )
    record_levers.checked_fact(spec, "price", record_levers.FactValues(number=4, unit=FactUnit.COIN))
    record_levers.checked_fact(spec, "good", record_levers.FactValues(enum_name="StepOutcome", enum_value="success"))
    for key, values in (
        ("weight", record_levers.FactValues(number=4)),
        ("price", record_levers.FactValues(name="dear")),
        ("price", record_levers.FactValues(number=4, unit=FactUnit.HP)),
        ("good", record_levers.FactValues(enum_name="StepOutcome", enum_value="nowhere")),
        ("good", record_levers.FactValues(enum_name="StepState", enum_value="prone")),
    ):
        with pytest.raises(ValidationFailedError):
            record_levers.checked_fact(spec, key, values)


async def test_steps_unfold_in_order_nest_carry_states_and_lift_their_children_when_struck(
    scope: PlayerScope, session: AsyncSession, world: PlayerWorld
) -> None:
    incident = await written(scope, world)
    first = await record_levers.add_step(
        scope,
        record_levers.AddStep(
            incident_id=incident.id,
            step_action=StepAction.STRIKE,
            year=4,
            day=2,
            actor_node_id=world.region.id,
            amount=3,
            unit=FactUnit.HP,
            outcome=StepOutcome.WOUNDED,
            states=[record_levers.StateEntry(node_id=world.region.id, state=StepState.PRONE)],
        ),
    )
    parent_id = first.created_ids[0]
    child = await record_levers.add_step(
        scope, record_levers.AddStep(incident_id=incident.id, step_action=StepAction.RISE, parent_step_id=parent_id, year=4, day=3)
    )
    states = list(await session.scalars(select(IncidentStepStateRow.state).where(IncidentStepStateRow.step_id == parent_id)))
    assert states == [StepState.PRONE]
    root = (await record_levers.add_step(scope, record_levers.AddStep(incident_id=incident.id, step_action=StepAction.CLOSE))).created_ids[0]
    leaf = (await record_levers.add_step(scope, record_levers.AddStep(incident_id=incident.id, step_action=StepAction.CUT, parent_step_id=root))).created_ids[0]
    with pytest.raises(ValidationFailedError):
        await record_levers.edit_step(scope, record_levers.EditStep(incident_step_id=root, parent_step_id=leaf))
    await record_levers.edit_step(
        scope, record_levers.EditStep(incident_step_id=leaf, step_action=StepAction.PARRY, parent_step_id=root, outcome=StepOutcome.PARRIED)
    )
    await record_levers.delete_step(scope, record_levers.StepRef(incident_step_id=root))
    await session.flush()
    kept = await session.get(IncidentStepRow, leaf)
    assert kept is not None and kept.parent_step_id is None and kept.action is StepAction.PARRY and child.created_ids


async def test_a_step_cannot_come_before_the_step_told_ahead_of_it(scope: PlayerScope, world: PlayerWorld) -> None:
    incident = await written(scope, world)
    await record_levers.add_step(scope, record_levers.AddStep(incident_id=incident.id, step_action=StepAction.STRIKE, year=4, day=2))
    with pytest.raises(ValidationFailedError):
        await record_levers.add_step(scope, record_levers.AddStep(incident_id=incident.id, step_action=StepAction.FLEE, year=4, day=1))


async def test_a_witness_and_a_teller_are_named_reshaped_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    incident = await written(scope, world)
    other = world.world.id
    await record_levers.add_witness(scope, record_levers.AddWitness(incident_id=incident.id, node_id=other, witness_mode=WitnessMode.HEARD, fidelity=60))
    await record_levers.add_witness(scope, record_levers.AddWitness(incident_id=incident.id, node_id=other, teller=True))
    with pytest.raises(ValidationFailedError):
        await record_levers.add_witness(scope, record_levers.AddWitness(incident_id=incident.id, node_id=other))
    await record_levers.edit_witness(scope, record_levers.EditWitness(incident_id=incident.id, node_id=other, witness_mode=WitnessMode.WAS_TOLD, fidelity=30))
    seen = await session.get(IncidentParticipantRow, (incident.id, other, IncidentRole.WITNESS))
    assert seen is not None and (seen.witness_mode, seen.fidelity) == (WitnessMode.WAS_TOLD, 30)
    await record_levers.delete_witness(scope, record_levers.WitnessRef(incident_id=incident.id, node_id=other, teller=True))
    await session.flush()
    assert await session.get(IncidentParticipantRow, (incident.id, other, IncidentRole.TELLER)) is None


async def test_a_held_part_of_a_happening_is_kept_until_released(scope: PlayerScope, world: PlayerWorld) -> None:
    incident = await written(scope, world)
    await record_levers.hold_incident(scope, record_levers.HoldIncident(incident_id=incident.id, fields=["text", "steps"]))
    assert incident.locked == ["steps", "text"]
    await record_levers.hold_incident(scope, record_levers.HoldIncident(incident_id=incident.id, fields=["steps"], hold=False))
    assert incident.locked == ["text"]
    with pytest.raises(ValidationFailedError):
        await record_levers.hold_incident(scope, record_levers.HoldIncident(incident_id=incident.id, fields=["weather"]))


def change(**values: object) -> StateChangeRow:
    return StateChangeRow(epoch=1, actor_kind=ActorKind.ENGINE, **values)


async def test_a_change_is_reverted_as_a_new_change_for_every_operation_and_can_be_erased(
    scope: PlayerScope, session: AsyncSession, world: PlayerWorld
) -> None:
    region = world.region
    before = region.power_level
    region.power_level = before + 2
    edited = change(table_name="entities", row_key=json.dumps({"id": region.id}), operation=LedgerOperation.UPDATE, field="power_level", before_number=before)
    session.add(AppliedFixupRow(key="made_by_hand", result={"done": 1}))
    made = change(table_name="applied_fixups", row_key=json.dumps({"key": "made_by_hand"}), operation=LedgerOperation.INSERT)
    gone = change(
        table_name="applied_fixups",
        row_key=json.dumps({"key": "struck_by_hand"}),
        operation=LedgerOperation.DELETE,
        before_text=json.dumps({"key": "struck_by_hand", "result": {"kept": 2}, "created_at": "2026-11-17T09:00:00+00:00"}),
    )
    session.add_all([edited, made, gone])
    await session.flush()
    await record_levers.revert_change(scope, record_levers.ChangeRef(state_change_id=edited.id))
    refreshed = await session.get(EntityRow, region.id)
    assert refreshed is not None and refreshed.power_level == before
    await record_levers.revert_change(scope, record_levers.ChangeRef(state_change_id=made.id))
    assert await session.get(AppliedFixupRow, "made_by_hand") is None
    await record_levers.revert_change(scope, record_levers.ChangeRef(state_change_id=gone.id))
    restored = await session.get(AppliedFixupRow, "struck_by_hand")
    assert restored is not None and restored.result == {"kept": 2}
    with pytest.raises(ValidationFailedError):
        await record_levers.revert_change(scope, record_levers.ChangeRef(state_change_id=gone.id))
    await record_levers.delete_change(scope, record_levers.ChangeRef(state_change_id=edited.id))
    await session.flush()
    assert await session.get(StateChangeRow, edited.id) is None
