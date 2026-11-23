from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission, Visibility
from aerona.domain.enums.body import BodyFunction, ConditionKind
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.mind import NeedKind, ValueAxis
from aerona.rules.registry import Rules

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
    quenches: frozenset[NeedKind] = frozenset()
    grants: frozenset[BodyFunction] = frozenset()
    sanity_loss: int = 0
    ageless: bool = False
    sunlight_harm: bool = False
    transforms: bool = False
    recruits: bool = False
    appearance: str = ""
    fears_source: bool = False
    changes_body: bool = False
    lucky: bool = False
    binds: bool = False
    fades: bool = False


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
    line: Callable[[Rules], int] | None = None


def stats(**values: int) -> MappingProxyType[str, int]:
    return MappingProxyType(values)


PACKAGES: MappingProxyType[PackageKind, PackageSpec] = total(
    PackageKind,
    {
        P.SNAKE_VENOM: PackageSpec(
            P.SNAKE_VENOM,
            "Venom",
            "A venom that rots the flesh where it enters, then leaves a lasting weakness.",
            frozenset({T.BITE, T.INHALATION}),
            0,
            (
                StageSpec("Necrosis", 1, ConditionKind.CHRONIC_ILLNESS, 3, stats(endurance=-10), appearance="lasting harm where the venom entered"),
                StageSpec("Lasting weakness", None, ConditionKind.CHRONIC_ILLNESS, 1, stats(strength=-5), appearance="a puckered scar"),
            ),
            frozenset({C.MEDICINE, C.POWER, C.SYMBIONT, C.AUGMENT}),
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
            frozenset({C.TIME, C.MEDICINE, C.RITE, C.SYMBIONT}),
            Visibility.NOTICEABLE,
        ),
        P.DRUG_DEPENDENCE: PackageSpec(
            P.DRUG_DEPENDENCE,
            "Drug dependence",
            "A hunger for a substance, with withdrawal when the supply fails.",
            frozenset({T.INGESTION, T.INHALATION}),
            0,
            (
                StageSpec("Craving", 1, ConditionKind.ADDICTION, 2, needs=frozenset({NeedKind.PLEASURE})),
                StageSpec("Dependence", None, ConditionKind.ADDICTION, 4, needs=frozenset({NeedKind.PLEASURE})),
            ),
            frozenset({C.TIME, C.MEDICINE, C.TECHNIQUE, C.SYMBIONT, C.AUGMENT}),
            Visibility.NOTICEABLE,
            cure_level=2,
        ),
        P.LYCANTHROPY: PackageSpec(
            P.LYCANTHROPY,
            "Beast curse",
            "Under the full face of the world's first moon the bearer becomes a thinking beast; a bite passes the curse on.",
            frozenset({T.BITE, T.CURSE}),
            1,
            (
                StageSpec(
                    "Moon-changed",
                    None,
                    stats=stats(strength=15, charisma=-10),
                    grants=frozenset({BodyFunction.VENOM}),
                    transforms=True,
                    appearance="the unrest of a body that changes",
                ),
            ),
            frozenset({C.RITE, C.QUEST, C.DIVINE, C.TRANSFER}),
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
            (
                StageSpec(
                    "Blood-cursed",
                    None,
                    ConditionKind.ENDLESS_HUNGER,
                    2,
                    stats(strength=10),
                    quenches=frozenset({NeedKind.SUSTENANCE}),
                    grants=frozenset({BodyFunction.VENOM}),
                    ageless=True,
                    sunlight_harm=True,
                    appearance="the look of one who no longer ages",
                ),
            ),
            frozenset({C.RITE, C.QUEST, C.DIVINE, C.TRANSFER}),
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
            (
                StageSpec(
                    "Blessed",
                    None,
                    ConditionKind.CHOSEN_MARK,
                    1,
                    stats(strength=10),
                    grants=frozenset({BodyFunction.PRESENCE}),
                    fears_source=True,
                    appearance="the mark of a god's favour",
                ),
            ),
            frozenset({C.RITE, C.DIVINE}),
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
                StageSpec("Tainted", 2, ConditionKind.VOID_TAINT, 2, sanity_loss=5, appearance="signs of a taint from outside"),
                StageSpec("Maddened", 2, ConditionKind.VISIONS, 3, sanity_loss=10, appearance="a mind turned toward what others cannot sense"),
                StageSpec(
                    "Claimed",
                    None,
                    ConditionKind.VOID_TAINT,
                    5,
                    sanity_loss=5,
                    quenches=frozenset({NeedKind.BELONGING}),
                    recruits=True,
                    appearance="the weight of a memory that keeps returning",
                ),
            ),
            frozenset({C.RITE, C.QUEST, C.DIVINE, C.POWER}),
            Visibility.NOTICEABLE,
            cure_level=3,
        ),
        P.POSSESSION: PackageSpec(
            P.POSSESSION,
            "Possession",
            "A bound spirit rides the bearer and speaks with their mouth.",
            frozenset({T.RITE, T.CURSE}),
            0,
            (StageSpec("Ridden", None, ConditionKind.POSSESSION, 3, appearance="another will acting through them"),),
            frozenset({C.RITE, C.DIVINE, C.POWER, C.TRANSFER}),
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
            frozenset({C.TIME, C.RITE, C.MEDICINE, C.POWER, C.AUGMENT}),
            Visibility.HIDDEN,
        ),
        P.HUNGER_CURSE: PackageSpec(
            P.HUNGER_CURSE,
            "Hunger curse",
            "A god's curse of a hunger that no meal fills.",
            frozenset({T.CURSE}),
            0,
            (StageSpec("Starving", None, ConditionKind.ENDLESS_HUNGER, 3, needs=frozenset({NeedKind.SUSTENANCE}), appearance="wasting despite every meal"),),
            frozenset({C.RITE, C.QUEST, C.DIVINE}),
            Visibility.OBVIOUS,
            cure_level=2,
        ),
        P.WARPING: PackageSpec(
            P.WARPING,
            "Warping",
            "What long exposure to magic does to a body and a mind.",
            frozenset({T.EXPERIENCE}),
            0,
            (
                StageSpec("Touched", None, None, 1, stats=stats(willpower=5)),
                StageSpec("Marked", None, None, 1, stats=stats(willpower=5, charisma=-5), appearance="marked by long exposure to magic"),
                StageSpec("Unmoored", None, ConditionKind.VISIONS, 2, sanity_loss=5, ageless=True, appearance="marked by long exposure to magic"),
            ),
            frozenset({C.RITE, C.QUEST, C.DIVINE, C.POWER, C.TRANSFER, C.AUGMENT}),
            Visibility.NOTICEABLE,
            cure_level=3,
        ),
        P.VIS_DEPENDENCE: PackageSpec(
            P.VIS_DEPENDENCE,
            "Vis dependence",
            "A body that has come to need magic to keep its years.",
            frozenset({T.RITE}),
            0,
            (StageSpec("Dependent", None, ConditionKind.ADDICTION, 1),),
            frozenset({C.RITE, C.MEDICINE, C.SYMBIONT, C.POWER}),
            Visibility.HIDDEN,
            cure_level=2,
        ),
        P.GEAS_DOOM: PackageSpec(
            P.GEAS_DOOM,
            "Geas doom",
            "The doom that falls on one who broke a geas.",
            frozenset({T.CURSE}),
            0,
            (StageSpec("Doomed", None, ConditionKind.CHRONIC_ILLNESS, 2, stats=stats(strength=-10, charisma=-5)),),
            frozenset({C.RITE, C.QUEST, C.DIVINE}),
            Visibility.NOTICEABLE,
            cure_level=3,
        ),
        P.FORTUNE: PackageSpec(
            P.FORTUNE,
            "Fortune",
            "A lasting shift of luck, for good or for ill, that holds and then fades; a line's fortune passes to its children.",
            frozenset({T.GAZE, T.CURSE, T.RITE, T.BIRTH}),
            0,
            (StageSpec("Holding", 3, lucky=True), StageSpec("Fading", 2, lucky=True, fades=True)),
            frozenset({C.RITE, C.DIVINE, C.QUEST, C.TIME}),
            Visibility.NOTICEABLE,
            cure_level=2,
            hereditary=True,
            line=lambda rules: rules.packages.fortune_line_pct,
        ),
        P.TRANSFORMATION: PackageSpec(
            P.TRANSFORMATION,
            "Transformation",
            "A change of the body into another plan, kind or substance, lasting or coming back at a set sign.",
            frozenset({T.CURSE, T.BITE, T.RITE, T.INGESTION, T.EXPERIENCE}),
            0,
            (StageSpec("Changed", 1, changes_body=True), StageSpec("Between changes", None)),
            frozenset({C.RITE, C.QUEST, C.DIVINE, C.POWER}),
            Visibility.OBVIOUS,
            contagion=frozenset({T.BITE}),
            cure_level=3,
        ),
        P.CHARM: PackageSpec(
            P.CHARM,
            "Charm",
            "A compelled bond of love, obedience or devotion toward a person or a god, which wears off unless renewed.",
            frozenset({T.INGESTION, T.GAZE, T.RITE, T.INTIMATE}),
            0,
            (StageSpec("Bound", None, binds=True), StageSpec("Fading", 1, binds=True, fades=True)),
            frozenset({C.RITE, C.TIME, C.MEDICINE, C.POWER}),
            Visibility.HIDDEN,
            cure_level=2,
        ),
        P.SOUL_TRAPPED: PackageSpec(
            P.SOUL_TRAPPED,
            "Soul trapped",
            "A soul held in a mythic realm while its body lies asleep, until another quest brings it back.",
            frozenset({T.EXPERIENCE}),
            0,
            (StageSpec("Lost in the myth", None, ConditionKind.COMATOSE, 3),),
            frozenset({C.QUEST, C.DIVINE, C.TRANSFER}),
            Visibility.OBVIOUS,
            cure_level=3,
        ),
    },
)

