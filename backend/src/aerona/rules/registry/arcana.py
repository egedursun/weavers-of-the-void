from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

H = RuleGroup.HEROES_AND_MORTALS
D = RuleGroup.THE_DIVINE
P = RuleGroup.THE_GODS_POWER


@dataclass(frozen=True)
class SpellGrammarRules:
    difficulty_per_power: int = rule(2, 0, 100, H, "Difficulty each step of power adds to a rite's technique and form")
    cost_per_difficulty_pct: int = rule(5, 0, 100, H, "Extra price of a rite for each point of its difficulty (%)")
    backlash_per_difficulty_pct: int = rule(1, 0, 100, H, "Extra backlash chance for each point of a rite's difficulty (%)")
    lab_learn_pct: int = rule(25, 0, 100, H, "Chance a mage near a lab text learns its rite each epoch (%)")
    lab_skill: int = rule(20, 0, 100, H, "Spellcraft in a rite a mage gains from learning it out of a lab text")
    lab_fidelity_floor: int = rule(40, 0, 100, H, "Fidelity of a lab text written by a mage with no skill in its rite")
    learners_max: int = rule(400, 0, 100000, H, "Mages who study lab texts each epoch at most")


@dataclass(frozen=True)
class VisRules:
    per_power: int = rule(1, 0, 100, H, "Vis of its form a rite burns for each step of power when its caster holds it")
    power_pct: int = rule(20, 0, 200, H, "Extra strength a rite gains when its caster burns vis of its form (%)")
    site_yield: int = rule(3, 0, 1000, H, "Vis of its form a found source site gives its holder each epoch at full strength")
    beast_pct: int = rule(15, 0, 100, H, "Chance the folk of a region harvest vis from a beast of matching affinity each epoch (%)")
    beast_yield: int = rule(2, 0, 1000, H, "Vis a harvested beast gives")
    corpse_yield: int = rule(6, 0, 1000, H, "Vis of each of its affinities a slain beast gives whoever slew it")
    phenomenon_yield: int = rule(2, 0, 1000, H, "Vis of its form a phenomenon at full intensity gives the folk of its region each epoch")
    trade_units: int = rule(2, 0, 1000, H, "Vis a community with a surplus sells to a neighbour that has none each epoch")
    surplus: int = rule(6, 0, 1000, H, "Vis of one form past which a community sells")
    price: int = rule(5, 0, 1000, H, "Coin a unit of vis fetches")
    black_market_crime: int = rule(4, 0, 100, H, "Crime a vis sale adds to a settlement whose realm forbids magic")


@dataclass(frozen=True)
class SpellResistanceRules:
    willpower_pct: int = rule(50, 0, 200, H, "Share of a target's willpower that resists hostile rites (%)")
    ward: int = rule(15, 0, 100, H, "Resistance each step of power of a ward over the target's settlement gives")
    iron: int = rule(20, 0, 100, H, "Resistance a target carrying iron has against spirit rites")
    sanctity_pct: int = rule(20, 0, 100, H, "Share of the sacredness of the target's place that resists hostile rites (%)")
    hostile_dominion_pct: int = rule(30, 0, 100, H, "Share of a hostile god's dominion over the target's land that resists the caster (%)")
    faith_pct: int = rule(20, 0, 100, H, "Share of the target's piety that resists rites of another faith (%)")
    penetration_per_power: int = rule(12, 0, 100, H, "Penetration each step of a rite's power gives")
    penetration_skill_pct: int = rule(50, 0, 200, H, "Share of the caster's mastery of the rite that becomes penetration (%)")
    dispel_per_power: int = rule(12, 0, 100, H, "Dispelling force each step of power of a dispelling rite gives")


@dataclass(frozen=True)
class ParadigmRules:
    floor_pct: int = rule(50, 0, 100, H, "Reliability of a rite designed under a paradigm that is wholly wrong (%)")
    shift_drop_pct: int = rule(20, 0, 100, H, "Reliability a tradition loses for a season when the theory it rests on is overturned (%)")


