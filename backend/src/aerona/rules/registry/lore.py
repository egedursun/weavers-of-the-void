from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

R = RuleGroup.RELIGION_AND_LANGUAGE
C = RuleGroup.CIVILIZATION
H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class InterpretersRules:
    barrier_floor_pct: int = rule(40, 0, 100, R, "Effect left of an exchange between peoples who share no words (%)")
    interpreter_skill: int = rule(40, 0, 100, R, "Language skill of a mortal who interprets between tongues")
    misread_chance: int = rule(10, 0, 100, R, "A treaty clause is misread between strangers to each other's tongue (%)")
    army_cohesion_pct: int = rule(15, 0, 100, R, "Cohesion lost by an army of many tongues (%)")
    assimilation_pct: int = rule(50, 0, 100, R, "Assimilation left between peoples who share no words (%)")
    shared_lexicon_pct: int = rule(60, 0, 100, R, "Weight of a shared lexicon in intelligibility (%)")


@dataclass(frozen=True)
class PrestigeRules:
    power_pct: int = rule(40, 0, 100, R, "Weight of the speakers' realm power in a language's prestige (%)")
    literature: int = rule(3, 0, 100, R, "Prestige each work of literature lends its language")
    sacred: int = rule(15, 0, 100, R, "Prestige of a sacred or liturgical language")
    lingua_franca: int = rule(60, 0, 100, R, "Prestige at which a language becomes the lingua franca of the trade roads")
    second_language_gain: int = rule(5, 0, 100, R, "Share of a trading people that learns the lingua franca each epoch (%)")
    conquered_pct: int = rule(50, 0, 200, R, "Weight of the conquered people's literature against the conquerors' prestige (%)")
    standardisation_gain: int = rule(4, 0, 100, R, "Standardisation a school of grammar adds each epoch")
    drift: int = rule(5, 0, 100, R, "Most prestige a language gains or loses in an epoch")


@dataclass(frozen=True)
class ScriptRules:
    alphabet_pct: int = rule(130, 0, 300, C, "Literacy growth with an alphabet (%)")
    syllabary_pct: int = rule(100, 0, 300, C, "Literacy growth with a syllabary (%)")
    logographic_pct: int = rule(60, 0, 300, C, "Literacy growth with a logographic script (%)")
    knots_pct: int = rule(40, 0, 300, C, "Literacy growth with knots or notches (%)")
    scribe_satisfaction: int = rule(8, 0, 100, C, "Satisfaction a scribe caste gains from a hard script")
    alphabet_tension: int = rule(5, 0, 100, C, "Unrest when an alphabet breaks the scribes' monopoly")


@dataclass(frozen=True)
class BeliefRules:
    distortion_rate: int = rule(3, 0, 100, R, "Distortion a legend gains each telling in an unlettered people")
    credence_per_teller: int = rule(2, 0, 100, R, "Credence each telling people adds to a legend")
    credence_decay: int = rule(2, 0, 100, R, "Credence a legend loses each epoch")
    confirmation: int = rule(15, 0, 100, R, "Credence a confirming event adds")
    moral_pressure_pct: int = rule(5, 0, 100, R, "Value pressure of a fully believed legend on its tellers (%)")
    return_king_claim: int = rule(15, 0, 100, R, "Claim strength a return-of-the-king legend lends the pretender who fits it")
    cursed_line_prestige: int = rule(10, 0, 100, R, "Prestige a cursed-line legend costs a house")
    haunted_avoidance: int = rule(30, 0, 100, R, "Credence at which settlers shun a haunted land")
    manifestation_credence: int = rule(70, 0, 100, R, "Credence a legend needs to take shape in the world")
    resonance_certainty: int = rule(10, 0, 100, R, "Certainty a prophecy gains from a legend of its kind")


