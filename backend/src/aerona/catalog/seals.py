from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.couplings import SealKind, SealLink
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SealSpec:
    label: str
    decay: Callable[[Rules], int]
    strength: Callable[[Rules], int]
    link: SealLink | None = None


SEALS: Mapping[SealKind, SealSpec] = total(
    SealKind,
    {
        SealKind.STRUCTURE: SealSpec("Walls and gates", lambda rules: rules.deep_seals.decay, lambda rules: rules.deep_seals.structure_strength),
        SealKind.RITE: SealSpec("A warding rite", lambda rules: rules.deep_seals.rite_decay, lambda rules: rules.deep_seals.rite_strength),
        SealKind.DIVINE: SealSpec("A god's hand", lambda rules: rules.deep_seals.divine_decay, lambda rules: rules.deep_seals.divine_strength),
        SealKind.POWER: SealSpec("An innate power", lambda rules: rules.deep_seals.power_decay, lambda rules: rules.deep_seals.power_strength, SealLink.POWER),
        SealKind.LIVING: SealSpec(
            "A grown barrier", lambda rules: rules.deep_seals.living_decay, lambda rules: rules.deep_seals.living_strength, SealLink.LINE
        ),
        SealKind.PACT: SealSpec("A sworn pact", lambda rules: rules.deep_seals.pact_decay, lambda rules: rules.deep_seals.pact_strength, SealLink.OATH),
    },
)
LINK_LABELS: Mapping[SealLink, str] = total(SealLink, {SealLink.OATH: "oath", SealLink.POWER: "power", SealLink.LINE: "living line"})
