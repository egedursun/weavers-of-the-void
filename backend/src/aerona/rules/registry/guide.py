from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class GuideRules:
    dangerous_place: int = rule(55, 0, 100, RuleGroup.CODEX_AND_GUIDE, "Guide: danger of a region or place counted as dangerous")
    dangerous_species: int = rule(50, 0, 100, RuleGroup.CODEX_AND_GUIDE, "Guide: danger of a species counted as a predator")
    leak_threshold: int = rule(30, 0, 100, RuleGroup.CODEX_AND_GUIDE, "Guide: level at which leak counts as a danger")
    danger_list: int = rule(6, 0, 100, RuleGroup.CODEX_AND_GUIDE, "Guide: listed from each danger type")
    people_list: int = rule(14, 0, 500, RuleGroup.CODEX_AND_GUIDE, "Guide: most populous communities listed")
