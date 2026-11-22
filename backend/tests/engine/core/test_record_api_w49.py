import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import aerona.engine.recording.record as recording
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.core.errors import ValidationFailedError
from aerona.db.record_context import Term
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, FactValue, IncidentTier, InstrumentKind, ProcessGroup, StepAction, StepLocus, StepOutcome, StepState
from aerona.engine.context import TickContext
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining, term
from tests.engine.core.factories import CoreWorld

DUEL = IncidentKindSpec(
    "test.duel",
    ProcessGroup.SINGLE_COMBAT,
    "{actor} broke the arm of {target} with {weapon} after {exchanges:exchange|exchanges}.",
    roles=(RoleSpec(IncidentRole.ACTOR), RoleSpec(IncidentRole.TARGET), RoleSpec(IncidentRole.WITNESS, required=False, many=True)),
    facts=(
        FactSpec("weapon", FactValue.NAME),
        FactSpec("exchanges", FactValue.NUMBER, FactUnit.COUNT),
        FactSpec("damage", FactValue.ENUM, enum=DamageType, required=False),
    ),
    steps=frozenset({StepAction.STRIKE, StepAction.FALL, StepAction.RISE}),
)


@pytest.fixture(autouse=True)
def kinds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recording, "INCIDENT_KINDS", {DUEL.key: DUEL})


async def test_a_happening_keeps_its_roles_facts_steps_and_terms_and_is_told_from_them(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    winner, loser = world.regions[0].id, world.regions[1].id
    steps = (
        StepDraft(
            StepAction.STRIKE,
            actor=winner,
            target=loser,
            round=1,
            instrument_kind=InstrumentKind.ITEM,
            instrument_key="mace",
            locus_kind=StepLocus.BODY_PART,
            locus_key="arm",
            damage_type=DamageType.BLUNT,
            amount=7,
            unit=FactUnit.HP,
            outcome=StepOutcome.BROKEN,
        ),
        StepDraft(StepAction.FALL, actor=loser, round=1, parent=0, states=((loser, StepState.PRONE),)),
        StepDraft(StepAction.RISE, actor=loser, round=2, states=((loser, StepState.RISEN),)),
    )
    written = await record(
        ctx,
        DUEL.key,
        roles={IncidentRole.ACTOR: winner, IncidentRole.TARGET: loser, IncidentRole.WITNESS: [world.people.id]},
        facts={"weapon": "a named mace", "exchanges": 3, "damage": DamageType.BLUNT},
        steps=steps,
        terms=(Term("records.test_strength", 4.0),),
        place=world.regions[0].id,
    )
    await session.flush()
    assert written.text == f"{world.regions[0].name} broke the arm of {world.regions[1].name} with a named mace after 3 exchanges."
    incident = await session.get_one(IncidentRow, written.incident_id)
    assert incident.kind == DUEL.key and incident.tier is IncidentTier.STEPS and incident.year is not None
    roles = {(row.node_id, row.role) for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id))}
    assert {(winner, IncidentRole.ACTOR), (loser, IncidentRole.TARGET), (world.people.id, IncidentRole.WITNESS)} <= roles
    facts = {row.key: row for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id))}
    assert facts["exchanges"].number == 3 and facts["exchanges"].unit is FactUnit.COUNT
    assert facts["damage"].enum_name == "DamageType" and facts["damage"].enum_value == DamageType.BLUNT.value and facts["weapon"].name == "a named mace"
    rows = list(await session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident.id).order_by(IncidentStepRow.position)))
    assert [row.action for row in rows] == [StepAction.STRIKE, StepAction.FALL, StepAction.RISE]
    assert rows[1].parent_step_id == rows[0].id and rows[0].outcome is StepOutcome.BROKEN and rows[0].locus_key == "arm"
    states = set(await session.scalars(select(IncidentStepStateRow.state).where(IncidentStepStateRow.step_id.in_([row.id for row in rows]))))
    assert states == {StepState.PRONE, StepState.RISEN}
    terms = list(await session.scalars(select(IncidentTermRow).where(IncidentTermRow.incident_id == incident.id)))
    assert [(term.term, term.amount) for term in terms] == [("records.test_strength", 4.0)]


