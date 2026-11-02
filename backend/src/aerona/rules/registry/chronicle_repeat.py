from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ChronicleRepeatRules:
    root_letters: int = rule(5, 2, 20, RuleGroup.CHRONICLE, "Number of leading letters counted as a word root in chronicle repetition comparison")
