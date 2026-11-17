from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.genetics import GiftStance


@dataclass(frozen=True)
class GiftStanceSpec:
    renown: bool = False
    fear_times: int = 0
    taxed: bool = False
    culls_the_gift: bool = False


GIFT_STANCES: Mapping[GiftStance, GiftStanceSpec] = total(
    GiftStance,
    {
        GiftStance.HONOURED: GiftStanceSpec(renown=True),
        GiftStance.FEARED: GiftStanceSpec(fear_times=1),
        GiftStance.PERSECUTED: GiftStanceSpec(fear_times=2, culls_the_gift=True),
        GiftStance.TAXED: GiftStanceSpec(taxed=True),
    },
)
