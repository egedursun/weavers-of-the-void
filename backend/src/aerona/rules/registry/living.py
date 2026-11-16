from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.CREATURES
P = RuleGroup.POPULATION_AND_GROWTH


@dataclass(frozen=True)
class LivingRules:
    seasons_per_epoch: int = rule(4, 1, 40, C, "Seasons a living thing ages each epoch")
    young_at: int = rule(2, 0, 400, C, "Seasons at which a seed becomes young")
    grown_at: int = rule(8, 0, 400, C, "Seasons at which a young thing is grown and can work at full")
    prime_at: int = rule(20, 0, 4000, C, "Seasons at which a grown thing reaches its prime")
    old_at_pct: int = rule(75, 0, 100, C, "Share of its lifespan at which a living thing grows old (%)")
    dying_at_pct: int = rule(95, 0, 100, C, "Share of its lifespan at which a living thing begins to die (%)")
    growth_size: int = rule(10, 0, 100, C, "Size a living thing gains each epoch while it grows")
    hunger_harm: int = rule(15, 0, 100, C, "Health a living thing loses each epoch it goes unfed")
    regeneration_pct: int = rule(50, 0, 200, C, "Share of its regeneration a living thing heals each epoch (%)")
    neglect_bond: int = rule(5, 0, 100, C, "Bond a living thing loses each epoch it goes unfed")
    care_bond: int = rule(2, 0, 100, C, "Bond a fed living thing gains with its handler each epoch")
    refuse_bond: int = rule(20, 0, 100, C, "Bond below which a living thing with a nervous system refuses its handler")
    breed_chance: int = rule(10, 0, 100, C, "Chance each epoch a fertile living thing in its prime breeds")
    wild_drift: int = rule(10, 0, 100, C, "Drift a line that breeds wild gains each generation")
    decay_fertility: int = rule(2, 0, 100, C, "Fertility a dead grown thing gives back to its land")
    mutation_pct: int = rule(3, 0, 100, C, "Chance a breeding brings a new trait into its line")
    mutation_strength: int = rule(15, 0, 100, C, "Strength of a trait that arises by mutation")
    monoculture_share: int = rule(60, 0, 100, C, "Share of a region's orchards and groves held by one line at which a blight can strike it all")
    blight_chance: int = rule(5, 0, 100, C, "Chance each epoch a blight strikes a line grown as a monoculture")
    blight_harm: int = rule(40, 0, 100, C, "Condition a blight takes from every planting of the line in the region")
    gift_at: int = rule(40, 0, 100, C, "Strength of a designed gift at which things of a line are born with a power")
    escape_spread_pct: int = rule(100, 0, 1000, C, "Extra chance of escape a flying or swimming line has (%)")
    unfed_army_harm: int = rule(10, 0, 100, C, "Condition a living army loses each epoch it goes unfed")
    link_heal: int = rule(1, 0, 20, C, "Epochs a cut in a grown link heals by each epoch")


@dataclass(frozen=True)
class LivingMethodRules:
    skill_floor: int = rule(30, 0, 100, C, "Skill a maker needs in the craft a method calls for")
    base_precision: int = rule(40, 0, 100, C, "Precision of a making before skill and works are counted")
    works_bonus: int = rule(20, 0, 100, C, "Precision a laboratory, cloning facility or garden adds")
    failure_below: int = rule(35, 0, 100, C, "Precision below which a making can fail")
    unstable_weight: int = rule(40, 0, 100, C, "Weight of a failed making leaving an unstable line")
    sterile_weight: int = rule(20, 0, 100, C, "Weight of a failed making leaving a sterile line")
    side_weight: int = rule(30, 0, 100, C, "Weight of a failed making leaving side effects")
    dead_weight: int = rule(10, 0, 100, C, "Weight of a failed making leaving nothing alive")
    escape_chance: int = rule(3, 0, 100, C, "Chance each epoch a line held by its makers escapes into the wild")
    drift_per_generation: int = rule(5, 0, 100, C, "Drift a line gains each generation")
    unstable_drift: int = rule(10, 0, 100, C, "Further drift an unstable line gains each generation")
    new_line_drift: int = rule(60, 0, 100, C, "Drift at which a line becomes a line of its own")


@dataclass(frozen=True)
class GenomeDesignRules:
    traits_per_level: int = rule(1, 0, 20, C, "Designed traits a method allows for each step of its makers' craft")
    trait_cap: int = rule(6, 1, 50, C, "Most traits any one line can carry by design")
    instability_per_trait: int = rule(8, 0, 100, C, "Stability a line loses for each designed trait")
    side_effect_chance: int = rule(20, 0, 100, C, "Chance each designed trait brings a side effect from its source")
    bank_upkeep: int = rule(2, 0, 100, C, "Wealth points a gene bank costs its holder each epoch")
    bank_unpaid_limit: int = rule(3, 1, 100, C, "Epochs a bank goes unpaid before it loses a sample")
    raise_fidelity_pct: int = rule(80, 0, 100, C, "Share of a sample's quality a line raised from it keeps as stability (%)")
    sapience_at: int = rule(60, 0, 100, C, "Strength of a designed nervous system at which a line's species rises to a people")


