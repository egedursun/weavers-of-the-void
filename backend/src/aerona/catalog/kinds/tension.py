from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.storyteller import TensionBand

TENSION_PUSH: Mapping[TensionBand, int] = total(TensionBand, {TensionBand.QUIET: 1, TensionBand.IN_BAND: 0, TensionBand.HEATED: -1})
