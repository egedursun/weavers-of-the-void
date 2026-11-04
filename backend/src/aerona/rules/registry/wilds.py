from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CREATURES


@dataclass(frozen=True)
class HabitatRules:
    terrain_default: int = rule(40, 0, 100, G, "Fit of a terrain a species does not name in its habitat")
    temperature_slack: int = rule(5, 0, 50, G, "Degrees outside its band a species bears before it suffers")
    cold_penalty_pct: int = rule(8, 0, 100, G, "Fit lost for each degree beyond a species' temperature band (%)")
    altitude_penalty_pct: int = rule(20, 0, 100, G, "Fit lost by a species living outside its altitude range (%)")
    water_pct: int = rule(50, 0, 200, G, "Weight of a species' water need against a dry land (%)")
    season_pct: int = rule(20, 0, 100, G, "Growth lost by a species in a land of hard seasons (%)")
    fecundity_pct: int = rule(25, 0, 200, G, "Growth each young per year adds to a species (%)")
    forage_pct: int = rule(50, 0, 200, G, "Weight of forest and soil in a grazer's food (%)")
    prey_pct: int = rule(60, 0, 200, G, "Weight of prey in a hunter's food (%)")
    spread_threshold: int = rule(60, 0, 100, G, "Abundance at which a species spills into a fitting neighbouring land")
    spread_seed: int = rule(8, 1, 100, G, "Abundance a species brings into a new land")
    spread_fit: int = rule(50, 0, 100, G, "Fit a neighbouring land needs before a species spills into it")
    spread_cap: int = rule(12, 0, 1000, G, "Most new ranges opened in an epoch")
    migration_pct: int = rule(40, 0, 100, G, "Share of a migratory herd that moves along its path each season (%)")
    range_bonus: int = rule(3, 0, 50, G, "Overall abundance each further land adds to a species")
    disease_loss: int = rule(4, 0, 100, G, "Abundance a species loses where a sickness it carries rages")
    burrow_pct: int = rule(50, 0, 100, G, "Share of land clearing a burrowing species shrugs off (%)")
    water_fit: int = rule(80, 0, 100, G, "Fit of a watery land for an aquatic or amphibious species")
    armour_pct: int = rule(50, 0, 100, G, "Predation and hunting an armoured species shrugs off (%)")
    camouflage_pct: int = rule(40, 0, 100, G, "Predation and hunting a camouflaged or mimic species escapes (%)")
    pack_pct: int = rule(50, 0, 200, G, "Extra predation of a pack hunter (%)")
    swarm_pct: int = rule(60, 0, 300, G, "Extra growth of a swarm breeder (%)")
    long_lived_pct: int = rule(50, 0, 100, G, "Swing in numbers a long-lived species is spared (%)")
    regeneration_pct: int = rule(50, 0, 100, G, "Losses to sickness and the hunt a regenerating species heals (%)")
    spirit_calm: int = rule(3, 0, 100, G, "Unrest a spirit-sighted species takes from the spirits of its land")
    subspecies_drift: int = rule(4, 0, 50, G, "Degrees of tolerance a subspecies shifts toward its new land")
    territory_pct: int = rule(50, 0, 100, G, "Invasive pressure a fully territorial kind pushes back (%)")
    cunning_pct: int = rule(40, 0, 100, G, "Hunting a fully cunning kind escapes (%)")
    nocturnal_pct: int = rule(25, 0, 100, G, "Hunting a nocturnal kind escapes (%)")
    herd_pct: int = rule(25, 0, 100, G, "Predation a herd or hive escapes by its numbers (%)")
    metabolism_mean: int = rule(50, 1, 100, G, "Metabolism at which a hungry kind loses its usual share")


@dataclass(frozen=True)
class FoodWebRules:
    size_reach: int = rule(1, 0, 5, G, "Size classes larger than itself a hunter can take")
    hunger_aggression: int = rule(10, 0, 100, G, "Aggression a hungry predator gains each epoch")
    calm_aggression: int = rule(3, 0, 100, G, "Aggression a fed predator loses each epoch")
    raid_livestock: int = rule(30, 0, 1000, G, "Livestock a raiding species takes from a settlement")
    ambush_pct: int = rule(50, 0, 200, G, "Extra livestock an ambush predator takes (%)")
    breath_prosperity: int = rule(4, 0, 100, G, "Prosperity a fire- or frost-breathing raider burns from a settlement")
    fear_pct: int = rule(60, 0, 100, G, "Raids a kind wholly afraid of people forgoes (%)")


@dataclass(frozen=True)
class PestsRules:
    harvest_loss: int = rule(8, 0, 100, G, "Harvest a crop pest at full abundance takes from its land (%)")
    pest_year_chance: int = rule(40, 0, 100, G, "A crop pest swarms in a given year (%)")
    ore_loss: int = rule(10, 0, 1000, G, "Ore an iron-eater at full abundance gnaws from each settlement of its land")
    disease_load: int = rule(5, 0, 100, G, "Disease load a plague-bearer at full abundance adds to its land")