@dataclass(frozen=True)
class SymbiontRules:
    mutual_gain: int = rule(3, 0, 100, C, "Health a mutual symbiont gives its host each epoch")
    parasite_harm: int = rule(4, 0, 100, C, "Health a parasite takes from its host each epoch")
    co_mind_stress: int = rule(5, 0, 100, C, "Stress two minds in one body share each epoch they disagree")
    control_pull: int = rule(10, 0, 100, C, "Opinion a controlling symbiont moves its host each epoch toward its own kind")
    spread_chance: int = rule(5, 0, 100, C, "Chance each epoch a parasite spreads to another in its host's town")
    removal_harm: int = rule(10, 0, 100, C, "Harm removing a symbiont does to its host by placement")
    partner_loss: int = rule(10, 0, 100, C, "Prosperity and craft a people bonded to a symbiont line loses when the partnership ends")


@dataclass(frozen=True)
class DesignedDiseaseRules:
    escape_chance: int = rule(2, 0, 100, C, "Chance each epoch a designed disease kept by its makers gets loose among them")
    escape_severity: int = rule(20, 1, 100, C, "Severity of the outbreak a loosed designed disease starts")
    target_bonus_pct: int = rule(100, 0, 1000, C, "Extra deaths a designed disease causes among those it was made to strike (%)")
    others_pct: int = rule(30, 0, 100, C, "Share of its deaths a designed disease causes among those it was not made for (%)")
    cure_potency_floor: int = rule(20, 0, 100, C, "Strength of a designed potency a line needs to yield a cure")


@dataclass(frozen=True)
class LivingProductionRules:
    yield_pct: int = rule(100, 0, 1000, C, "Share of a designed yield trait that adds to what living works and orchards give (%)")
    works_feed: int = rule(1, 0, 100, C, "Feed a living works eats each season")
    sick_works_pct: int = rule(50, 0, 100, C, "Health below which living works give less")
    seed_due: int = rule(2, 0, 100, C, "Coin a grower pays the owner of a sterile or maker-bound line for each planting each epoch")
    seed_regard: int = rule(2, 0, 100, C, "Regard a grower comes to owe the owner of the line it depends on each epoch")


@dataclass(frozen=True)
class CloneRules:
    health_pct: int = rule(85, 0, 100, C, "Share of the source's lifespan a clone lives (%)")
    generation_loss: int = rule(5, 0, 100, C, "Further lifespan a clone of a clone loses (%)")
    born_skill_pct: int = rule(20, 0, 100, C, "Share of each of its source's skills a clone is born with as aptitude (%)")
    people_at: int = rule(12, 2, 1000, P, "Clones of one line at which they form a people")
    movement_gap: int = rule(2, 1, 4, P, "Steps of standing below what their people's mercy calls for at which clones and designed peoples rise")
    movement_chance: int = rule(10, 0, 100, P, "Chance each epoch such a rising forms")
    bond_by_status: int = rule(5, 0, 100, P, "Regard clones and designed peoples lose for their realm when held too low")
    stance_regard: int = rule(5, 0, 100, P, "Regard a faith gives or takes from clones and makers by its stance on living craft")


@dataclass(frozen=True)
class FortuneRules:
    source_epochs: int = rule(4, 1, 100, C, "Epochs a fortune source lasts unless it says otherwise")
    streak_step: int = rule(5, 0, 15, C, "Largest step the personal streak takes each season")
    streak_cap: int = rule(15, 0, 50, C, "Largest the personal streak may grow either way")
    streak_halflife: int = rule(4, 1, 40, C, "Seasons over which the streak halves back toward nothing")
    draw_cap_pct: int = rule(20, 0, 50, C, "Most that fortune moves any single draw, as a share of its base (%)")
    curse_strength: int = rule(20, 0, 100, C, "Fortune a curse of misfortune takes from its bearer")
    blessing_strength: int = rule(15, 0, 100, C, "Fortune a god's blessing gives")
    oath_strength: int = rule(10, 0, 100, C, "Fortune keeping or breaking an oath gives or takes where a law binds oaths")
    charm_pct: int = rule(30, 0, 100, C, "Share of a real charm of luck's strength it adds to its bearer's fortune (%)")
    care_cost: int = rule(1, 0, 100, C, "Wealth a mortal spends to take care for a season")
    care_strength: int = rule(10, 0, 100, C, "Fortune care gives against mishaps for the epoch it is taken")