@dataclass(frozen=True)
class MythCouplingRules:
    power_pct: int = rule(40, 0, 200, H, "Extra strength of a rite that re-enacts a myth its people fully believe (%)")
    site_pct: int = rule(30, 0, 200, H, "Extra strength of a group rite worked at the place its myth is fixed in (%)")
    corruption_at: int = rule(60, 0, 100, H, "Distortion of a myth past which rites re-enacting it may turn on their aim")


@dataclass(frozen=True)
class SpellEnvironmentRules:
    rain_pct: int = rule(30, 0, 100, H, "Strength rain takes from fire and light rites and gives water and plant rites, at full wet (%)")
    wet_pct: int = rule(30, 0, 100, H, "Strength wet ground gives air rites that strike their target, at full wet (%)")
    wildfire_pct: int = rule(30, 0, 100, H, "Chance a fire rite in a dry forested region lights a wildfire (%)")
    iron_pct: int = rule(40, 0, 100, H, "Strength iron takes from spirit rites cast at one who carries it (%)")
    leak_power_pct: int = rule(50, 0, 200, H, "Extra strength void rites gain at full leakage of their world (%)")
    leak_backlash_pct: int = rule(50, 0, 200, H, "Extra backlash void rites risk at full leakage of their world (%)")


@dataclass(frozen=True)
class WarpingRules:
    per_cast: int = rule(2, 0, 100, H, "Warping a caster gathers from a rite of full power")
    ley: int = rule(1, 0, 100, H, "Warping a mortal living on a ley line gathers each epoch")
    item: int = rule(1, 0, 100, H, "Warping the bearer of an enchanted item gathers each time it is used")
    touched_at: int = rule(25, 0, 100, H, "Warping at which a mortal is touched by magic")
    marked_at: int = rule(50, 0, 100, H, "Warping at which magic marks a mortal's body")
    unmoored_at: int = rule(75, 0, 100, H, "Warping at which magic unmoors a mortal's mind and slows its ageing")
    bearers_max: int = rule(2000, 0, 100000, H, "Mortals the warping step weighs each epoch at most")


@dataclass(frozen=True)
class EnchantedItemRules:
    capacity: int = rule(3, 1, 100, H, "Charges a new enchantment holds")
    crack: int = rule(10, 0, 100, H, "Condition an item loses each time it is used with no charge left")
    site_recharge: int = rule(1, 0, 100, H, "Charges an item regains each epoch at a found magic site")
    vis_recharge_cost: int = rule(1, 0, 100, H, "Vis of the item's form a charge costs to restore")
    moon_recharge: int = rule(1, 0, 100, H, "Charges an item bound to the moon regains each epoch its world's first moon is full")


@dataclass(frozen=True)
class LongevityRules:
    years: int = rule(4, 0, 100, H, "Years of life a dose of longevity magic adds each epoch")
    dependence_gain: int = rule(8, 0, 100, H, "Dependence each epoch of dosing adds")
    dose_step_at: int = rule(50, 1, 100, H, "Dependence past which each dose needs one more vis")
    lapse_years: int = rule(6, 0, 100, H, "Years of borrowed life a mortal loses each epoch its dose is not paid")
    lapse_stress: int = rule(10, 0, 100, H, "Stress a missed dose brings")


@dataclass(frozen=True)
class GlobalEnchantmentRules:
    essence_per_strength_pct: int = rule(10, 0, 100, P, "Essence upkeep a god pays each epoch for each point of strength of a law it keeps (%)")
    vis_upkeep: int = rule(2, 0, 1000, H, "Vis a mage order pays each epoch to keep a global enchantment")
    lapse_after: int = rule(2, 1, 100, D, "Unpaid epochs after which a kept law lapses")
    dispel_resistance: int = rule(50, 0, 100, D, "Dispel resistance of a new global enchantment")
    mage_skill: int = rule(60, 0, 100, H, "Spellcraft a mage needs to lay a global enchantment")
    foreign_power_pct: int = rule(10, 0, 100, P, "Power a foreign god spends for each essence of upkeep of a law it keeps (%)")
