from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class PantheonRules:
    extinguish_star_apocalypse: int = rule(8, 0, 100, RuleGroup.APOCALYPSE, "Contribution of extinguishing a star to the apocalypse")
    foreign_attract_chance: int = rule(25, 0, 100, RuleGroup.CIVILIZATION, "A foreign god attracts a worshipper (%)")
    foreign_sacrifice_chance: int = rule(50, 0, 100, RuleGroup.CIVILIZATION, "A foreign god demands a sacrifice (%)")
    foreign_friend_help_chance: int = rule(15, 0, 100, RuleGroup.CIVILIZATION, "A friendly foreign god helps (%)")
    outer_expel_chance: int = rule(50, 0, 100, RuleGroup.COSMIC_HORROR, "The Creator pushes an Outer Being out (%)")
    foreign_strength_base: int = rule(40, 0, 100, RuleGroup.CIVILIZATION, "Base strength of a new foreign god")
    foreign_strength_die: int = rule(40, 1, 100, RuleGroup.CIVILIZATION, "Strength die of a new foreign god")
    foreign_attract_targets: int = rule(2, 0, 100, RuleGroup.CIVILIZATION, "Maximum unclaimed communities a foreign god turns to per epoch")
    foreign_population_per_faith: int = rule(2000, 1, 10000000, RuleGroup.CIVILIZATION, "Worshipping population giving 1 faith to a foreign god")
    foreign_followers_per_faith: int = rule(60, 1, 10000000, RuleGroup.CIVILIZATION, "Followers giving 1 faith to a foreign god")
    foreign_growth_faith: int = rule(10, 0, 100000, RuleGroup.CIVILIZATION, "Faith at which a foreign god starts to grow stronger")
    foreign_growth: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Per-epoch strength growth of a foreign god with enough faith")
    attitude_curious: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "Attitude of a foreign god showing curiosity at first contact")
    attitude_hostile: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "Attitude of a foreign god showing hostility at first contact (negative)")
    foreign_attack_base_pct: int = rule(20, 0, 100, RuleGroup.CIVILIZATION, "Base attack chance of a hostile foreign god (%)")
    foreign_attack_hostility_divisor: int = rule(300, 1, 100000, RuleGroup.CIVILIZATION, "Hostility contribution to attack chance: hostility / this number")
    foreign_steal_wrath: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "Wrath gain of a son whose worshipper is stolen")
    foreign_friend_min_attitude: int = rule(40, 0, 100, RuleGroup.CIVILIZATION, "Minimum attitude of a foreign god counted as friendly")
    foreign_friend_help_targets: int = rule(2, 0, 100, RuleGroup.CIVILIZATION, "Maximum worshippers a friendly foreign god helps per epoch")
    foreign_friend_prosperity: int = rule(4, 0, 100, RuleGroup.CIVILIZATION, "Prosperity contribution of a friendly foreign god to its worshippers")
    foreign_rebel_attitude_drift: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Each rebel son on the world lowers the foreign god's attitude")
    foreign_curse_attitude_drift: int = rule(1, 0, 100, RuleGroup.CIVILIZATION, "Foreign god attitude drop when a native is cursed")
    outer_gnaw_divisor: int = rule(10, 1, 1000, RuleGroup.COSMIC_HORROR, "Essence an Outer Being gnaws from the Creator: influence / this number")
    holy_world_take_relation: int = rule(15, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Sibling-relation cost of taking someone else's holy world")
    seal_leak_reduction: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Leak reduction on both worlds from sealing a gate")
    star_brightness_base: int = rule(50, 0, 100, RuleGroup.SKY, "Base brightness of a new star")
    star_brightness_die: int = rule(45, 1, 100, RuleGroup.SKY, "Brightness die of a new star")
    dead_star_brightness: int = rule(5, 0, 100, RuleGroup.SKY, "Brightness of an extinguished star")
    extinguish_leak: int = rule(20, 0, 100, RuleGroup.SKY, "Leak flowing to its planets when a star is extinguished")
    extinguish_fertility_loss: int = rule(25, 0, 100, RuleGroup.SKY, "Fertility loss of planet regions when a star is extinguished")
    cleanse_leak_amount: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "Leak reduced by cleansing")
    bargain_essence_base: int = rule(40, 0, 1000, RuleGroup.COSMIC_HORROR, "Base essence gain from bargaining with an Outer Being")
    bargain_influence_divisor: int = rule(2, 1, 100, RuleGroup.COSMIC_HORROR, "Outer Being influence contribution to the bargain: influence / this number")
    bargain_ambition: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Ambition gain of the bargaining son")
    bargain_loyalty_loss: int = rule(15, 0, 100, RuleGroup.COSMIC_HORROR, "Loyalty loss of the bargaining son")
    bargain_leak: int = rule(20, 0, 100, RuleGroup.COSMIC_HORROR, "Leak the bargain adds to the world")
    bargain_sibling_relation_loss: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Relation loss of the bargaining son with his siblings")
    son_war_chance: int = rule(10, 0, 100, RuleGroup.CIVILIZATION, "A son spontaneously goes to war with a hostile foreign god (% per epoch)")
    son_war_max_attitude: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Maximum attitude (negative) of a foreign god a son spontaneously goes to war with")
    sleep_wake_threshold: int = rule(
        100,
        1,
        100000,
        RuleGroup.CIVILIZATION,
        "Sleeping local god: accumulated awakening pressure needed to wake (only events accumulate; it never wakes by itself over time)",
    )
    sleep_epoch_cap: int = rule(
        25,
        0,
        100000,
        RuleGroup.CIVILIZATION,
        "Awakening pressure: maximum pressure that can accumulate in one epoch (even the god of a crowded world wakes through sustained events, not in a single epoch)",
    )
    sleep_per_son: int = rule(
        15,
        0,
        1000,
        RuleGroup.CIVILIZATION,
        "Awakening pressure: each son acting (creating or entering the chronicle) on that world this epoch; merely staying there doesn't count",
    )
    sleep_per_expedition: int = rule(20, 0, 1000, RuleGroup.CIVILIZATION, "Awakening pressure: each expedition setting out to that world or each route opened")
    sleep_per_event: int = rule(
        6, 0, 1000, RuleGroup.CIVILIZATION, "Awakening pressure: each major event on that world this epoch (war, disaster, plague, battle\u2026)"
    )
    sleep_per_land: int = rule(8, 0, 1000, RuleGroup.CIVILIZATION, "Awakening pressure: each new region or place opened on that world by sons or mortals")
    sleep_per_relic: int = rule(
        25, 0, 1000, RuleGroup.CIVILIZATION, "Awakening pressure: each ancient remnant or trace of a previous creation found on that world"
    )
    sleep_per_death: int = rule(
        2,
        0,
        1000,
        RuleGroup.CIVILIZATION,
        "Awakening pressure: each named mortal who died on that world in the previous epoch (old-age deaths happen at the engine's end; each death counts once)",
    )
    sleep_baseline_ignore_pct: int = rule(
        100,
        0,
        1000,
        RuleGroup.CIVILIZATION,
        "Awakening pressure: percentage of the world's usual noise (moving average) ignored; only shaking above the usual accumulates (0: all counts)",
    )
    sleep_average_weight_pct: int = rule(20, 1, 100, RuleGroup.CIVILIZATION, "Awakening pressure: each epoch's contribution to the usual-noise average (%)")
    auto_holy_world_per_son: int = rule(
        1, 0, 100, RuleGroup.CIVILIZATION, "Spontaneous holy world: maximum worlds a son can claim this way (those given by tool or the god's hand don't count)"
    )
    rival_relation: int = rule(60, 0, 100, RuleGroup.CIVILIZATION, "Rival clash: two active siblings with relation below minus this may clash on their own")
    rival_chance: int = rule(15, 0, 100, RuleGroup.CIVILIZATION, "Rival clash: chance of a suitable rival pair clashing in one epoch (%)")
    rival_cap: int = rule(1, 0, 50, RuleGroup.CIVILIZATION, "Rival clash: maximum spontaneous clashes in one epoch (0: off)")
    rival_cooldown_epochs: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Rival clash: epochs that must pass before the same two siblings clash again")
    rival_soften: int = rule(
        2, 0, 100, RuleGroup.CIVILIZATION, "Rival clash: per-epoch softening of the relation of rivals who don't clash (up to the rivalry threshold)"
    )
    rival_defeat_streak: int = rule(2, 1, 100, RuleGroup.CIVILIZATION, "Rival clash: one defeated this many times in a row by the same sibling withdraws")
    rival_withdraw_relation: int = rule(
        25, 0, 100, RuleGroup.CIVILIZATION, "Rival clash: improvement of the relation between the one withdrawing and the victor (leaves rivalry)"
    )
    auto_holy_world_worshippers: int = rule(
        3,
        0,
        1000,
        RuleGroup.CIVILIZATION,
        "On a world without a protector, the son with the most worshippers declares it his holy world on his own if he has this many worshippers (0: off)",
    )
    foreign_wake_epochs: int = rule(8, 1, 1000, RuleGroup.CIVILIZATION, "Number of epochs after which a defeated foreign god wakes on its own (after defeat)")
    foreign_wake_faith: int = rule(15, 0, 100000, RuleGroup.CIVILIZATION, "Worshipper faith that immediately wakes a defeated foreign god")
    foreign_wake_min_strength: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Minimum strength of a waking foreign god")
    foreign_wake_grudge: int = rule(15, 0, 200, RuleGroup.CIVILIZATION, "Attitude loss toward the pantheon of a waking foreign god (the grudge of defeat)")
    default_fertility: int = rule(50, 0, 100, RuleGroup.SKY, "Fertility assumed when a star is extinguished for a region with no recorded fertility")
    outer_default_influence: int = rule(
        50, 0, 100, RuleGroup.COSMIC_HORROR, "Influence assumed for an Outer Being with no recorded influence (gnawing and bargaining)"
    )
