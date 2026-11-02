from aerona.constants.engine import UNRUNNABLE_PHASES
from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.pipeline import find_phase
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

COUNTERS_SHOWN = 6


class RunPhase(Command):
    phase: str
    replay: bool = False


def summarize(counters: dict[str, int]) -> str:
    ranked = sorted(counters.items(), key=lambda item: (-item[1], item[0]))[:COUNTERS_SHOWN]
    return ", ".join(f"{name} {value}" for name, value in ranked)


@player_action("engine:run_phase", ActionKind.OTHER)
async def run_phase(scope: PlayerScope, command: RunPhase) -> Effect:
    if command.phase in UNRUNNABLE_PHASES:
        raise ValidationFailedError(f"The {command.phase} step cannot be run on its own; advance the epoch instead.")
    phase = find_phase(command.phase)
    manual = await scope.context(f"phase.{phase.name}")
    ctx = TickContext(manual.environment, scope.session, phase.name) if command.replay else manual
    await run_guarded(phase, ctx)
    prefix = f"{ctx.phase}."
    counters = {name.removeprefix(prefix): value for name, value in ctx.environment.stats.counters.items() if value}
    detail = summarize(counters)
    seed = "with the epoch's own seed" if command.replay else "now"
    message = f"The {phase.name} step ran {seed}" + (f": {detail}." if detail else " and found nothing to change.")
    return Effect(message, values={"changes": sum(counters.values()), "stream": ctx.phase, "world_seed": ctx.environment.world_seed})