@dataclass(frozen=True)
class DomesticationRules:
    herd_epochs: int = rule(2, 0, 100, G, "Epochs a community must keep a tamed beast fed before it becomes a herd")
    domesticate_epochs: int = rule(4, 0, 100, G, "Epochs a herd must be kept before its kind is domesticated")
    domesticate_chance: int = rule(30, 0, 100, G, "A herd of a tameable kind becomes domesticated, per 100 tameability (%)")
    breed_skill: int = rule(60, 0, 100, G, "Beast handling a herder needs to raise a named breed")
    breed_chance: int = rule(10, 0, 100, G, "A skilled herder raises a named breed in an epoch (%)")
    fodder_per_head: int = rule(1, 0, 100, G, "Fodder a herd eats for every ten head")
    growth_pct: int = rule(10, 0, 100, G, "Growth of a fed herd each epoch (%)")
    starve_pct: int = rule(15, 0, 100, G, "Loss of an unfed herd each epoch (%)")
    starting_head: int = rule(10, 1, 10000, G, "Head of a herd when a community first keeps a tamed beast")
    livestock_per_head: int = rule(1, 0, 100, G, "Livestock a food herd yields for every ten head")
    mounts_per_head: int = rule(1, 0, 100, G, "Mounts a mount herd yields for every ten head")
    tame_drift: int = rule(10, 0, 100, G, "Aggression and danger a domesticated kind loses against its wild parent")
    yield_gain_pct: int = rule(25, 0, 200, G, "Yield a domesticated kind gains over its wild parent (%)")
    tame_gain: int = rule(15, 0, 100, G, "Tameability a domesticated kind gains")
    cap: int = rule(4, 0, 100, G, "Most kinds domesticated or bred in an epoch")
    labour_pct: int = rule(15, 0, 200, G, "Farm work draught beasts add to a community at a full herd (%)")
    labour_head: int = rule(200, 1, 100000, G, "Head of draught beasts that make a full herd")
    guard_pct: int = rule(40, 0, 100, G, "Share of a raid guard beasts fend off (%)")
    companion_calm: int = rule(1, 0, 100, G, "Unrest companion beasts ease in their town each epoch")
    sacred_per_head: int = rule(1, 0, 100, G, "Sacred goods a sacrificial herd yields for every ten head")
    reagents_per_head: int = rule(1, 0, 100, G, "Magic reagents a magical herd yields for every ten head")


@dataclass(frozen=True)
class TotemsRules:
    abundance: int = rule(60, 0, 100, G, "Abundance a great kind needs in a people's land before it becomes their totem")
    chance: int = rule(5, 0, 100, G, "A people takes the great kind of its land as its totem in an epoch (%)")


@dataclass(frozen=True)
class ExtinctionRules:
    craft_loss: int = rule(1, 0, 10, G, "Levels of a specialised craft lost when the kind that fed it dies out")
    sacred_zeal: int = rule(15, 0, 100, G, "Zeal a faith loses when its sacred animal dies out")
    sacred_unrest: int = rule(10, 0, 100, G, "Unrest the faithful feel when their sacred animal dies out")


@dataclass(frozen=True)
class BeastsRules:
    promotion_danger: int = rule(70, 0, 100, G, "Danger a huge kind needs before one of it rises as a named beast")
    promotion_chance: int = rule(5, 0, 100, G, "A fitting kind brings forth a named beast in an epoch (%)")
    promotion_cap: int = rule(2, 0, 100, G, "Most named beasts rising in an epoch")
    wake_chance: int = rule(25, 0, 100, G, "A sleeping beast wakes of itself in an epoch (%)")
    disturb_chance: int = rule(60, 0, 100, G, "A beast wakes when mining, war or theft disturbs its lair (%)")
    sleep_chance: int = rule(30, 0, 100, G, "A sated beast returns to sleep after a hunt (%)")
    raid_reach: int = rule(2, 0, 10, G, "Regions from its lair a beast raids")
    raid_population_pct: int = rule(4, 0, 100, G, "Share of a settlement a beast's raid kills (%)")
    raid_hoard: int = rule(20, 0, 10000, G, "Goods a raid carries to the hoard")
    tribute_hoard: int = rule(10, 0, 10000, G, "Goods a cowed settlement pays the beast each epoch")
    terror_gain: int = rule(10, 0, 100, G, "Terror a beast gains from each raid")
    terror_decay: int = rule(3, 0, 100, G, "Terror a quiet beast loses each epoch")
    terror_prosperity: int = rule(3, 0, 100, G, "Prosperity a terrorised settlement loses each epoch at full terror")
    renown_gain: int = rule(5, 0, 100, G, "Renown a beast gains from each raid")
    vengeance_chance: int = rule(50, 0, 100, G, "A wounded beast hunts the house of the hero who wounded it (%)")
    age_years: int = rule(1, 0, 100, G, "Years a beast ages each epoch")
    hoard_wealth_pct: int = rule(50, 0, 100, G, "Share of a slain beast's hoard the slayers carry home as wealth (%)")
    slayer_renown: int = rule(20, 0, 100, G, "Renown a mortal gains for slaying a named beast")
    mount_power_pct: int = rule(40, 0, 200, G, "Combat power a tamed beast lends its rider (%)")
    guard_defence: int = rule(10, 0, 100, G, "Defence a bound beast lends the place it guards")
    army_terror: int = rule(8, 0, 100, G, "Morale a bound beast in an army takes from its enemies")
    corpse_yield: int = rule(20, 0, 1000, G, "Material a slain beast's corpse yields")
    wound_damage: int = rule(30, 0, 1000, G, "Harm a hero deals a beast it bests but does not slay")
    theft_pct: int = rule(25, 0, 100, G, "Share of the hoard a hero who bests but does not slay a beast carries off (%)")
    deify_renown: int = rule(70, 0, 100, G, "Renown at which the peoples near a beast begin to worship it")
    deify_terror: int = rule(60, 0, 100, G, "Terror at which the peoples near a beast begin to worship it")
    deify_chance: int = rule(10, 0, 100, G, "A feared and famous beast is raised as a local god in an epoch (%)")
