from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class FolkBeliefRules:
    god_name_max_letters: int = rule(40, 3, 200, RuleGroup.FATE_AND_CHRONICLE, "Folk belief: maximum letters of the god name the model gives")
    name_attempts: int = rule(
        4,
        1,
        20,
        RuleGroup.FATE_AND_CHRONICLE,
        "Folk belief: tries to derive a local god name from the people's language that differs from the god's own name and title",
    )
