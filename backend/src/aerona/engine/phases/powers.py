from aerona.engine.concealment.truths import keep_concealment
from aerona.engine.phase import Phase
from aerona.engine.powers.phase import keep_powers
from aerona.engine.powers.society import keep_powered_society
from aerona.engine.powers.systems import keep_systems

PHASES = (
    Phase("magic_systems", keep_systems),
    Phase("powers", keep_powers),
    Phase("powered_society", keep_powered_society),
    Phase("concealment", keep_concealment),
)
