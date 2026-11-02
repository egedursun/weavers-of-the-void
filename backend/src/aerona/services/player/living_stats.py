from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.living_stats import run_living_stats
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Empty(Command):
    pass


@player_action("records:living_stats", ActionKind.OTHER)
async def run_now(scope: PlayerScope, command: Empty) -> Effect:
    await run_living_stats(scope.session, scope.rules)
    return Effect("Mysteries, works and prophecies took their course.")
