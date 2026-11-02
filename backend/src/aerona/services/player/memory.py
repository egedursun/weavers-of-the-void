from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.belief_memory import event_to_legend, fulfil_prophecy, manifest_legend, retire_legend, retire_prophecy, revive_legend
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class LegendTarget(Command):
    legend_id: int


class ProphecyTarget(Command):
    prophecy_id: int


class EventTarget(Command):
    event_id: int


@player_action("legend:forget", ActionKind.FORGET_LEGEND)
async def forget_legend(scope: PlayerScope, command: LegendTarget) -> Effect:
    legend = await retire_legend(await scope.context("forget_legend"), command.legend_id)
    return Effect(f"{legend.name} was forgotten.", legend.id)


@player_action("legend:revive", ActionKind.REVIVE_LEGEND)
async def revive(scope: PlayerScope, command: LegendTarget) -> Effect:
    legend = await revive_legend(await scope.context("revive_legend"), command.legend_id)
    return Effect(f"{legend.name} is told again.", legend.id)


@player_action("legend:from_event", ActionKind.REVIVE_LEGEND)
async def legendify(scope: PlayerScope, command: EventTarget) -> Effect:
    legend = await event_to_legend(await scope.context("legendify"), command.event_id)
    return Effect(f"{legend.name} became a legend.", legend.id, created_ids=(legend.id,))


@player_action("legend:manifest", ActionKind.MANIFESTATION)
async def manifest(scope: PlayerScope, command: LegendTarget) -> Effect:
    shape = await manifest_legend(await scope.context("manifest_legend"), command.legend_id)
    return Effect(f"{shape.name} walked out of the tale.", shape.id, created_ids=(shape.id,))


@player_action("prophecy:fulfil", ActionKind.FULFIL_PROPHECY)
async def fulfil(scope: PlayerScope, command: ProphecyTarget) -> Effect:
    prophecy = await fulfil_prophecy(await scope.context("fulfil_prophecy"), command.prophecy_id)
    return Effect(f"{prophecy.name} was fulfilled.", prophecy.id)


@player_action("prophecy:forget", ActionKind.FORGET_LEGEND)
async def forget_prophecy(scope: PlayerScope, command: ProphecyTarget) -> Effect:
    prophecy = await retire_prophecy(await scope.context("forget_prophecy"), command.prophecy_id)
    return Effect(f"{prophecy.name} was forgotten unfulfilled.", prophecy.id)
