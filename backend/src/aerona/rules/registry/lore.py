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
    phonology_pct: int = rule(20, 0, 100, R, "Intelligibility a shared sound system adds to tongues that already share words")
    misread_grievance: int = rule(10, 0, 100, R, "Ill will a misread treaty clause breeds, counted as a breach")
    remeasure_epochs: int = rule(5, 0, 100, R, "Epochs between new measures of how well two tongues understand each other (0 never)")


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
    standard_literacy_pct: int = rule(50, 0, 300, R, "Literacy growth a fully standardised tongue adds (%)")
    standard_distortion_pct: int = rule(50, 0, 100, R, "Legend distortion a fully standardised written tongue holds back (%)")


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
    credence_base: int = rule(30, 0, 100, R, "Credence a legend starts with before its spread is counted")
    spread_credence_pct: int = rule(50, 0, 200, R, "Credence a legend draws from how widely it has spread (%)")
    category_credence: int = rule(10, 0, 100, R, "Credence a legend of a known kind (creature, spirit, treasure, relic) gains")
    bard_skill: int = rule(40, 0, 100, R, "Oratory or lore at which a mortal tells legends as a bard")
    bards_per_legend: int = rule(3, 0, 50, R, "Most bards counted among a legend's tellers")
    credence_per_bard: int = rule(1, 0, 100, R, "Credence each bard who tells a legend adds")
    return_king_usurper: int = rule(8, 0, 100, R, "Legitimacy a usurper of the foretold line draws from a believed return-of-the-king tale")


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
    harvest_blessing: int = rule(2, 0, 100, C, "Harvest a harvest rite blesses the land with (%)")
    value_push: int = rule(1, 0, 100, C, "Values a tradition of a new kind pushes each epoch")
    scar_harm: int = rule(4, 0, 100, C, "Harm a ritual scar deals the youth who takes it")
    season_growth: int = rule(60, 0, 100, C, "Growth of a season in which sowing and harvest feasts fall")
    dead_growth: int = rule(20, 0, 100, C, "Growth at or below which a season is the dead of winter")
    season_campaign: int = rule(60, 0, 100, C, "Campaign suitability of the season in which war feasts fall")
    calendar_slot_pct: int = rule(30, 0, 300, C, "Strength an effect gains when its feast falls in its season (%)")
    calendar_misfit_pct: int = rule(50, 0, 100, C, "Strength left to a feast whose season never comes (%)")
    sync_cohesion: int = rule(1, 0, 100, C, "Cohesion each other keeper of the same calendar feast adds")
    sync_max: int = rule(5, 0, 100, C, "Most fellow keepers counted for a synchronised feast")
    commemoration_keepers: int = rule(3, 0, 50, C, "Most communities of a land that keep the memory of a notable year")
    taboo_importance: int = rule(5, 0, 100, C, "Renown a mortal loses for breaking a taboo")
    guest_killing_infamy: int = rule(40, 0, 100, C, "Ill will the keepers of hospitality hold for a guest-killer")
    ritual_presence_pct: int = rule(5, 0, 100, C, "Presence each ritual scar lends among those who keep the rite (%)")
    ritual_presence_cap: int = rule(15, 0, 100, C, "Most presence ritual scars can lend (%)")
    adoption_fit: int = rule(70, 0, 100, C, "Value distance above which a people refuses a tradition offered by contact")
    syncretism_rigidity: int = rule(40, 0, 100, C, "Rigidity at which a feast survives conversion and is absorbed by the new faith")
    rigid_threshold: int = rule(20, 0, 100, C, "Rigidity below which a tradition bends to laws and creeds without unrest")
    rigidity_pct: int = rule(100, 0, 300, C, "Weight of rigidity in the unrest a tradition stirs against what defies it (%)")
    creed_resistance: int = rule(3, 0, 100, C, "Adherence a creed loses where a rigid tradition it defies is kept")


@dataclass(frozen=True)
class ResearchRules:
    need_pct: int = rule(100, 0, 500, C, "Weight of need (war, disease, famine) in research (%)")
    institution_pct: int = rule(50, 0, 500, C, "Weight of each school, academy or library in research (%)")
    literacy_pct: int = rule(100, 0, 500, C, "Weight of literacy in research (%)")
    contact_pct: int = rule(50, 0, 500, C, "Weight of contact with a more learned people in research (%)")
    practitioners_per_level: int = rule(20, 0, 100000, C, "Practitioners each level of a knowledge needs among a thousand people")
    loss_chance: int = rule(30, 0, 100, C, "A level is lost when its practitioners die and no books or masters remain (%)")
    book_diffusion_pct: int = rule(50, 0, 300, C, "Weight of books in carrying knowledge without a teacher (%)")
    teacher_pct: int = rule(100, 0, 300, C, "Weight of a teacher bond in passing knowledge (%)")
    master_skill: int = rule(50, 0, 100, C, "Skill in its craft a mortal needs to keep a branch of knowledge alive as its master")
    book_progress: int = rule(10, 0, 100, C, "Progress toward the next level a faithful book gives its readers each epoch")
    progress_pct: int = rule(100, 0, 500, C, "Weight of research pressure in the progress toward a deeper level (%)")
    enlightenment_relief_pct: int = rule(10, 0, 100, C, "Share of the world's mean spread of learning that eases the doom each epoch (%)")
    enlightenment_cap: int = rule(5, 0, 100, C, "Most doom the spread of learning can ease in an epoch")


