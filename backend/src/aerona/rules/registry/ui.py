from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class UiRules:
    graph_focus_node_cap: int = rule(
        10000, 10, 100000, RuleGroup.INTERFACE, "Graph: maximum nodes shown around the focus (if exceeded, the step count is reduced)"
    )
    graph_auto_focus_max_links: int = rule(
        50,
        3,
        100000,
        RuleGroup.INTERFACE,
        "Graph: maximum links of an automatically chosen focus node (so hub nodes don't become the focus and turn the view into a hairball)",
    )
    map_population_trend_min_pct: int = rule(5, 0, 100, RuleGroup.INTERFACE, "Minimum change for population to count as growing or shrinking on the map (%)")
    delta_max_changes: int = rule(1500, 50, 100000, RuleGroup.INTERFACE, "Maximum changes in one incremental-update response (more triggers a full refresh)")
    change_log_max_rows: int = rule(20000, 100, 10000000, RuleGroup.INTERFACE, "Maximum rows kept in the change log (pruned at epoch end)")