@dataclass(frozen=True)
class TraditionsRules:
    festival_food: int = rule(2, 0, 100, C, "Food a festival eats")
    festival_cohesion: int = rule(4, 0, 100, C, "Cohesion a festival brings")
    festival_satisfaction: int = rule(3, 0, 100, C, "Satisfaction a festival brings")
    skipped_cohesion: int = rule(4, 0, 100, C, "Cohesion lost when a festival is skipped in hunger")
    fast_food: int = rule(1, 0, 100, C, "Food a fast saves")
    taboo_infamy: int = rule(15, 0, 100, C, "Ill will toward a breaker of a taboo")
    scar_rite_chance: int = rule(20, 0, 100, C, "A youth takes the scar or the finger of the rite (%)")
    hospitality_danger: int = rule(10, 0, 100, C, "Danger a hospitality law takes from the roads")
    commemoration_chance: int = rule(25, 0, 100, C, "A great year or deed founds a commemoration (%)")
    conflict_unrest: int = rule(5, 0, 100, C, "Unrest a rigid tradition stirs against a law that defies it")
    participation_gain: int = rule(5, 0, 100, C, "Participation a tradition gains each epoch with fit")
    participation_decay: int = rule(5, 0, 100, C, "Participation a tradition loses each epoch without fit")
    war_dance_martial: int = rule(2, 0, 100, C, "Martial value a war dance pushes")
    marriage_fertility_pct: int = rule(5, 0, 100, C, "Births a marriage rite adds (%)")
    ancestor_feast_placation: int = rule(10, 0, 100, C, "Unrest an ancestor feast takes from the spirits")
    offering_cost: int = rule(1, 0, 100, C, "Goods an offering burns")
    piety: int = rule(2, 0, 100, C, "Piety a holy rite pushes")
    cap: int = rule(40, 0, 1000, C, "Most traditions celebrated in an epoch")


@dataclass(frozen=True)
class ResearchRules:
    need_pct: int = rule(100, 0, 500, C, "Weight of need (war, disease, famine) in research (%)")
    institution_pct: int = rule(50, 0, 500, C, "Weight of each school, academy or library in research (%)")
    literacy_pct: int = rule(100, 0, 500, C, "Weight of literacy in research (%)")
    contact_pct: int = rule(50, 0, 500, C, "Weight of contact with a more learned people in research (%)")
    scholar_pct: int = rule(50, 0, 500, C, "Weight of the community's best scholar, by skill and ability to study, in research (%)")
    master_scholarship: int = rule(50, 0, 100, C, "Ability to study below which a master no longer counts as one")
    master_skill: int = rule(50, 0, 100, C, "Skill at which a mortal is a master")
    practitioners_per_level: int = rule(20, 0, 100000, C, "Practitioners each level of a knowledge needs among a thousand people")
    loss_chance: int = rule(30, 0, 100, C, "A level is lost when its practitioners die and no books or masters remain (%)")
    book_diffusion_pct: int = rule(50, 0, 300, C, "Weight of books in carrying knowledge without a teacher (%)")
    teacher_pct: int = rule(100, 0, 300, C, "Weight of a teacher bond in passing knowledge (%)")


@dataclass(frozen=True)
class TechGraphRules:
    adopt_chance: int = rule(30, 0, 100, C, "A holder adopts a technique whose gate it meets (%)")
    secret_pct: int = rule(30, 0, 100, C, "Techniques a guild or cult keeps secret (%)")
    steal_chance: int = rule(20, 0, 100, C, "Spies steal a secret technique (%)")
    cap: int = rule(40, 0, 1000, C, "Most techniques adopted in an epoch")


@dataclass(frozen=True)
class IdeologiesRules:
    emergence_chance: int = rule(5, 0, 100, C, "A learned mortal founds a creed in an epoch (%)")
    spread_chance: int = rule(10, 0, 100, C, "A creed spreads along a road or through a school (%)")
    discontent_pct: int = rule(100, 0, 500, C, "Weight of an unhappy class in a creed's appeal (%)")
    adoption_strength: int = rule(60, 0, 100, C, "Adherence at which a realm takes a creed as its own")
    decision_pct: int = rule(30, 0, 300, C, "Weight a state creed lends its favoured decisions (%)")
    revolution_satisfaction: int = rule(30, 0, 100, C, "Class satisfaction below which an egalitarian creed calls revolution")
    revolution_stability: int = rule(40, 0, 100, C, "Realm stability below which a revolution breaks out")
    revolution_chance: int = rule(10, 0, 100, C, "A revolution breaks out when the creed, the class and the realm are ripe (%)")
    anti_god_faith_pct: int = rule(10, 0, 100, C, "Faith a godless creed draws away from the gods (%)")
    persecution_chance: int = rule(15, 0, 100, C, "A faith persecutes the creed that defies its tenets (%)")
    value_pressure: int = rule(2, 0, 100, C, "Values a creed pushes on its adherents each epoch")
    cap: int = rule(4, 0, 100, C, "Most creed events in an epoch")


