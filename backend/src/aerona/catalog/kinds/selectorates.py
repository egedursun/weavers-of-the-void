from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.regime import SelectorateKind
from aerona.domain.enums.society import SocialClass

ShareRule = Literal["adult_pct", "citizen_pct", "council_pct"]


@dataclass(frozen=True)
class Selectorate:
    classes: tuple[SocialClass, ...]
    share_rule: ShareRule | None = None

    @property
    def by_class(self) -> bool:
        return bool(self.classes)


S = SelectorateKind
SELECTORATE_BASES: Mapping[SelectorateKind, Selectorate] = total(
    SelectorateKind,
    {
        S.TRIBE: Selectorate((), "adult_pct"),
        S.NOBLES: Selectorate((SocialClass.NOBLE,)),
        S.COUNCIL: Selectorate((SocialClass.NOBLE, SocialClass.MERCHANT), "council_pct"),
        S.ARMY: Selectorate((SocialClass.WARRIOR,)),
        S.PRIESTS: Selectorate((SocialClass.PRIEST,)),
        S.CITIZENS: Selectorate((), "citizen_pct"),
        S.ALGORITHM: Selectorate((SocialClass.PROFESSIONAL, SocialClass.OFFICIAL)),
        S.PARTY: Selectorate((SocialClass.OFFICIAL, SocialClass.CITIZEN, SocialClass.WORKER)),
        S.SHAREHOLDERS: Selectorate((SocialClass.MERCHANT, SocialClass.PROFESSIONAL)),
    },
)
