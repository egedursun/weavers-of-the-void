from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.body_lines import ONSET_STEPS
from aerona.catalog.incident_kinds.g04_body import affliction_steps
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentStepRow, IncidentStepStateRow
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission
from aerona.domain.enums.body import BodyPart, DamageType, HarmCause, InjuryKind, InjuryState, MedicineTier
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.minds import MindSeat, StateMedium
from aerona.domain.enums.records import StepAction, StepState
from aerona.engine.body.afflictions import afflict, cure, onset_steps
from aerona.engine.body.healing import record_tending, treatment_steps
from aerona.engine.body.treatment import treat
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import mark_wound_states
from aerona.engine.minds.continuity import copy_mind, merge_minds, save_mind, transfer_mind
from aerona.engine.minds.phase import break_links
from aerona.engine.minds.profiles import profile_of
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "steps", rules=tuned_rules(**rules))


async def steps_of(session: AsyncSession, kind: str) -> list[IncidentStepRow]:
    statement = select(IncidentStepRow).join(IncidentRow, IncidentRow.id == IncidentStepRow.incident_id).where(IncidentRow.kind == kind)
    return list(await session.scalars(statement.order_by(IncidentStepRow.id)))


def wound(bearer_id: int, part: BodyPart, kind: InjuryKind, *, bleeding: int = 0, step_id: int | None = None) -> InjuryRow:
    return InjuryRow(
        bearer_node_id=bearer_id,
        part=part,
        kind=kind,
        damage_type=DamageType.BLUNT,
        severity=3,
        state=InjuryState.FRESH,
        function_loss=10,
        cause_kind=HarmCause.DUEL,
        epoch=2,
        bleeding=bleeding,
        step_id=step_id,
    )


