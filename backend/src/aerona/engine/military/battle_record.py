from collections.abc import Mapping
from dataclasses import replace

from aerona.catalog.life.military import PHASE_ACTIONS, PHASE_STATES
from aerona.domain.enums.military import BattlePhase, Tactic
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepOutcome, StepState
from aerona.engine.military.battle import BattleResult, PhaseLog, Side, StackChange
from aerona.engine.military.tables import counters
from aerona.engine.recording.record import StepDraft


def phase_action(log: PhaseLog) -> StepAction:
    if log.phase is BattlePhase.CHARGE and log.details.get("flank"):
        return StepAction.FLANK
    return PHASE_ACTIONS[log.phase]


def stack_steps(
    change: StackChange, action: StepAction, parent: int, round_index: int, steps: list[StepDraft], *, arms: Mapping[int, int] | None = None
) -> None:
    main = len(steps)
    arm = (arms or {}).get(change.stack_id)
    steps.append(
        StepDraft(
            action,
            actor=change.army_id,
            target=change.enemy_id,
            round=round_index,
            parent=parent,
            instrument_kind=InstrumentKind.EQUIPMENT_MODEL if arm is not None else InstrumentKind.NONE,
            instrument_node=arm,
            instrument_key=change.kind.value,
            amount=change.lost,
            unit=FactUnit.PEOPLE,
            outcome=StepOutcome.KILLED if change.lost else StepOutcome.NO_EFFECT,
            record_table="army_units",
            record_key=str(change.stack_id),
        )
    )
    if change.routed or change.rallied or change.morale:
        turn = StepAction.ROUT if change.routed else StepAction.RALLY if change.rallied else StepAction.HOLD
        state = ((change.army_id, StepState.ROUTED),) if change.routed else ((change.army_id, StepState.RALLIED),) if change.rallied else ()
        steps.append(
            StepDraft(
                turn,
                actor=change.army_id,
                round=round_index,
                parent=main,
                amount=change.morale,
                unit=FactUnit.PERCENT,
                record_table="army_units",
                record_key=str(change.stack_id),
                states=state,
            )
        )
    if change.formation is not None:
        steps.append(
            StepDraft(
                StepAction.WHEEL,
                actor=change.army_id,
                round=round_index,
                parent=main,
                instrument_key=change.formation.value,
                record_table="army_units",
                record_key=str(change.stack_id),
            )
        )


def commander_step(side: Side, commander_id: int | None, round_index: int, parent: int | None) -> StepDraft | None:
    if not side.commander_struck or commander_id is None:
        return None
    return StepDraft(
        StepAction.FALL, actor=commander_id, round=round_index, parent=parent, outcome=StepOutcome.DOWNED, states=((commander_id, StepState.PRONE),)
    )


def phase_states(log: PhaseLog, result: BattleResult) -> tuple[tuple[int, StepState], ...]:
    if log.phase is BattlePhase.PURSUIT and result.loser is not None:
        return ((result.loser.army.id, StepState.FLEEING),)
    if log.phase not in PHASE_STATES:
        return ()
    word, state = PHASE_STATES[log.phase]
    sides = (("attacker", result.attacker), ("defender", result.defender))
    return tuple((side.army.id, state) for role, side in sides if int(log.details.get(f"{role}_{word}", 0) or 0) > 0)


def envelopment_steps(result: BattleResult, round_index: int, parent: int) -> list[StepDraft]:
    return [
        StepDraft(
            StepAction.ENCIRCLE,
            actor=side.army.id,
            target=other.army.id,
            round=round_index,
            parent=parent,
            instrument_key=side.tactic.value,
            outcome=StepOutcome.SUCCESS if result.winner is side else StepOutcome.FAILURE,
        )
        for side, other in ((result.attacker, result.defender), (result.defender, result.attacker))
        if side.tactic is Tactic.DOUBLE_ENVELOPMENT
    ]


def captive_step(result: BattleResult) -> StepDraft | None:
    if result.winner is None or result.loser is None or result.loser.captives <= 0:
        return None
    return StepDraft(
        StepAction.TAKE_CAPTIVES,
        actor=result.winner.army.id,
        target=result.loser.army.id,
        round=len(result.phases),
        amount=result.loser.captives,
        unit=FactUnit.PEOPLE,
        outcome=StepOutcome.CAPTURED,
    )


def counter_step(result: BattleResult, round_index: int, parent: int) -> StepDraft | None:
    for side, other in ((result.attacker, result.defender), (result.defender, result.attacker)):
        if counters(side.tactic, other.tactic):
            return StepDraft(
                StepAction.COUNTER,
                actor=side.army.id,
                target=other.army.id,
                round=round_index,
                parent=parent,
                instrument_key=side.tactic.value,
                outcome=StepOutcome.SUCCESS,
            )
    return None


def battle_steps(result: BattleResult, commanders: dict[int, int | None], arms: Mapping[int, int] | None = None) -> list[StepDraft]:
    steps: list[StepDraft] = []
    sides = (result.attacker, result.defender)
    for index, log in enumerate(result.phases):
        round_index = index + 1
        parent = len(steps)
        action = phase_action(log)
        steps.append(
            StepDraft(action, round=round_index, amount=log.attacker_losses + log.defender_losses, unit=FactUnit.PEOPLE, states=phase_states(log, result))
        )
        if log.phase is BattlePhase.PLAN:
            countered = counter_step(result, round_index, parent)
            if countered is not None:
                steps.append(countered)
            steps.extend(envelopment_steps(result, round_index, parent))
        for change in log.changes:
            stack_steps(change, action, parent, round_index, steps, arms=arms)
        if log.phase is BattlePhase.RESERVES and log.details.get("commander_fell"):
            for side in sides:
                fallen = commander_step(side, commanders.get(side.entity.id), round_index, parent)
                if fallen is not None:
                    steps.append(fallen)
    last = len(result.phases)
    parent = len(steps)
    if result.vehicle_steps:
        steps.append(StepDraft(StepAction.BOMBARD, round=last, amount=len(result.vehicle_steps), unit=FactUnit.COUNT))
        steps.extend(replace(draft, round=last, parent=parent if draft.parent is None else draft.parent + parent + 1) for draft in result.vehicle_steps)
    if result.standard_taken is not None and result.winner is not None and result.loser is not None:
        steps.append(
            StepDraft(
                StepAction.TAKE_STANDARD,
                actor=result.winner.army.id,
                target=result.loser.army.id,
                round=len(result.phases),
                instrument_kind=InstrumentKind.ITEM,
                instrument_node=result.standard_taken,
                outcome=StepOutcome.CAPTURED,
            )
        )
    taken = captive_step(result)
    if taken is not None:
        steps.append(taken)
    return steps
