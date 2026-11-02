from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class FateRules:
    budget_new_creations_chars: int = rule(
        60000,
        2000,
        1000000,
        RuleGroup.CONTEXT_BUDGETS,
        "Fate: creations in a single judgment call (characters); those that don't fit are weighed in extra rounds in the same epoch",
    )
    budget_old_prophecies_chars: int = rule(12000, 500, 200000, RuleGroup.CONTEXT_BUDGETS, "Fate: old prophecies (characters)")
    budget_epoch_events_chars: int = rule(20000, 1000, 400000, RuleGroup.CONTEXT_BUDGETS, "Fate: the epoch's events (characters)")
    budget_engine_notes_chars: int = rule(12000, 500, 200000, RuleGroup.CONTEXT_BUDGETS, "Fate: engine notes (characters)")
    budget_judgment_prompt_chars: int = rule(140000, 10000, 2000000, RuleGroup.CONTEXT_BUDGETS, "Fate: entire judgment prompt (characters)")
    budget_chronicler_prompt_chars: int = rule(30000, 2000, 400000, RuleGroup.CONTEXT_BUDGETS, "Entire chronicler prompt (characters)")
    open_thread_cap: int = rule(12, 2, 100, RuleGroup.FATE_AND_CHRONICLE, "Open story-thread cap (when exceeded, Fate closes more)")
    forced_close_cap: int = rule(6, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Maximum forced thread closures in one epoch")
    new_thread_cap: int = rule(4, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Maximum new threads in one epoch")
    stale_thread_epochs: int = rule(4, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "A thread not advancing for this many epochs becomes a closure candidate")
    long_thread_steps: int = rule(8, 2, 200, RuleGroup.FATE_AND_CHRONICLE, "After this many advances a thread should be concluded")
    reward_cap: int = rule(15, 0, 500, RuleGroup.FATE_AND_CHRONICLE, "Maximum renown a son can receive from Fate in one epoch")
    canon_facts_max: int = rule(24, 0, 200, RuleGroup.FATE_AND_CHRONICLE, "Maximum canon facts in a judgment")
    canon_facts_min: int = rule(3, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Minimum canon facts in a judgment")
    words_per_epoch_cap: int = rule(10, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Maximum words Fate adds to languages in one epoch")
    seer_correct_charisma: int = rule(10, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Charisma to the seer for a prophecy that comes true")
    seer_wrong_charisma_loss: int = rule(8, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Charisma taken from the seer for a misinterpreted prophecy")
    reward_streak_window: int = rule(5, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Fate reward: epochs looked back for consecutive rewards (0: no decay)")
    reward_streak_keep_pct: int = rule(75, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Fate reward: share remaining for each reward received in recent epochs (%)")
    thread_advance_cap: int = rule(6, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Maximum threads Fate advances with events in one epoch")
    prophecy_renown: int = rule(10, 0, 500, RuleGroup.FATE_AND_CHRONICLE, "Renown to the creating son for a fulfilled prophecy")
    prophecy_xp: int = rule(30, 0, 1000, RuleGroup.FATE_AND_CHRONICLE, "XP to the creating son for a fulfilled prophecy")
    banned_previous_openings: int = rule(6, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Previous narrative openings forbidden to the chronicler")
    previous_epoch_names_shown: int = rule(12, 0, 200, RuleGroup.FATE_AND_CHRONICLE, "Previous epoch names shown to the chronicler")
    banned_son_message_openings: int = rule(3, 0, 20, RuleGroup.FATE_AND_CHRONICLE, "Recent message openings forbidden to a son")
    fate_timeout: int = rule(480, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Fate and chronicler timeout (s); safety margin for a judgment whose output grows")
    judgment_parallel: int = rule(
        3, 1, 16, RuleGroup.AGENTS_AND_MODEL, "Fate: extra judgment rounds (for creations not fitting the context) running at the same time"
    )
    reason_max_words: int = rule(
        24,
        4,
        400,
        RuleGroup.FATE_AND_CHRONICLE,
        "Fate: maximum words in a judgment's reasoning (stated in the prompt; excess cut at a sentence boundary; output and time shrink)",
    )
    historians_per_epoch: int = rule(2, 0, 20, RuleGroup.FATE_AND_CHRONICLE, "Peoples writing a perspective in one epoch")
    folk_beliefs_per_epoch: int = rule(5, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "New folk beliefs written in one epoch")
    voices_timeout: int = rule(240, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Voices-of-the-peoples timeout (s)")
    model_retries: int = rule(3, 1, 10, RuleGroup.AGENTS_AND_MODEL, "Total attempts on a transient model error")
    son_turn_timeout: int = rule(420, 60, 3600, RuleGroup.AGENTS_AND_MODEL, "Son turn timeout (s)")
    prescreen_min_description: int = rule(140, 0, 2000, RuleGroup.FATE_AND_CHRONICLE, "Prescreen: a description shorter than this gets a warning (characters)")
    prescreen_max_off_domain_power: int = rule(7, 1, 11, RuleGroup.FATE_AND_CHRONICLE, "Prescreen: an off-domain creation stronger than this gets a warning")
    voices_events_chars: int = rule(6000, 500, 100000, RuleGroup.CONTEXT_BUDGETS, "Events sent to the voices of the peoples (characters)")
    pantheon_root_threshold_pct: int = rule(
        50, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "Summoning: a root appearing in the titles/obsessions of this percentage of sons is forbidden to the new son"
    )
    pantheon_root_min_sons: int = rule(4, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "Summoning: minimum sons for the pantheon-root measurement")
    council_sentences: int = rule(
        2, 1, 50, RuleGroup.FATE_AND_CHRONICLE, "Sentences taken from the council line in epoch events (so the minutes aren't copied into the narrative)"
    )
    name_type_lines: int = rule(60, 0, 1000, RuleGroup.FATE_AND_CHRONICLE, "Chronicler prompt: types of records mentioned in the epoch (maximum lines)")
    budget_name_type_chars: int = rule(3000, 0, 50000, RuleGroup.CONTEXT_BUDGETS, "Chronicler prompt: name and type list (characters)")
    message_tic_window: int = rule(8, 0, 200, RuleGroup.FATE_AND_CHRONICLE, "Message tic: recent messages examined")
    message_tic_threshold_pct: int = rule(
        60, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "Message tic: a word appearing in this percentage of recent messages is forbidden"
    )
    shared_tic_window: int = rule(24, 0, 500, RuleGroup.FATE_AND_CHRONICLE, "Shared message tic: recent messages of all sons examined")
    shared_tic_threshold_pct: int = rule(
        30, 1, 100, RuleGroup.FATE_AND_CHRONICLE, "Shared message tic: a root appearing in this percentage of recent messages is forbidden to all"
    )
    budget_previous_judgments_chars: int = rule(
        2500, 0, 50000, RuleGroup.CONTEXT_BUDGETS, "Chronicler prompt: Fate's judgments from the previous epoch (characters)"
    )
    historian_opening_chars: int = rule(
        160, 20, 2000, RuleGroup.FATE_AND_CHRONICLE, "Historian prompt: length of the previous narrative opening shown (characters)"
    )
    prescreen_tired_images: int = rule(3, 1, 50, RuleGroup.FATE_AND_CHRONICLE, "Prescreen: warning if this many tired images appear in the description")
    chronicler_min_tenure: int = rule(
        6, 1, 1000, RuleGroup.FATE_AND_CHRONICLE, "Chronicler continuity: minimum epochs a chronicler writes before handing over to a successor"
    )
    shared_tic_cap: int = rule(3, 0, 20, RuleGroup.FATE_AND_CHRONICLE, "Shared message tic: maximum forbidden roots")
    message_tic_min_messages: int = rule(4, 1, 200, RuleGroup.FATE_AND_CHRONICLE, "Message tic: minimum messages before checking starts")
    message_tic_cap: int = rule(3, 0, 20, RuleGroup.FATE_AND_CHRONICLE, "Message tic: maximum forbidden words per message")
    son_opening_words: int = rule(3, 1, 20, RuleGroup.FATE_AND_CHRONICLE, "Length of the message opening forbidden to a son (words)")
    summary_min_chars: int = rule(120, 0, 2000, RuleGroup.FATE_AND_CHRONICLE, "Shortest form of the epoch summary (characters)")
    thread_recent_advancers: int = rule(3, 0, 50, RuleGroup.CONTEXT_BUDGETS, "Recent creations advancing each thread in the Fate prompt")
    closure_candidates_shown: int = rule(6, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Threads written into the Fate prompt as priority closure candidates")
    zero_progress_close_epochs: int = rule(
        6,
        1,
        200,
        RuleGroup.FATE_AND_CHRONICLE,
        "A thread that never advanced may be closed only after this many stagnant epochs (closing a young thread as 'nothing happened' is an easy ending)",
    )
    budget_chronicler_engine_chars: int = rule(6000, 500, 200000, RuleGroup.CONTEXT_BUDGETS, "Chronicler: engine notes (characters)")
    seer_default_charisma: int = rule(40, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Charisma of a seer with unknown charisma")
    creator_belief_max_people: int = rule(6, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Largest people for which the Creator's belief can be written in one epoch")
    budget_engine_born_chars: int = rule(
        20000,
        500,
        400000,
        RuleGroup.CONTEXT_BUDGETS,
        "Fate prompt: section of those born from the world's own flow (characters; those not fitting are named in a separate naming round)",
    )
    budget_world_records_chars: int = rule(4000, 0, 100000, RuleGroup.CONTEXT_BUDGETS, "Fate prompt: list of this epoch's world records (characters)")
    chronicler_side_share_pct: int = rule(
        25, 0, 100, RuleGroup.CONTEXT_BUDGETS, "Chronicler prompt: maximum share for engine results and unnamed records (% of data budget)"
    )
    opening_window: int = rule(12, 0, 200, RuleGroup.FATE_AND_CHRONICLE, "Opening template: recent epoch narratives examined")
    opening_pattern_threshold: int = rule(
        3, 2, 50, RuleGroup.FATE_AND_CHRONICLE, "Opening template: a two-word pair appearing in this many separate openings is forbidden"
    )
    opening_fix: int = rule(
        1,
        0,
        1,
        RuleGroup.FATE_AND_CHRONICLE,
        "If an opening starts with a forbidden template, the chronicler is asked to rewrite only the first sentence (1 on, 0 off)",
    )
    epoch_name_root_threshold: int = rule(3, 2, 100, RuleGroup.FATE_AND_CHRONICLE, "Epoch name: a root appearing in this many previous names is forbidden")
    complete_missing_worlds: int = rule(
        1, 0, 1, RuleGroup.FATE_AND_CHRONICLE, "If the chronicler skips a world's section, a second short call for those worlds (1 on, 0 off)"
    )
    backfill_world_sections: int = rule(
        2, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Missing world sections written retroactively for past epochs in one completion"
    )
    backfill_chronicles: int = rule(3, 0, 100, RuleGroup.FATE_AND_CHRONICLE, "Missing epoch chronicles written retroactively in one completion")
    backfill_timeout: int = rule(300, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Missing epoch chronicle timeout (s)")
    seer_power_mult: int = rule(2, 1, 20, RuleGroup.FATE_AND_CHRONICLE, "Renown and XP multiplier a son with the Seer power receives from a fulfilled prophecy")
    xp_per_renown: int = rule(2, 0, 50, RuleGroup.FATE_AND_CHRONICLE, "Son's XP per renown granted by Fate")
    review_mortal_creations: int = rule(1, 0, 1, RuleGroup.FATE_AND_CHRONICLE, "Fate also judges the creations of mortal agents (1 on, 0 off)")
