from pydantic import Field
from sqlalchemy import delete, func, select

from aerona.db.tables.agency import AgentTurnRow, TurnCounterRow
from aerona.domain.enums.action import ActionKind
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class SonTarget(Command):
    son_id: int


class TurnRank(Command):
    son_id: int
    rank: int | None = Field(default=None, ge=1)


@player_action("son:reset_counters", ActionKind.EDIT_RECORD)
async def reset_counters(scope: PlayerScope, command: SonTarget) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    epoch = (await scope.cosmos()).epoch
    scope_filter = (TurnCounterRow.agent_node_id == son.id, TurnCounterRow.epoch == epoch)
    cleared = int(await scope.session.scalar(select(func.count()).select_from(TurnCounterRow).where(*scope_filter)) or 0)
    await scope.session.execute(delete(TurnCounterRow).where(*scope_filter))
    turn = await scope.session.get(AgentTurnRow, son.id)
    if turn is not None and turn.epoch == epoch:
        turn.context = turn.context.model_copy(update={"counters": {}})
    return Effect(f"{son.name}'s tool counters for this epoch were cleared ({cleared}).", son.id, values={"cleared": cleared})


@player_action("son:turn_rank", ActionKind.EDIT_RECORD)
async def set_turn_rank(scope: PlayerScope, command: TurnRank) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    son.turn_rank = command.rank
    await scope.session.flush()
    if command.rank is None:
        return Effect(f"{son.name} again waits for his initiative in the gods' turn.", son.id, values={"rank": None})
    return Effect(
        f"{son.name} is set to act at place {command.rank} in the gods' turn, before initiative decides the rest.", son.id, values={"rank": command.rank}
    )
