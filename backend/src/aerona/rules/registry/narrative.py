from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class NarrativeRules:
    epic_sections_min: int = rule(3, 0, 50, RuleGroup.CONTENT_JOBS, "Sections of a god's epic (minimum)")
    epic_epoch_mentions: int = rule(
        3, 0, 100, RuleGroup.CONTENT_JOBS, "Epic: most mentions of epoch numbers; more reads like a ledger and the epic is written once more"
    )
    epic_retries: int = rule(1, 0, 5, RuleGroup.AGENTS_AND_MODEL, "Epic: rewrites asked when it comes out as a list of epochs")
    epic_sections_max: int = rule(7, 1, 100, RuleGroup.CONTENT_JOBS, "Sections of a god's epic (maximum)")
    god_names_min: int = rule(2, 0, 50, RuleGroup.CONTENT_JOBS, "God's depth: names (minimum)")
    god_names_max: int = rule(6, 1, 100, RuleGroup.CONTENT_JOBS, "God's depth: names (maximum)")
    secrets_min: int = rule(2, 0, 50, RuleGroup.CONTENT_JOBS, "God's depth: secrets (minimum)")
    secrets_max: int = rule(4, 1, 100, RuleGroup.CONTENT_JOBS, "God's depth: secrets (maximum)")
    fears_min: int = rule(1, 0, 50, RuleGroup.CONTENT_JOBS, "God's depth: fears (minimum)")
    fears_max: int = rule(3, 1, 100, RuleGroup.CONTENT_JOBS, "God's depth: fears (maximum)")
    taboos_min: int = rule(2, 0, 50, RuleGroup.CONTENT_JOBS, "God's depth: taboos (minimum)")
    taboos_max: int = rule(5, 1, 100, RuleGroup.CONTENT_JOBS, "God's depth: taboos (maximum)")
    gifts_min: int = rule(2, 0, 50, RuleGroup.CONTENT_JOBS, "God's depth: gifts (minimum)")
    gifts_max: int = rule(5, 1, 100, RuleGroup.CONTENT_JOBS, "God's depth: gifts (maximum)")
    quotes_min: int = rule(2, 0, 50, RuleGroup.CONTENT_JOBS, "Depth: mortals' sayings (minimum)")
    quotes_max: int = rule(4, 1, 100, RuleGroup.CONTENT_JOBS, "Depth: mortals' sayings (maximum)")
    rumors_min: int = rule(3, 0, 50, RuleGroup.CONTENT_JOBS, "Depth: rumours (minimum)")
    rumors_max: int = rule(5, 1, 100, RuleGroup.CONTENT_JOBS, "Depth: rumours (maximum)")
    sensory_details_min: int = rule(3, 0, 50, RuleGroup.CONTENT_JOBS, "Depth: sensory details (minimum)")
    sensory_details_max: int = rule(6, 1, 100, RuleGroup.CONTENT_JOBS, "Depth: sensory details (maximum)")
