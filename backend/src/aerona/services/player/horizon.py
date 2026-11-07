from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus
from aerona.domain.enums.travel import HorizonStatus
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

OPEN_STEPS = frozenset({DeferredStepStatus.PENDING, DeferredStepStatus.RUNNING, DeferredStepStatus.HELD})


class IntuitionTarget(Command):
    intuition_id: int


class DiscardAll(Command):
    pass


class SensedStepTarget(Command):
    step_id: int


class HoldSensedStep(Command):
    step_id: int
    hold: bool = True


@player_action("intuition:discard", ActionKind.DISCARD_INTUITION)
async def discard_intuition(scope: PlayerScope, command: IntuitionTarget) -> Effect:
    intuition = await scope.session.get(HorizonIntuitionRow, command.intuition_id)
    if intuition is None:
        raise NotFoundError("No such intuition.")
    if intuition.status is not HorizonStatus.PENDING:
        raise ValidationFailedError("Only an intuition still waiting can be let go.")
    intuition.status = HorizonStatus.WASTED
    return Effect("A sensed world stayed a legend: the intuition was let go.", intuition.id, values={"intuition_id": intuition.id})


@player_action("intuition:discard_all", ActionKind.DISCARD_INTUITION)
async def discard_all(scope: PlayerScope, command: DiscardAll) -> Effect:
    waiting = list(await scope.session.scalars(select(HorizonIntuitionRow).where(HorizonIntuitionRow.status == HorizonStatus.PENDING)))
    for intuition in waiting:
        intuition.status = HorizonStatus.WASTED
    return Effect(f"{len(waiting)} waiting intuitions were let go.", values={"discarded": len(waiting)})


async def sensed_step(scope: PlayerScope, step_id: int) -> DeferredStepRow:
    step = await scope.session.get(DeferredStepRow, step_id)
    if step is None or step.kind is not DeferredStepKind.SENSED_WORLD:
        raise NotFoundError("No such sensed world waiting to be born.")
    return step


@player_action("sensed_world:request", ActionKind.EDIT_RECORD)
async def request_sensed(scope: PlayerScope, command: IntuitionTarget) -> Effect:
    intuition = await scope.session.get(HorizonIntuitionRow, command.intuition_id)
    if intuition is None or intuition.status is not HorizonStatus.PENDING:
        raise ValidationFailedError("Only an intuition still waiting can be brought toward a world.")
    steps = await scope.session.scalars(select(DeferredStepRow).where(DeferredStepRow.kind == DeferredStepKind.SENSED_WORLD))
    if any(step.payload.get("intuition_id") == intuition.id and step.status in OPEN_STEPS for step in steps):
        raise ValidationFailedError("That sensed world is already waiting to be born.")
    step = DeferredStepRow(
        epoch=await scope.epoch(), kind=DeferredStepKind.SENSED_WORLD, requested_by_node_id=intuition.mortal_entity_id, payload={"intuition_id": intuition.id}
    )
    scope.session.add(step)
    await scope.session.flush()
    return Effect("The sensed world will be born when the next work of the age runs.", values={"step_id": step.id})


@player_action("sensed_world:hold", ActionKind.EDIT_RECORD)
async def hold_sensed(scope: PlayerScope, command: HoldSensedStep) -> Effect:
    step = await sensed_step(scope, command.step_id)
    if step.status not in (DeferredStepStatus.PENDING, DeferredStepStatus.HELD):
        raise ValidationFailedError("Only a sensed world still waiting can be held or released.")
    step.status = DeferredStepStatus.HELD if command.hold else DeferredStepStatus.PENDING
    return Effect("The sensed world waits on your word." if command.hold else "The sensed world may be born again.", values={"step_id": step.id})


@player_action("sensed_world:retry", ActionKind.EDIT_RECORD)
async def retry_sensed(scope: PlayerScope, command: SensedStepTarget) -> Effect:
    step = await sensed_step(scope, command.step_id)
    if step.status is not DeferredStepStatus.FAILED:
        raise ValidationFailedError("Only a sensed world whose birth failed can be tried again.")
    step.status, step.attempts, step.error = DeferredStepStatus.PENDING, 0, None
    intuition = await scope.session.get(HorizonIntuitionRow, int(step.payload.get("intuition_id", 0)))
    if intuition is not None and intuition.status is not HorizonStatus.BORN:
        intuition.status = HorizonStatus.PENDING
    return Effect("The birth of the sensed world will be tried again.", values={"step_id": step.id})


@player_action("sensed_world:cancel", ActionKind.EDIT_RECORD)
async def cancel_sensed(scope: PlayerScope, command: SensedStepTarget) -> Effect:
    step = await sensed_step(scope, command.step_id)
    if step.status is DeferredStepStatus.RUNNING:
        raise ValidationFailedError("A sensed world being born right now cannot be called off.")
    await scope.session.delete(step)
    await scope.session.flush()
    return Effect("The waiting birth of the sensed world was called off.")
