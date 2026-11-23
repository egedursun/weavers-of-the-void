from aerona.core.total import total
from aerona.domain.enums.climes import OscillationPhase
from aerona.domain.enums.culture import Technique

SKY_READING = (Technique.ECLIPSE_PREDICTION, Technique.ASTRONOMY_INSTRUMENTS)

PHASE_AT_OSCILLATION_PHASES = (OscillationPhase.WARM, OscillationPhase.NEUTRAL, OscillationPhase.COLD)

PHASE_BASE = total(
    OscillationPhase,
    {
        OscillationPhase.NEUTRAL: OscillationPhase.NEUTRAL,
        OscillationPhase.WARM: OscillationPhase.WARM,
        OscillationPhase.COLD: OscillationPhase.COLD,
        OscillationPhase.STRONG_WARM: OscillationPhase.WARM,
        OscillationPhase.STRONG_COLD: OscillationPhase.COLD,
    },
)
PHASE_SIGN = total(
    OscillationPhase,
    {OscillationPhase.NEUTRAL: 0, OscillationPhase.WARM: 1, OscillationPhase.COLD: -1, OscillationPhase.STRONG_WARM: 2, OscillationPhase.STRONG_COLD: -2},
)
STRONGER = {OscillationPhase.WARM: OscillationPhase.STRONG_WARM, OscillationPhase.COLD: OscillationPhase.STRONG_COLD}
