from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ChronicleAuditRules:
    enabled: int = rule(
        1,
        0,
        1,
        RuleGroup.FATE_AND_CHRONICLE,
        "Chronicle audit: after Fate's verdict the narrative is checked for rejected records, skipped sons and events, reversed outcomes (1 on, 0 off)",
    )
    rewrite: int = rule(
        1,
        0,
        1,
        RuleGroup.FATE_AND_CHRONICLE,
        "Chronicle audit: findings ask the chronicler for one corrected rewrite, kept only when findings shrink (1 on, 0 off: rule repairs only)",
    )
    son_deeds_shown: int = rule(4, 1, 50, RuleGroup.FATE_AND_CHRONICLE, "Fact sheet: most deeds shown for one son")
    major_events: int = rule(24, 0, 200, RuleGroup.FATE_AND_CHRONICLE, "Fact sheet: most major events the chronicle must mention")
    major_events_per_category: int = rule(4, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "Fact sheet: most major events from one category (war, disaster…)")
    previous_verdicts: int = rule(
        4, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Fact sheet: previous-epoch Fate verdicts (closed stories, fulfilled prophecies) the chronicle must mention"
    )
    deed_chars: int = rule(160, 30, 2000, RuleGroup.CONTEXT_BUDGETS, "Fact sheet: shown length of one deed or event (characters)")
    budget_chars: int = rule(
        7000, 500, 100000, RuleGroup.CONTEXT_BUDGETS, "Chronicler prompt: fact sheet and mandatory coverage (characters; not cut together with the rules)"
    )
    name_min_letters: int = rule(4, 2, 20, RuleGroup.FATE_AND_CHRONICLE, "Audit: shortest word of a name counted when looking for its mention (letters)")
    silent_min_deeds: int = rule(2, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "Audit: an actor with this many deeds told as silent or idle is a contradiction")
    duplicate_sentence_chars: int = rule(
        60, 10, 2000, RuleGroup.FATE_AND_CHRONICLE, "A world-section sentence of this length found verbatim in the main narrative is dropped from the section"
    )
    findings_shown: int = rule(24, 1, 500, RuleGroup.FATE_AND_CHRONICLE, "Most findings sent to the correction prompt")
    heavy_weight: int = rule(
        2, 1, 20, RuleGroup.FATE_AND_CHRONICLE, "Audit weight of a heavy finding (rejected record, reversed outcome, skipped son, miscredited deed)"
    )
    light_weight: int = rule(1, 1, 20, RuleGroup.FATE_AND_CHRONICLE, "Audit weight of a light finding (skipped event or verdict, number contradiction)")
    rewrite_timeout: int = rule(300, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Chronicle correction rewrite timeout (s)")
    manual_cost: int = rule(0, 0, 1000, RuleGroup.GOD_AND_SON_COSTS, "Essence cost of auditing an epoch's chronicle again by hand")