@dataclass(frozen=True)
class RitesRules:
    enchant_chance: int = rule(10, 0, 100, H, "A wizard binds a rite into an item they made (%)")
    cult_chance: int = rule(10, 0, 100, H, "A cult performs a collective rite in an epoch (%)")
    invention_chance: int = rule(5, 0, 100, H, "A wizard devises a new rite (%)")
    essence_per_power: int = rule(2, 0, 100, H, "Essence a divine rite costs per power")
    hp_per_power: int = rule(4, 0, 1000, H, "Harm a blood rite costs its caster per power")
    reagents_per_power: int = rule(1, 0, 100, H, "Reagents a rite burns per power")
    sanity_per_power: int = rule(3, 0, 100, H, "Sanity a void rite costs per power")
    magic_price_pct: int = rule(150, 100, 500, H, "Cost of rites under the price of magic (%)")
    damage_per_power: int = rule(8, 0, 1000, H, "Harm a rite of destruction deals per power")
    heal_per_power: int = rule(10, 0, 100, H, "Function a healing rite restores per power")
    ward_pct: int = rule(5, 0, 100, H, "Siege defence a ward lends per power (%)")
    scry_intel: int = rule(10, 0, 100, H, "Intelligence a scrying rite yields per power")
    weather_power: int = rule(4, 1, 10, H, "Power a weather rite needs")
    desperate_mercy: int = rule(-20, -100, 100, H, "Mercy below which a desperate caster turns to blood and void")
    cap: int = rule(12, 0, 1000, H, "Most castings in an epoch")


@dataclass(frozen=True)
class BacklashRules:
    per_power_pct: int = rule(3, 0, 100, H, "Backlash chance each power adds (%)")
    phenomenon_power: int = rule(7, 1, 10, H, "Power at which a failed rite tears the world")
    injury_hp: int = rule(15, 0, 1000, H, "Harm a backlash deals its caster")
    leak_gain: int = rule(2, 0, 100, H, "Leak a void backlash adds to the world")


@dataclass(frozen=True)
class ProphecyRules:
    pressure_gain: int = rule(5, 0, 100, R, "Self-fulfilling pressure a believed prophecy gains each epoch")
    claim_strength: int = rule(15, 0, 100, R, "Claim strength a prophecy lends the one it names")
    paranoia_chance: int = rule(10, 0, 100, R, "A ruler threatened by a prophecy moves against its child (%)")
    failure_rationalism: int = rule(3, 0, 100, R, "Superstition a failed prophecy costs its audience")


@dataclass(frozen=True)
class CraftingRules:
    skill_pct: int = rule(60, 0, 200, H, "Weight of the crafter's skill in quality (%)")
    material_pct: int = rule(20, 0, 200, H, "Weight of the material in quality (%)")
    masterwork: int = rule(85, 0, 100, H, "Quality of a masterwork")
    masterwork_renown: int = rule(10, 0, 100, H, "Renown a masterwork brings its maker")


@dataclass(frozen=True)
class ItemWearRules:
    battle_wear: int = rule(4, 0, 100, H, "Condition a weapon or armour loses in a battle")
    decay_wet: int = rule(2, 0, 100, H, "Condition iron loses each epoch in a wet land")
    repair_gain: int = rule(20, 0, 100, H, "Condition a smith restores")
    broken: int = rule(10, 0, 100, H, "Condition below which an item is broken")


@dataclass(frozen=True)
class TechniqueEffectsRules:
    logistics_regions: int = rule(1, 0, 10, C, "Regions more an army marches in a season with logistics")
    inoculation_pct: int = rule(40, 0, 100, C, "Spread of sickness cut among an inoculated people (%)")
    irrigation_pct: int = rule(30, 0, 200, C, "Harvest a dry land gains from irrigation (%)")
    crop_rotation_pct: int = rule(15, 0, 200, C, "Harvest gained from rotating fields (%)")
    terracing_pct: int = rule(20, 0, 200, C, "Harvest a hill land gains from terraces (%)")
    plough_pct: int = rule(20, 0, 200, C, "Harvest gained from the plough (%)")
    breeding_pct: int = rule(20, 0, 200, C, "Yield herds and crops gain from selective breeding (%)")
    paper_pct: int = rule(50, 0, 200, C, "Weight books gain in carrying knowledge once paper is known (%)")
    printing_copies: int = rule(3, 0, 100, C, "Copies a loved verbal work gains each epoch once printing is known")
    calendar_pct: int = rule(20, 0, 200, C, "Strength festivals gain when the calendar counts them (%)")
    navigation_pct: int = rule(25, 0, 200, C, "Sea route capacity gained by steering by the stars (%)")
    instruments_pct: int = rule(10, 0, 200, C, "Sea route capacity gained by astrolabes (%)")
    eclipse_calm_pct: int = rule(50, 0, 100, C, "Dread of an eclipse spared a people who foretold it (%)")


