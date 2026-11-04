from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MATERIALS


@dataclass(frozen=True)
class ExtractionRules:
    farmer_labour_pct: int = rule(40, 0, 100, G, "Share of a community's farmers who work its fields, pastures, fisheries and forests (%)")
    artisan_labour_pct: int = rule(35, 0, 100, G, "Share of a community's artisans who work its mines and quarries (%)")
    output_per_1000_workers: int = rule(120, 0, 100000, G, "Units a thousand workers win from a resource of full richness in an epoch")
    skill_pct_per_level: int = rule(6, 0, 100, G, "Extra output per level of the best worker's skill (%)")
    tools_pct: int = rule(40, 0, 200, G, "Extra output when every worker has good tools (%)")
    tools_per_1000_workers: int = rule(20, 1, 10000, G, "Tools a thousand workers need to count as fully equipped")
    knowledge_pct_per_level: int = rule(8, 0, 100, G, "Extra output per level of the resource's required knowledge (%)")
    season_pct: int = rule(25, 0, 100, G, "Extra output in the season that suits the work: logging in the cold season, fishing in the warm one (%)")
    difficulty_pct: int = rule(60, 0, 100, G, "Output lost at the highest extraction difficulty (%)")
    reserve_per_abundance: int = rule(20, 1, 10000, G, "Units of reserve per point of abundance when a resource is first profiled")
    renewable_regen_pct: int = rule(12, 0, 100, G, "Share of a renewable resource's initial reserve that regrows each epoch (%)")
    owner_wealth_per_value: int = rule(4, 0, 100, G, "Prosperity or wealth an owner gains per hundred units of value extracted")
    byproduct_scar: int = rule(2, 0, 100, G, "Land scarred (mined and eroded) per epoch by slag from a worked seam")
    deposit_reveal_chance: int = rule(6, 0, 100, G, "A community with mining knowledge finds a hidden deposit in its region (% per epoch)")
    deposit_reveal_level: int = rule(2, 0, 10, G, "Metallurgy level needed to find hidden deposits")
    deposit_reserve: int = rule(1500, 1, 100000, G, "Reserve of a newly found deposit")
    hidden_share_pct: int = rule(25, 0, 100, G, "Share of rich mineral seams that start hidden when a world is profiled (%)")
    workshop_pct_per_level: int = rule(15, 0, 100, G, "Extra output per level of the mine, lumber camp or fishery that works a resource (%)")
    species_ground_abundance: int = rule(30, 0, 100, G, "Abundance a wild species needs before its herds, fish or silk are worked as a ground of their own")
    knowledge_short_pct: int = rule(0, 0, 100, G, "Output kept per level a community falls short of the knowledge a resource needs (%); zero closes the work")


@dataclass(frozen=True)
class RefiningRules:
    batches_per_level: int = rule(200, 0, 100000, G, "Batches a workshop can run per level each epoch")
    workers_per_batch: int = rule(5, 1, 10000, G, "Artisans a batch needs for an epoch")
    skill_quality_per_level: int = rule(4, 0, 100, G, "Quality gained per level of the smith's or maker's skill")
    material_quality_pct: int = rule(50, 0, 100, G, "Share of the input's quality carried into the output (%)")
    build_chance: int = rule(20, 0, 100, G, "A community short of a workshop it needs builds one (% per epoch)")
    build_timber: int = rule(8, 0, 10000, G, "Timber a new workshop costs")
    build_stone: int = rule(6, 0, 10000, G, "Stone a new workshop costs")
    upgrade_idle_limit: int = rule(3, 0, 100, G, "Epochs a workshop may stand idle before it falls down a level")
    max_level: int = rule(5, 1, 20, G, "Highest workshop level")
    ship_chance: int = rule(30, 0, 100, G, "A shipyard with timber and cloth launches a ship (% per epoch)")
    fleet_cap: int = rule(12, 0, 1000, G, "Most ships a community keeps afloat")
    weapon_batch_threshold: int = rule(20, 0, 100000, G, "Weapons in store at which the smiths of a warlike people forge a named batch")
    shortage_note_cap: int = rule(4, 0, 100, G, "Most bottleneck notes written per epoch")
    target_index: int = rule(200, 0, 10000, G, "Supply index of a good its makers work towards before they stop")
    household_batches_pct: int = rule(30, 0, 100, G, "Share of the artisans' batches a community can run at home without a workshop (%)")
    upgrade_chance: int = rule(15, 0, 100, G, "A workshop that ran at full stretch is enlarged (% per epoch)")


@dataclass(frozen=True)
class MiningHazardsRules:
    cave_in_pct: int = rule(4, 0, 100, G, "Chance per sampled year of a cave-in at a mine of full difficulty (%)")
    felling_pct: int = rule(3, 0, 100, G, "Chance per sampled year of a felling accident at the hardest forest (%)")
    drowning_pct: int = rule(2, 0, 100, G, "Chance per sampled year that fishers drown in rough water (%)")
    goring_pct: int = rule(1, 0, 100, G, "Chance per sampled year that herders are gored or trampled (%)")
    engineering_pct_per_level: int = rule(12, 0, 100, G, "Hazard averted per level of the overseers' engineering skill (%)")
    workers_lost_pct: int = rule(3, 0, 100, G, "Share of the workers killed by a hazard (%)")
    maimed_pct: int = rule(40, 0, 100, G, "Share of the survivors of a hazard who are maimed for life (%)")
    named_hurt: int = rule(2, 0, 20, G, "Named mortals of the community hurt in a hazard")
    seal_epochs: int = rule(2, 0, 100, G, "Epochs a mine stays sealed after a cave-in")
    cavern_chance: int = rule(15, 0, 100, G, "A cave-in breaks into a cavern and lets something out (%)")
    flood_rainfall: int = rule(75, 0, 100, G, "Rainfall from which a mine's hazard is a flooded shaft rather than a cave-in")
