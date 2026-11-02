from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.travel import HorizonStatus
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class IntuitionTarget(Command):
    intuition_id: int


class DiscardAll(Command):
    pass


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
