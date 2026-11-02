from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class EpochFlowRules:
    year_gods: int = rule(15, 0, 100000, RuleGroup.EPOCH_FLOW, "Gods' turn: until this year of the epoch")
    year_mortals: int = rule(30, 0, 100000, RuleGroup.EPOCH_FLOW, "Mortals' turn: until this year of the epoch")
    year_engine: int = rule(45, 0, 100000, RuleGroup.EPOCH_FLOW, "The world's own flow: until this year of the epoch")
    year_fate: int = rule(49, 0, 100000, RuleGroup.EPOCH_FLOW, "Fate and chronicler: until this year of the epoch")
    year_transition: int = rule(4, 0, 100000, RuleGroup.EPOCH_FLOW, "First years of the new epoch after the transition (until this year)")
    live_log_memory: int = rule(600, 10, 100000, RuleGroup.INTERFACE, "Recent live-feed events kept in memory")
    live_log_db: int = rule(1000, 10, 1000000, RuleGroup.INTERFACE, "Recent live-feed events kept in the database")
    epoch_end_summary_lines: int = rule(6, 0, 100, RuleGroup.INTERFACE, "Summary lines shown in the epoch-ended notification")
