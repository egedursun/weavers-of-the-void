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
    book_entry_chronicle_lines: int = rule(300, 0, 10000, RuleGroup.CODEX_AND_GUIDE, "Book: chronicle lines appended to a single son or record page")
    book_son_fate_lines: int = rule(
        400, 0, 5000, RuleGroup.CODEX_AND_GUIDE, "Book and codex: most lines in a son's fate (the creator's hand, death, return, rebellion, orders)"
    )
    book_god_lines: int = rule(60, 0, 1000, RuleGroup.CODEX_AND_GUIDE, "Book and codex: most lines in a foreign god's record")
