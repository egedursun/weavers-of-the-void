from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

B = RuleGroup.BODY


@dataclass(frozen=True)
class AugmentRules:
    base_integration: int = rule(50, 0, 100, B, "Integration an augment starts with before the surgeon and the make")
    skill_pct: int = rule(40, 0, 100, B, "Share of the surgeon's skill that adds to integration (%)")
    integration_floor: int = rule(60, 0, 100, B, "Integration below which an augment strains its bearer")
    poor_integration_pct: int = rule(100, 0, 400, B, "Strain each point of integration below the floor adds (%)")
    many_augments: int = rule(3, 0, 100, B, "Augments a body bears before each further one strains it")
    per_extra: int = rule(10, 0, 100, B, "Strain each augment past that many adds")
    doctrine_strain: int = rule(20, 0, 100, B, "Strain a faith that holds augments an abomination adds to its faithful")
    stress_at: int = rule(40, 0, 100, B, "Strain at which an augment stresses its bearer")
    stress_pct: int = rule(20, 0, 100, B, "Share of strain turned into stress each epoch (%)")
    upkeep_wealth: int = rule(15, 0, 100, B, "Wealth a bearer needs to keep a made or rite-bound augment working")
    enhance_wealth: int = rule(60, 0, 100, B, "Wealth from which a being seeks an augment that heightens its best skill")
    enhance_cost: int = rule(20, 0, 100, B, "Wealth an augment that heightens a skill costs")
    enhance_lift: int = rule(10, 0, 100, B, "Skill an augment of heightening adds to the skill it serves")
    unpaid_loss: int = rule(8, 0, 100, B, "Integration an augment loses each epoch its upkeep goes unpaid")
    rejection_at: int = rule(20, 0, 100, B, "Integration at or below which a body may reject an augment")
    rejection_chance: int = rule(25, 0, 100, B, "Chance each epoch a body rejects such an augment")
    removal_harm: int = rule(10, 0, 100, B, "Health a body loses when an augment that replaces a part is taken out")

    life_support_pct: int = rule(
        60, 0, 200, B, "Share of an augment's quality and integration by which one that keeps a body alive covers what its air, pressure or gravity lacks (%)"
    )
    plating_pct: int = rule(50, 0, 200, B, "Share of an augment's quality and integration that armours the torso and limbs before the tissues take a blow (%)")
    power_bound_loss: int = rule(10, 0, 100, B, "Integration a power-bound augment loses each epoch its bearer holds no awake power")
