from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.mind import DreamKind

DREAM_TRUTH: Mapping[DreamKind, int] = total(
    DreamKind,
    {
        DreamKind.ORDINARY: 50,
        DreamKind.NIGHTMARE: 50,
        DreamKind.LONGING: 50,
        DreamKind.PROPHETIC: 100,
        DreamKind.VISITATION: 50,
        DreamKind.SHARED: 50,
        DreamKind.LUCID: 60,
        DreamKind.MEMORY: 90,
    },
)
