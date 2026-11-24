from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.activities import ActivityKind, SatisfactionSource
from aerona.domain.enums.mind import NeedKind

N = NeedKind
S = SatisfactionSource
A = ActivityKind

NEED_SOURCES: Mapping[NeedKind, frozenset[SatisfactionSource]] = total(
    NeedKind,
    {
        N.SUSTENANCE: frozenset({S.GOODS}),
        N.SAFETY: frozenset({S.RELATION, S.GOODS}),
        N.BELONGING: frozenset({S.RELATION, S.ACTIVITY}),
        N.STATUS: frozenset({S.ACHIEVEMENT, S.GOODS}),
        N.PURPOSE: frozenset({S.ACHIEVEMENT, S.ACTIVITY}),
        N.FAITH: frozenset({S.FAITH, S.ACTIVITY}),
        N.PLEASURE: frozenset({S.GOODS, S.ACTIVITY}),
        N.DRINK: frozenset({S.GOODS}),
        N.REST: frozenset({S.ACTIVITY}),
        N.COMFORT: frozenset({S.GOODS}),
        N.HEALTH: frozenset({S.GOODS, S.RELATION}),
        N.FAMILY: frozenset({S.RELATION, S.ACTIVITY}),
        N.FRIENDS: frozenset({S.RELATION}),
        N.ROMANCE: frozenset({S.RELATION}),
        N.SOLITUDE: frozenset({S.ACTIVITY}),
        N.LEARNING: frozenset({S.ACTIVITY, S.ACHIEVEMENT}),
        N.CREATING: frozenset({S.ACTIVITY, S.ACHIEVEMENT}),
        N.BEAUTY: frozenset({S.GOODS, S.ACTIVITY}),
        N.NATURE: frozenset({S.ACTIVITY}),
        N.ADVENTURE: frozenset({S.ACTIVITY, S.ACHIEVEMENT}),
        N.FIGHTING: frozenset({S.ACTIVITY, S.ACHIEVEMENT}),
        N.WEALTH: frozenset({S.GOODS, S.ACHIEVEMENT}),
        N.ORDER: frozenset({S.RELATION}),
        N.AUTONOMY: frozenset({S.RELATION, S.ACHIEVEMENT}),
        N.KNOWLEDGE: frozenset({S.ACTIVITY, S.GOODS}),
        N.STIMULATION: frozenset({S.ACTIVITY, S.GOODS}),
        N.CONTINUITY: frozenset({S.FAITH, S.RELATION}),
        N.UPKEEP: frozenset({S.GOODS, S.RELATION}),
        N.JUSTICE: frozenset({S.RELATION, S.ACHIEVEMENT}),
        N.CARE: frozenset({S.RELATION, S.ACTIVITY}),
    },
)
ACTIVITY_NEEDS: Mapping[ActivityKind, tuple[NeedKind, ...]] = total(
    ActivityKind,
    {
        A.WORK: (N.PURPOSE, N.STATUS),
        A.REST: (N.REST, N.SOLITUDE),
        A.WORSHIP: (N.FAITH, N.BELONGING),
        A.LEARNING: (N.LEARNING, N.KNOWLEDGE),
        A.PLAY: (N.PLEASURE, N.STIMULATION),
        A.CARE: (N.FAMILY, N.BELONGING),
        A.TRAVEL: (N.ADVENTURE, N.NATURE, N.STIMULATION),
        A.ART: (N.CREATING, N.BEAUTY),
    },
)
ACTIVITY_COLUMNS: Mapping[ActivityKind, str] = total(
    ActivityKind,
    {
        A.WORK: "work",
        A.REST: "rest",
        A.WORSHIP: "worship",
        A.LEARNING: "learning",
        A.PLAY: "leisure",
        A.CARE: "care",
        A.TRAVEL: "travel",
        A.ART: "art",
    },
)
