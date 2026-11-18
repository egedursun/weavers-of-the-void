from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class MetricsRules:
    slow_call_seconds: int = rule(120, 5, 3600, RuleGroup.RECORDS, "A model call exceeding this many seconds counts as slow")
    keep_epochs: int = rule(100, 1, 10000, RuleGroup.RECORDS, "Epochs kept in model metrics")
    eta_average_epochs: int = rule(6, 1, 1000, RuleGroup.RECORDS, "Remaining-time estimate: number of recent epochs averaged")
    error_chars: int = rule(4000, 200, 100000, RuleGroup.RECORDS, "Longest model error kept in the metrics record and the log (characters)")
    rank_uncommon_tokens: int = rule(25_000_000, 1, 10**15, RuleGroup.ACHIEVEMENTS, "Lifetime tokens at which the usage rank reaches uncommon")
    rank_rare_tokens: int = rule(100_000_000, 1, 10**15, RuleGroup.ACHIEVEMENTS, "Lifetime tokens at which the usage rank reaches rare")
    rank_epic_tokens: int = rule(500_000_000, 1, 10**15, RuleGroup.ACHIEVEMENTS, "Lifetime tokens at which the usage rank reaches epic")
    rank_legendary_tokens: int = rule(2_000_000_000, 1, 10**15, RuleGroup.ACHIEVEMENTS, "Lifetime tokens at which the usage rank reaches legendary")
    rank_mythic_tokens: int = rule(10_000_000_000, 1, 10**15, RuleGroup.ACHIEVEMENTS, "Lifetime tokens at which the usage rank reaches mythic")
    rank_pace_epochs: int = rule(5, 1, 100, RuleGroup.ACHIEVEMENTS, "Recent epochs averaged to tell the pace toward the next usage rank")
    missing_fields_listed: int = rule(10, 1, 200, RuleGroup.RECORDS, "Most missing or invalid output field paths named in a schema mismatch error")
