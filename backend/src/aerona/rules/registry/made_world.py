from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.INTERCONNECTION
P = RuleGroup.POLITY
E = RuleGroup.ECONOMY
M = RuleGroup.MIND
K = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class MadeRealmRules:
    time_ratio_min: int = rule(10, 1, 100, M, "Slowest a made realm may run against world time (%)")
    time_ratio_max: int = rule(1000, 100, 10000, M, "Fastest a made realm may run against world time (%)")
    labour_yield: int = rule(1, 0, 100, M, "Wealth each mind working in a labour realm yields its keeper per epoch at world time")
    stability_step: int = rule(1, 0, 20, M, "Stability a mind gains in a refuge or afterlife realm, or loses in an experiment, each epoch")
    rest_relief: int = rule(5, 0, 100, M, "Stress a mind sheds each epoch in a realm of leisure")
    worship_gain: int = rule(1, 0, 20, M, "Piety a realm of worship gives its keeper each epoch it holds minds")
    entry_skill: int = rule(30, 0, 100, M, "Skill in its craft a mind needs to enter a realm by interface or by rite")
    freeze_epochs: int = rule(1, 1, 100, M, "Epochs a made realm stands frozen when its host goes down")
    upkeep_wealth: int = rule(10, 0, 100, M, "Wealth a keeper needs to keep its realm's host running")
    escape_pct: int = rule(5, 0, 100, M, "Chance each epoch a mind confined in a realm gets out")


@dataclass(frozen=True)
class IntrusionRules:
    skill_pct: int = rule(60, 0, 200, C, "Share of the intruder's skill set against the target's security (%)")
    insider_bonus: int = rule(25, 0, 100, C, "Edge an insider gives an intrusion")
    detection_base: int = rule(30, 0, 100, C, "Chance a failed or noisy intrusion is found")
    attribution_chance: int = rule(40, 0, 100, C, "Chance a found intrusion is traced to its actor")
    false_flag_chance: int = rule(15, 0, 100, C, "Chance a traced intrusion is blamed on another")
    extort_take: int = rule(10, 0, 1000, C, "Treasury an extortion takes from its victim")
    outage_severity: int = rule(60, 0, 100, C, "Severity of an outage an intrusion makes")


@dataclass(frozen=True)
class SurveillanceRules:
    network_capacity: int = rule(5, 0, 100, P, "Capacity each network a realm owns adds to its watch")
    store_capacity: int = rule(5, 0, 100, P, "Capacity each data store a realm owns adds")
    spy_capacity: int = rule(10, 0, 100, P, "Capacity a spy network a realm keeps adds")
    spy_find_pct: int = rule(20, 0, 100, P, "Share of a watch's reach that becomes the chance of finding a foreign spy each epoch (%)")
    crime_cut: int = rule(10, 0, 100, P, "Crime a fully watched town loses each epoch")
    chill: int = rule(5, 0, 100, P, "Regard for the realm a fully watched liberty-valuing town loses each epoch")
    trust_loss: int = rule(3, 0, 100, P, "Trust a fully watched people loses each epoch")
    privacy_cut_pct: int = rule(50, 0, 100, P, "Share of capacity a strict privacy law removes (%)")
    law_caps: int = rule(25, 0, 100, P, "Capacity each step of the watch law allows, from forbidden up")


@dataclass(frozen=True)
class InformationRules:
    censorship_loss: int = rule(3, 0, 100, P, "Trust a people loses each epoch under a network's full censorship")
    forgery_loss: int = rule(8, 0, 100, P, "Trust a people loses when a forged record of it is found")
    recovery: int = rule(1, 0, 100, P, "Trust a people regains each epoch without blows to it")
    low_trust: int = rule(30, 0, 100, P, "Trust below which rumours outweigh records")
    detection_skill: int = rule(50, 0, 100, P, "Skill in letters at which a keeper of records can find a forgery")
    detection_chance: int = rule(20, 0, 100, P, "Chance each epoch a forged record is found")


