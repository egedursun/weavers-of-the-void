from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.nature import Thermoregulation


@dataclass(frozen=True)
class ThermoSpec:
    keeps_warm: bool
    untouched: bool


THERMOREGULATION: Mapping[Thermoregulation, ThermoSpec] = total(
    Thermoregulation,
    {
        Thermoregulation.ENDOTHERM: ThermoSpec(keeps_warm=True, untouched=True),
        Thermoregulation.ECTOTHERM: ThermoSpec(keeps_warm=False, untouched=False),
        Thermoregulation.HETEROTHERM: ThermoSpec(keeps_warm=True, untouched=False),
        Thermoregulation.ATHERMIC: ThermoSpec(keeps_warm=False, untouched=True),
    },
)
WARM_KEEPING = frozenset(kind for kind, spec in THERMOREGULATION.items() if spec.keeps_warm)
UNTOUCHED = frozenset(kind for kind, spec in THERMOREGULATION.items() if spec.untouched)
