from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.mechanics_assignment import weigh_everything
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Empty(Command):
    pass


@player_action("mechanics:weigh", ActionKind.ASSIGN_MECHANICS)
async def weigh_all(scope: PlayerScope, command: Empty) -> Effect:
    weighed = await weigh_everything(scope.session, scope.rules)
    return Effect(f"{several(weighed, 'resource', 'resources')} and laws were weighed and given their workings.", values={"weighed": weighed})
