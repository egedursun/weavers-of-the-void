from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class EnginePhasesRules:
    dead_bonds_opening: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: dead bonds opening")
    modifier_upkeep: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: modifier upkeep")
    world_maps: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: world maps")
    expire_truces: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: expire truces")
    language_and_faith: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: language and faith")
    divine_grudges: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: divine grudges")
    diplomacy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: diplomacy")
    war_upkeep: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: war upkeep")
    tribute: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: tribute")
    campaigns: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: campaigns")
    prisoners: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: prisoners")
    travel: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: travel")
    seafaring: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: seafaring")
    exploration: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: exploration")
    resource_mechanics: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: resource mechanics")
    cosmic_economy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cosmic economy")
    horror: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: horror")
    creatures: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creatures")
    pantheon: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: pantheon")
    death_engine: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: death engine")
    civilization: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: civilization")
    sky: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: sky")
    beyond: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: beyond")
    monster_raids: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: monster raids")
    sworn_hunts: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: sworn hunts")
    glory_hunts: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: glory hunts")
    trade_income: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: trade income")
    curse_decay: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: curse decay")
    resource_economy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: resource economy")
    prosperity_reversion: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: prosperity reversion")
    barter_and_rivalry: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: barter and rivalry")
    curse_lifting: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: curse lifting")
    cursed_items: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cursed items")
    magic_storms: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: magic storms")
    resource_regeneration: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: resource regeneration")
    schisms: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: schisms")
    creature_migration: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creature migration")
    hero_births: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: hero births")
    knowledge_diffusion: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: knowledge diffusion")
    cultural_exchange: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cultural exchange")
    natural_disasters: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: natural disasters")
    famine_migration: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: famine migration")
    refugees: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: refugees")
    uprisings: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: uprisings")
    spirits_rest: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: spirits rest")
    hauntings: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: hauntings")
    settlement_laws: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: settlement laws")
    currency: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: currency")
    wizards: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: wizards")
    creature_rebellion: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creature rebellion")
    godlessness: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: godlessness")
    speciation: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: speciation")
    couple_births: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: couple births")
    love_and_rivalry: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: love and rivalry")
    dialect_divergence: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: dialect divergence")
    language_death: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: language death")
    price_of_magic: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: price of magic")
    architecture: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: architecture")
    society_economy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: society economy")
    heroes: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: heroes")
    spontaneous_births: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: spontaneous births")
    factions: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: factions")
    engine_works: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: engine works")
    splendor_growth: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: splendor growth")
    structure_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: structure survey")
    structure_upkeep: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: structure upkeep")
    structure_functions: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: structure functions")
    religion_spread: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: religion spread")
    life_seed: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: life seed")
    writing_systems: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: writing systems")
    belief_and_memory: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: belief and memory")
    espionage: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: espionage")
    wonders: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: wonders")
    dark_ages: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: dark ages")
    ruins: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ruins")
    mortal_wounds: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal wounds")
    mortal_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal survey")
    mortal_life_course: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal life course")
    mortal_kin: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal kin")
    mortal_standing: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal standing")
    mortal_minds: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal minds")
    ethnic_relations: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ethnic relations")
    mortal_aging: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortal aging")
    dead_bonds_closing: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: dead bonds closing")
    local_gods: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: local gods")
    law_fertility: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: law fertility")
    population_baseline: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: population baseline")
    climate_transition: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: climate transition")
    population_growth: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: population growth")
    epoch_stars: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: epoch stars")
    sons_renewal: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: sons renewal")
    gods_fate: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: gods fate")
    works_remember_gods: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: works remember gods")
    domain_rivalry: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: domain rivalry")
    rebel_theft: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: rebel theft")
    doom_clock: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: doom clock")
    creator_essence: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creator essence")
    epoch_statistics: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: epoch statistics")
    creator_mood: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creator mood")
    god_power: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: god power")
    reputation: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: reputation")
    goals: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: goals")
    war_casualties: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: war casualties")
    geography: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: geography")
    place_profiles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: place profiles")
    place_secrets: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: place secrets")
    ecology: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ecology")
    world_balance: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: world balance")
    disaster_casualties: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: disaster casualties")
    settlement_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: settlement cycles")
    remembrance: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: remembrance")
    mechanics_assignment: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mechanics assignment")
    market: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: market")
    native_faith: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: native faith")
    language_contact: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: language contact")
    knowledge_levels: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: knowledge levels")
    living_stats: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: living stats")
    institution_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: institution cycles")
    culture_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: culture cycles")
    environment_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: environment survey")
    environment_modifiers: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: environment modifiers")
    body_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: body survey")
    body_healing: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: healing of wounds")
    body_afflictions: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: venoms, curses, blessings, dependences and traumas running their stages"
    )
    body_conditions: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: lasting conditions")
    body_society: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the maimed among the living")
    mind_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: minds for every mortal, people and god")
    mind_values: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: drift of cultures and personal values")
    mind_skills: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: teaching, rusting skills and changing callings")
    mind_split: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: attributes growing with use and age, facets granting traits")
    mind_ideas: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ideas met, turned over, taken to heart or let go")
    mind_memories: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: fading memories")
    mind_thoughts: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: thoughts and feelings, formative memories and mood")
    mind_grief: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mourning, acceptance and grief that will not heal")
    mind_dreams: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: dreams, nightmares, visitations and their readings")
    mind_preferences: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: likes and dislikes, taboos of disgust and totems of love")
    mind_ethics: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ethics following beliefs, honour and shame, schisms")
    mind_aspirations: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: life's dreams, wants, fears, focus, perks and inspiration")
    relations_social: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortals meeting, talking, courting, quarrelling, and affairs found out"
    )
    relations_circles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: circles gathering around shared tastes and beliefs")
    relations_passions: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: passions kindled by bonds, oaths, memories and upbringing")
    relations_pecking: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: pecking orders in households, courts, circles, warbands and crews")
    genetics_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: allele pools for every people and a genome for every mortal")
    intrigue_survey: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: true names, hidden conditions, hidden debts and memberships, and the false names of spies, exiles and the blood-cursed",
    )
    correspondence: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: messages on their way, interception, delivery, envoys, gifts and insults between rulers, ciphers and signal links",
    )
    estates: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: estates and their privileges, movements and parties, chartered companies, holy orders, guild ranks and craft secrets",
    )
    titles: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: titles founded, passed on, drifting de jure lands, claims, usurpation, creation, restoration, partition and personal unions",
    )
    public_opinion: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: what every community thinks of its ruler, its wars, its laws, its gods and its creeds"
    )
    legislature: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: laws before each realm weighed by their voices, hooks and obstruction, debated, rioted over, softened, passed or failed",
    )
    affairs: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: council tasks, elections and seats, corruption and taxes, mandates and nobles' demands, the policy network and the fundamental law",
    )
    statecraft: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: threat and trust between realms, coalitions, crises and their backers, spheres and summits, subjects and their terms",
    )
    trials: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: cases at law tried before a judge, a jury, by combat or by ordeal, the guilty sentenced and the wrongly convicted mourned",
    )
    intrigue: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: beliefs seen, spied and fading, secrets learned and exposed, masks wearing thin, true names sought and schemes plotted",
    )
    bloodlines: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: drifting allele pools, the gift and how peoples read it, looks, house resemblance and gifted children",
    )
    household_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: a household and a home for every named mortal")
    households: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: household purses, care, homes and their quality, and the choices households make"
    )
    industry_methods: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: energy of each place and the production methods it chooses")
    industry_aftermath: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: preserving, spoilage, tool wear, fuel burned, pollution and its harm, and what nobles want"
    )
    site_profits: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: owners of works and resources, their profits, taxes, investment and lobbying"
    )
    trade_policy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: tariffs, subsidies and embargoes realms lay and lift")
    credit_ratings: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: credit ratings, bankruptcy states, interest and the reserves that back coin"
    )
    speculation: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: greedy merchants hoarding rising goods and food in famine, booms and busts")
    economic_indicators: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: output, prices, trade balance, debt, idleness and living of realms and worlds"
    )
    renown_hearsay: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: deeds heard of in rumours, fading reputations, renown and infamy")
    renown_claims: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: shared and false claims of deeds, tested and exposed")
    ruler_currencies: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: prestige, piety, dread and tyranny of rulers, spent on clergy and silence"
    )
    lore_market: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: lore traded for wealth, favours and renown")
    gatherings: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: feasts, weddings, funerals, tournaments, councils and every other gathering")
    event_collections: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: incidents gathered into wars, battles, plagues and every other history"
    )
    storyteller: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the tension of each world, its aim and the pace of disruptions")
    thrones: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: thrones of power, who holds them and the ascension they lead to")
    magic_sites: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: hidden magic sites, the mages who find them and what they yield")
    dominion: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the dominion of every god over the land, its contests and its scales")
    worship_views: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: how each people sees each god and whether it worships in devotion or appeasement"
    )
    god_images: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the image peoples hold of their gods and how it reshapes them")
    divine_creatures: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: divine creatures acting on what their gods taught them")
    spell_grammar: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the grammar of every rite and the study of lab texts")
    vis: int = rule(
        1,
        0,
        1,
        RuleGroup.ENGINE_PHASES,
        "Run the engine step: magic resources gathered at sites, from beasts and phenomena, traded and used to recharge enchanted items",
    )
    warping: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: warping gathered from long exposure to magic and what it does to mortals")
    longevity: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: longevity magic paid for in vis, and the borrowed years lost when it lapses")
    heroquests: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: heroquests into the mythic realms and how they rewrite the myths")
    mantling: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mortals walking a god's path toward ascension or replacement")
    servitors: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: divine servitors, their duties and their loyalty")
    geasa: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: geasa laid on mortals, kept or broken")
    cosmic_offices: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the cosmic offices of the gods, their duties and their neglect")
    sound_changes: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: sound changes that reshape each tongue's words")
    grammar: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the grammar of each tongue and how contact reshapes it")
    semantic_drift: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: words that shift their meaning and names that may not be spoken")
    script_evolution: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: scripts that are reformed, worn simpler and borrowed")
    decipherment: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: scholars deciphering dead scripts")
    pidgins: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: pidgins born of contact and the creoles they become")
    language_policy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: official, sacred, suppressed and revived tongues")
    divine_tongues: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: the sacred tongues of the gods")
    site_rooms: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: rooms of towers, lairs, vaults and ruins, and who holds each site")
    excavations: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: digs at ruins and old sites, stage by stage, with their risks and finds")
    battlefields: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: mass graves and fields of salvage left where battles were fought")
    relations_contests: int = rule(
        1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: contests of wit between rivals, suitors, captives, courtiers and priests"
    )
    mind_needs: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: needs of mortals and pressures on communities")
    incident_threads: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: long chains of causes open stories")
    famine_aid: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: well-stocked neighbours feed the starving")
    mind_opinion: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: community relations from opinion")
    environment_derive: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: environment derive")
    land_use: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: land use")
    geomorphology: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: geomorphology")
    event_phases: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: event phases")
    harvest: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: harvest")
    calendars: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: calendars")
    ley_lines: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ley lines")
    economy_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: economy survey")
    world_materials: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: world materials")
    species_yields: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: species yields")
    deposit_finding: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: deposit finding")
    refining: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: refining")
    markets: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: markets")
    trade_flow: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: trade flow")
    banking: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: banking")
    material_decay: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: material decay")
    epidemics: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: epidemics")
    cohort_upkeep: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cohort upkeep")
    labour_allocation: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: labour allocation")
    society_mobility: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: society mobility")
    people_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: people cycles")
    settlement_life: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: settlement life")
    polity_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: polity cycles")
    treaty_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: treaty cycles")
    house_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: house cycles")
    vendetta_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: vendetta cycles")
    faith_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: faith cycles")
    soul_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: soul cycles")
    rite_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: rite cycles")
    language_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: language cycles")
    ideology_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: ideology cycles")
    research_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: research cycles")
    legend_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: legend cycles")
    prophecy_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: prophecy cycles")
    tradition_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: tradition cycles")
    item_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: item cycles")
    artwork_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: artwork cycles")
    rumour_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: rumour cycles")
    husbandry: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: husbandry")
    flora_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: flora cycles")
    beast_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: beast cycles")
    pet_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: pet cycles")
    necromancy_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: necromancy cycles")
    region_survey: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: region survey")
    danger_harm: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: danger harm")
    terrain_hazards: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: terrain hazards")
    sacred_pilgrims: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: sacred pilgrims")
    domain_economy: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: domain economy")
    god_goals: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: god goals")
    divine_standing: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: divine standing")
    divine_wounds: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: divine wounds")
    scale_ladder: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: scale ladder")
    cosmic_influence: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cosmic influence")
    galaxy_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: galaxy cycles")
    star_lives: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: star lives")
    stellar_systems: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: stellar systems")
    world_physics: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: world physics")
    planetary_climate: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: planetary climate")
    cosmic_features: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cosmic features")
    impacts: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: impacts")
    terraforming: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: terraforming")
    surveys: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: surveys")
    dimension_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: dimension cycles")
    rift_cycles: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: rift cycles")
    cosmic_beings: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cosmic beings")
    phenomena: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: phenomena")
    regional_leak: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: regional leak")
    celestial_omens: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: celestial omens")
    cosmic_trade: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: cosmic trade")
    world_lives: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: world lives")
    regional_climate: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: regional climate")
    avatars: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: avatars")
    creator_taboos: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creator taboos")
    creator_attention: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: creator attention")
    god_relations: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: god relations")
    council_rulings: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: council rulings")
    natural_laws: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: natural laws")
    outer_hunger: int = rule(1, 0, 1, RuleGroup.ENGINE_PHASES, "Run the engine step: outer hunger")
