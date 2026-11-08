from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CREATURES


@dataclass(frozen=True)
class HusbandryRules:
    graze_head_per_pct: int = rule(50, 1, 100000, G, "Head of grazing herds that press one more share of a land into pasture (%)")
    litter_norm: int = rule(3, 1, 100, G, "Young a year, from litters and breeding seasons, at which a herd grows at its usual rate")
    litter_growth_cap_pct: int = rule(200, 100, 1000, G, "Most a herd's growth can rise above its usual rate from fertile breeding (%)")
    muscle_per_10_draught: int = rule(4, 0, 100, G, "Muscle energy ten head of draught beasts give a community")
    train_pct: int = rule(10, 0, 100, G, "Share of a herd's untrained head a master handler trains each epoch at full skill (%)")
    train_skill: int = rule(20, 0, 100, G, "Beast-handling skill a community needs before it trains its herds")
    trained_full_head: int = rule(30, 1, 100000, G, "Trained head at which training gives its full effect")
    war_share_pct: int = rule(15, 0, 100, G, "Share of a community's army its trained war beasts make up at full effect (%)")
    hunt_pct: int = rule(30, 0, 300, G, "Hunting yield a community gains from trained hunting beasts at full effect (%)")
    guard_pct: int = rule(20, 0, 100, G, "Further share of raiding losses trained guard beasts prevent at full effect (%)")
    pet_chance: int = rule(3, 0, 100, G, "Chance each epoch a mortal of a community keeping small tame kinds takes one as a pet (%)")
    pet_cap: int = rule(4, 0, 1000, G, "Most pets taken across the cosmos in an epoch")
    pet_grief_strength: int = rule(40, 0, 100, G, "How hard an owner grieves a pet that died")
    pet_hero_bonus: int = rule(8, 0, 100, G, "Strength a hound, falcon or other hunting pet adds to its owner in a hunt for a beast")
    pet_hunt_xp: int = rule(6, 0, 100, G, "Hunting practice an owner gains each epoch from a pet that hunts at their side")
