from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MORTALS


@dataclass(frozen=True)
class AgingRules:
    infant_end_pct: int = rule(5, 0, 100, G, "Share of a lifespan spent as an infant when the people sets no curve (%)")
    child_end_pct: int = rule(15, 0, 100, G, "Share of a lifespan spent as a child when the people sets no curve (%)")
    youth_end_pct: int = rule(25, 0, 100, G, "Share of a lifespan spent as a youth when the people sets no curve (%)")
    elder_start_pct: int = rule(70, 0, 200, G, "Share of a lifespan at which old age begins when the people sets no curve (%)")
    ancient_start_pct: int = rule(100, 0, 300, G, "Share of a lifespan past which a mortal is ancient (%)")
    elder_strength_decline: int = rule(4, 0, 100, G, "Strength an elder loses each epoch")
    elder_agility_decline: int = rule(4, 0, 100, G, "Agility an elder loses each epoch")
    elder_endurance_decline: int = rule(4, 0, 100, G, "Endurance an elder loses each epoch")
    elder_wisdom_gain: int = rule(3, 0, 100, G, "Wisdom an elder gains each epoch")
    youth_growth: int = rule(2, 0, 100, G, "Strength, agility and endurance a youth gains each epoch")
    age_condition_chance: int = rule(15, 0, 100, G, "Chance each epoch an elder suffers failing sight, deafness or frailty (%)")
    elder_health_loss: int = rule(4, 0, 100, G, "Health an elder loses each epoch")
    ancient_health_loss: int = rule(8, 0, 100, G, "Health an ancient loses each epoch")
    health_recovery: int = rule(5, 0, 100, G, "Health a sound adult regains each epoch")
    hazard_base_pct: int = rule(25, 0, 100, G, "Chance of death each epoch at exactly the lifespan (%)")
    hazard_steepness: float = rule(4.0, 0.0, 50.0, G, "How steeply the chance of death climbs past the lifespan")
    hazard_start_pct: int = rule(85, 0, 200, G, "Share of the lifespan from which old age can kill (%)")
    hazard_medicine_pct: int = rule(70, 0, 100, G, "Death chance of the old where medicine is known (%)")


@dataclass(frozen=True)
class FertilityRules:
    window_start_pct: int = rule(16, 0, 100, G, "Share of a lifespan at which mortals can first bear children (%)")
    female_window_end_pct: int = rule(60, 0, 200, G, "Share of a lifespan past which women bear no more children (%)")
    male_window_end_pct: int = rule(85, 0, 200, G, "Share of a lifespan past which men father no more children (%)")
    other_window_end_pct: int = rule(70, 0, 200, G, "Share of a lifespan past which others bear no more children (%)")
    unwed_rate_pct: int = rule(25, 0, 100, G, "Rate of children born to lovers who are not wed (%)")
    concubine_rate_pct: int = rule(60, 0, 100, G, "Rate of children born of concubinage (%)")
    youth_rate_pct: int = rule(40, 0, 100, G, "Rate of children born to youths where custom allows it (%)")
    stress_divisor: int = rule(200, 1, 1000, G, "Stress that halves fertility, doubled")
    mortality_base_pct: float = rule(6.0, 0.0, 100.0, G, "Chance the bearer dies in childbirth (%)")
    late_age_risk_pct: int = rule(200, 100, 1000, G, "Childbirth risk late in the fertile years (%)")
    late_age_from_pct: int = rule(75, 0, 100, G, "Share of the fertile window past which childbirth grows riskier (%)")
    twins_pct: float = rule(3.0, 0.0, 100.0, G, "Chance of twins (%)")
    stillbirth_pct: float = rule(8.0, 0.0, 100.0, G, "Chance of a stillbirth (%)")
    hunger_stillbirth_pct: int = rule(200, 100, 1000, G, "Stillbirth chance in a starving community (%)")
    hunger_from: int = rule(50, 0, 100, G, "Hunger at which stillbirths grow more likely")
    other_sex_pct: float = rule(0.0, 0.0, 100.0, G, "Chance a child is born neither female nor male, where the world allows it (%)")
    kinship_pct: int = rule(40, 0, 200, G, "How much a culture that prizes kinship lifts the birth rate (%)")
    ability_deviation: int = rule(8, 0, 50, G, "How far a child's abilities stray from their parents' mean")
    twin_cap: int = rule(2, 1, 6, G, "Most children one birth can bring")


@dataclass(frozen=True)
class EducationRules:
    parent_xp: int = rule(4, 0, 100, G, "Skill a child learns from a parent each epoch")
    school_xp: int = rule(6, 0, 100, G, "Skill a child learns at a school each epoch")
    temple_xp: int = rule(5, 0, 100, G, "Skill a child learns at a temple each epoch")
    literacy_weight_pct: int = rule(60, 0, 200, G, "How much a community's literacy lifts education (%)")
    education_gain: int = rule(6, 0, 100, G, "Education a schooled child gains each epoch")
    education_skill_pct: int = rule(50, 0, 200, G, "How much education speeds learning as an adult (%)")
    hostage_drift_pct: int = rule(30, 0, 100, G, "How far a hostage child's values drift toward the captor's culture each epoch (%)")


@dataclass(frozen=True)
class KinshipRules:
    betrothal_chance: int = rule(10, 0, 100, G, "Chance each epoch a noble family betroths a child (%)")
    marriage_chance: int = rule(25, 0, 100, G, "Chance each epoch that adult lovers or the betrothed wed (%)")
    divorce_chance: int = rule(2, 0, 100, G, "Chance each epoch that a cold marriage ends (%)")
    divorce_opinion_below: int = rule(-40, -100, 100, G, "Opinion between spouses below which they may part")
    forced_marriage_magnitude: int = rule(30, 0, 100, G, "How bitterly the unwilling remember a forced marriage")
    widowed_magnitude: int = rule(40, 0, 100, G, "How deeply a spouse remembers losing their partner")
    orphan_magnitude: int = rule(40, 0, 100, G, "How deeply a child remembers losing a parent")
    foster_chance: int = rule(30, 0, 100, G, "Chance an orphan is fostered by kin or a noble (%)")
    sworn_kin_chance: int = rule(5, 0, 100, G, "Chance each epoch that companions swear sworn kinship (%)")
