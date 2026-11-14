from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

P = RuleGroup.POPULATION_AND_GROWTH
M = RuleGroup.MIND
R = RuleGroup.RELIGION_AND_LANGUAGE
J = RuleGroup.POLITY


@dataclass(frozen=True)
class NutritionRules:
    need_weight: int = rule(50, 0, 100, P, "Weight a people's biology gives each nutrient it needs when its needs are first read")
    protein_share: int = rule(15, 1, 100, P, "Share of a diet that protein must make up to meet the need in full (%)")
    fat_share: int = rule(10, 1, 100, P, "Share of a diet that fats must make up to meet the need in full (%)")
    fresh_share: int = rule(10, 1, 100, P, "Share of a diet that fresh food must make up to meet the need in full (%)")
    mineral_share: int = rule(5, 1, 100, P, "Share of a diet that minerals must make up to meet the need in full (%)")
    essence_share: int = rule(20, 1, 100, P, "Essence a people that feeds on essence must draw to meet the need in full")
    essence_per_magic: int = rule(20, 0, 100, P, "Essence a community draws from each level of its magic, for peoples who feed on essence")
    preserved_fresh_pct: int = rule(30, 0, 100, P, "Share of preserved food that stands in for fresh food (%)")
    night_light: int = rule(20, 0, 100, P, "Light a world under eternal night gives peoples who live from light")
    energy_weight_pct: int = rule(50, 0, 100, P, "Weight of energy, against the balance of nutrients, in a nutrition score (%)")
    deficient_below: int = rule(50, 0, 100, P, "Adequacy of a nutrient below which a diet is deficient in it")
    elite_bonus: int = rule(15, 0, 100, P, "Nutrition the elite classes gain over their town's score")
    lowly_penalty: int = rule(15, 0, 100, P, "Nutrition the lowest classes lose against their town's score")
    well_fed: int = rule(70, 0, 100, P, "Nutrition score from which a body is fully fed; below it disease resistance and healing fall")
    immunity_pct: int = rule(40, 0, 100, P, "Disease resistance and recuperation lost for each point of nutrition below being well fed (%)")
    childhood_mean: int = rule(60, 0, 100, P, "Childhood nutrition at which an adult grows to the stature of its kind")
    stature_pct: int = rule(25, 0, 100, P, "Strength and toughness an adult gains or loses for each point of childhood nutrition above or below the mean (%)")
    deficiency_health: int = rule(3, 0, 100, P, "Health a mortal loses each epoch to a deficient diet")
    malnutrition_chance: int = rule(25, 0, 100, P, "Chance each epoch that a deficient diet wastes a body into malnutrition (%)")
    cognition_pct: int = rule(15, 0, 100, P, "Reckoning and memory an adult gains or loses for each point of childhood nutrition above or below the mean (%)")
    voyage_epochs: int = rule(3, 1, 100, P, "Epochs of a journey from which food without fresh or preserved stores leaves its travellers deficient")
    voyage_deficiency: int = rule(15, 0, 100, P, "Condition travellers lose to a long journey without fresh or preserved food")
    stores_pct: int = rule(50, 0, 100, P, "Share of a people's food stores against hunger that counts as preserved food in its towns' diets (%)")
    fertility_pct: int = rule(
        50, 0, 100, P, "Share of the chance of a birth lost for each point of the bearer's nutrition below being well fed, in hundredths (%)"
    )


@dataclass(frozen=True)
class BiasRules:
    push_pct: int = rule(30, 0, 100, M, "Most a single bias at its strongest shifts the chance of a decision (%)")
    drift_pct: int = rule(25, 0, 100, M, "Share of the gap to the weight its character implies that a bias closes each epoch (%)")
    stress_pct: int = rule(20, 0, 100, M, "Bias weight added by each point of stress, in hundredths (%)")
    council_pct: int = rule(50, 0, 100, M, "Weight of the rest of a ruling council against its first ruler when their biases are combined (%)")
    skill_damp_pct: int = rule(8, 0, 100, M, "Share of every bias that each level of strategy or tactics takes off (%)")