@pytest.mark.parametrize(
    ("roles", "facts", "steps", "message"),
    [
        ({IncidentRole.ACTOR: 1}, {"weapon": "a mace", "exchanges": 1}, (), "needs its target"),
        ({IncidentRole.ACTOR: 1, IncidentRole.TARGET: 2}, {"weapon": "a mace"}, (), "needs the facts exchanges"),
        ({IncidentRole.ACTOR: 1, IncidentRole.TARGET: 2}, {"weapon": "a mace", "exchanges": "three"}, (), "must be number"),
        ({IncidentRole.ACTOR: 1, IncidentRole.TARGET: 2}, {"weapon": "a mace", "exchanges": 1, "colour": "red"}, (), "has no fact colour"),
        ({IncidentRole.ACTOR: 1, IncidentRole.TARGET: 2}, {"weapon": "a mace", "exchanges": 1}, (StepDraft(StepAction.MARRY),), "has no step marry"),
        ({IncidentRole.ACTOR: [1, 2], IncidentRole.TARGET: 3}, {"weapon": "a mace", "exchanges": 1}, (), "takes one actor"),
    ],
)
async def test_a_write_that_breaks_its_kind_is_refused(ctx: TickContext, roles: dict, facts: dict, steps: tuple, message: str) -> None:
    with pytest.raises(ValidationFailedError, match=message):
        await record(ctx, DUEL.key, roles=roles, facts=facts, steps=steps)


async def test_an_unknown_kind_is_refused(ctx: TickContext) -> None:
    with pytest.raises(ValidationFailedError, match="no kind of happening"):
        await record(ctx, "test.unknown", text="Nothing happened.")


async def test_a_write_that_names_fewer_of_a_role_than_its_kind_tells_is_refused(ctx: TickContext, world: CoreWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    pair = IncidentKindSpec(
        "test.pair",
        DUEL.group,
        "{subject[0]} met {subject[1]}.",
        roles=(RoleSpec(IncidentRole.SUBJECT, required=False, many=True),),
    )
    monkeypatch.setattr(recording, "INCIDENT_KINDS", {pair.key: pair})
    with pytest.raises(ValidationFailedError, match="names 2 of its subject"):
        await record(ctx, pair.key, roles={IncidentRole.SUBJECT: [world.regions[0].id]})
    written = await record(ctx, pair.key, roles={IncidentRole.SUBJECT: [world.regions[0].id, world.regions[1].id]})
    assert written.text == f"{world.regions[0].name} met {world.regions[1].name}."


async def test_each_term_of_a_scope_is_told_by_one_happening_only(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    roles = {IncidentRole.ACTOR: world.regions[0].id, IncidentRole.TARGET: world.regions[1].id}
    facts = {"weapon": "a mace", "exchanges": 1}
    with explaining():
        term("records.first_strength", 2.0)
        first = await record(ctx, DUEL.key, roles=roles, facts=facts, place=world.regions[0].id)
        with explaining():
            term("records.inner_strength", 3.0)
            inner = await record(ctx, DUEL.key, roles=roles, facts=facts, place=world.regions[0].id)
        term("records.second_strength", 5.0)
        second = await record(ctx, DUEL.key, roles=roles, facts=facts, place=world.regions[0].id)
    await session.flush()
    told = {}
    for written in (first, inner, second):
        rows = await session.scalars(select(IncidentTermRow.term).where(IncidentTermRow.incident_id == written.incident_id).order_by(IncidentTermRow.position))
        told[written.incident_id] = [key for key in rows if key.startswith("records.")]
    assert told == {
        first.incident_id: ["records.first_strength"],
        inner.incident_id: ["records.inner_strength"],
        second.incident_id: ["records.second_strength"],
    }
