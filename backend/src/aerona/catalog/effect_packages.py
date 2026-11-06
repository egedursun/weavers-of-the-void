from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission, Visibility
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.mind import NeedKind, ValueAxis

P = PackageKind
T = Transmission
C = CureKind


@dataclass(frozen=True)
class StageSpec:
    label: str
    epochs: int | None
    condition: ConditionKind | None = None
    severity: int = 1
    stats: MappingProxyType[str, int] = field(default_factory=lambda: MappingProxyType({}))
    values: MappingProxyType[ValueAxis, int] = field(default_factory=lambda: MappingProxyType({}))
    needs: frozenset[NeedKind] = frozenset()
    sanity_loss: int = 0
    ageless: bool = False
    sunlight_harm: bool = False
    transforms: bool = False
    recruits: bool = False
    fears_source: bool = False


@dataclass(frozen=True)
class PackageSpec:
    kind: PackageKind
    label: str
    description: str
    transmissions: frozenset[Transmission]
    onset: int
    stages: tuple[StageSpec, ...]
    cures: frozenset[CureKind]
    visibility: Visibility
    contagion: frozenset[Transmission] = frozenset()
    cure_level: int = 1
    hereditary: bool = False


def stats(**values: int) -> MappingProxyType[str, int]:
    return MappingProxyType(values)


PACKAGES: MappingProxyType[PackageKind, PackageSpec] = MappingProxyType(
    {
        P.SNAKE_VENOM: PackageSpec(
            P.SNAKE_VENOM,
            "Venom",
            "A venom that rots the flesh around the bite, then leaves a lasting weakness.",
            frozenset({T.BITE}),
            0,
            (
                StageSpec("Necrosis", 1, ConditionKind.CHRONIC_ILLNESS, 3, stats(endurance=-10)),
                StageSpec("Lasting weakness", None, ConditionKind.CHRONIC_ILLNESS, 1, stats(strength=-5)),
            ),
            frozenset({C.MEDICINE}),
            Visibility.OBVIOUS,
            cure_level=2,
        ),
        P.DRINK_DEPENDENCE: PackageSpec(
            P.DRINK_DEPENDENCE,
            "Drink dependence",
            "A need for strong drink that turns to withdrawal when it is denied.",
            frozenset({T.INGESTION}),
            1,
            (
                StageSpec("Craving", 2, ConditionKind.ADDICTION, 1, needs=frozenset({NeedKind.PLEASURE})),
                StageSpec("Dependence", None, ConditionKind.ADDICTION, 3, needs=frozenset({NeedKind.PLEASURE})),
            ),
            frozenset({C.TIME, C.MEDICINE, C.RITE}),
            Visibility.NOTICEABLE,
        ),
        P.DRUG_DEPENDENCE: PackageSpec(
            P.DRUG_DEPENDENCE,
            "Drug dependence",
            "A hunger for a smoke, an elixir or a sacred herb, with withdrawal when the supply fails.",
            frozenset({T.INGESTION, T.INHALATION}),
            0,
            (
                StageSpec("Craving", 1, ConditionKind.ADDICTION, 2, needs=frozenset({NeedKind.PLEASURE})),
                StageSpec("Dependence", None, ConditionKind.ADDICTION, 4, needs=frozenset({NeedKind.PLEASURE})),
            ),
            frozenset({C.TIME, C.MEDICINE, C.TECHNIQUE}),
            Visibility.NOTICEABLE,
            cure_level=2,
        ),
        P.LYCANTHROPY: PackageSpec(
            P.LYCANTHROPY,
            "Beast curse",
            "Under the full face of the world's first moon the bearer becomes a thinking beast; a bite passes the curse on.",
            frozenset({T.BITE, T.CURSE}),
            1,
            (StageSpec("Moon-changed", None, stats=stats(strength=15, charisma=-10), transforms=True),),
            frozenset({C.RITE, C.QUEST}),
            Visibility.HIDDEN,
            contagion=frozenset({T.BITE}),
            cure_level=3,
        ),
        P.VAMPIRISM: PackageSpec(
            P.VAMPIRISM,
            "Blood curse",
            "The bearer stops ageing, hungers for blood and burns under the sun; a feeding can pass it on.",
            frozenset({T.BLOOD, T.CURSE, T.RITE}),
            1,
            (StageSpec("Blood-cursed", None, ConditionKind.ENDLESS_HUNGER, 2, stats(strength=10), ageless=True, sunlight_harm=True),),
            frozenset({C.RITE, C.QUEST}),
            Visibility.HIDDEN,
            contagion=frozenset({T.BLOOD}),
            cure_level=4,
        ),
        P.DIVINE_BLESSING: PackageSpec(
            P.DIVINE_BLESSING,
            "Divine blessing",
            "A god's favour: strength beyond the mortal measure, and a fear of the giver.",
            frozenset({T.RITE, T.BIRTH}),
            0,
            (StageSpec("Blessed", None, ConditionKind.CHOSEN_MARK, 1, stats(strength=10), fears_source=True),),
            frozenset({C.RITE}),
            Visibility.NOTICEABLE,
            hereditary=True,
        ),
        P.VOID_TAINT: PackageSpec(
            P.VOID_TAINT,
            "Void taint",
            "A touch from outside that grows into madness and ends in the service of an outer cult.",
            frozenset({T.CONTACT, T.INHALATION, T.GAZE}),
            0,
            (
                StageSpec("Tainted", 2, ConditionKind.VOID_TAINT, 2, sanity_loss=5),
                StageSpec("Maddened", 2, ConditionKind.VISIONS, 3, sanity_loss=10),
                StageSpec("Claimed", None, ConditionKind.VOID_TAINT, 5, sanity_loss=5, recruits=True),
            ),
            frozenset({C.RITE, C.QUEST}),
            Visibility.NOTICEABLE,
            cure_level=3,
        ),
        P.POSSESSION: PackageSpec(
            P.POSSESSION,
            "Possession",
            "A bound spirit rides the bearer and speaks with their mouth.",
            frozenset({T.RITE, T.CURSE}),
            0,
            (StageSpec("Ridden", None, ConditionKind.POSSESSION, 3),),
            frozenset({C.RITE}),
            Visibility.NOTICEABLE,
            cure_level=2,
        ),
        P.TRAUMA: PackageSpec(
            P.TRAUMA,
            "Trauma",
            "A memory too heavy to carry that returns in fear and grief.",
            frozenset({T.EXPERIENCE}),
            0,
            (
                StageSpec("Haunted", 3, ConditionKind.MELANCHOLY, 2, values=MappingProxyType({ValueAxis.MERCY: -5})),
                StageSpec("Scarred", None, ConditionKind.PARANOIA, 1),
            ),
            frozenset({C.TIME, C.RITE, C.MEDICINE}),
            Visibility.HIDDEN,
        ),
        P.HUNGER_CURSE: PackageSpec(
            P.HUNGER_CURSE,
            "Hunger curse",
            "A god's curse of a hunger that no meal fills.",
            frozenset({T.CURSE}),
            0,
            (StageSpec("Starving", None, ConditionKind.ENDLESS_HUNGER, 3, needs=frozenset({NeedKind.SUSTENANCE})),),
            frozenset({C.RITE, C.QUEST}),
            Visibility.OBVIOUS,
            cure_level=2,
        ),
    }
)
