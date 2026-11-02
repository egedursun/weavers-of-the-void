from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.services.player.chronicle import tell
from aerona.services.player.lines import CHEAT
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class CheatEssence(Command):
    amount: int


@player_action("cheat:essence", ActionKind.OTHER)
async def cheat_essence(scope: PlayerScope, command: CheatEssence) -> Effect:
    cap = scope.rules.server.cheat_essence_max
    if not 1 <= command.amount <= cap:
        raise ValidationFailedError(f"Essence from nowhere must be between 1 and {cap} (world rule server.cheat_essence_max).")
    creator = await scope.creator()
    creator.essence += command.amount
    ctx = await scope.context("cheat")
    message = await tell(ctx, CHEAT, kind=ChronicleKind.SYSTEM, creator=creator.name, amount=command.amount)
    return Effect(message, creator.id, essence_gained=command.amount)
