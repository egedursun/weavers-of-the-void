from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class WorldEpochTransitionRules:
    capacity_architecture_pct: int = rule(
        120, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Carrying-capacity multiplier of a settlement knowing architecture (%)"
    )
    capacity_fertility_base_pct: int = rule(30, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Share of carrying capacity independent of fertility (%)")
    capacity_fertility_divisor: int = rule(60, 1, 1000, RuleGroup.POPULATION_AND_GROWTH, "Fertility contribution to carrying capacity: fertility / this number")
    capacity_breadth_base_pct: int = rule(50, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Share of carrying capacity independent of breadth (%)")
    place_fertility_share_pct: int = rule(
        40,
        0,
        100,
        RuleGroup.POPULATION_AND_GROWTH,
        "Share of the place in the fertility of one living in a place outside the region (%; the rest is the region's)",
    )
    bounty_power_growth_mult: int = rule(2, 1, 20, RuleGroup.POPULATION_AND_GROWTH, "Growth multiplier of a patron with the Bounty power (times)")
    bounty_power_min_fertility: int = rule(35, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Minimum fertility at which the Bounty power multiplies growth")
    cult_default_charisma: int = rule(30, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Default charisma in the growth of a cult without a patron")
    cult_capacity_min: int = rule(150, 0, 10000000, RuleGroup.POPULATION_AND_GROWTH, "Lowest cap of cult followers in a region (people)")
    cult_shrink_max_pct: int = rule(20, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Maximum shrinkage of a cult in one epoch (%)")
    cult_growth_max_pct: int = rule(50, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Maximum growth of a cult in one epoch (%)")
    growth_prosperity_threshold: int = rule(40, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "A city above this prosperity grows faster (below it, slower)")
    immortality_law_growth_pct: int = rule(50, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Population growth rate under the immortality law (%)")
    short_life_law_growth_pct: int = rule(150, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "Population growth rate under the short-life law (%)")
    star_pick_base_weight: int = rule(5, 0, 1000, RuleGroup.SKY, "Base weight of each celestial body when picking the star of the epoch")
    wake_hp_divisor: int = rule(2, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "HP of a son waking from sleep: max HP / this number")
    heal_base: int = rule(5, 0, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Son's per-epoch HP healing: base")
    heal_endurance_divisor: int = rule(10, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Endurance contribution to a son's healing: endurance / this number")
    existence_step: int = rule(10, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Maximum approach of a son's existence toward its target in one epoch")
    faith_essence_divisor: int = rule(10, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Essence income from faith: faith / this number (son and Creator)")
    essence_spring_bonus: int = rule(4, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Extra essence income of a son with the Essence Spring power")
    radiant_essence_bonus: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Extra essence income of a son whose existence is Radiant")
    star_domain_essence_bonus: int = rule(3, 0, 100, RuleGroup.SKY, "Extra essence income of a son bearing the domain of the epoch's star")
    artwork_renown: int = rule(1, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch renown contribution of an artwork depicting a god")
    artwork_existence: int = rule(1, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch existence contribution of an artwork depicting a god")
    dedicated_work_renown: int = rule(1, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch fame a son gains from each standing structure dedicated to it")
    dedicated_work_existence: int = rule(
        1, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch existence a son gains from each standing structure dedicated to it"
    )
    star_influence_pivot: int = rule(50, 1, 100, RuleGroup.SKY, "Celestial influence at which the epoch star gives its full essence bonus")
    domain_rivalry: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch relation loss of sons sharing the same domain (per shared domain)")
    domain_rivalry_floor: int = rule(
        70,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Domain rivalry lowers the relation at most to minus this value (deeper hostility comes from conflict and slowly reverts)",
    )
    rebel_steal_base: int = rule(6, 0, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Essence a rebel son steals from the Creator: base")
    rebel_steal_per_level: int = rule(2, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Extra essence a rebel son steals per level")
    temples_per_apocalypse_push: int = rule(2, 1, 100, RuleGroup.APOCALYPSE, "Number of temples that push the apocalypse back by 1")
    apocalypse_disaster_severity: int = rule(90, 0, 100, RuleGroup.APOCALYPSE, "Severity of the apocalypse's disasters destroying regions (%)")
    apocalypse_event_severity: int = rule(100, 0, 100, RuleGroup.APOCALYPSE, "Severity of the apocalypse event record")
    apocalypse_chronicle_regions: int = rule(12, 0, 1000, RuleGroup.CHRONICLE, "Maximum regions linked to the apocalypse chronicle entry")
    folded_chronicle_ids_cap: int = rule(40, 0, 1000, RuleGroup.CHRONICLE, "Maximum entities linked to a folded chronicle line")
    essence_overflow_note: int = rule(20, 0, 100000, RuleGroup.CHRONICLE, "When overflowing essence exceeds this, a note is added to the chronicle")
