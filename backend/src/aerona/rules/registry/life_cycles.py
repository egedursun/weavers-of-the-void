from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class LifeCyclesRules:
    decline_epochs: int = rule(3, 1, 20, G, "Decline and collapse are measured against the population this many epochs ago")
    decline_loss_pct: int = rule(25, 1, 100, G, "A settlement that lost at least this share of its people over the decline window is declining (%)")
    relative_threshold_pct: int = rule(
        30, 1, 100, G, "A declining settlement below this share of its world's median settlement population may be abandoned (%)"
    )
    abandon_max_prosperity: int = rule(50, 0, 100, G, "Highest prosperity of a settlement that can still be abandoned for decline")
    abandon_chance: int = rule(25, 0, 100, G, "Per-epoch chance that a declining, poor, dwindling settlement is abandoned (%)")
    abandon_grace_epochs: int = rule(3, 0, 50, G, "A new settlement is not abandoned for decline for this many epochs")
    abandon_cap: int = rule(2, 0, 50, G, "Most settlements abandoned for decline per epoch")
    abandon_migration_pct: int = rule(60, 0, 100, G, "Share of an abandoned settlement's people who move to the nearest settlement (%)")
    collapse_loss_pct: int = rule(40, 1, 100, G, "A poor community that lost this share of its people over the decline window may collapse (%)")
    collapse_max_prosperity: int = rule(25, 0, 100, G, "Highest prosperity of a community that can collapse")
    collapse_chance: int = rule(35, 0, 100, G, "Per-epoch chance that a qualifying community collapses (%)")
    collapse_grace_epochs: int = rule(10, 1, 200, G, "A collapsed community does not collapse again for this many epochs")
    collapse_cap: int = rule(1, 0, 20, G, "Most community collapses per epoch")
    collapse_chain_prosperity: int = rule(8, 0, 100, G, "Prosperity lost by each community breaking away from a collapsed ruler")
    collapse_sway_loss: int = rule(15, 0, 100, G, "Sway lost by every faction seated in a collapsed community")
    siege_damage_chance: int = rule(35, 0, 100, G, "Chance that each structure in a besieged settlement is damaged (%)")
    siege_durability_loss: int = rule(20, 0, 100, G, "Durability lost by a structure damaged in a siege")
    conquest_loot_chance: int = rule(10, 0, 100, G, "Chance that a wonder of a conquered settlement is looted and razed (%)")
    end_cost: int = rule(15, 0, 1000, RuleGroup.INTERVENTION, "Base essence cost of the god ordering a record's end (collapse or razing)")
    end_cost_per_power: int = rule(2, 0, 100, RuleGroup.INTERVENTION, "Extra essence per power level when the god orders a record's end")
    tradition_rigidity_resistance_pct: int = rule(
        60, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Share of a fading tradition's loss that full rigidity holds back (%)"
    )
    law_grace_epochs: int = rule(3, 0, 100, G, "A law is not repealed before it has stood this many epochs")
    repeal_orphan_chance: int = rule(50, 0, 100, G, "Per-epoch chance that a law whose settlement is gone falls out of force (%)")
    repeal_conquest_chance: int = rule(35, 0, 100, G, "Chance that a law of a settlement conquered this epoch is repealed (%)")
    unjust_justice: int = rule(35, 0, 100, G, "A law below this justice counts as unjust")
    repeal_unjust_chance: int = rule(8, 0, 100, G, "Per-epoch chance that an unjust law is repealed (%)")
    repeal_rebels_bonus: int = rule(20, 0, 100, G, "Extra repeal chance of an unjust law where rebels are organised (%)")
    rigidity_resistance_pct: int = rule(70, 0, 100, G, "Share of a law's repeal chance that full rigidity holds back (%)")
    oppression_rigidity: int = rule(60, 0, 100, G, "An unjust law of this rigidity or more oppresses its people")
    oppression_prosperity: int = rule(2, 0, 100, G, "Prosperity an oppressive law gnaws from its settlement every epoch")
    repeal_cap: int = rule(3, 0, 50, G, "Most laws repealed per epoch")
    cult_grace_epochs: int = rule(4, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A cult neither disbands nor merges before it has lived this many epochs")
    cult_small_pct: int = rule(
        10, 1, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A cult with fewer followers than this share of its world's median cult is small (%)"
    )
    cult_weak_influence: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A cult below this influence is weak")
    cult_disband_chance: int = rule(8, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Per-epoch chance that a small or weak cult disbands (%)")
    cult_godless_bonus: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Extra disband chance of a cult left without a god or a home (%)")
    cult_merge_ratio_pct: int = rule(
        30,
        1,
        100,
        RuleGroup.RELIGION_AND_LANGUAGE,
        "A small cult can join a cult of the same god that this share of the larger one's followers still exceeds (%)",
    )
    cult_merge_chance: int = rule(6, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Per-epoch chance that a small cult joins a larger cult of the same god (%)")
    cult_reconcile_chance: int = rule(
        10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Per-epoch chance that a sect at peace returns to the cult it split from (%)"
    )
    cult_zeal_block: int = rule(70, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A cult of this zeal or more refuses to merge")
    cult_cap: int = rule(1, 0, 20, RuleGroup.RELIGION_AND_LANGUAGE, "Most cults disbanded and most cults merged per epoch (each)")
    assimilation_ratio_pct: int = rule(20, 1, 100, G, "A small people at or below this share of a larger people of its region can be assimilated (%)")
    assimilation_chance: int = rule(1, 0, 100, G, "Per-epoch chance that a small people is assimilated (%)")
    assimilation_rule_bonus: int = rule(5, 0, 100, G, "Extra assimilation chance when the larger people rules the smaller (%)")
    assimilation_language_bonus: int = rule(3, 0, 100, G, "Extra assimilation chance when both peoples speak the same tongue (%)")
    union_ratio_pct: int = rule(60, 1, 100, G, "Two friendly peoples whose population ratio exceeds this can unite (%)")
    union_relation: int = rule(40, 0, 100, G, "Least relation of two peoples that unite")
    union_chance: int = rule(2, 0, 100, G, "Per-epoch chance that two equal, friendly peoples of one tongue unite (%)")
    people_grace_epochs: int = rule(5, 0, 100, G, "A people is neither assimilated nor united before it has lived this many epochs")
    people_kept_pct: int = rule(80, 0, 100, G, "Share of a vanishing people's population that joins the other (%)")
    people_cap: int = rule(1, 0, 20, G, "Most assimilations and unions per epoch")
    work_renown_gain: int = rule(2, 0, 100, G, "Renown each carrier (maker, celebrant, teller, owner) adds to a work per epoch")
    work_carrier_cap: int = rule(3, 0, 100, G, "Most carriers counted toward a work's renown")
    work_fade: int = rule(1, 0, 100, G, "Renown a work loses every epoch")
    work_orphan_fade: int = rule(2, 0, 100, G, "Extra renown lost by a work no one carries")
    work_influence_step: int = rule(2, 0, 100, G, "Most a work's influence moves toward its renown per epoch")
    work_forget_renown: int = rule(3, 0, 100, G, "A work no one carries is forgotten at or below this renown")
    work_grace_epochs: int = rule(6, 0, 100, G, "A work is not forgotten before it has existed this many epochs")
    written_resistance_pct: int = rule(50, 0, 100, G, "Share of the fading that lasting works (books, inscriptions, epics, frescoes) resist (%)")
    item_grace_epochs: int = rule(4, 0, 100, G, "An unowned item is not lost before it has existed this many epochs")
    item_loss_chance: int = rule(3, 0, 100, G, "Per-epoch chance that an unowned item lying in ruins or the wild is lost (%)")
    item_might_resistance_pct: int = rule(50, 0, 100, G, "Share of an item's loss chance that full might holds back (%)")
    item_cap: int = rule(2, 0, 50, G, "Most items lost per epoch")
    swallow_severity: int = rule(70, 0, 100, G, "An earthquake or flood of this severity can swallow a place of its region")
    swallow_chance: int = rule(8, 0, 100, G, "Chance that a severe earthquake or flood swallows a place (%)")
    swallow_cap: int = rule(1, 0, 20, G, "Most places swallowed per epoch")
