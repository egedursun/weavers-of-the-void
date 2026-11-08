from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.discovery import AnomalyKind
from aerona.engine.lore import theory_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class TheoryAdherent(Command):
    theory_id: int
    holder_id: int
    strength: int = 50
    orthodox: bool = False
    present: bool = True


class TheoryAnomaly(Command):
    theory_id: int
    kind: AnomalyKind
    weight: int = 1
    witness_id: int | None = None


class RevealTruth(Command):
    theory_id: int
    community_id: int


class Practitioner(Command):
    art_form_id: int
    holder_id: int
    mastery: int = 30
    present: bool = True


@player_action("theory:adherent", ActionKind.EDIT_RECORD)
async def set_adherent(scope: PlayerScope, command: TheoryAdherent) -> Effect:
    ctx = await scope.context("theory_adherent")
    row = await theory_control.set_adherent(
        ctx, command.theory_id, command.holder_id, strength=command.strength, orthodox=command.orthodox, present=command.present
    )
    if row is None:
        return Effect("They no longer hold that theory.", command.theory_id)
    return Effect("It is now their ruling account." if row.orthodox else f"They hold it at {row.strength}%.", command.theory_id)


@player_action("theory:anomaly", ActionKind.EDIT_RECORD)
async def add_anomaly(scope: PlayerScope, command: TheoryAnomaly) -> Effect:
    await theory_control.add_anomaly(await scope.context("theory_anomaly"), command.theory_id, command.kind, command.weight, command.witness_id)
    return Effect("An anomaly now weighs against it.", command.theory_id)


@player_action("theory:reveal", ActionKind.EDIT_RECORD)
async def reveal_truth(scope: PlayerScope, command: RevealTruth) -> Effect:
    await theory_control.reveal_truth(await scope.context("theory_reveal"), command.theory_id, command.community_id)
    return Effect("You made its truth known.", command.theory_id)


@player_action("art_form:practitioner", ActionKind.EDIT_RECORD)
async def set_practitioner(scope: PlayerScope, command: Practitioner) -> Effect:
    ctx = await scope.context("art_form_practitioner")
    row = await theory_control.set_practitioner(ctx, command.art_form_id, command.holder_id, mastery=command.mastery, present=command.present)
    return Effect("They no longer practise it." if row is None else f"They practise it with {row.mastery}% mastery.", command.art_form_id)
