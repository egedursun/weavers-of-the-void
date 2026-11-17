from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow
from aerona.db.tables.vehicles import DesignMountRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.military import Formation, UnitKind, VesselStatus
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome, StepState
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import MountKind, VehicleDomain, VehicleFrame
from aerona.domain.models.entity_stats import VesselStats
from aerona.engine.collective.designs import draw_design
from aerona.engine.equipment.models import draw_model
from aerona.engine.military.battle import BattlePhase, PhaseLog, StackChange
from aerona.engine.military.battle_record import stack_steps
from aerona.engine.military.vessels import SeaTally, can_meet, fight_key, sea_fight
from aerona.engine.operations.engagement import Engagement, engage, weapons_of
from aerona.engine.operations.sail import SailTally
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.records import retire
from aerona.engine.recording.record import StepDraft
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules

LONG_FIGHT = {"rounds": 20, "strike_crew_pct": 0, "strike_condition": 0}


async def vessel(
    session: AsyncSession, world: CoreWorld, name: str, frame: VehicleFrame, owner: EntityRow, *, weapons: tuple[EquipmentFamily, ...]
) -> tuple[EntityRow, VesselProfileRow]:
    ctx = await manual_context(session, "seafaring")
    body = await entity(session, name, EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=world.regions[0].id)
    design = await draw_design(ctx, owner, frame)
    await session.execute(delete(DesignMountRow).where(DesignMountRow.design_id == design.id))
    for slot, family in enumerate(weapons):
        model = await draw_model(ctx, owner, family, world_id=world.world.id)
        session.add(DesignMountRow(design_id=design.id, slot=slot, mount=MountKind.SPINAL, model_id=model.id, count=4, locked=[]))
    row = VesselProfileRow(
        entity_id=body.id,
        kind=VehicleKind.SHIP,
        frame=frame,
        design_id=design.id,
        crew=200,
        seamanship=50,
        condition=100,
        status=VesselStatus.AFLOAT,
        region_entity_id=world.regions[0].id,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return body, row


async def test_two_spacecraft_fight_round_by_round_and_the_beam_takes_the_shield_then_life_support(session: AsyncSession, world: CoreWorld) -> None:
    owner = await settlement(session, "Halo Dock", world, world.regions[0])
    rival = await settlement(session, "Far Dock", world, world.regions[1])
    lancer = await vessel(session, world, "Lancer", VehicleFrame.STARSHIP, owner, weapons=(EquipmentFamily.BEAM_CANNON,))
    hulk = await vessel(session, world, "Hulk", VehicleFrame.STARSHIP, rival, weapons=())
    assert [weapon.family for weapon in await weapons_of(await manual_context(session, "seafaring"), lancer[1])] == [EquipmentFamily.BEAM_CANNON]
    ctx = await manual_context(session, "seafaring", rules=tuned_rules(age_of_sail=LONG_FIGHT, engagement={"shield_absorb_pct": 0}))
    fight = await engage(ctx, lancer, hulk, (2.0, 1.0), SailTally())
    assert fight.domain is VehicleDomain.SPACE and fight.winner.id == lancer[0].id
    actions = [step.action for step in fight.steps]
    assert actions.index(StepAction.RAISE_SHIELD) < actions.index(StepAction.LOSE_SHIELD)
    beams = [step for step in fight.steps if step.action is StepAction.FIRE and step.actor == lancer[0].id]
    assert beams and all(step.instrument_key == EquipmentFamily.BEAM_CANNON.value for step in beams)
    assert beams[0].locus_key == "ward"
    assert any(step.locus_key == "life_support" and step.outcome is StepOutcome.DESTROYED for step in beams)
    vented = [index for index, step in enumerate(fight.steps) if step.action is StepAction.VENT]
    assert vented and any(step.action is StepAction.DIE and step.parent in vented for step in fight.steps)
    assert any(step.action is StepAction.LOSE_POWER and (hulk[0].id, StepState.ADRIFT) in step.states for step in fight.steps)


async def test_an_engagement_is_written_as_one_happening_with_its_rounds_steps_and_facts(session: AsyncSession, world: CoreWorld) -> None:
    owner = await settlement(session, "Halo Dock", world, world.regions[0])
    rival = await settlement(session, "Far Dock", world, world.regions[1])
    lancer = await vessel(session, world, "Lancer", VehicleFrame.STARSHIP, owner, weapons=(EquipmentFamily.BEAM_CANNON,))
    hulk = await vessel(session, world, "Hulk", VehicleFrame.STARSHIP, rival, weapons=())
    ctx = await manual_context(session, "seafaring", rules=tuned_rules(age_of_sail=LONG_FIGHT, engagement={"shield_absorb_pct": 0}))
    winner = await sea_fight(ctx, lancer, hulk, None, SeaTally())
    assert winner.id == lancer[0].id
    incident = await session.scalar(select(IncidentRow).where(IncidentRow.kind.like("seafaring.%")).order_by(IncidentRow.id.desc()).limit(1))
    assert incident is not None
    steps = list(await session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident.id)))
    facts = {row.key: row for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id))}
    assert {StepAction.MANOEUVRE, StepAction.FIRE, StepAction.RAISE_SHIELD} <= {step.action for step in steps}
    assert facts["domain"].enum_value == VehicleDomain.SPACE.value and (facts["rounds"].number or 0) >= 1
    states = list(await session.scalars(select(IncidentStepStateRow).where(IncidentStepStateRow.step_id.in_([step.id for step in steps]))))
    assert any(state.state is StepState.SHIELDED for state in states)


