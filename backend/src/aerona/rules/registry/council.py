from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span


@dataclass(frozen=True)
class CouncilRules(Spanned):
    max_members: int = rule(9, 2, 200, RuleGroup.COUNCIL, "Maximum sons joining the council, the greatest in level and fame first")
    min_members: int = rule(2, 2, 30, RuleGroup.COUNCIL, "Minimum sons required for the council to convene")
    same_vote_closeness: int = rule(3, 0, 50, RuleGroup.COUNCIL, "Rapprochement between those casting the same vote")
    covenant_relation: int = rule(12, 0, 100, RuleGroup.COUNCIL, "Relation contribution of a council covenant")
    rupture_relation: int = rule(15, 0, 100, RuleGroup.COUNCIL, "Relation cost of a rupture in the council")
    apocalypse_motion_push: int = rule(10, 0, 100, RuleGroup.COUNCIL, "Clock push-back of an accepted motion against the apocalypse")
    blessing_existence: int = rule(5, 0, 100, RuleGroup.COUNCIL, "Contribution of a joint blessing to existence")
    censure_renown_cost: int = rule(10, 0, 200, RuleGroup.COUNCIL, "Renown cost of censuring a rebel")
    agenda_apocalypse_pct: int = rule(50, 0, 100, RuleGroup.COUNCIL, "Apocalypse comes onto the agenda at this percentage of the threshold")
    timeout: int = rule(240, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Council timeout (s)")
    relation_min_magnitude: int = rule(20, 0, 100, RuleGroup.COUNCIL, "Minimum magnitude (\u00b1) of sibling relations written into the council prompt")
    alliance_rupture_cap: int = rule(3, 0, 20, RuleGroup.COUNCIL, "Maximum alliances or ruptures in one council")
    default_interval: int = rule(4, 0, 100, RuleGroup.COUNCIL, "On a world with no set council frequency, a council convenes once every this many epochs")
    agenda_thread_max_chars: int = rule(260, 20, 5000, RuleGroup.CONTEXT_BUDGETS, "Maximum length of an open story taken onto the agenda (characters)")
    agenda_cut_chars: int = rule(250, 10, 5000, RuleGroup.CONTEXT_BUDGETS, "A long story is cut at the last space before this character")
    persona_temperament_chars: int = rule(160, 0, 5000, RuleGroup.CONTEXT_BUDGETS, "Council: son's temperament (characters)")
    persona_style_chars: int = rule(120, 0, 5000, RuleGroup.CONTEXT_BUDGETS, "Council: son's style (characters)")
    persona_obsession_chars: int = rule(100, 0, 5000, RuleGroup.CONTEXT_BUDGETS, "Council: son's obsession (characters)")
    persona_plan_chars: int = rule(160, 0, 5000, RuleGroup.CONTEXT_BUDGETS, "Council: son's plan (characters)")
    dream_max_chars: int = rule(600, 10, 20000, RuleGroup.COUNCIL, "Longest text of a dream sent to a mortal (characters)")
    dream_min_chars: int = rule(5, 1, 1000, RuleGroup.COUNCIL, "Shortest text of a dream (characters)")
    translate_max_chars: int = rule(300, 10, 20000, RuleGroup.LANGUAGE_AND_NAMES, "Longest sentence to be translated (characters)")
    translate_lexicon_words: int = rule(250, 0, 10000, RuleGroup.LANGUAGE_AND_NAMES, "Lexicon words sent to the translation prompt")
    translate_syllables: int = rule(12, 0, 200, RuleGroup.LANGUAGE_AND_NAMES, "Frequent initial and final syllables sent to the translation prompt (each)")
    translate_new_words_max: int = rule(6, 0, 100, RuleGroup.LANGUAGE_AND_NAMES, "Maximum new words that can be added to the lexicon in one translation")
    translate_timeout: int = rule(120, 10, 3600, RuleGroup.AGENTS_AND_MODEL, "Translation timeout (s)")
    ruling_epochs: int = rule(6, 1, 200, RuleGroup.COUNCIL, "Epochs a lasting ruling of the council holds")
    petition_interest: int = rule(15, 0, 100, RuleGroup.COUNCIL, "Interest the Creator turns to the gods when the council petitions it")
    petition_calm: int = rule(10, 0, 100, RuleGroup.COUNCIL, "Anger a petition of the council takes from the Creator")
    worlds_per_son: int = rule(1, 1, 20, RuleGroup.COUNCIL, "Worlds each son is given when the council divides the worlds")
    relation_vote_pct: int = rule(50, 0, 200, RuleGroup.COUNCIL, "Share of a son's relation to the target that moves its vote (%)")
    goal_vote: int = rule(30, 0, 200, RuleGroup.COUNCIL, "Lean toward a motion that names the target of a son's own aim")
    firm_lean: int = rule(60, 1, 500, RuleGroup.COUNCIL, "Lean at which a son's nature decides its vote whatever it says")
    truce_window: int = rule(3, 1, 50, RuleGroup.COUNCIL, "Epochs of duels the council weighs when it considers a truce")
    truce_duels: int = rule(2, 1, 100, RuleGroup.COUNCIL, "Duels between gods in that window that bring a truce onto the agenda")
    invite_stance: int = rule(30, 0, 200, RuleGroup.COUNCIL, "Stance toward the pantheon at which a foreign god is invited to a seat on the council")
    veto_attention: int = rule(20, 0, 300, RuleGroup.COUNCIL, "Essence the Creator spends to veto a ruling of the council")
    sanction_essence: int = rule(10, 0, 300, RuleGroup.COUNCIL, "Essence a god loses when the council sanctions it")
    exclusion_epochs: int = rule(5, 1, 100, RuleGroup.COUNCIL, "Epochs a god is kept from the council once excluded")
    penance_epochs: int = rule(3, 1, 20, RuleGroup.COUNCIL, "Epochs a god bound to penance has to do the deed the council set it")
    essence_fine_share_pct: int = rule(
        20, 0, 100, RuleGroup.COUNCIL, "Share of its essence a god fined by the council pays to the gods it wronged or to the council (%)"
    )
    essence_fine_renown: int = rule(4, 0, 200, RuleGroup.COUNCIL, "Renown a god loses when the council fines its essence")
    penance_kept_renown: int = rule(6, 0, 200, RuleGroup.COUNCIL, "Renown a god regains when it does the penance the council set it")
    duel_relation: int = rule(20, 0, 100, RuleGroup.COUNCIL, "Relation lost between a violator and the council's champion when the ladder reaches a duel")
    tithe_essence: int = rule(5, 0, 300, RuleGroup.COUNCIL, "Essence each member pays to a tithe the council levies for a common work")
    tithe_doom: int = rule(3, 0, 100, RuleGroup.COUNCIL, "Points the doom clock falls when a tithe is paid for a common work")
    regulation_step: int = rule(2, 0, 50, RuleGroup.COUNCIL, "How far a regulation of made minds or living craft binds them each epoch")
    regulate_at: int = rule(5, 1, 1000, RuleGroup.COUNCIL, "Made minds, or sources of power open to anyone, at which the council moves to regulate them")
    regulate_drift: int = rule(30, 0, 100, RuleGroup.COUNCIL, "Drift of a living line at which the council moves to regulate living craft")
    failed_councils: int = rule(3, 1, 20, RuleGroup.COUNCIL, "Councils in a row that pass nothing before the council moves to change how it decides")
    improve_relations_effect: int = rule(100, 0, 100, RuleGroup.POLITY, "How fully a chancellor's courting of a neighbour works (%)")
    train_troops_effect: int = rule(100, 0, 100, RuleGroup.POLITY, "How fully a marshal's drilling of the armies works (%)")
    collect_taxes_effect: int = rule(100, 0, 100, RuleGroup.POLITY, "How fully a treasurer's gathering of taxes works (%)")
    disrupt_schemes_effect: int = rule(100, 0, 100, RuleGroup.POLITY, "How fully a spymaster's breaking of schemes works (%)")
    convert_province_effect: int = rule(100, 0, 100, RuleGroup.POLITY, "How fully a chaplain's turning of a land works (%)")
    purge_corruption_effect: int = rule(100, 0, 100, RuleGroup.POLITY, "How fully a judge's purge of corruption works (%)")
    oversee_works_effect: int = rule(
        10, 0, 100, RuleGroup.POLITY, "Share of each work's cost an overseer of works raises each epoch at full skill and diligence (%)"
    )
    promote_trade_effect: int = rule(
        5, 0, 100, RuleGroup.POLITY, "Treasury an officer promoting trade earns per trading road of the realm each epoch at full skill and diligence"
    )
    advance_learning_effect: int = rule(
        10, 0, 100, RuleGroup.POLITY, "Research an officer advancing learning adds to the realm's seat each epoch at full skill and diligence"
    )
    public_health_effect: int = rule(20, 0, 100, RuleGroup.POLITY, "Share a councillor for public health adds to sanitation and cure in the realm (%)")
    secure_borders_effect: int = rule(25, 0, 100, RuleGroup.POLITY, "Share a councillor for the borders takes from smuggling and raids into the realm (%)")
    rebuke_renown: int = rule(2, 0, 200, RuleGroup.COUNCIL, "Renown a god loses when the council rebukes it")
    bound_world_years: int = span(50, 1, 2500, RuleGroup.COUNCIL, "Years a god the council binds to one world cannot act beyond it")
