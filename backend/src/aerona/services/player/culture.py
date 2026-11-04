from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import LanguageRegister, SpeakerKind, TraditionEffectKind
from aerona.engine.lore import culture_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Register(Command):
    holder_id: int
    kind: LanguageRegister
    language_id: int | None = None
    hold: bool = True


class PairTarget(Command):
    first_id: int
    second_id: int


class SpeakerTarget(Command):
    community_id: int
    language_id: int
    kind: SpeakerKind = SpeakerKind.SECOND


class KeeperTarget(Command):
    tradition_id: int
    community_id: int


class TraditionEffect(Command):
    tradition_id: int
    effect: TraditionEffectKind
    target: str = ""
    magnitude: int


class TraditionTarget(Command):
    tradition_id: int


@player_action("language:register", ActionKind.EDIT_RECORD)
async def set_register(scope: PlayerScope, command: Register) -> Effect:
    ctx = await scope.context("language_register")
    row = await culture_control.set_register(ctx, command.holder_id, command.kind, command.language_id, hold=command.hold)
    label = command.kind.value
    if row is None:
        return Effect(f"The {label} register is left to the world.", command.holder_id)
    return Effect(f"The {label} register is set{' and held' if command.hold else ''}.", command.holder_id)


@player_action("language:release_understanding", ActionKind.EDIT_RECORD)
async def release_understanding(scope: PlayerScope, command: PairTarget) -> Effect:
    row = await culture_control.release_intelligibility(await scope.context("language_release_understanding"), command.first_id, command.second_id)
    return Effect(f"The world measures the two tongues again (now {row.value}%).", command.first_id)


@player_action("language:release_speakers", ActionKind.EDIT_RECORD)
async def release_speakers(scope: PlayerScope, command: SpeakerTarget) -> Effect:
    row = await culture_control.release_speakers(await scope.context("language_release_speakers"), command.community_id, command.language_id, command.kind)
    return Effect(f"The share of speakers ({row.share}%) moves with the world again.", command.community_id)


@player_action("tradition:release_participation", ActionKind.EDIT_RECORD)
async def release_participation(scope: PlayerScope, command: KeeperTarget) -> Effect:
    row = await culture_control.release_participation(await scope.context("tradition_release_participation"), command.tradition_id, command.community_id)
    return Effect(f"How fully they keep it ({row.participation}%) moves with the world again.", command.tradition_id)


@player_action("tradition:effect", ActionKind.EDIT_RECORD)
async def set_tradition_effect(scope: PlayerScope, command: TraditionEffect) -> Effect:
    ctx = await scope.context("tradition_effect")
    row = await culture_control.set_tradition_effect(ctx, command.tradition_id, command.effect, command.target, command.magnitude)
    label = command.effect.value.replace("_", " ")
    return Effect(f"It brings {label} at {row.magnitude}." if row is not None else f"It no longer brings {label}.", command.tradition_id)


@player_action("tradition:reseed", ActionKind.EDIT_RECORD)
async def reseed_tradition(scope: PlayerScope, command: TraditionTarget) -> Effect:
    count = await culture_control.reseed_tradition(await scope.context("tradition_reseed"), command.tradition_id)
    return Effect(f"Its {count} effects are drawn again from its kind.", command.tradition_id)
