from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ContextRules:
    plan_stale_epochs: int = rule(
        4, 1, 1000, RuleGroup.SON_TOOLS, "A son's plan not renewed for this many epochs shows as stale in memory and asks to be renewed"
    )
    plan_closed_stories: int = rule(
        3, 0, 50, RuleGroup.CONTEXT_BUDGETS, "Stale plan: closed stories (bound to the son's creations) shown since the plan was written"
    )
    plan_closed_chars: int = rule(120, 20, 2000, RuleGroup.CONTEXT_BUDGETS, "Stale plan: shown length of a closed story (characters)")
    fate_geography_chars: int = rule(9000, 500, 200000, RuleGroup.CONTEXT_BUDGETS, "Fate: geography (characters)")
    fate_map_chars: int = rule(4000, 200, 100000, RuleGroup.CONTEXT_BUDGETS, "Fate: map (characters)")
    fate_cosmos_chars: int = rule(2500, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Fate: other worlds (characters)")
    fate_language_chars: int = rule(3000, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Fate: languages (characters)")
    fate_unlocated_chars: int = rule(3000, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Fate: legends and traditions (characters)")
    fate_chronicle_chars: int = rule(4000, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Fate: recent events (characters)")
    fate_summary_chars: int = rule(26000, 2000, 400000, RuleGroup.CONTEXT_BUDGETS, "Fate: entire world summary (characters)")
    son_geography_chars: int = rule(5000, 500, 100000, RuleGroup.CONTEXT_BUDGETS, "Son: geography and inhabitants (characters)")
    son_map_chars: int = rule(2500, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Son: map (characters)")
    son_cosmos_chars: int = rule(1500, 200, 30000, RuleGroup.CONTEXT_BUDGETS, "Son: other worlds (characters)")
    son_language_chars: int = rule(1600, 200, 30000, RuleGroup.CONTEXT_BUDGETS, "Son: languages and lexicon (characters)")
    son_unlocated_chars: int = rule(1500, 200, 30000, RuleGroup.CONTEXT_BUDGETS, "Son: legends and traditions (characters)")
    son_chronicle_chars: int = rule(2200, 200, 30000, RuleGroup.CONTEXT_BUDGETS, "Son: recent events (characters)")
    son_summary_chars: int = rule(14000, 2000, 200000, RuleGroup.CONTEXT_BUDGETS, "Son: entire world summary (characters)")
    son_memory_chars: int = rule(5000, 500, 100000, RuleGroup.CONTEXT_BUDGETS, "Son: memory (characters)")
    son_prompt_chars: int = rule(24000, 4000, 400000, RuleGroup.CONTEXT_BUDGETS, "Son: entire turn prompt (characters)")
    son_chronicle_lines: int = rule(10, 1, 200, RuleGroup.CONTEXT_BUDGETS, "Son: lines of recent events (+ wisdom/8)")
    read_tool_multiplier: int = rule(
        3,
        1,
        50,
        RuleGroup.CONTEXT_BUDGETS,
        "Read tools: how many times longer recent events and memories are when a section cut from the prompt is shown in full",
    )
    short_cosmology_chars: int = rule(500, 50, 100000, RuleGroup.CONTEXT_BUDGETS, "Length of the cosmology in the mortals' short world header (characters)")
    section_min_chars: int = rule(
        600, 0, 100000, RuleGroup.CONTEXT_BUDGETS, "Minimum space reserved for each context section (characters; whole section if it is short)"
    )
    budget_trim_min_chars: int = rule(
        120, 0, 10000, RuleGroup.CONTEXT_BUDGETS, "Context budget: minimum space for a non-fitting line to be included truncated (characters)"
    )
    memory_named_worshippers: int = rule(12, 0, 1000, RuleGroup.CONTEXT_BUDGETS, "Son memory: worshippers shown by name (the rest as a count)")
    son_threads: int = rule(6, 1, 100, RuleGroup.CONTEXT_BUDGETS, "Son: open story threads shown")
    fate_chronicle_lines: int = rule(24, 1, 400, RuleGroup.CONTEXT_BUDGETS, "Fate: lines of recent events")
    mortal_context_chars: int = rule(12000, 2000, 200000, RuleGroup.CONTEXT_BUDGETS, "Mortal: entire context (characters)")
    memory_creations_chars: int = rule(1600, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Son memory: creations (characters)")
    memory_recollections_chars: int = rule(1200, 200, 50000, RuleGroup.CONTEXT_BUDGETS, "Son memory: recollections (characters)")
    memory_about_chars: int = rule(900, 100, 50000, RuleGroup.CONTEXT_BUDGETS, "Son memory: events about the son (characters)")
    memory_folk_beliefs_chars: int = rule(900, 100, 50000, RuleGroup.CONTEXT_BUDGETS, "Son memory: folk beliefs (characters)")
    memory_messages_chars: int = rule(1000, 100, 50000, RuleGroup.CONTEXT_BUDGETS, "Son memory: incoming messages (characters)")
    repeat_warning_threshold: int = rule(3, 2, 50, RuleGroup.SON_TOOLS, '"You are repeating yourself" warning in memory: creations of the same subtype')
    repeat_window: int = rule(20, 1, 500, RuleGroup.SON_TOOLS, "Repetition check in memory: recent creations examined")
    son_location_tree_lines: int = rule(90, 10, 5000, RuleGroup.CONTEXT_BUDGETS, "Son: lines in the location tree (+ wisdom)")
    fate_location_tree_lines: int = rule(220, 10, 10000, RuleGroup.CONTEXT_BUDGETS, "Fate: lines in the location tree")
    son_chronicle_wisdom_step: int = rule(8, 1, 100, RuleGroup.CONTEXT_BUDGETS, "Son: every this much wisdom adds one line to recent events")
    son_words_per_language: int = rule(6, 0, 200, RuleGroup.CONTEXT_BUDGETS, "Son: sample words per language")
    fate_words_per_language: int = rule(10, 0, 200, RuleGroup.CONTEXT_BUDGETS, "Fate: sample words per language")
    near_language_extra_words: int = rule(4, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Extra sample words in the son's nearby languages")
    far_language_fewer_words: int = rule(3, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Fewer sample words in the son's distant languages")
    far_language_min_words: int = rule(3, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Minimum sample words in distant languages")
    unlocated_rows: int = rule(45, 1, 1000, RuleGroup.CONTEXT_BUDGETS, "Legends and traditions: newest records shown")
    inspect_lexicon_words: int = rule(40, 0, 2000, RuleGroup.CONTEXT_BUDGETS, "Entity inspection: words shown from the language's lexicon")
    inspect_canon_facts: int = rule(8, 0, 200, RuleGroup.CONTEXT_BUDGETS, "Entity inspection: canon facts shown")
    body_weakness_pct: int = rule(15, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Capacity loss at which a mortal is told they are hampered (%)")
    chronicle_default: int = rule(12, 1, 500, RuleGroup.CONTEXT_BUDGETS, "Recent events: default lines")
    search_results_max: int = rule(25, 1, 500, RuleGroup.CONTEXT_BUDGETS, "search_entity (varlik_ara): maximum results")
    memory_creations_count: int = rule(30, 1, 500, RuleGroup.CONTEXT_BUDGETS, "Son memory: number of recent creations")
    memory_recollections_count: int = rule(12, 1, 500, RuleGroup.CONTEXT_BUDGETS, "Son memory: number of recent recollections")
    memory_about_count: int = rule(10, 1, 500, RuleGroup.CONTEXT_BUDGETS, "Son memory: number of recent events about the son")
    memory_messages_count: int = rule(10, 1, 500, RuleGroup.CONTEXT_BUDGETS, "Son memory: number of recent incoming messages")
    thread_related_score: int = rule(3, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Story priority: score per related record of the son")
    thread_name_score: int = rule(4, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Story priority: score if the son's name appears in the text")
    thread_stale_penalty: int = rule(50, 0, 1000, RuleGroup.CONTEXT_BUDGETS, "Story priority: score lost per stagnant epoch (percentage points)")
    thread_progressed_score: int = rule(1, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Story priority: score if it has progressed at all")
    apocalypse_warning_pct: int = rule(30, 0, 100, RuleGroup.APOCALYPSE, "Doomsday clock appears in the prompt at this percentage of the threshold")
    harvest_poor_below_pct: int = rule(80, 0, 200, RuleGroup.CONTEXT_BUDGETS, "Harvest below which a region is described to the gods as hungry (%)")
    harvest_rich_above_pct: int = rule(120, 0, 300, RuleGroup.CONTEXT_BUDGETS, "Harvest above which a region is described to the gods as rich (%)")
    scar_shown_depth: int = rule(20, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Least depth of a scar the gods are told about")
