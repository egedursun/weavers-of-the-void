from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.monetary import MonetaryAim

MONETARY_AIM = total(
    MonetaryAim,
    {
        MonetaryAim.STABLE_VALUE: Defined(
            "Stable value",
            checked_by=("engine.monetary.policy.target_rate",),
            used_by=(
                "db.tables.monetary.MonetaryAuthorityRow",
                "db.tables.monetary.MonetaryRateRow",
                "engine.monetary.authorities.establish",
                "engine.monetary.pegs.break_peg",
            ),
        ),
        MonetaryAim.CHEAP_CREDIT: Defined("Cheap credit", checked_by=("engine.monetary.policy.target_rate",), used_by=()),
        MonetaryAim.FUND_THE_STATE: Defined(
            "Fund the state",
            checked_by=("engine.monetary.policy.target_rate",),
            used_by=("engine.monetary.authorities.establish", "engine.monetary.policy.PRINTING_AIMS", "engine.monetary.policy.bend"),
        ),
        MonetaryAim.PEG: Defined(
            "Peg",
            checked_by=(
                "agents.context.money_policy_lines.authority_line",
                "engine.monetary.policy.target_rate",
                "engine.monetary.policy.tend_authority",
                "tools.mortal.monetary.checked_peg",
                "tools.mortal.monetary.set_monetary_policy_tool",
            ),
            used_by=(),
        ),
        MonetaryAim.GROWTH: Defined("Growth", checked_by=("engine.monetary.policy.target_rate",), used_by=()),
        MonetaryAim.NONE: Defined("None", checked_by=("engine.monetary.policy.target_rate",), used_by=()),
    },
)