@dataclass(frozen=True)
class PurityRules:
    culture_from: int = rule(30, -100, 100, R, "Purity a culture must value before it keeps rules of pure and impure")
    castes_from: int = rule(40, -100, 100, R, "Hierarchy a culture that keeps purity must value before it ranks its folk in hereditary castes")
    sources_per_culture: int = rule(4, 1, 13, R, "Sources of impurity a culture that keeps purity holds when first read")
    methods_per_culture: int = rule(2, 1, 8, R, "Ways of purification a culture that keeps purity holds when first read")
    weight_low: int = rule(20, 0, 100, R, "Least chance that a touch of an impurity a culture holds makes a mortal impure (%)")
    weight_high: int = rule(80, 0, 100, R, "Greatest chance that a touch of an impurity a culture holds makes a mortal impure (%)")
    longest_lasts: int = rule(3, 1, 50, R, "Most epochs an impurity lasts or a purification takes when a culture is first read")
    highest_cost: int = rule(40, 0, 10000, R, "Most coin a purification costs when a culture is first read")
    success_low: int = rule(50, 0, 100, R, "Least chance a purification succeeds when a culture is first read (%)")
    defiled_from: int = rule(70, 0, 100, R, "Weight of an impurity from which a mortal is defiled and only a rite, not waiting, cleanses them")
    ranks: int = rule(4, 2, 12, R, "Hereditary ranks a caste culture holds when first read")
    impure_professions: int = rule(3, 0, 25, R, "Professions a culture without castes counts as impure")
    food_chance: int = rule(10, 0, 100, R, "Chance each epoch that a mortal eats a food its culture counts as impure (%)")
    rise_wealth: int = rule(70, 0, 100, R, "Wealth from which a mortal may rise a caste rank")
    reform_pct: int = rule(
        10,
        0,
        100,
        R,
        "Share of the gap to what its culture now values that each source of impurity closes each epoch; sources a culture no longer keeps fade away (%)",
    )
    rise_chance: int = rule(5, 0, 100, R, "Chance each epoch that a mortal with that wealth rises a caste rank (%)")
    avoidance_pct: int = rule(
        30, 0, 100, R, "Share by which a people that holds the dead and bodily fluids unclean, at full weight, slows an epidemic it shuns (%)"
    )
    carer_loss_pct: int = rule(
        20, 0, 100, R, "Share by which such a people's shunning of the sick, at full weight, raises an epidemic's deaths for want of carers (%)"
    )
    outsider_trade_pct: int = rule(
        60, 0, 100, R, "Share of trade with another people that a people holding outsiders unclean, at full weight, refuses away from a trading post (%)"
    )
    corpse_exposure_pct: int = rule(50, 0, 100, R, "Share by which a plague's chance of killing rises for one made unclean by handling the dead (%)")
    quarter_pct: int = rule(30, 0, 100, R, "Desirability a district gains or loses for each point of standing its caste holds above or below the middle (%)")


