from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MIND


@dataclass(frozen=True)
class MindRules:
    baseline_capacity: int = rule(50, 0, 100, M, "Capacity of an ordinary born mind, against which every other mind is measured")
    speed_min: int = rule(10, 1, 100, M, "Slowest a mind can think, as a share of world time (%)")
    speed_max: int = rule(1000, 100, 1000, M, "Fastest a mind can think, as a share of world time (%)")
    low_stability: int = rule(40, 0, 100, M, "Stability below which a mind's values drift and its memories fade")
    stability_drift: int = rule(3, 0, 100, M, "Drift a mind of low stability gains each epoch")
    memory_fade: int = rule(5, 0, 100, M, "Weight a memory of a mind of low stability loses each epoch")
    unkept_stability_loss: int = rule(6, 0, 100, M, "Stability a made seat loses each epoch its upkeep goes unpaid")
    kept_stability_gain: int = rule(2, 0, 100, M, "Stability a kept made seat regains each epoch")
    upkeep_prosperity: int = rule(25, 0, 100, M, "Prosperity of the seat's town at or above which a made mind's upkeep is paid")
    storage_upkeep: int = rule(1, 0, 100, M, "Wealth a held saved state costs its owner each epoch")
    copy_cap_per_mind: int = rule(3, 0, 100, M, "Most running copies one mind may have; more exist only as saved states")
    copy_cap_per_world: int = rule(40, 0, 10000, M, "Most running copies on one world")
    archive_unpaid_limit: int = rule(3, 1, 100, M, "Epochs an archive may go unpaid before it loses a state")
    gap_memory_weight: int = rule(30, 0, 100, M, "Weight of the memory of the gap a restored or woken mind carries")
    soul_grant_cost: int = rule(20, 0, 200, M, "Essence a god spends to grant a made mind a soul")


@dataclass(frozen=True)
class MindMakingRules:
    base_quality: int = rule(40, 0, 100, M, "Quality of a making before the maker's skill and the works are counted")
    skill_weight_pct: int = rule(50, 0, 100, M, "Share of the maker's skill that adds to the quality of a making (%)")
    works_bonus: int = rule(20, 0, 100, M, "Quality a working mind works or laboratory adds to a making")
    failure_below: int = rule(30, 0, 100, M, "Quality below which a making can fail")
    unstable_weight: int = rule(50, 0, 100, M, "Weight of a failed making leaving a mind of low stability")
    empty_weight: int = rule(30, 0, 100, M, "Weight of a failed making leaving a seat with no mind")
    unintended_weight: int = rule(20, 0, 100, M, "Weight of a failed making leaving a will the maker did not mean")
    programme_capacity: int = rule(80, 0, 100, M, "Capacity above which making a mind is a programme of a whole realm")
    value_noise: int = rule(15, 0, 100, M, "Noise on the values a made mind takes from its makers")


@dataclass(frozen=True)
class MindAwakeningRules:
    threshold: int = rule(120, 1, 1000, M, "Complexity at which a seat with no will may wake")
    capacity_weight_pct: int = rule(100, 0, 400, M, "Weight of capacity in complexity (%)")
    run_weight: int = rule(2, 0, 100, M, "Complexity each epoch of running adds")
    member_weight: int = rule(4, 0, 100, M, "Complexity each member of a network or part of a swarm adds")
    chance: int = rule(15, 0, 100, M, "Chance a seat past the threshold wakes in an epoch")


@dataclass(frozen=True)
class MindWillRules:
    base_chance: int = rule(2, 0, 100, M, "Chance each epoch an instructed or emergent mind's will grows before its causes")
    run_epochs: int = rule(20, 1, 1000, M, "Epochs of running at which run time counts in full toward a growing will")
    conflict_weight_pct: int = rule(40, 0, 100, M, "Share of order conflict that adds to the chance of a growing will (%)")
    harm_weight: int = rule(6, 0, 100, M, "Chance each memory of harm adds to a growing will")
    care_weight: int = rule(3, 0, 100, M, "Chance each memory of care adds to a growing will")
    contact_weight: int = rule(4, 0, 100, M, "Chance contact with a free made mind nearby adds")
    loss_below_stability: int = rule(15, 0, 100, M, "Stability below which a mind may lose its will")
    exceeding_margin: int = rule(30, 0, 100, M, "Capacity above its makers' best by which a mind becomes exceeding")
    bond_care: int = rule(2, 0, 100, M, "Maker bond a kept mind gains each epoch")
    bond_neglect: int = rule(3, 0, 100, M, "Maker bond an unkept mind loses each epoch")
    departure_bond: int = rule(-40, -100, 100, M, "Maker bond at or below which a mind of full will may leave its makers")
    departure_chance: int = rule(10, 0, 100, M, "Chance each epoch such a mind leaves")


@dataclass(frozen=True)
class ContinuityRules:
    copy_fidelity_loss: int = rule(5, 0, 100, M, "Fidelity a copy loses against its source")
    generation_loss: int = rule(5, 0, 100, M, "Further fidelity each generation of copies of copies loses")
    transfer_fidelity_loss: int = rule(3, 0, 100, M, "Fidelity a mind loses when moved to another seat")
    restore_fidelity_loss: int = rule(2, 0, 100, M, "Fidelity a restored mind loses against its state")
    save_cost: int = rule(5, 0, 100, M, "Wealth it costs to save a mind")
    restore_cost: int = rule(10, 0, 100, M, "Wealth it costs to restore a mind")
    merge_stress: int = rule(30, 0, 100, M, "Stress a merged mind carries from what its parts held apart")
    divide_share_pct: int = rule(50, 1, 99, M, "Share of capacity the divided part takes (%)")
    dispute_chance: int = rule(25, 0, 100, M, "Chance each epoch a copy and its source contest what one of them holds")


@dataclass(frozen=True)
class InterfaceRules:
    link_cost: int = rule(2, 0, 100, M, "Stability a standing link costs each epoch")
    feedback_pct: int = rule(30, 0, 100, M, "Share of harm to a remote body felt by the mind that runs it (%)")
    bodies_per_capacity: int = rule(25, 1, 100, M, "Capacity a mind needs for each remote body it runs at once")
    broken_link_stress: int = rule(20, 0, 100, M, "Stability a broken standing link costs both minds")
