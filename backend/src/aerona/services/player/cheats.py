from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.recording.record import record
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
    message = (
        await record(ctx, "player.cheat.essence", roles={IncidentRole.ACTOR: creator.id}, facts={"amount": command.amount}, kind=ChronicleKind.SYSTEM)
    ).text
    return Effect(message, creator.id, essence_gained=command.amount)