@dataclass(frozen=True)
class MishapRules:
    bad_luck_chance: int = rule(15, 0, 100, R, "Chance each epoch that a town suffers a small misfortune no one did (%)")
    explained_medicine: int = rule(3, 0, 20, R, "Medicine a community needs to explain an illness or a child's death by its cause")
    explained_farming: int = rule(3, 0, 20, R, "Agriculture a community needs to explain a failed harvest or a loss of herds by its cause")
    known_cause_weight: int = rule(60, 0, 100, R, "Weight of a known cause among the attributions of a mishap the community can explain")
    base_weight: int = rule(10, 0, 100, R, "Weight every attribution a culture can make starts from")
    value_weight_pct: int = rule(50, 0, 100, R, "Weight a culture's values add to the attributions they lean to, for each point of value (%)")
    luck_weight: int = rule(20, 0, 100, R, "Weight an omen or fate gains for each luck belief of the people that reaches the kind of mishap")
    charm_ward: int = rule(50, 0, 100, R, "Share of the chance of a mishap that a real charm of protection or luck wards off (%)")
    charm_calm: int = rule(5, 0, 100, R, "Stress a charm takes off its bearer each epoch, real or not")
    charm_heal: int = rule(25, 0, 100, R, "Recuperation a real charm of healing gives its bearer")
    charm_fertility: int = rule(20, 0, 100, R, "Share added to the chance of a birth by a real charm of fertility (%)")
    rite_calm: int = rule(10, 0, 100, R, "Stress a rite or an offering after a mishap takes off its victim")
    offering_loyalty: int = rule(5, 0, 100, R, "Loyalty to their god a victim gains by an offering after a mishap")
    oath_honour: int = rule(5, 0, 100, R, "Honour a victim loses when a mishap is read as the price of a broken oath")
    scheme_opinion: int = rule(5, 0, 100, R, "Opinion a town loses of a foe it blames for a mishap")
    luck_from: int = rule(10, -100, 100, R, "Superstition a culture must value before it holds beliefs about luck")
    beliefs_per_people: int = rule(3, 0, 7, R, "Beliefs about luck a superstitious people holds when first read")
    charm_strength: int = rule(60, 0, 100, R, "Strength of a charm made after a misfortune")
    lucky_morale: int = rule(5, 0, 100, R, "Morale an army gains in battle for each luck belief of its people that reaches battle")


@dataclass(frozen=True)
class WitchcraftRules:
    belief_from: int = rule(20, -100, 100, J, "Superstition a culture must value before it reads misfortune as witchcraft")
    accuse_chance: int = rule(50, 0, 100, J, "Chance a mishap read as witchcraft brings an accusation (%)")
    envy_weight: int = rule(30, 0, 100, J, "Weight the accuser's envy of a richer neighbour adds to suspicion")
    outsider_weight: int = rule(30, 0, 100, J, "Weight an outsider to the town's people adds to suspicion")
    isolation_weight: int = rule(25, 0, 100, J, "Weight a mortal with no close kin to defend them, or one who keeps apart from others, adds to suspicion")
    grievance_weight: int = rule(20, 0, 100, J, "Weight an earlier grievance of the accuser against them adds to suspicion")
    repeat_weight: int = rule(30, 0, 100, J, "Weight an earlier accusation adds to suspicion")
    caster_weight: int = rule(40, 0, 100, J, "Weight the true casting of a curse on the victim adds to suspicion")
    rumour_weight: int = rule(30, 0, 100, J, "Weight a rumour about a mortal that the town carries adds to suspicion")
    hunt_from: int = rule(3, 1, 100, J, "Accusations in one town within the memory of a hunt that start a witch hunt")
    hunt_memory: int = rule(3, 1, 50, J, "Epochs back a town counts its accusations toward a witch hunt")
    hunt_stress: int = rule(40, 0, 100, J, "Hunger, insecurity, plague, war or political stress in a town from which its accusations become a witch hunt")
    plague_stress: int = rule(50, 0, 100, J, "Stress an epidemic in a town's region lays on it toward a witch hunt")
    war_stress: int = rule(40, 0, 100, J, "Stress a war of a town's realm lays on it toward a witch hunt")
    zealous_fervour: int = rule(30, 0, 100, J, "Fervour a witch hunt gains where the town's church has turned to inquisition")
    hunt_fervour: int = rule(60, 0, 100, J, "Fervour a witch hunt starts with")
    hunt_fade: int = rule(15, 0, 100, J, "Fervour a witch hunt loses each epoch")
    hunt_accusations: int = rule(2, 0, 50, J, "Accusations a witch hunt brings each epoch at full fervour")
    wrongful_unrest: int = rule(30, 0, 100, J, "Unrest the spirit of one killed for a witchcraft they did not do carries")
