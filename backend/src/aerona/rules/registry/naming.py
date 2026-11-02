from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class NamingRules:
    batch: int = rule(
        12, 1, 500, RuleGroup.AGENTS_AND_MODEL, "Records per naming model call (not a limit: all pending ones are named in batches in the same epoch)"
    )
    retries: int = rule(
        2,
        0,
        20,
        RuleGroup.AGENTS_AND_MODEL,
        "Retries for a record that couldn't be named; then its temporary description is cleared and it is left for deepening",
    )
    parallel: int = rule(4, 1, 32, RuleGroup.AGENTS_AND_MODEL, "Naming: number of batches (calls) running at the same time; batches don't wait in sequence")
    dialect_check: int = rule(
        1, 0, 1, RuleGroup.AGENTS_AND_MODEL, "Naming: an invented name not fitting its own world's dialect (forbidden vowel) is retried once (1 on, 0 off)"
    )
    weak_name_letters: int = rule(4, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Weak name: invented names shorter than this are sent back (letters)")
    weak_vowel_start_letters: int = rule(5, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Weak name: a name starting with a vowel needs at least this many letters")
    fresh_name_attempts: int = rule(
        4, 0, 50, RuleGroup.LANGUAGE_AND_NAMES, "Fresh name: names tried from the record's own language when the last suggestion still does not fit"
    )
    god_similar_max_length: int = rule(
        10, 0, 30, RuleGroup.LANGUAGE_AND_NAMES, "God names: longest name for which a single-letter difference from a god's name is forbidden (letters)"
    )
    god_root_min_distance: int = rule(
        2, 1, 10, RuleGroup.LANGUAGE_AND_NAMES, "God names: two god names sharing a root must differ by at least this many letters"
    )