async def test_a_galleon_and_a_starship_cannot_meet_but_a_submarine_can_meet_a_ship(session: AsyncSession, world: CoreWorld) -> None:
    owner = await settlement(session, "Halo Dock", world, world.regions[0])
    ship = await vessel(session, world, "Gull", VehicleFrame.WARSHIP, owner, weapons=(EquipmentFamily.CANNON,))
    star = await vessel(session, world, "Lancer", VehicleFrame.STARSHIP, owner, weapons=())
    sub = await vessel(session, world, "Eel", VehicleFrame.SUBMARINE, owner, weapons=(EquipmentFamily.TORPEDO,))
    assert not can_meet(ship[1], star[1]) and can_meet(ship[1], sub[1])


async def test_every_ending_of_an_engagement_is_told_by_its_own_kind() -> None:

    body = EntityRow(id=1, name="A")
    ends = {
        (StepOutcome.DAMAGED, False, False): "seafaring.sea_fight",
        (StepOutcome.ESCAPED, False, False): "seafaring.escaped",
        (StepOutcome.YIELDED, False, False): "seafaring.struck",
        (StepOutcome.CAPTURED, False, False): "seafaring.boarded",
        (StepOutcome.DESTROYED, False, False): "seafaring.foundered",
        (StepOutcome.DESTROYED, True, False): "seafaring.blew_up",
        (StepOutcome.DESTROYED, False, True): "seafaring.downed",
    }
    for (end, exploded, crashed), key in ends.items():
        fight = Engagement(body, body, VehicleDomain.WATER, 1, end, exploded=exploded, crashed=crashed)
        assert fight_key(fight) == key


def test_a_stack_change_in_a_battle_phase_becomes_steps_with_losses_morale_rout_and_formation() -> None:

    change = StackChange(
        army_id=10, enemy_id=20, stack_id=7, kind=UnitKind.LINE_INFANTRY, lost=40, morale=-30, routed=True, rallied=False, formation=Formation.SQUARE
    )
    steps: list[StepDraft] = [StepDraft(StepAction.VOLLEY, round=1)]
    stack_steps(change, StepAction.VOLLEY, 0, 1, steps)
    main, turn, wheel = steps[1:]
    assert main.amount == 40 and main.outcome is StepOutcome.KILLED and main.record_key == "7" and main.parent == 0
    assert turn.action is StepAction.ROUT and turn.amount == -30 and (10, StepState.ROUTED) in turn.states and turn.parent == 1
    assert wheel.action is StepAction.WHEEL and wheel.instrument_key == Formation.SQUARE.value
    assert PhaseLog(BattlePhase.MISSILE, 0, 0, "volleys").changes == []
    assert StepLocus.SETTLEMENT is not None


async def test_a_vessel_made_this_tick_can_be_retired_before_anything_reloads_it(session: AsyncSession, world: CoreWorld) -> None:

    owner = await settlement(session, "Halo Dock", world, world.regions[0])
    body, _ = await vessel(session, world, "Gull", VehicleFrame.WARSHIP, owner, weapons=())
    await retire(session, body, 3, "lost", append=True)
    assert body.status is EntityStatus.DEAD and body.end_epoch == 3
