from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class GodActionsRules:
    bless_essence_amount: int = rule(20, 0, 1000, RuleGroup.THE_GODS_ACTIONS, "Essence given to the son by an essence blessing")
    bless_stat_amount: int = rule(5, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Stat contribution of a stat blessing")
    bless_existence_amount: int = rule(20, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Contribution of an existence blessing to the son's existence")
    bless_loyalty: int = rule(3, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Loyalty contribution of each blessing")
    star_stat_gain: int = rule(3, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Contribution of adding a star to each stat")
    ascension_existence: int = rule(25, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Contribution of ascension to the son's existence")
    ascension_myth_spread: int = rule(80, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Starting spread of the ascension myth")
    defiant_will: int = rule(70, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Will of a son who doesn't submit to punishment (above this)")
    lightning_hp_pct: int = rule(30, 0, 100, RuleGroup.THE_GODS_ACTIONS, "HP taken by lightning (% of max HP)")
    suppress_base: int = rule(70, 0, 1000, RuleGroup.THE_GODS_ACTIONS, "Suppressing a rebellion: base of the god's strength")
    suppress_essence_divisor: int = rule(
        10, 1, 10000, RuleGroup.THE_GODS_ACTIONS, "Suppressing a rebellion: essence / this number is added to the god's strength"
    )
    suppress_die: int = rule(30, 1, 1000, RuleGroup.THE_GODS_ACTIONS, "Suppressing a rebellion: each side's die (1\u2013this number)")
    suppress_son_strength_pct: int = rule(50, 0, 1000, RuleGroup.THE_GODS_ACTIONS, "Suppressing a rebellion: contribution of the son's strength (%)")
    suppress_son_per_level: int = rule(3, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Suppressing a rebellion: son's contribution per level")
    suppress_loyalty_gain: int = rule(15, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Loyalty gain of a suppressed rebel")
    suppress_hp_left_pct: int = rule(50, 1, 100, RuleGroup.THE_GODS_ACTIONS, "Remaining HP of a suppressed rebel (%)")
    suppress_renown_loss: int = rule(10, 0, 1000, RuleGroup.THE_GODS_ACTIONS, "Renown loss of a suppressed rebel")
    suppress_fail_renown: int = rule(10, 0, 1000, RuleGroup.THE_GODS_ACTIONS, "Renown gain of a rebel who couldn't be suppressed")
    suppress_fail_ambition: int = rule(5, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Ambition gain of a rebel who couldn't be suppressed")
    suppress_fail_essence: int = rule(20, 0, 10000, RuleGroup.THE_GODS_ACTIONS, "Extra essence loss of the god on a failed suppression")
    pardon_loyalty: int = rule(8, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Loyalty contribution of a pardon")
    punish_defiant_loyalty_loss: int = rule(8, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Loyalty loss of a defiant son after punishment")
    punish_defiant_wrath: int = rule(8, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Wrath gain of a defiant son after punishment")
    punish_submissive_loyalty: int = rule(3, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Loyalty gain of a submissive son after punishment")
    punish_submissive_wrath: int = rule(4, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Wrath gain of a submissive son after punishment")
    prayer_essence_cap: int = rule(100, 0, 100000, RuleGroup.THE_GODS_ACTIONS, "Maximum essence that can be granted to one prayer")
    prayer_reply_loyalty: int = rule(4, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Contribution of a verbal reply to the son's loyalty")
    prayer_essence_per_loyalty: int = rule(10, 1, 10000, RuleGroup.THE_GODS_ACTIONS, "Every this much essence granted to a prayer gives +1 loyalty")
    prayer_existence: int = rule(3, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Contribution of an answered prayer to the son's existence")
    disaster_severity_pct: int = rule(110, 0, 1000, RuleGroup.THE_GODS_ACTIONS, "Severity multiplier of a disaster sent manually by the god (%)")
    disaster_event_severity: int = rule(75, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Severity in the event record of the god's disaster")
    curse_stat_loss: int = rule(15, 0, 100, RuleGroup.THE_GODS_ACTIONS, "Taken from community stats by the god's curse")
    note_max_chars: int = rule(6000, 100, 200000, RuleGroup.CONTEXT_BUDGETS, "Maximum length of the god's own note (characters; goes into prompts)")
    inspiration_max_chars: int = rule(600, 10, 20000, RuleGroup.CONTEXT_BUDGETS, "Maximum length of the inspiration text in world creation (characters)")