async def test_mind_continuity_writes_its_own_steps(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lockfall", world, world.regions[0])
    keeper = await mortal(session, "Avera", world, town.id)
    held_mind = await mortal(session, "Steward", world, town.id)
    other = await mortal(session, "Second", world, town.id)
    ctx = await at(session, 2)
    for node in (held_mind.id, other.id):
        mind = await profile_of(session, ctx.rules, node, ctx.epoch)
        mind.copyable = mind.restorable = mind.transferable = mind.mergeable = True
    await session.flush()
    await copy_mind(ctx, held_mind.id, MindSeat.BODY, None)
    await save_mind(ctx, held_mind.id, keeper.id, keeper.id, StateMedium.RECORD)
    await transfer_mind(ctx, held_mind.id, MindSeat.BODY, None)
    await merge_minds(ctx, held_mind.id, other.id)
    assert [step.action for step in await steps_of(session, "mind.copied")] == [StepAction.COPY_MIND]
    saved = await steps_of(session, "mind.saved")
    assert [step.action for step in saved] == [StepAction.SAVE_MIND] and saved[0].actor_node_id == keeper.id
    assert [step.action for step in await steps_of(session, "mind.transferred")] == [StepAction.TRANSFER_MIND]
    merged = await steps_of(session, "mind.merged")
    assert [step.action for step in merged] == [StepAction.MERGE_MINDS] and merged[0].target_node_id == other.id


async def test_a_broken_mind_link_is_told_as_an_unlinking(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lockfall", world, world.regions[0])
    first = await mortal(session, "Ila", world, town.id)
    second = await mortal(session, "Oren", world, town.id)
    ctx = await at(session, 3)
    await connect(session, first.id, second.id, BondKind.LINKED_WITH, 1, description="minds linked")
    second.status, second.end_epoch = EntityStatus.DEAD, 2
    await session.flush()
    assert await break_links(ctx) == 1
    unlinked = await steps_of(session, "mind.link_broken")
    assert [step.action for step in unlinked] == [StepAction.UNLINK]
    assert (unlinked[0].actor_node_id, unlinked[0].target_node_id) == (first.id, second.id)


async def test_possession_marks_the_host_and_a_cure_by_medicine_is_treated_then_recovered(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lockfall", world, world.regions[0])
    host = await mortal(session, "Host", world, town.id)
    bitten = await mortal(session, "Bitten", world, town.id)
    ctx = await at(session, 2)
    await afflict(ctx, host, PackageKind.POSSESSION, Transmission.CURSE)
    possessed = await steps_of(session, "affliction.possession")
    assert [step.action for step in possessed] == [StepAction.POSSESS]
    state = await session.scalar(select(IncidentStepStateRow).where(IncidentStepStateRow.step_id == possessed[0].id))
    assert state is not None and state.state is StepState.POSSESSED and state.node_id == host.id
    venom = await afflict(ctx, bitten, PackageKind.SNAKE_VENOM, Transmission.BITE)
    assert venom is not None
    assert [step.action for step in await steps_of(session, "affliction.snake_venom")] == [StepAction.FALL_ILL]
    await cure(ctx, bitten, venom, CureKind.MEDICINE)
    assert [step.action for step in await steps_of(session, "affliction.cured_by")] == [StepAction.TREAT, StepAction.RECOVER]


async def test_a_healer_examines_cauterises_and_sets_a_bone_and_the_tending_is_told(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lockfall", world, world.regions[0])
    patient = await mortal(session, "Patient", world, town.id)
    healer = await mortal(session, "Healer", world, town.id)
    ctx = await at(session, 2, tissues={"diagnose_pct": 100, "diagnose_floor_pct": 100})
    row = wound(patient.id, BodyPart.LEFT_ARM, InjuryKind.FRACTURE, bleeding=6)
    session.add(row)
    await session.flush()
    treatment = await treat(ctx, row, skill=100, medicine=10, community_id=None, walking=False, rng=ctx.rng("treat"))
    assert treatment.changed and row.bleeding == 0
    drafts = treatment_steps(treatment, row, healer.id, patient.id)
    assert [draft.action for draft in drafts] == [StepAction.EXAMINE, StepAction.TREAT, StepAction.SET_BONE]
    await record_tending(ctx, patient, healer.id, MedicineTier.HERBS, drafts)
    told = await steps_of(session, "healing.tended")
    assert [step.action for step in told] == [StepAction.EXAMINE, StepAction.TREAT, StepAction.SET_BONE]
    assert all(step.record_key == str(row.id) and step.actor_node_id == healer.id for step in told)


async def test_a_wound_marks_its_step_bleeding_stunned_or_blinded(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lockfall", world, world.regions[0])
    patient = await mortal(session, "Patient", world, town.id)
    healer = await mortal(session, "Healer", world, town.id)
    ctx = await at(session, 2, tissues={"diagnose_pct": 100, "diagnose_floor_pct": 100})
    seed = wound(patient.id, BodyPart.LEFT_ARM, InjuryKind.FRACTURE)
    session.add(seed)
    await session.flush()
    treatment = await treat(ctx, seed, skill=100, medicine=10, community_id=None, walking=False, rng=ctx.rng("treat"))
    await record_tending(ctx, patient, healer.id, MedicineTier.HERBS, treatment_steps(treatment, seed, healer.id, patient.id))
    step_id = (await steps_of(session, "healing.tended"))[0].id
    rows = [
        wound(patient.id, BodyPart.LEFT_ARM, InjuryKind.DEEP_CUT, bleeding=8, step_id=step_id),
        wound(patient.id, BodyPart.HEAD, InjuryKind.CONCUSSION, step_id=step_id),
        wound(patient.id, BodyPart.LEFT_EYE, InjuryKind.GOUGED, step_id=step_id),
    ]
    session.add_all(rows)
    await session.flush()
    await mark_wound_states(ctx, patient.id, rows)
    await mark_wound_states(ctx, patient.id, rows)
    await session.flush()
    marked = set(await session.scalars(select(IncidentStepStateRow.state).where(IncidentStepStateRow.step_id == step_id)))
    assert marked == {StepState.BLEEDING, StepState.STUNNED, StepState.BLINDED}


def test_every_onset_with_a_step_names_its_own_and_a_blessing_is_blessed() -> None:
    blessing = onset_steps(7, AfflictionRow(id=1, package=PackageKind.DIVINE_BLESSING), 3)
    assert [step.action for step in blessing] == [StepAction.BLESS]
    possession = onset_steps(7, AfflictionRow(id=2, package=PackageKind.POSSESSION), 3)
    assert possession[0].states == ((7, StepState.POSSESSED),)
    assert onset_steps(7, AfflictionRow(id=3, package=PackageKind.TRAUMA), None) == ()
    assert all(affliction_steps(package) == frozenset({action}) for package, action in ONSET_STEPS.items())
