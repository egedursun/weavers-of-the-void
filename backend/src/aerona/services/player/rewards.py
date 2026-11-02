from pydantic import Field

from aerona.core.errors import NotFoundError
from aerona.domain.enums.action import ActionKind
from aerona.engine.gods.rewards import adjust_reward
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PERCENT_MAX = 100
MANUAL_REASON = "set by the Creator"


class RewardShare(Command):
    entity_id: int
    taken_back_pct: int = Field(ge=0, le=PERCENT_MAX)
    thread_reverted: bool | None = None


@player_action("creation:reward", ActionKind.OVERRIDE_VERDICT)
async def set_reward(scope: PlayerScope, command: RewardShare) -> Effect:
    change = await adjust_reward(scope.session, scope.rules, command.entity_id, command.taken_back_pct, thread=command.thread_reverted, reason=MANUAL_REASON)
    if change is None:
        raise NotFoundError("This creation has no reward ledger, or nothing changed.")
    return Effect(
        f"The creation's reward is now {change.taken_back_pct}% taken back (XP {change.xp:+}, renown {change.renown:+}, essence {change.essence:+}).",
        command.entity_id,
        values={"taken_back_pct": change.taken_back_pct},
    )
