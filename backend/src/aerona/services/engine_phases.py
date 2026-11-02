from dataclasses import dataclass
from enum import StrEnum

from aerona.constants.engine import HEAVY_PHASES, UNRUNNABLE_PHASES
from aerona.engine import pipeline
from aerona.engine.phase import Phase
from aerona.rules.registry import Rules


class PhaseStage(StrEnum):
    TICK = "tick"
    PRE_TRANSITION = "pre_transition"
    TRANSITION = "transition"
    POST_TRANSITION = "post_transition"


@dataclass(frozen=True)
class PhaseInfo:
    name: str
    stage: PhaseStage
    enabled: bool
    essential: bool
    heavy: bool
    runnable: bool
    rule_key: str


STAGES: tuple[tuple[PhaseStage, tuple[Phase, ...]], ...] = (
    (PhaseStage.TICK, pipeline.TICK_ORDER),
    (PhaseStage.PRE_TRANSITION, pipeline.PRE_TRANSITION_ORDER),
    (PhaseStage.TRANSITION, pipeline.TRANSITION_ORDER),
    (PhaseStage.POST_TRANSITION, pipeline.POST_TRANSITION_ORDER),
)


def list_phases(rules: Rules) -> list[PhaseInfo]:
    disabled = pipeline.disabled_by_rules(rules)
    infos: list[PhaseInfo] = []
    for stage, phases in STAGES:
        for phase in phases:
            infos.append(
                PhaseInfo(
                    name=phase.name,
                    stage=stage,
                    enabled=phase.name not in disabled,
                    essential=phase.name in pipeline.ESSENTIAL_PHASES,
                    heavy=phase.name in HEAVY_PHASES or stage is PhaseStage.TRANSITION,
                    runnable=phase.name not in UNRUNNABLE_PHASES,
                    rule_key=phase.name,
                )
            )
    return infos