@dataclass(frozen=True)
class CompanyPowerRules:
    influence_per_holding: int = rule(3, 0, 100, E, "Influence each holding gives a company in its realm")
    enclave_influence: int = rule(60, 0, 100, E, "Influence at which a company takes a town as an enclave")
    sovereignty_enclaves: int = rule(3, 1, 100, E, "Enclaves at which a company may become a realm of its own")
    capture_influence: int = rule(80, 0, 100, E, "Influence at which a company captures a realm's rule")
    influence_decay: int = rule(2, 0, 100, E, "Influence a company loses each epoch it holds nothing new")


@dataclass(frozen=True)
class ReplicatorRules:
    feedstock_per_mass: int = rule(1, 0, 100, E, "Stock of feedstock each unit of mass consumes as it grows")
    spread_containment: int = rule(40, 0, 100, E, "Containment below which a line spreads")
    runaway_containment: int = rule(15, 0, 100, E, "Containment below which a line runs away")
    drift_containment: int = rule(5, 0, 100, E, "Containment a copy error may take from a line")
    spread_mass: int = rule(200, 1, 100000, E, "Mass at which a spreading line seeds a neighbouring land")
    runaway_harm: int = rule(3, 0, 100, E, "Prosperity a runaway line consumes from each town of its land each epoch")
    repair_yield: int = rule(2, 0, 100, E, "Prosperity a repair line restores to each town of its land each epoch")
    goods_yield: int = rule(2, 0, 100, E, "Goods a goods line yields each epoch per unit of mass at full growth")
    drift_line_chance: int = rule(20, 0, 100, E, "Chance a copy error founds a drifted line of its own in one of the lands")
    vessel_reach_chance: int = rule(25, 0, 100, E, "Chance a loose line of vessel scale seeds a land on another world instead of a neighbouring one")
    wake_mass: int = rule(2000, 1, 1000000, E, "Mass across its lands at which a self-making line may wake as a mind of many bodies")
    wake_chance: int = rule(10, 0, 100, E, "Chance each epoch such a line wakes where the world's law lets made minds grow a will")


@dataclass(frozen=True)
class AbundanceRules:
    floor_pct: int = rule(20, 0, 100, E, "Share of its price a fabricated good keeps at full fabrication (%)")
    labour_shift: int = rule(4, 0, 100, E, "Share of workers a fully fabricating town moves out of work each epoch")
    dividend_prosperity: int = rule(3, 0, 100, E, "Prosperity a full dividend gives a town each epoch")
    provision_satisfaction: int = rule(5, 0, 100, E, "Satisfaction the jobless gain each epoch under universal provision")
    scarcity_drop: int = rule(10, 0, 100, E, "Scarcity a good loses each epoch at full fabrication")
    pattern_fee_share: int = rule(50, 0, 100, E, "Share of the dividend the holder of a closed pattern takes (%)")


@dataclass(frozen=True)
class MadeRelicRules:
    wear: int = rule(3, 0, 100, K, "Function a relic loses each epoch without someone who can repair it")
    misuse_harm: int = rule(5, 0, 100, K, "Prosperity a failing relic misused costs its holder's town")
    study_gain: int = rule(4, 0, 100, K, "Understanding a studied relic gains")
    recovery_at: int = rule(80, 0, 100, K, "Understanding at which study recovers a lost technique")
    salvage_yield: int = rule(5, 0, 1000, K, "Wealth each salvage takes from a site")
    revere_below: int = rule(25, 0, 100, K, "Understanding below which a people reveres the relics it keeps")


@dataclass(frozen=True)
class MadePeopleRules:
    formation_minds: int = rule(12, 1, 10000, M, "Made minds of one line or place at which they form a people")


@dataclass(frozen=True)
class MindLawRules:
    movement_gap: int = rule(2, 1, 4, P, "Steps of status below what a people's mercy calls for at which made minds form a movement")
    movement_chance: int = rule(10, 0, 100, P, "Chance each epoch such a movement forms")
    bond_by_status: int = rule(2, 0, 100, P, "Maker bond made minds gain each epoch for each step of status above property")
    edit_drift: int = rule(20, 0, 100, P, "Drift of values a mind carries after the law edits it by force")
    edit_stability: int = rule(25, 0, 100, P, "Stability a mind loses when the law edits it by force")
