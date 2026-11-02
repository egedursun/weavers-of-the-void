from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class DeathRules:
    take_life_base_cost: int = rule(25, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Base cost (essence) of a son taking a mortal's life")
    take_life_cost_per_power: int = rule(6, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Essence added to the take-life cost per power level of the victim")
    take_life_cost_importance_divisor: int = rule(
        2, 1, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Victim's importance score / this number is added to the take-life cost as essence"
    )
    take_life_notable_surcharge: int = rule(
        20, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Surcharge (essence) for an important mortal (ruler, hero, chosen one, titled)"
    )
    take_life_per_epoch: int = rule(1, 0, 20, RuleGroup.DEATH_AND_RESURRECTION, "Maximum take-life attempts by a son in one epoch (0 disables the tool)")
    take_life_base_success: int = rule(65, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Base success chance of taking a life (%)")
    take_life_might_divisor: int = rule(5, 1, 1000, RuleGroup.DEATH_AND_RESURRECTION, "The son's might / this number is added to success")
    take_life_importance_resist: int = rule(4, 1, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Victim's importance score / this number is subtracted from success")
    take_life_patron_resist: int = rule(
        25, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Subtracted from success if another son protects the victim (its patron) (%)"
    )
    take_life_creator_resist: int = rule(
        35, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Subtracted from success if the victim worships the Creator directly (%)"
    )
    take_life_protected_resist: int = rule(40, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Subtracted from success if the victim is protected or chosen (%)")
    take_life_item_protection: int = rule(
        50,
        0,
        100,
        RuleGroup.DEATH_AND_RESURRECTION,
        "If an item owned by the victim has protection at or above this it can draw death's breath upon itself (mentioned in the story)",
    )
    take_life_min_chance: int = rule(5, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Minimum success chance of taking a life (%)")
    take_life_max_chance: int = rule(95, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Maximum success chance of taking a life (%)")
    take_life_refund_pct: int = rule(0, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Share of essence returned on a failed take-life (%)")
    take_life_relation_loss: int = rule(
        15, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Relation loss of the life-taking son with the victim's patron and creator"
    )
    survivor_charisma_gain: int = rule(10, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Charisma gain of a mortal who returns from death")
    survivor_legend_power: int = rule(3, 1, 12, RuleGroup.DEATH_AND_RESURRECTION, "Power level of the legend of the return from death")
    foreign_god_smite_chance: int = rule(
        4, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "An awake foreign god strikes a named mortal on its own world who does not worship it (% per epoch)"
    )
    creator_take_life_cost: int = rule(15, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Cost for Aeron (the Creator) to take a mortal's life (divine essence)")
    creator_kill_son_cost: int = rule(100, 0, 100000, RuleGroup.DEATH_AND_RESURRECTION, "Cost for Aeron to kill a son (divine essence)")
    kill_son_loyalty_gain: int = rule(10, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Loyalty the other sons gain out of fear when Aeron kills a son")
    kill_son_friend_wrath: int = rule(15, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Wrath of the dead son's friendly siblings when Aeron kills a son")
    resurrection_min_epochs: int = rule(
        3, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "A dead son can resurrect on his own at the earliest after this many epochs (except by Aeron's hand)"
    )
    rite_chance: int = rule(
        20, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A community loyal to its dead god holds a resurrection rite on its own (% per epoch)"
    )
    rite_devotion: int = rule(6, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Contribution of a spontaneous rite (devotion)")
    rite_prosperity_cost: int = rule(5, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Cost of the rite to the community (prosperity or wealth)")
    pilgrimage_multiplier_pct: int = rule(
        200, 100, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Contribution multiplier if the rite is held in the region where the god's bones lie (%)"
    )
    sacrifice_chance: int = rule(5, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A loyal community makes a blood sacrifice on its own (% per epoch)")
    sacrifice_population_pct: int = rule(3, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Population lost in a blood sacrifice (%)")
    sacrifice_devotion: int = rule(20, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Contribution of a blood sacrifice (devotion)")
    self_sacrifice_devotion: int = rule(
        35, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Contribution of a named mortal sacrificing themself (or their people sacrificing them) (devotion)"
    )
    offering_devotion: int = rule(10, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Contribution of offering wealth and votive gifts (devotion)")
    offering_cost: int = rule(15, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Cost of a wealth offering (prosperity or wealth)")
    prayer_devotion: int = rule(4, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Contribution of prayer (devotion)")
    rite_per_epoch: int = rule(
        1, 0, 20, RuleGroup.DEATH_AND_RESURRECTION, "resurrection_rite (dirilis_ayini): maximum rites by one mortal per epoch (0 disables the tool)"
    )
    sibling_rite_cost: int = rule(45, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Sibling's resurrection rite: cost (essence)")
    sibling_rite_devotion: int = rule(25, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Sibling's resurrection rite: contribution (devotion)")
    sibling_descent_cost: int = rule(70, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Descent into the realm of the dead: cost (essence)")
    sibling_descent_devotion: int = rule(50, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Descent into the realm of the dead: contribution (devotion)")
    sibling_descent_success: int = rule(
        60, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Success chance of the descent into the realm of the dead (%); on failure the descender falls asleep"
    )
    sibling_descent_sleep_epochs: int = rule(
        2, 1, 100, RuleGroup.DEATH_AND_RESURRECTION, "Sleep duration of a sibling who loses their way in the realm of the dead (epochs)"
    )
    sibling_bargain_cost: int = rule(
        25,
        0,
        10000,
        RuleGroup.DEATH_AND_RESURRECTION,
        "Bargain with a foreign god: cost (essence); additionally one of the dead god's loyal communities converts to the foreign god",
    )
    sibling_bargain_devotion: int = rule(40, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Bargain with a foreign god: contribution (devotion)")
    sibling_intrigues_per_epoch: int = rule(
        1, 0, 20, RuleGroup.DEATH_AND_RESURRECTION, "Maximum resurrection intrigues or bone scatterings by one son in one epoch (0 disables the tools)"
    )
    auto_intrigue_min_relation: int = rule(
        40, -100, 100, RuleGroup.DEATH_AND_RESURRECTION, "Minimum relation with the sibling for a spontaneous resurrection intrigue"
    )
    auto_intrigue_chance: int = rule(
        25, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A sufficiently close sibling with enough essence enters an intrigue on their own (% per epoch)"
    )
    auto_intrigue_essence_share: int = rule(
        60, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "In a spontaneous intrigue the sibling spends at most this share of their essence (%)"
    )
    sibling_scheme_relation_gain: int = rule(
        12, 0, 200, RuleGroup.DEATH_AND_RESURRECTION, "Relation gain with the dead sibling of a son whose resurrection scheme adds devotion"
    )
    scatter_bones_cost: int = rule(30, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Cost of scattering the bones (essence)")
    scatter_bones_devotion_loss: int = rule(35, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Devotion reduced by scattering the bones")
    auto_scatter_relation: int = rule(40, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Relation with the dead for spontaneous bone scattering: below minus this")
    auto_scatter_chance: int = rule(15, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A hostile sibling scatters the bones on their own (% per epoch)")
    new_cult_followers: int = rule(
        80,
        1,
        1000000,
        RuleGroup.DEATH_AND_RESURRECTION,
        "Followers of the new resurrection cult born when a rite is held for a dead god with no remaining cult",
    )
    god_corpse_power: int = rule(8, 1, 12, RuleGroup.DEATH_AND_RESURRECTION, "Power level of a god's corpse")
    god_corpse_danger: int = rule(45, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Danger of a god's corpse")
    god_corpse_fertility: int = rule(30, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Fertility of a god's corpse")
    god_corpse_mystery: int = rule(95, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Mystery of a god's corpse")
    god_shade_power: int = rule(7, 1, 12, RuleGroup.DEATH_AND_RESURRECTION, "Power level of the dead god's shade")
    god_shade_strength: int = rule(70, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Strength of the dead god's shade")
    god_shade_unrest: int = rule(75, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Unrest of the dead god's shade")
    resurrection_cult_default_population: int = rule(
        500, 0, 1000000, RuleGroup.DEATH_AND_RESURRECTION, "Resurrection cult: population assumed for a loyal community with no population record"
    )
    resurrection_cult_join_pct: int = rule(10, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Share of loyal communities joining the resurrection cult (%)")
    resurrection_cult_min_followers: int = rule(50, 1, 1000000, RuleGroup.DEATH_AND_RESURRECTION, "Minimum followers of a resurrection cult")
    resurrection_cult_max_followers: int = rule(1000000, 1, 100000000, RuleGroup.DEATH_AND_RESURRECTION, "Maximum followers of a resurrection cult")
    resurrection_cult_power: int = rule(4, 1, 12, RuleGroup.DEATH_AND_RESURRECTION, "Power level of a resurrection cult")
    resurrection_cult_zealotry: int = rule(75, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Zealotry of a resurrection cult")
    resurrection_cult_influence: int = rule(40, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Influence of a resurrection cult")
    dead_essence_divisor: int = rule(2, 1, 100, RuleGroup.DEATH_AND_RESURRECTION, "The dead god's essence is divided by this number and returns to the Creator")
    god_death_relation_threshold: int = rule(30, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Hostility/friendship threshold toward the dead god")
    god_death_enemy_renown: int = rule(5, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Renown gain of the dead god's enemy")
    god_death_friend_wrath: int = rule(10, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Wrath gain of the dead god's friend")
    resurrected_existence: int = rule(35, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Existence of a resurrected god")
    resurrected_hp_divisor: int = rule(2, 1, 100, RuleGroup.DEATH_AND_RESURRECTION, "Resurrected god's HP: max HP / this number")
    resurrected_essence_divisor: int = rule(3, 1, 100, RuleGroup.DEATH_AND_RESURRECTION, "Resurrected god's essence: max essence / this number")
    resurrected_renown: int = rule(20, 0, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Renown gain of a resurrected god")
    resurrected_stat_loss: int = rule(4, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Loss in each stat of a resurrected god")
    devotion_follower_log_mult: int = rule(6, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "Resurrection devotion: log10(followers) multiplier")
    devotion_influence_divisor: int = rule(10, 1, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Resurrection devotion: influence / this number")
    devotion_zealotry_divisor: int = rule(20, 1, 1000, RuleGroup.DEATH_AND_RESURRECTION, "Resurrection devotion: zealotry / this number")
    devotion_cap: int = rule(200, 1, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Cap of resurrection devotion")
    resurrection_devotion_required: int = rule(100, 0, 10000, RuleGroup.DEATH_AND_RESURRECTION, "Devotion required for the resurrection rite")
    fading_threshold: int = rule(10, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A son below this existence starts fading out")
    fading_death_epochs: int = rule(3, 1, 50, RuleGroup.DEATH_AND_RESURRECTION, "Epochs for a fading son to die")
    apostasy_chance: int = rule(50, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A worshipper of a dead god falls into denial (%)")
    cult_resurrection_chance: int = rule(50, 0, 100, RuleGroup.DEATH_AND_RESURRECTION, "A devoted cult resurrects its god (%)")