@dataclass(frozen=True)
class MapsRules:
    march_regions: int = rule(1, 0, 10, H, "Regions more an army marches in a season when its lord holds a map")


@dataclass(frozen=True)
class ItemCursesRules:
    threshold: int = rule(25, 0, 100, H, "Curse at which a thing carries a typed curse")
    wasting_pct: int = rule(10, 0, 100, H, "Harm a wasting curse deals its bearer each epoch (% of the curse)")
    madness_pct: int = rule(10, 0, 100, H, "Sanity a maddening curse takes from its bearer each epoch (% of the curse)")
    bloodthirst_pct: int = rule(5, 0, 100, H, "Martial lust a bloodthirsty curse stirs in its bearer each epoch (% of the curse)")
    misfortune_pct: int = rule(5, 0, 100, H, "Prosperity a curse of misfortune takes from its bearer's home each epoch (% of the curse)")
    betrayal_pct: int = rule(10, 0, 100, H, "A betraying curse slips from its bearer's hand each epoch (% of the curse)")


@dataclass(frozen=True)
class ItemRenownRules:
    kill: int = rule(5, 0, 100, H, "Renown a weapon gains for each famous kill")
    battle: int = rule(3, 0, 100, H, "Renown an item gains from a battle won")
    coronation: int = rule(10, 0, 100, H, "Renown a crown gains from a coronation")
    symbol: int = rule(60, 0, 100, H, "Renown at which an item becomes a symbol")
    standard_morale: int = rule(5, 0, 100, H, "Morale a famous standard lends its army")
    decay: int = rule(1, 0, 100, H, "Renown an idle item loses each epoch")


@dataclass(frozen=True)
class RegaliaRules:
    legitimacy: int = rule(8, 0, 100, H, "Legitimacy a ruler draws from holding the realm's regalia")
    lost_legitimacy: int = rule(10, 0, 100, H, "Legitimacy a realm loses while its regalia are in other hands")
    humiliation: int = rule(15, 0, 100, H, "Ill will a realm holds for the captor of its symbols")


@dataclass(frozen=True)
class RelicsRules:
    healing_chance: int = rule(10, 0, 100, H, "A pilgrim is healed at a relic (%)")
    theft_chance: int = rule(3, 0, 100, H, "A rival faith steals a relic (%)")
    zeal: int = rule(3, 0, 100, H, "Zeal a famous relic stirs")
    pilgrims_per_cure: int = rule(100, 1, 100000, H, "Pilgrims at a relic for each sick pilgrim it can heal in an epoch")


@dataclass(frozen=True)
class ArtRules:
    pressure_pct: int = rule(5, 0, 100, C, "Value pressure of an influential artwork on those who hold it (%)")
    commemoration_memory: int = rule(10, 0, 100, C, "Memory a portrayed mortal's spirit keeps each epoch")
    god_fame: int = rule(2, 0, 100, C, "Fame a portrayed god gains each epoch")
    translation_chance: int = rule(10, 0, 100, C, "A scribe of both tongues translates a work (%)")
    copies_gain: int = rule(1, 0, 100, C, "Copies a verbal work gains each epoch where it is loved")
    humiliation: int = rule(5, 0, 100, C, "Ill will a conquered people hold for a statue of their conqueror")
    iconoclasm_chance: int = rule(20, 0, 100, C, "An iconoclast faith smashes an image in its lands (%)")
    sack_chance: int = rule(30, 0, 100, C, "A sacking army breaks an image of the vanquished (%)")


@dataclass(frozen=True)
class PropagandaRules:
    commission_chance: int = rule(10, 0, 100, C, "A realm with a weak claim commissions a work to praise its ruler (%)")
    cost: int = rule(20, 0, 100000, C, "Treasury a commissioned work costs")
    legitimacy: int = rule(4, 0, 100, C, "Legitimacy a work praising the ruler lends")
