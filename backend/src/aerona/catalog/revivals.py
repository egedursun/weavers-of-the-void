from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.customs import RevivalGoal, RevivalWay
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.world import SkyEventKind
from aerona.rules.registry import Rules

W = RevivalWay
G = RevivalGoal
V = ValueAxis


@dataclass(frozen=True)
class WaySpec:
    label: str
    leaning: tuple[ValueAxis, ...]
    weight: Callable[[Rules], int]
    goals: frozenset[RevivalGoal]
    clashes: bool = False
    founds_faith: bool = False
    assimilates: bool = False
    awaits_sign: bool = False
    withdraws: bool = False
    pulls_to_ruler: bool = False


@dataclass(frozen=True)
class GoalSpec:
    label: str
    met: str


REVIVAL_WAYS: Mapping[RevivalWay, WaySpec] = total(
    RevivalWay,
    {
        W.RESTORE: WaySpec(
            "Restore the old ways",
            (V.TRADITION,),
            lambda rules: rules.revival.restore_weight,
            frozenset({G.REVIVE_LANGUAGE, G.RESTORE_GOD, G.EXPEL_FOREIGNERS, G.RESTORE_LAND, G.RESTORE_RULE}),
            clashes=True,
        ),
        W.SYNTHESIS: WaySpec(
            "Join old and new round a prophet",
            (V.PIETY,),
            lambda rules: rules.revival.synthesis_weight,
            frozenset({G.RESTORE_GOD, G.REVIVE_LANGUAGE}),
            founds_faith=True,
        ),
        W.ADOPT: WaySpec(
            "Take the rulers' ways",
            (V.XENOPHILIA,),
            lambda rules: rules.revival.adopt_weight,
            frozenset({G.RESTORE_RULE}),
            assimilates=True,
            pulls_to_ruler=True,
        ),
        W.AWAIT: WaySpec(
            "Wait for a foretold change",
            (V.SUPERSTITION,),
            lambda rules: rules.revival.await_weight,
            frozenset({G.RESTORE_RULE, G.RESTORE_LAND, G.EXPEL_FOREIGNERS}),
            awaits_sign=True,
        ),
        W.WITHDRAW: WaySpec(
            "Live apart from the rulers",
            (V.KINSHIP,),
            lambda rules: rules.revival.withdraw_weight,
            frozenset({G.REVIVE_LANGUAGE, G.RESTORE_GOD}),
            withdraws=True,
        ),
    },
)
REVIVAL_GOALS: Mapping[RevivalGoal, GoalSpec] = total(
    RevivalGoal,
    {
        G.REVIVE_LANGUAGE: GoalSpec("Revive the language", "its tongue is spoken with pride again"),
        G.RESTORE_GOD: GoalSpec("Restore the old god", "it worships its old god again"),
        G.EXPEL_FOREIGNERS: GoalSpec("Expel the foreigners", "no foreign realm presses on it any more"),
        G.RESTORE_LAND: GoalSpec("Take back the land", "its land is its own again"),
        G.RESTORE_RULE: GoalSpec("Rule itself", "it is ruled by its own again"),
    },
)
SIGNS = frozenset({SkyEventKind.COMET, SkyEventKind.ECLIPSE, SkyEventKind.SUPERNOVA, SkyEventKind.BLACK_SUN, SkyEventKind.ALIGNMENT})
