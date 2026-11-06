from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class GodPowerRules:
    drain_son_pct: int = rule(50, 1, 100, RuleGroup.THE_GODS_POWER, "Drain essence from a son: percentage of the son's essence per drain")
    drain_son_efficiency_pct: int = rule(
        80, 0, 100, RuleGroup.THE_GODS_POWER, "Percentage of essence drained from a son that passes to the god (the rest scatters)"
    )
    drain_son_loyalty_loss: int = rule(10, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty loss of a drained son")
    drain_son_wrath: int = rule(15, 0, 100, RuleGroup.THE_GODS_POWER, "Wrath gain of a drained son")
    drain_son_existence_loss: int = rule(5, 0, 100, RuleGroup.THE_GODS_POWER, "Existence loss of a drained son")
    drain_witness_loyalty: int = rule(3, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty gain out of fear of other sons witnessing a drain")
    devour_son_essence_per_might: int = rule(3, 0, 100, RuleGroup.THE_GODS_POWER, "Devour a son: extra essence passing to the god per might point")
    devour_son_essence_per_level: int = rule(20, 0, 1000, RuleGroup.THE_GODS_POWER, "Devour a son: extra essence passing to the god per level")
    devour_son_witness_loyalty: int = rule(10, 0, 100, RuleGroup.THE_GODS_POWER, "Devour a son: loyalty gain out of fear of the other sons")
    devour_son_friend_wrath: int = rule(25, 0, 100, RuleGroup.THE_GODS_POWER, "Devour a son: wrath gain of those who loved the devoured")
    drain_mortal_pct: int = rule(50, 1, 100, RuleGroup.THE_GODS_POWER, "Drain life from a mortal: percentage of their HP")
    drain_mortal_hp_per_essence: int = rule(10, 1, 1000, RuleGroup.THE_GODS_POWER, "Every this much HP drained from a mortal becomes 1 essence for the god")
    devour_mortal_essence_per_power: int = rule(2, 0, 100, RuleGroup.THE_GODS_POWER, "Devour a mortal: extra essence per power level")
    harvest_population_pct: int = rule(10, 0, 100, RuleGroup.THE_GODS_POWER, "Faith harvest: percentage of the community's population sacrificed")
    harvest_piety_loss: int = rule(20, 0, 100, RuleGroup.THE_GODS_POWER, "Faith harvest: community's piety loss")
    harvest_victims_per_essence: int = rule(500, 1, 1000000, RuleGroup.THE_GODS_POWER, "Faith harvest: every this many victims become 1 essence")
    harvest_essence_per_piety: int = rule(1, 0, 100, RuleGroup.THE_GODS_POWER, "Faith harvest: essence of each piety point lost")
    harvest_patron_loyalty_loss: int = rule(8, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty loss of the son worshipped by the harvested community")
    drain_foreign_pct: int = rule(30, 1, 100, RuleGroup.THE_GODS_POWER, "Drain essence from a foreign god: percentage of its strength")
    foreign_essence_per_strength: int = rule(3, 0, 100, RuleGroup.THE_GODS_POWER, "Essence of each strength point of a foreign god")
    drain_foreign_attitude_loss: int = rule(20, 0, 200, RuleGroup.THE_GODS_POWER, "A drained foreign god's attitude drops by this much")
    kill_foreign_base_cost: int = rule(60, 0, 2000, RuleGroup.THE_GODS_POWER, "Base cost of killing a foreign god")
    kill_foreign_strength_pct: int = rule(100, 0, 1000, RuleGroup.THE_GODS_POWER, "Killing a foreign god: this percentage of its strength is added to the cost")
    kill_immortal_foreign_mult: int = rule(2, 1, 10, RuleGroup.THE_GODS_POWER, "Cost multiplier for killing a foreign god with the immortal power")
    foreign_worshipper_convert_pct: int = rule(
        50, 0, 100, RuleGroup.THE_GODS_POWER, "Chance a dead foreign god's worshippers turn to the Creator (%); those who don't become godless"
    )
    resurrect_mortal_base_cost: int = rule(40, 0, 1000, RuleGroup.THE_GODS_POWER, "Base cost of resurrecting a mortal")
    resurrect_mortal_cost_per_power: int = rule(2, 0, 100, RuleGroup.THE_GODS_POWER, "Resurrect a mortal: extra cost per power level")
    resurrect_mortal_hp: int = rule(50, 1, 300, RuleGroup.THE_GODS_POWER, "HP of a resurrected mortal")
    resurrect_mortal_lifespan_years: int = rule(
        20, 0, 50000, RuleGroup.THE_GODS_POWER, "Years added to the lifespan of a mortal who died of old age when resurrected"
    )
    deify_cost: int = rule(150, 0, 5000, RuleGroup.THE_GODS_POWER, "Cost of raising a mortal to godhood")
    deify_loyalty: int = rule(80, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty of the deified mortal toward you")
    deify_existence: int = rule(50, 1, 100, RuleGroup.THE_GODS_POWER, "Starting existence of the deified")
    deify_passion_max: int = rule(50, 0, 100, RuleGroup.THE_GODS_POWER, "Highest starting ambition, wrath and mercy rolled for a deified mortal")
    deify_strong_stats: int = rule(
        2, 0, 9, RuleGroup.THE_GODS_POWER, "Son stats that start strong when a mortal is deified (picked from its best mortal stats)"
    )
    demote_cost: int = rule(40, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of demoting a son one rarity down")
    demote_loyalty_loss: int = rule(15, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty loss of a demoted son")
    demote_wrath: int = rule(25, 0, 100, RuleGroup.THE_GODS_POWER, "Wrath gain of a demoted son")
    strip_power_cost: int = rule(30, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of stripping one of a son's powers")
    strip_power_wrath: int = rule(20, 0, 100, RuleGroup.THE_GODS_POWER, "Wrath gain of a son whose power is stripped")
    strip_power_essence: int = rule(15, 0, 1000, RuleGroup.THE_GODS_POWER, "Essence passing to the god from the stripped power")
    absolute_command_cost: int = rule(25, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of an irrefusable command")
    absolute_command_loyalty_loss: int = rule(5, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty loss of a son receiving an irrefusable command")
    prophet_cost: int = rule(20, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of choosing a mortal as prophet")
    prophet_charisma: int = rule(15, 0, 100, RuleGroup.THE_GODS_POWER, "Charisma gain of the prophet")
    prophet_piety: int = rule(10, 0, 100, RuleGroup.THE_GODS_POWER, "Piety gain of the prophet's community")
    prophet_convert_chance: int = rule(15, 0, 100, RuleGroup.THE_GODS_POWER, "Chance each epoch that the prophet's community turns to the Creator (%)")
    manifest_cost: int = rule(10, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of appearing to a mortal or community while awake")
    manifest_piety: int = rule(10, 0, 100, RuleGroup.THE_GODS_POWER, "Piety gain from a manifestation")
    manifest_worship_chance: int = rule(30, 0, 100, RuleGroup.THE_GODS_POWER, "Chance the witness of a manifestation starts worshipping the Creator (%)")
    manifest_message_max_chars: int = rule(600, 50, 5000, RuleGroup.THE_GODS_POWER, "Maximum length of the words spoken in a manifestation (characters)")
    bloodline_curse_cost: int = rule(40, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of cursing a bloodline")
    bloodline_curse_lift_cost: int = rule(20, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of lifting a bloodline's curse")
    bloodline_curse_depth: int = rule(6, 1, 50, RuleGroup.THE_GODS_POWER, "How many generations down a bloodline curse reaches")
    bloodline_curse_stat_loss: int = rule(
        10, 0, 100, RuleGroup.THE_GODS_POWER, "Strength, prosperity and similar removed from each cursed member by a bloodline curse"
    )
    convert_cost: int = rule(30, 0, 1000, RuleGroup.THE_GODS_POWER, "Cost of converting a community to yourself (it leaves its previous god)")
    convert_patron_loyalty_loss: int = rule(10, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty loss of the son whose worshipper is taken away")
    wrath_base_cost: int = rule(60, 0, 5000, RuleGroup.THE_GODS_POWER, "Wrath: base cost of destroying a record")
    wrath_cost_per_power: int = rule(5, 0, 1000, RuleGroup.THE_GODS_POWER, "Wrath: extra cost per power level")
    wrath_death_chance: int = rule(70, 0, 100, RuleGroup.THE_GODS_POWER, "Wrath: chance named mortals at the destroyed place die (%)")
    world_wrath_cost: int = rule(200, 0, 10000, RuleGroup.THE_GODS_POWER, "Cost of bringing wrath upon an entire world")
    world_wrath_severity: int = rule(60, 1, 100, RuleGroup.THE_GODS_POWER, "Severity of the disaster striking each region in world wrath (%)")
    auto_drain_wrath: int = rule(
        60, 0, 100, RuleGroup.THE_GODS_POWER, "When the Creator's wrath exceeds this, it may automatically drain the essence of rebel sons"
    )
    auto_drain_chance: int = rule(30, 0, 100, RuleGroup.THE_GODS_POWER, "Chance in one epoch that a wrathful Creator drains a rebel son's essence (%)")
    auto_drain_effect_pct: int = rule(
        50, 0, 100, RuleGroup.THE_GODS_POWER, "Loyalty and wrath effect of a wrathful Creator's spontaneous drain compared with a deliberate one (%)"
    )
    auto_drain_spacing: int = rule(
        3, 0, 100, RuleGroup.THE_GODS_POWER, "A spontaneous drain falls on the same son at most once in this many epochs (0: every epoch)"
    )
    drain_repeat_keep_pct: int = rule(
        50, 0, 100, RuleGroup.THE_GODS_POWER, "Each further drain of the same son in the same epoch keeps this share of the loyalty and wrath effect (%)"
    )
    auto_drain_loyalty: int = rule(
        20, 0, 100, RuleGroup.THE_GODS_POWER, "If there are no rebel sons, the wrathful Creator may drain the most defiant son with loyalty below this"
    )
    auto_rebel_loyalty: int = rule(15, 0, 100, RuleGroup.THE_GODS_POWER, "A son whose loyalty fell below this may rebel unprompted")
    auto_rebel_wrath: int = rule(60, 0, 100, RuleGroup.THE_GODS_POWER, "Minimum wrath of a son for spontaneous rebellion")
    auto_rebel_chance: int = rule(20, 0, 100, RuleGroup.THE_GODS_POWER, "Chance in one epoch that a son meeting the conditions rebels unprompted (%)")
    auto_return_loyalty: int = rule(50, 0, 100, RuleGroup.THE_GODS_POWER, "A rebel son whose loyalty rises back to this may return to the Creator unprompted")
    auto_return_chance: int = rule(
        25, 0, 100, RuleGroup.THE_GODS_POWER, "Chance in one epoch that a rebel son with restored loyalty abandons the rebellion (%)"
    )
    auto_curse_epochs: int = rule(
        3,
        0,
        100,
        RuleGroup.THE_GODS_POWER,
        "Whoever kills a prophet or a Creator worshipper becomes a candidate for a spontaneous bloodline curse within this many epochs",
    )
    auto_curse_chance: int = rule(30, 0, 100, RuleGroup.THE_GODS_POWER, "Chance in one epoch that the bloodline of the bloody hand is cursed automatically (%)")
    auto_curse_wrath: int = rule(
        55,
        0,
        100,
        RuleGroup.THE_GODS_POWER,
        "When the Creator's wrath exceeds this, it may automatically curse the bloodline of a cursed, temple-razing or many-lives-taking mortal",
    )
    auto_curse_min_kills: int = rule(
        2, 0, 100, RuleGroup.THE_GODS_POWER, "The wrathful Creator may also curse the bloodline of a mortal who took at least this many lives (0: off)"
    )
    auto_curse_wrath_chance: int = rule(
        15, 0, 100, RuleGroup.THE_GODS_POWER, "Chance in one epoch that the wrathful Creator automatically curses a cursed bloodline (%)"
    )
    auto_prophet_contentment: int = rule(
        55, 0, 100, RuleGroup.THE_GODS_POWER, "When the Creator's contentment exceeds this, it may automatically choose one of its cult's devotees as prophet"
    )
    auto_prophet_chance: int = rule(20, 0, 100, RuleGroup.THE_GODS_POWER, "Chance in one epoch that a content Creator automatically chooses a prophet (%)")
    auto_prophet_cap: int = rule(
        2,
        0,
        100,
        RuleGroup.THE_GODS_POWER,
        "When living prophets reach this number the Creator does not automatically choose a new one (0: never automatically)",
    )
    auto_candidates: int = rule(4, 1, 100, RuleGroup.THE_GODS_POWER, "In automatic choice, picked by dice from this many best candidates")