CURSE_PACKAGES: MappingProxyType[CurseKind, PackageKind | None] = total(
    CurseKind,
    {
        CurseKind.NONE: None,
        CurseKind.BLOODTHIRST: P.VAMPIRISM,
        CurseKind.MISFORTUNE: P.FORTUNE,
        CurseKind.WASTING: P.GEAS_DOOM,
        CurseKind.MADNESS: P.TRAUMA,
        CurseKind.BETRAYAL: P.CHARM,
        CurseKind.BARRENNESS: P.FORTUNE,
        CurseKind.TRANSFORMATION: P.TRANSFORMATION,
        CurseKind.SLEEP: P.SOUL_TRAPPED,
        CurseKind.SILENCE: P.FORTUNE,
        CurseKind.HUNGER: P.HUNGER_CURSE,
        CurseKind.FORGETTING: P.TRAUMA,
        CurseKind.RESTLESSNESS: P.TRAUMA,
        CurseKind.LINE_CURSE: P.FORTUNE,
        CurseKind.PLACE_CURSE: P.FORTUNE,
        CurseKind.COMPULSION: P.CHARM,
        CurseKind.AGING: P.GEAS_DOOM,
        CurseKind.EXPOSURE: P.FORTUNE,
    },
)
NEW_CURSE_KINDS = (CurseKind.TRANSFORMATION, CurseKind.COMPULSION)