@dataclass(frozen=True)
class TechGraphRules:
    adopt_chance: int = rule(30, 0, 100, C, "A holder adopts a technique whose gate it meets (%)")
    secret_pct: int = rule(30, 0, 100, C, "Techniques a guild or cult keeps secret (%)")
    steal_chance: int = rule(20, 0, 100, C, "Spies steal a secret technique (%)")
    cap: int = rule(40, 0, 1000, C, "Most techniques adopted in an epoch")


@dataclass(frozen=True)
class IdeologiesRules:
    emergence_chance: int = rule(5, 0, 100, C, "A learned mortal founds a creed in an epoch (%)")
    founding_tenets: int = rule(3, 1, 13, C, "Most tenets a creed founded from a mortal's convictions carries")
    school_pct: int = rule(50, 0, 300, C, "Weight a school, academy or library lends a creed spreading into its town (%)")
    text_chance: int = rule(10, 0, 100, C, "A learned founder sets down the teachings of their creed in a book in an epoch (%)")
    texts_max: int = rule(3, 0, 100, C, "Most books of teachings a creed is written into")
    persecuting_mercy: int = rule(40, 0, 100, C, "Mercy below which a god answers a godless creed by striking its followers")
    persecution_blow: int = rule(15, 0, 100, C, "Adherence a god's persecution strikes from a godless creed's followers")
    miracle_essence: int = rule(5, 0, 1000, C, "Essence a god spends on a sign to win back the godless")
    miracle_faith: int = rule(5, 0, 1000, C, "Faith a god's sign wins back from the godless")
    miracle_doubt: int = rule(8, 0, 100, C, "Adherence a god's sign takes from a godless creed")
    suppression_blow: int = rule(25, 0, 100, C, "Adherence a suppression strikes from every follower of a creed")
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
    wizard_skill: int = rule(30, 0, 100, H, "Spellcraft a mortal needs before the world counts them a wizard")
    spellcraft_xp: int = rule(4, 0, 100, H, "Spellcraft a learned mortal who knows magic gains from study each epoch")
    hp_per_captive: int = rule(8, 1, 1000, H, "Harm a blood rite would cost that one captive's blood pays instead")
    regrow_power: int = rule(7, 1, 10, H, "Power at which a healing rite makes lost limbs whole")
    undead_per_dead: int = rule(10, 0, 1000, H, "Soldiers of the risen dead each battle death yields")
    undead_per_power: int = rule(40, 0, 10000, H, "Most risen dead a raising rite yields per point of its strength")
    army_chance: int = rule(30, 0, 100, H, "War mages work a battle rite against their army's target in an epoch (%)")
    dark_infamy: int = rule(10, 0, 100, H, "Standing a caster loses for working blood or void magic")
    cap: int = rule(12, 0, 1000, H, "Most castings in an epoch")


@dataclass(frozen=True)
class BacklashRules:
    per_power_pct: int = rule(3, 0, 100, H, "Backlash chance each power adds (%)")
    phenomenon_power: int = rule(7, 1, 10, H, "Power at which a failed rite tears the world")
    injury_hp: int = rule(15, 0, 1000, H, "Harm a backlash deals its caster")
    leak_gain: int = rule(2, 0, 100, H, "Leak a void backlash adds to the world")
    phenomenon_epochs: int = rule(5, 1, 100, H, "Epochs an eternal storm torn by a failed rite lasts")
    phenomenon_danger: int = rule(15, 0, 100, H, "Danger an eternal storm adds to its region")


@dataclass(frozen=True)
class ProphecyRules:
    pressure_gain: int = rule(5, 0, 100, R, "Self-fulfilling pressure a believed prophecy gains each epoch")
    claim_strength: int = rule(15, 0, 100, R, "Claim strength a prophecy lends the one it names")
    paranoia_chance: int = rule(10, 0, 100, R, "A ruler threatened by a prophecy moves against its child (%)")
    failure_rationalism: int = rule(3, 0, 100, R, "Superstition a failed prophecy costs its audience")
    failure_importance: int = rule(5, 0, 100, R, "Standing a seer loses, and ill will its hearers bear, when the prophecy fails")
    failure_zeal: int = rule(5, 0, 100, R, "Zeal the seer's cult loses when the prophecy fails")
    omen_superstition: int = rule(3, 0, 100, R, "Superstition a fulfilled omen adds to those who heard it")
    consequence_claim: int = rule(15, 0, 100, R, "Claim strength or standing the one foretold to rule or be born gains when it comes true")
    consequence_unrest: int = rule(10, 0, 100, R, "Defence lost by a city foretold to fall, and ill will toward a foretold enemy, when it comes true")
    consequence_harm: int = rule(30, 0, 1000, R, "Harm doom deals the one foretold to die when the sign is met")
    infanticide_grudge: int = rule(30, 0, 100, R, "Grief a house holds for the ruler who moved against its foretold child")


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
    canon_pct: int = rule(50, 0, 300, C, "Weight a classic gains in pressing its message and being copied (%)")
    translated_pct: int = rule(50, 0, 100, C, "Share of a work's pressure felt by the speakers of a tongue it was translated into (%)")
    bilingual_share: int = rule(20, 0, 100, C, "Share of a people speaking a second tongue before its scribes can translate into it")
    performer_skill: int = rule(30, 0, 100, C, "Oratory or lore a mortal needs to keep a performed work alive")


@dataclass(frozen=True)
class PropagandaRules:
    commission_chance: int = rule(10, 0, 100, C, "A realm with a weak claim commissions a work to praise its ruler (%)")
    cost: int = rule(20, 0, 100000, C, "Treasury a commissioned work costs")
    legitimacy: int = rule(4, 0, 100, C, "Legitimacy a work praising the ruler lends")
