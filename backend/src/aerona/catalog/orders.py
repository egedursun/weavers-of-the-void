from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.constructs import OrderCondition, OrderKind, OrderTime
from aerona.rules.registry import Rules

K = OrderKind

ORDER_LITERALNESS: Mapping[OrderKind, Callable[[Rules], int]] = total(
    OrderKind,
    {
        K.GUARD: lambda rules: rules.instructions.guard_literalness,
        K.SERVE: lambda rules: rules.instructions.serve_literalness,
        K.OBEY_HOLDER: lambda rules: rules.instructions.obey_holder_literalness,
        K.BUILD: lambda rules: rules.instructions.build_literalness,
        K.GATHER: lambda rules: rules.instructions.gather_literalness,
        K.PROTECT: lambda rules: rules.instructions.protect_literalness,
        K.DESTROY: lambda rules: rules.instructions.destroy_literalness,
        K.REPORT: lambda rules: rules.instructions.report_literalness,
        K.MAINTAIN: lambda rules: rules.instructions.maintain_literalness,
        K.REPLICATE: lambda rules: rules.instructions.replicate_literalness,
        K.HOLD_STILL: lambda rules: rules.instructions.hold_still_literalness,
        K.FOLLOW: lambda rules: rules.instructions.follow_literalness,
        K.FORBID: lambda rules: rules.instructions.forbid_literalness,
        K.CARRY: lambda rules: rules.instructions.carry_literalness,
        K.TEND: lambda rules: rules.instructions.tend_literalness,
    },
)


@dataclass(frozen=True)
class ConditionSpec:
    label: str
    ends_when_done: bool = False
    timed: bool = False


ORDER_CONDITIONS = total(
    OrderCondition,
    {
        OrderCondition.ALWAYS: ConditionSpec("Always"),
        OrderCondition.WHILE_MAKER_LIVES: ConditionSpec("While its maker lives"),
        OrderCondition.UNTIL_DATE: ConditionSpec("Until a set epoch"),
        OrderCondition.WHEN_ATTACKED: ConditionSpec("When attacked"),
        OrderCondition.WHEN_TOKEN_SHOWN: ConditionSpec("When its token is shown"),
        OrderCondition.UNTIL_DONE: ConditionSpec("Until its task is done", ends_when_done=True),
        OrderCondition.AT_SET_TIMES: ConditionSpec("At set times", timed=True),
    },
)
DONE_CONDITIONS = frozenset(kind for kind, spec in ORDER_CONDITIONS.items() if spec.ends_when_done)
TIMED_CONDITIONS = frozenset(kind for kind, spec in ORDER_CONDITIONS.items() if spec.timed)


@dataclass(frozen=True)
class TimeSpec:
    label: str
    share_pct: int
    sky: bool = False
    by_season: bool = False


ORDER_TIMES = total(
    OrderTime,
    {
        OrderTime.DAY: TimeSpec("By day", 50),
        OrderTime.NIGHT: TimeSpec("By night", 50),
        OrderTime.SEASON: TimeSpec("In one season of the year", 100, by_season=True),
        OrderTime.SKY_EVENT: TimeSpec("At a sign in the sky", 100, sky=True),
    },
)
