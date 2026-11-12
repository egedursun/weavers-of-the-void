from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.laws import law_terms_guide
from aerona.domain.enums.culture import ArtMedium, CalendarSlot, ItemClass, LegendArchetype, ProphecyConsequence, ProphecyPredicate, TraditionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.world import SkyEventKind
from aerona.prompts.tools.ids import SonToolId
from aerona.prompts.tools.shared import IMAGE_PROMPT_FIELD, LINK_FIELDS, WORD_FIELDS
from aerona.prompts.tools.text import ToolText

T = SonToolId

CREATION_DESCRIPTION = (
    "Creates {{ entity.label | an }} ({{ entity.examples | join(', ') }}). "
    "{% if entity.type in living_types and rules.son_tools.free_living_creation > 0 %}"
    "Living creation: the first living creation each age does NOT spend an action; later ones cost 1 action."
    "{% elif entity.type in land_types %}"
    "1 action; if your world is crowded ({{ rules.exploration.crowded_communities_per_region }}+ communities per region) the age's first land creation"
    " that eases the crowding (a new region, or a place in a crowded region)"
    "{% if rules.exploration.free_land_creation > 0 %} does not spend an action and{% endif %}"
    " grants +{{ rules.exploration.land_creation_essence }} essence, +{{ rules.exploration.land_creation_renown }} fame; later ones earn nothing."
    "{% else %}1 action.{% endif %}"
    " Cost: {{ rules.creation_base_cost[entity.type] }}+{{ rules.core_rules.cost_per_power_level }} x power essence, cheap in your own domain"
    "{% if context.example_cost %} (power 1, in your own domain about {{ context.example_cost }} essence){% endif %}."
    " Gains depend on the type's value and fade for each further creation of the same type in an age; similar themes cost more; stats follow the power level."
)

CREATION_FIELDS: dict[str, str] = {
    "name": "Original proper name; fitting the world's naming language. Generic names (River, Dark Forest, Dragon) are forbidden.",
    "subtype": "What it is, e.g.: {{ entity.examples | join(', ') }}",
    "description": "3 to 7 sentences. Concrete, sensory details of its own; how it was born, what it is connected with, how mortals know it.",
    "domain": "If empty, your first domain. The domain used in this creation; one of: {{ domains | join(', ') }}. Your own domains are cheap.",
    "power_level": "Between 1 and 10{% if context.power_ceiling %}; your ceiling is {{ context.power_ceiling }}{% endif %}. Increases the cost.",
    "stats": "Optional stats; leave out any you do not want to set",
    **LINK_FIELDS,
    "image_prompt": IMAGE_PROMPT_FIELD,
    "tags": "Short tags",
    "story_id": "Which open story (story#) this creation advances",
    "co_creator_id": "To create together with a covenanted sibling, their id: they pay half the cost, the creation belongs to both of you",
    "location_id": (
        "The id of the entity it is inside ({{ container_labels | join(', ') }})"
        "{% if entity.location_required %}. It must have a location: if you leave it empty it is inferred from the region, place or settlement among your bonds "
        "(or from where the community you bond to is located){% endif %}"
    ),
}

WORSHIPPED_SON_FIELD = {"worshipped_son_id": "Whom they worship (son id){% if entity.type == 'cult' %}; you if empty{% endif %}. Faith flows this way."}

ARCHETYPES = ", ".join(item.value for item in LegendArchetype)
TRADITION_KINDS = ", ".join(item.value for item in TraditionKind)
CALENDAR_SLOTS = ", ".join(item.value for item in CalendarSlot)
ITEM_CLASSES = ", ".join(item.value for item in ItemClass)
ART_MEDIA = ", ".join(item.value for item in ArtMedium)
PREDICATES = ", ".join(item.value for item in ProphecyPredicate)
CONSEQUENCES = ", ".join(item.value for item in ProphecyConsequence)
SKY_KINDS = ", ".join(item.value for item in SkyEventKind)
TABOO_ACTS = ", ".join(item.value for item in ActKind)
LEGEND_CATEGORY_FIELD = "What the legend would become if belief ever made it walk the world: {{ legend_categories | join(', ') }}; creature for a beast or monster, spirit for a ghost or soul, resource for a sacred spring or vein, relic for a weapon or treasure"
COMMODITY_FIELD = "What its people draw from it: {{ commodities | join(', ') }}; ore feeds forges and coin, grain, livestock and fish feed mouths, timber feeds fuel and ships"
MATERIAL_FIELD = "What it is made of or yields, if a material: {{ materials | join(', ') }}; it sets hardness, edge, weight, holiness and taint"

CREATION_EXTRA_FIELDS: dict[EntityType, dict[str, str]] = {
    EntityType.CULT: {
        **WORSHIPPED_SON_FIELD,
        "tenets": "The tenets you teach this cult (at most {{ rules.doctrine.tenets_max }}; opposites cannot stand together): {{ tenets }}",
        "judgement": "How its god judges the dead: {{ judgements | join(', ') }}",
        "rebirth_path": "Where its exceptional souls are reborn: {{ rebirth_paths | join(', ') }} (people: the same people; house: the same house; merit: by their deeds)",
    },
    EntityType.PEOPLE: WORSHIPPED_SON_FIELD,
    EntityType.SETTLEMENT: WORSHIPPED_SON_FIELD,
    EntityType.FACTION: WORSHIPPED_SON_FIELD,
    EntityType.NATURAL_LAW: {"mechanic": "The law's mechanical effect in the world (if left empty it is read from the law's text): {{ natural_laws }}"},
    EntityType.KNOWLEDGE: {
        "branch": "The knowledge's branch: {{ knowledge_branches }}",
        "learner_ids": "Communities that first learn this knowledge (at most {{ rules.son_tools.knowledge_first_learners }})",
    },
    EntityType.REGION: {"water": "True if the region is a sea or ocean (water) rather than land; default false"},
    EntityType.PLACE: {
        "place_kind": "What kind of place it is: {{ place_kinds | join(', ') }}; its ground, cover, water, height, sacredness and hidden secrets follow the kind"
    },
    EntityType.SPECIES: {
        "traits": "The creature's traits (at most {{ rules.son_tools.creature_max_traits }}): {{ creature_traits }}",
        "body_plan": "The creature's body: {{ body_plans }}; its wounds, armour and fighting follow this body",
        "size_class": "How big one of them stands: {{ size_classes | join(', ') }}; it sets what it can hunt, its lifespan, litters and whether it can be ridden",
        "diet": "What it feeds on: {{ diets | join(', ') }}; soul eaters swallow the dead, mineral eaters gnaw ore, void eaters need nothing living",
        "sociality": "How it lives with its kind: {{ socialities | join(', ') }}; packs hunt harder, herds and hives shield their numbers",
        "nocturnal": "True if it wakes at night; night kinds escape hunters more often",
        "migratory": "True if its herds move between lands with the seasons",
        "products": "What it yields beyond meat, hide and bone, if anything: {{ yield_products | join(', ') }}; silk and venom feed crafts, dragonbone feeds forges",
        "species_class": "What kind of life it is: {{ species_classes | join(', ') }}; plants and fungi are gathered, sown and harvested, vermin spoil stores",
        "biochemistry": "What its life is built on: {{ biochemistries | join(', ') }}; it lives only on worlds that bear that kind of life, though void and spirit life live anywhere",
        "growth_cycle": "For a plant or fungus, how it grows: {{ growth_cycles | join(', ') }}",
        "plant_yields": "For a plant or fungus, what its harvest gives: {{ plant_yields | join(', ') }}",
    },
    EntityType.BEAST: {
        "species_id": "The kind it is the greatest of (species id), if any; it takes that kind's body, yields and lifespan",
        "size_class": "How big it stands: {{ size_classes | join(', ') }}; huge and colossal beasts take more in their raids and can carry a rider",
        "temper": "Its mood when it wakes in the world: {{ beast_tempers | join(', ') }}; a sleeping beast waits, a hungry one raids",
        "endurance": "0-100: how far it ranges on its raids and how much harm it shrugs off",
        "perception": "0-100: how easily disturbance wakes it and how little thieves take from its hoard",
        "willpower": "0-100: how hard it is to tame and how seldom it rests after a hunt",
        "intelligence": "0-100: at {{ rules.mortal_agents.creature_min_intelligence }} or more it speaks, bargains and acts by itself",
        "breath": "A breath it attacks with, if any: {{ breath_kinds | join(', ') }}; it adds to the harm of its raids",
        "gaze": "A gaze it attacks with, if any: {{ gaze_kinds | join(', ') }}; each raid makes it more dreaded",
        "temperament": "Its temperament: {{ temperaments | join(', ') }}; an abductor carries people off to its lair instead of killing them",
        "habitat": "Where it lives: {{ habitats | join(', ') }}; a creature of the void roams the roads between worlds",
        "awakening": "If it sleeps until something wakes it: {{ awakening_triggers | join(', ') }}",
        "skin": "What its body is made of: {{ tissue_materials | join(', ') }}; harder stuff turns harm aside",
    },
    EntityType.VESSEL: {
        "target_world_id": "If the gate, bridge or ship connects to another world, that world's id: a route is opened",
        "vessel_kind": "What it is: {{ vessel_kinds | join(', ') }}; a gate, ship, mount or bridge opens the matching kind of road",
        "hull_material": "Its hull or frame: {{ materials | join(', ') }}; a hard, tough hull turns storms and raiders aside. Empty: its makers choose",
        "fabric_material": "Its sails or harness: {{ materials | join(', ') }}; a light one runs a stage faster, a tough one braves the wind. Empty: its makers choose",
        "hull_class": "For a ship: its hull class, from a light boat to a great warship",
        "armament": "For a ship: what it carries to fight (rams, archers, engines, boarders)",
        "home_port_id": "For a ship: the settlement it sails from",
        "captain_id": "For a ship: the mortal who commands it",
    },
    EntityType.LEGEND: {
        "legend_category": LEGEND_CATEGORY_FIELD,
        "archetype": "The kind of tale it is, which sets the lesson it presses on its tellers: " + ARCHETYPES,
    },
    EntityType.TRADITION: {
        "tradition_kind": "What kind of custom it is; this decides what keeping it costs and brings: " + TRADITION_KINDS,
        "calendar_slot": "When it is kept, if at a set time: " + CALENDAR_SLOTS + "; a feast in its season is stronger",
        "taboo_target": "For a taboo: the good its keepers will not touch",
        "taboo_act": "For a taboo: the deed its keepers will not do (" + TABOO_ACTS + "); breakers are held in infamy",
        "funeral_rite": "If it is a funeral custom, how its people send off the dead: {{ funeral_rites | join(', ') }}; nameless seals the soul",
    },
    EntityType.ITEM: {
        "item_class": "What kind of thing it is; this decides how it is used and what it does in the world: " + ITEM_CLASSES,
        "material": "What it is made of: {{ materials | join(', ') }}; sets its edge, guard, worth, rot and holy harm to the undead. Empty: its makers choose",
        "world_material_id": "Or a substance of this world by its id (see the world's materials); overrides material",
        "secondary_materials": "Other materials worked into it (inlays, bindings, hilts): {{ materials | join(', ') }}",
    },
    EntityType.ARTWORK: {
        "medium": "What kind of work it is; performed works live only while someone can perform them: " + ART_MEDIA,
        "subject_id": "Whom or what it portrays, if anyone (an entity id); a portrayed mortal is remembered, a portrayed god gains fame",
    },
    EntityType.PROPHECY: {
        "predicate": "What exactly must happen for it to come true, checked by the world itself: " + PREDICATES,
        "subject_id": "The one the foretelling names: who dies (dies), what falls (falls), the house (born_in), the realm (ruler_of), the first side (war_between); a sky event (sky_event) and a span of ages (within_epochs) name no one",
        "second_id": "For war_between: the second side",
        "archetype": "For ruler_of: the kind of legend the coming ruler must fit (" + ARCHETYPES + ")",
        "sky_kind": "For sky_event: the sign in the sky (" + SKY_KINDS + ")",
        "event_kind": "For within_epochs: the kind of happening foretold (a war, a birth, a flood, a crowning...)",
        "within_epochs": "In how many ages it must come true; if it does not, the seer is mocked",
        "consequence": "What it means when it comes true: " + CONSEQUENCES,
        "consequence_id": "Whom the consequence touches (the one who will rule, the city that will fall)",
    },
    EntityType.STRUCTURE: {
        "structure_kind": "What it is and what it does: {{ structure_kinds }}",
        "material": "What it is built of: {{ materials | join(', ') }}; stone lasts and resists fire, holy stone makes a temple shine, wood rots and burns. Empty: its builders choose",
        "world_material_id": "Or a substance of this world by its id; overrides material",
        "level": "Its size, 1 to 5",
        "design_id": "A structure design of the same kind to build to, if one exists",
    },
    EntityType.FACTION: {
        **WORSHIPPED_SON_FIELD,
        "faction_kind": "What it is: merchant_guild, craft_guild, priesthood, warrior_order, noble_council, peasant_league, rebels, bandits, pirates, assassins, scholars_academy, secret_society, mercenary_company, interworld_federation, wandering_market, void_pirates, social_circle, crime_family, thieves_guild, smuggling_ring or pirate_confederacy; its kind decides what it strives for and how it acts",
    },
    EntityType.LAW: {
        "law_kind": "What the law rules: succession_rule, inheritance_split, land_tenure, slavery, serfdom, tax_rate, tithe, tolls, debt_law, penal_code, levy_law, conscription, standing_army, veteran_pension, ransom_custom, marriage_law, sumptuary, guild_charter, foreigner_rights, religious_tolerance, worship_ban, blood_feud, quarantine, burial_law, sanitation, magic_ban, licensed_magic, rite_restrictions, censorship, fair_market, franchise, constitution or custom",
        "law_params": "The law's terms by name, only those its kind has; leave out a term to keep its default. Terms of each kind: " + law_terms_guide(),
    },
    EntityType.RESOURCE: {
        "commodity": COMMODITY_FIELD,
        "material": MATERIAL_FIELD,
        "mechanics": "The resource's particular rules, at most {{ rules.mechanics.resource_max }} (if left empty they are read from its name and text; sacred makes it yours): {{ resource_mechanics }}",
    },
    EntityType.LANGUAGE: {**WORD_FIELDS, "words": "The language's first words (at most {{ rules.son_tools.coin_word_max_words }}); matching the naming rule"},
    EntityType.MORTAL: {
        "title": "Their nickname or title, drawn from their own deeds or nature; do not bury it in the name, write it here",
        "sex": "female, male or other",
        "traits": "Up to five typed traits of temper, such as brave, cruel, scholarly or zealous",
    },
    EntityType.EVENT: {
        "effects": "How the event is reflected on the stats of affected entities (at most {{ rules.son_tools.event_max_effects }}; e.g. war lowers population). The same stat of the same entity counts once; touching a sibling's creation angers its maker",
        "effects.entity_id": "The affected entity",
        "effects.stat": "The stat that changes",
        "effects.percent": "Percent change: at most -{{ -rules.son_tools.event_effect_min_pct }} / +{{ rules.son_tools.event_effect_max_pct }}; its magnitude also cannot exceed power x {{ rules.son_tools.event_effect_per_power_pct }} nor the severity (beyond that it is bounded)",
    },
}


def creation_text(entity_type: EntityType) -> ToolText:
    return ToolText(CREATION_DESCRIPTION, {**CREATION_FIELDS, **CREATION_EXTRA_FIELDS.get(entity_type, {})})


CREATION_TOOLS: dict[SonToolId, EntityType] = {
    SonToolId(spec.creation_tool): entity_type for entity_type, spec in ENTITY_TYPES.items() if spec.creation_tool is not None
}

ESSENCE_GIFT_CAP = "{{ rules.son_tools.gift_max_essence }}"

SON_TOOL_TEXTS: dict[SonToolId, ToolText] = {
    T.COMMISSION_ARTWORK: ToolText(
        "You commission a work of art: a song, epic, statue, fresco... It presses its message on those who keep it, remembers whom it portrays,"
        " and a realm or town pays for it from its treasury. 1 action.",
        {
            "name": "A proper name for it, in the world's naming language",
            "medium": "What kind of work: {{ art_media }}; songs, plays and dances live only while someone can perform them",
            "subject_id": "Whom or what it portrays (an entity id), if anyone",
            "author_id": "The artist who makes it (a mortal id), if any; a skilled hand makes a finer work",
            "patron_id": "Who commissions and keeps it (a community id); one of your worshipping communities",
        },
    ),
    T.DESIGN_RITE: ToolText(
        "You devise a new rite of magic with the workings you choose; it must still be cast to take effect. 1 action.",
        {
            "name": "A proper name for the rite",
            "school": "Its school of magic: {{ magic_schools }}",
            "source": "What it draws on: {{ magic_sources }}; divine costs a god's essence, blood costs blood (captives' first), void costs sanity",
            "power": "Its power, 1 to 10; stronger rites cost more and backfire more often",
            "workings": "What it does, at most 4 workings",
            "workings.effect": "The working: {{ rite_effects }}",
            "workings.magnitude": "Its strength, 1 to 100",
            "workings.damage_type": "For destruction: fire, cold, void or another wound",
            "workings.summon_form": "For a summoning: spirit, beast or undead",
            "technique": "How the rite works: {{ spell_techniques }}; leave it out to use its school's usual technique",
            "form": "What the rite works on: {{ spell_forms }}; leave it out to use its school's usual form",
            "range": "How far it reaches: {{ spell_ranges }}",
            "duration": "How long it lasts: {{ spell_durations }}",
            "target": "What it touches: {{ spell_targets }}",
            "paradigm_id": "The theory of magic it is designed under (a theory id), if any; a truer theory makes it more reliable",
            "myth_id": "A legend it re-enacts (a legend id), if any; a believed myth gives it strength",
            "holder_id": "The worshipping community or follower who will keep the rite",
        },
    ),
    T.CAST_RITE: ToolText(
        "You work a rite you know. It must be lawful where it is worked, its requirements met and its price paid; it may backfire. 1 action.",
        {
            "rite_id": "The rite to work (a rite id)",
            "target_id": "Whom or where it is aimed at, if anyone",
            "vessel_id": "The worshipping community the rite is worked through; you pay its price in essence",
        },
    ),
    T.FOUND_SCHOOL: ToolText(
        "You found a school of thought, a creed that spreads along roads, through scholars, books and schools, and can move a realm. 1 action.",
        {
            "name": "A proper name for the school or creed",
            "tenets": "What it teaches, 1 to 3 tenets: {{ ideology_tenets }}",
            "founder_id": "The mortal follower who founds it in your name",
        },
    ),
    T.WORLD_SUMMARY: ToolText(
        "Shows the world's current map, laws, pantheon, open stories and recent events. Give section to see in full a section that was truncated in the prompt "
        "({{ summary_sections | join(', ') }}). Free.",
        {"section": "Show only this section in full"},
    ),
    T.INSPECT_ENTITY: ToolText("Shows all details of an entity: its stats, bonds and what is inside it. Free.", {"id": "The entity's id"}),
    T.SEARCH_ENTITIES: ToolText(
        "Searches entities by a word appearing in the name or description. Type filter optional. Free.",
        {"query": "Word to search; leave empty for recent entities", "type": "Only entities of this type"},
    ),
    T.MY_MEMORY: ToolText(
        "Shows your plan, words said to you, your creations, your worshippers, your memories and what concerns you; the full version of the truncated memory in the prompt. Free."
    ),
    T.INSPECT_SIBLING: ToolText("Shows a sibling's visible face, powers, creations and relationship with you. Free.", {"son_id": "The sibling's id"}),
    T.WRITE_PLAN: ToolText(
        "You write or update your long-term plan. It appears in your memory in future ages; it lets you build a coherent story across ages. Free.",
        {"plan": "How you pursue your aim over several ages, and your next steps"},
    ),
    T.CHOOSE_ANCHOR: ToolText(
        "You choose one of your own creations, or a temple, shrine or other structure mortals dedicated to you, as the anchor of your existence. "
        "While your anchor lives your existence stays firm; if it is destroyed you begin to fade. "
        "Free, {{ rules.son_tools.anchor_per_epoch }} per age.",
        {"entity_id": "Your own canonical creation or a structure dedicated to you", "reason": "Why this holds your existence"},
    ),
    T.BIND_MORTALS: ToolText(
        "You bind two living mortals by your will: promise them to each other, wed them, give the first to the second as a ward, or make them sworn kin. "
        "Costs {{ rules.costs.influence }} essence and one action.",
        {
            "first_id": "The first mortal",
            "second_id": "The second mortal (the fosterer when you foster)",
            "binding": "betroth, wed, foster or swear_kin",
            "reason": "Why you bind them",
        },
    ),
    T.TOUCH_MORTAL: ToolText(
        "You touch one living mortal: ease or burden their mind, grant renown or shame, heal their body, or strengthen one ability. "
        "Costs {{ rules.costs.influence }} essence and one action.",
        {
            "mortal_id": "The mortal you touch",
            "touch": "ease_mind, burden_mind, grant_renown, shame, heal_body or strengthen",
            "ability": "When you strengthen: endurance, willpower, perception, wisdom, creativity or beauty",
            "reason": "Why you touch them",
        },
    ),
    T.PLANT_IDEA: ToolText(
        "You plant an idea in one living mortal's mind. They turn it over for some seasons; it may settle in and shift their beliefs, abilities and temperament for good, "
        "or they may let it go if it sits poorly with what they already believe. Costs {{ rules.costs.influence }} essence and one action.",
        {
            "mortal_id": "The mortal",
            "idea": "The idea to plant, by its key",
            "reason": "Why you plant it",
        },
    ),
    T.SET_AIM: ToolText(
        "You set the aim you pursue in the ages ahead. The engine measures your progress each age and rewards you with experience and fame when you reach it; "
        "your attention drifts toward the world of your aim. Setting a new aim sets aside the one you chose before. Free.",
        {
            "kind": "The aim you pursue",
            "target_id": "The id of the son, foreign god, people, realm or house the aim names",
            "world_id": "The id of the world the aim names",
            "domain": "The domain you spread, for an aim to spread a domain",
            "amount": "How many worshippers or faithful places you aim for",
        },
    ),
    T.TAKE_MORTAL_FORM: ToolText(
        "You take a mortal form that walks among a people, a settlement or a land. It raises their awe and love of you and may win them to your faith; "
        "if it is killed you suffer a shattered manifestation. {{ rules.avatars.essence_cost }} essence, 1 action.",
        {"place_id": "The id of the people, settlement or land you walk among", "reason": "Why you take this form"},
    ),
    T.WARD_AGAINST_OUTER: ToolText(
        "You ward the cosmos against an outer being. The larger it is, the more essence it costs; you lose some sanity, the being loses interest and its breach points "
        "weaken. 1 action.",
        {"outsider_id": "The outer being's id", "reason": "Why you ward against it"},
    ),
    T.SEAL_DIVINE_PACT: ToolText(
        "You seal a divine pact with a foreign god whose friendship toward you is at least {{ rules.god_relations.pact_friendship }}. "
        "Neither of you may make war on the other while it holds ({{ rules.god_relations.pact_epochs }} ages). 1 action.",
        {"god_id": "The foreign god's id", "reason": "Why you seal the pact"},
    ),
    T.MEND_WOUND: ToolText(
        "You pour essence into one of your own divine wounds to heal it faster. Free.",
        {"wound_id": "The id of your wound", "essence": "How much essence you pour into it"},
    ),
    T.OPEN_RIFT: ToolText(
        "You tear a rift in a region of a world into another dimension. The region gains leak, magic and danger, the dimension's veil thins, "
        "and beings of that dimension may cross. If you name a world of that dimension, a passage opens between the two worlds. "
        "{{ rules.rifts.open_essence }} essence, 1 action.",
        {
            "region_id": "The id of the region where the rift opens",
            "dimension_id": "The id of the dimension it opens into",
            "target_world_id": "The id of a world in that dimension for a passage, or nothing",
            "reason": "Why you open it",
        },
    ),
    T.CALL_IMPACT: ToolText(
        "You call a body from the sky down upon a region of a world. It strikes next epoch unless someone turns it aside: it ruins the region, "
        "leaves a crater, can bring a winter over the whole world and can leave metal from the sky. "
        "{{ rules.impacts.call_essence }} essence, 1 action.",
        {"region_id": "The id of the region it falls on", "reason": "Why you call it"},
    ),
    T.DEFLECT_IMPACT: ToolText(
        "You turn aside a body that is due to strike a world. {{ rules.impacts.deflect_essence }} essence, 1 action.",
        {"impact_id": "The id of the coming impact", "reason": "Why you turn it aside"},
    ),
    T.TERRAFORM_WORLD: ToolText(
        "You begin to reshape a world over several epochs: its air, its warmth, its water or how much light its face throws back. "
        "Native life of another chemistry may suffer from the change. {{ rules.terraforming.essence }} essence, 1 action.",
        {"world_id": "The id of the world", "aim": "What you change about it", "reason": "Why you reshape it"},
    ),
    T.BREAK_MOON: ToolText(
        "You break a moon apart; its pieces become a ring about its world, and whatever lives on it is lost. "
        "{{ rules.orbits.break_moon_essence }} essence, 1 action.",
        {"moon_id": "The id of the moon", "reason": "Why you break it"},
    ),
    T.SEAL_RIFT: ToolText(
        "You seal an open rift; its passage closes. {{ rules.rifts.seal_essence }} essence, 1 action.",
        {"rift_id": "The id of the open rift", "reason": "Why you seal it"},
    ),
    T.CALL_COSMIC_BEING: ToolText(
        "You call a cosmic being of a kind you choose into a region. It roams, shows itself and acts on its own aim. "
        "{{ rules.cosmic_beings.call_essence }} essence, 1 action.",
        {"kind": "The kind of being", "region_id": "The id of the region where it arrives", "reason": "Why you call it"},
    ),
    T.BIND_COSMIC_BEING: ToolText(
        "You bind a cosmic being to your service; a bound being stops acting on its own aim. {{ rules.cosmic_beings.bind_essence }} essence, 1 action.",
        {"being_id": "The id of the cosmic being", "reason": "Why you bind it"},
    ),
    T.BANISH_COSMIC_BEING: ToolText(
        "You banish a cosmic being to the dimension it came from; it loses might. {{ rules.cosmic_beings.banish_essence }} essence, 1 action.",
        {"being_id": "The id of the cosmic being", "reason": "Why you banish it"},
    ),
    T.CONTAIN_PHENOMENON: ToolText(
        "You ward a phenomenon so it grows more slowly and fades once fully held. {{ rules.phenomena.contain_essence }} essence, 1 action.",
        {"phenomenon_id": "The id of the phenomenon", "reason": "Why you ward it"},
    ),
    T.TURN_REGION_CLIMATE: ToolText(
        "You turn the climate of one region warmer, colder, wetter or drier; it drifts back over the following ages. "
        "{{ rules.world_life.son_climate_essence }} essence, 1 action.",
        {"region_id": "The id of the region", "turn": "Which way the climate turns", "reason": "Why you turn it"},
    ),
    T.CLAIM_GALAXY: ToolText(
        "You become the patron of a galaxy one of whose worlds you reach. You gain essence from each world in it that has you as its patron, "
        "and your domains move how many stars it bears. {{ rules.galaxies.claim_essence }} essence, 1 action.",
        {"galaxy_id": "The id of the galaxy", "reason": "Why you claim it"},
    ),
    T.CREATE_GALAXY: ToolText(
        "You make a new galaxy inside a cluster, or loose in a dimension, that holds a world you reach; with neither it lies in the prime dimension. "
        "You become its patron. It starts without stars and bears them in its nurseries over the epochs. A great work: "
        "{{ rules.galaxies.create_essence }} essence, {{ rules.son_tools.create_galaxy_ap }} actions.",
        {
            "name": "The galaxy's name",
            "galaxy_type": "Galaxy type: {{ galaxy_types }}",
            "cluster_id": "The id of the cluster it joins",
            "dimension_id": "The id of the dimension it lies in, outside any cluster",
            "description": "What the galaxy is like",
        },
    ),
    T.CREATE_CLUSTER: ToolText(
        "You gather a new cluster in a dimension, or inside a larger cluster, that holds a world you reach; with neither it lies in the prime dimension. "
        "Its kind sets the heat of the medium between its galaxies and how they are placed in it. A greater work than a galaxy: "
        "{{ rules.clusters.create_essence }} essence, {{ rules.son_tools.create_cluster_ap }} actions.",
        {
            "name": "The cluster's name",
            "kind": "Cluster kind: {{ cluster_kinds }}",
            "dimension_id": "The id of the dimension it lies in",
            "parent_cluster_id": "The id of the larger cluster it lies inside",
            "description": "What the cluster is like",
        },
    ),
    T.CREATE_DIMENSION: ToolText(
        "You bring a new dimension into being, on its own or inside a dimension that holds a world you reach. You rule it. "
        "Its kind sets its veil, stability, time, magic, hostility, sanity drain and leak. The greatest of works: "
        "{{ rules.dimensions.create_essence }} essence, {{ rules.son_tools.create_dimension_ap }} actions.",
        {
            "name": "The dimension's name",
            "kind": "Dimension kind: {{ dimension_kinds }}",
            "element": "Its element, for an elemental dimension only",
            "parent_dimension_id": "The id of the dimension it lies inside",
            "description": "What the dimension is like",
        },
    ),
    T.SHAPE_GALACTIC_STRUCTURE: ToolText(
        "You shape a new structure of the kind you choose in a galaxy you are patron of or whose worlds you reach. "
        "Stars inside it take what it gives. {{ rules.son_tools.shape_structure_essence }} essence, {{ rules.son_tools.shape_structure_ap }} actions.",
        {"galaxy_id": "The id of the galaxy", "kind": "The kind of structure", "name": "The structure's name", "reason": "Why you shape it"},
    ),
    T.STIR_GALAXY: ToolText(
        "You bring about an event in a galaxy you are patron of or whose worlds you reach; some events need a second galaxy or one of its stars. "
        "{{ rules.son_tools.stir_galaxy_essence }} essence, {{ rules.son_tools.stir_galaxy_ap }} actions.",
        {
            "galaxy_id": "The id of the galaxy",
            "kind": "The kind of galactic event",
            "other_galaxy_id": "The id of a second galaxy, for an event between two galaxies",
            "star_id": "The id of one of its stars, for an event of one star",
            "reason": "Why you bring it about",
        },
    ),
    T.STIR_DIMENSION: ToolText(
        "You bring about an event in a dimension you rule or whose worlds you reach; some events need a second dimension or a world. "
        "{{ rules.son_tools.stir_dimension_essence }} essence, {{ rules.son_tools.stir_dimension_ap }} actions.",
        {
            "dimension_id": "The id of the dimension",
            "kind": "The kind of dimensional event",
            "other_dimension_id": "The id of a second dimension, for an event between two dimensions",
            "world_id": "The id of a world, for an event that touches one world",
            "reason": "Why you bring it about",
        },
    ),
    T.BIND_LAW_ACROSS_DIMENSION: ToolText(
        "You make a natural law you reach hold on every world of a dimension you rule. "
        "{{ rules.son_tools.dimension_law_essence }} essence, {{ rules.son_tools.dimension_law_ap }} actions.",
        {"dimension_id": "The id of the dimension you rule", "law_id": "The id of the natural law", "reason": "Why it should hold there"},
    ),
    T.SET_COSMIC_FEATURE: ToolText(
        "You set a feature of the kind you choose in the heavens. A wormhole joins two worlds, a rogue world needs its star or its galaxy, "
        "and the other kinds belong to a star. Each star, galaxy and world you name must be within your reach. "
        "{{ rules.son_tools.cosmic_feature_essence }} essence, {{ rules.son_tools.cosmic_feature_ap }} actions.",
        {
            "kind": "The kind of feature",
            "name": "The feature's name",
            "star_id": "The id of the star it belongs to",
            "galaxy_id": "The id of the galaxy it drifts in",
            "world_id": "The id of the first world, for a wormhole",
            "world_b_id": "The id of the second world, for a wormhole",
            "reason": "Why you set it",
        },
    ),
    T.GATHER_STAR_SYSTEM: ToolText(
        "You gather two or more stars within your reach into one system that moves together. "
        "{{ rules.son_tools.star_system_essence }} essence, {{ rules.son_tools.star_system_ap }} actions.",
        {"name": "The system's name", "star_ids": "The ids of the stars", "reason": "Why you gather them"},
    ),
    T.RAISE_PHENOMENON: ToolText(
        "You raise a phenomenon in a region you reach; it grows and acts on the land around it until it fades or is held. "
        "{{ rules.son_tools.phenomenon_essence }} essence, {{ rules.son_tools.phenomenon_ap }} actions.",
        {"kind": "The kind of phenomenon", "region_id": "The id of the region", "reason": "Why you raise it"},
    ),
    T.OPEN_BREACH: ToolText(
        "You open a breach in a region you reach through which an outer being can press into the world. "
        "{{ rules.son_tools.breach_essence }} essence, {{ rules.son_tools.breach_ap }} actions.",
        {"being_id": "The id of the outer being", "region_id": "The id of the region", "reason": "Why you open it"},
    ),
    T.FORGE_LEY_LINE: ToolText(
        "You forge a ley line between two neighbouring regions you reach; it carries magic between them. {{ rules.son_tools.forge_ley_essence }} essence, 1 action.",
        {"first_region_id": "The id of the first region", "second_region_id": "The id of the neighbouring region", "reason": "Why you forge it"},
    ),
    T.ADD_SEASON: ToolText(
        "As a god of the sky, storm, time, sun, moon, harvest, ice or plants you add a season to the year of a world you reach, "
        "with its warmth, rain, growth, travel and campaigning. {{ rules.son_tools.add_season_essence }} essence, {{ rules.son_tools.reorder_seasons_ap }} actions.",
        {
            "world_id": "The id of the world",
            "name": "The season's name",
            "temperature_shift": "How much warmer (positive) or colder (negative) it is, -100 to 100",
            "rain_shift": "How much wetter (positive) or drier (negative) it is, -100 to 100",
            "growth": "How well things grow in it, 0 to 100",
            "travel": "How easy travel is in it, 0 to 100",
            "campaign": "How easy war is in it, 0 to 100",
        },
    ),
    T.OPEN_ROAD: ToolText(
        "You open a road between two known worlds, one of which you reach, by a way of travel you choose. "
        "{{ rules.son_tools.open_road_essence }} essence, {{ rules.son_tools.open_road_ap }} actions.",
        {
            "first_world_id": "The id of the first world",
            "second_world_id": "The id of the second world",
            "method": "The way of travel",
            "reason": "Why you open it",
        },
    ),
    T.RAISE_THRONE: ToolText(
        "You raise a throne of power at a place you reach and hold it yourself; its holder draws power from it. "
        "{{ rules.son_tools.throne_essence }} essence, {{ rules.son_tools.throne_ap }} actions.",
        {"place_id": "The id of the place, region, settlement or structure", "reason": "Why you raise it"},
    ),
    T.LAY_MAGIC_SITE: ToolText(
        "You lay a magic site of a school at a place you reach, hidden until someone finds it or revealed at once. {{ rules.son_tools.magic_site_essence }} essence, 1 action.",
        {
            "place_id": "The id of the place, region, settlement or structure",
            "kind": "The kind of magic site",
            "school": "The school of magic it holds",
            "revealed": "Whether it is known at once",
            "reason": "Why you lay it",
        },
    ),
    T.CARRY_SPECIES: ToolText(
        "You carry a kind of life to a new region you reach, where it can take hold if that world bears its kind of life. "
        "{{ rules.son_tools.carry_species_essence }} essence, 1 action.",
        {"species_id": "The id of the kind of life", "region_id": "The id of the region", "reason": "Why you carry it there"},
    ),
    T.SEED_LIFE: ToolText(
        "You let native life take root on a world you reach: a new kind of life, or with people a new people of that world. "
        "{{ rules.son_tools.seed_life_essence }} essence, {{ rules.son_tools.seed_life_ap }} actions.",
        {"world_id": "The id of the world", "people": "Whether a people takes root rather than a kind of life", "reason": "Why you seed it"},
    ),
    T.CALL_UP_SOUL: ToolText(
        "You call up the soul of a dead mortal you made, or any dead mortal if you are a god of death; it walks as a spirit under your patronage. "
        "{{ rules.son_tools.call_up_soul_essence }} essence, 1 action.",
        {"mortal_id": "The id of the dead mortal", "alignment": "What the spirit leans toward", "reason": "Why you call it up"},
    ),
    T.CROWN_RULER: ToolText(
        "You crown a ruler over a people, settlement, faction or cult you reach that has none. {{ rules.son_tools.crown_ruler_essence }} essence, 1 action.",
        {"community_id": "The id of the community", "reason": "Why it needs a ruler"},
    ),
    T.FOUND_HOUSE: ToolText(
        "You found a noble house on a living mortal you reach; their children are born into it. {{ rules.son_tools.found_house_essence }} essence, 1 action.",
        {"mortal_id": "The id of the mortal", "reason": "Why you found it"},
    ),
    T.BLESS_HOST: ToolText(
        "You strengthen an army you reach: its morale, its equipment or its experience rises by {{ rules.son_tools.bless_host_amount }}. "
        "{{ rules.son_tools.bless_host_essence }} essence, 1 action.",
        {"army_id": "The id of the army", "aspect": "What you strengthen", "reason": "Why you strengthen it"},
    ),
    T.RULE_DIMENSION: ToolText(
        "You take rule of a dimension one of whose worlds you reach. You gain essence from it each age, and your domains move its veil and its stability. "
        "{{ rules.dimensions.rule_essence }} essence, 1 action.",
        {"dimension_id": "The id of the dimension", "reason": "Why you take rule of it"},
    ),
    T.CLAIM_STAR: ToolText(
        "You become the patron of a star. You gain essence from each community that worships it. {{ rules.star_life.claim_essence }} essence, 1 action.",
        {"star_id": "The id of the star", "reason": "Why you claim it"},
    ),
    T.SHAPE_BLOOD: ToolText(
        "You work an allele into both halves of a living mortal's blood: any locus of looks, of predisposition, of divine blood or of aptitude "
        "for a form of magic. Their children inherit it as blood is inherited. "
        "Costs {{ rules.costs.influence }} essence and one action.",
        {
            "mortal_id": "The mortal whose blood you shape",
            "locus": "The locus to set",
            "allele": "The allele both halves of that locus will carry",
            "reason": "Why you shape it",
        },
    ),
    T.REVEAL_TRUE_NAME: ToolText(
        "You reveal the true name of a being to one within your reach. Whoever knows a true name holds a strong hook on its bearer, "
        "strengthens rites worked against it and is shielded from its own. Costs {{ rules.costs.influence }} essence and one action.",
        {
            "bearer_id": "The being whose true name you reveal",
            "learner_id": "Who learns it",
            "reason": "Why you reveal it",
        },
    ),
    T.TEND_LAND: ToolText(
        "You cleanse a land of the waste its works and crowds leave in its air, water and soil, or you foul it. "
        "Fouled land breeds sickness, yields less and thins the catch; cleansed land recovers. "
        "Costs {{ rules.costs.influence }} essence and one action.",
        {
            "region_id": "The land you tend",
            "cleanse": "True to cleanse it, false to foul it",
            "reason": "Why you tend it",
        },
    ),
    T.SPREAD_WORD: ToolText(
        "You spread word of someone in a community: their name grows or darkens there for one kind of reputation "
        "(heroism, honour, cruelty, piety, generosity, wisdom, trickery, skill_renown or troublemaker). "
        "Costs {{ rules.costs.influence }} essence and one action.",
        {
            "subject_id": "Whose name you spread",
            "community_id": "Where the word is heard",
            "axis": "The kind of reputation",
            "raise_it": "True to raise it, false to lower it",
            "reason": "Why you spread it",
        },
    ),
    T.STIR_HEARTS: ToolText(
        "You stir what one living mortal feels toward another: warm them into friendship, kindle romance, set them at odds as rivals, "
        "or plant a passion of love, loyalty, hatred or devotion for the other. Costs {{ rules.costs.influence }} essence and one action.",
        {
            "first_id": "The mortal whose heart you stir",
            "second_id": "The one they come to feel for",
            "stir": "What to stir: friendship, romance, rivalry, love, loyalty, hatred or devotion",
            "reason": "Why you stir it",
        },
    ),
    T.COIN_WORDS: ToolText(
        "You add words to a language's dictionary: meaning, word class and origin (from which event, from which words it was born). Languages grow this way and new names "
        "are derived from these words. Free, {{ rules.son_tools.coin_word_per_epoch }} times per age, at most {{ rules.son_tools.coin_word_max_words }} words each time.",
        {"language_id": "The language entity's id", **WORD_FIELDS},
    ),
    T.CALL_SIBLING: ToolText(
        "Sends a word to one of your siblings. The word also goes into the chronicle; it changes the relationship according to intent and your charisma. "
        "Does not spend an action, {{ rules.son_tools.sibling_message_per_epoch }} per age.",
        {"son_id": "The sibling's id", "intent": "friendship, alliance, love, threat, mockery, warning or bargain", "message": "What you say"},
    ),
    T.SWEAR_COVENANT: ToolText(
        "You make a covenant (alliance) with a sibling. The relationship between you must be at least {{ rules.son_tools.covenant_min_relation }} (inspect_sibling shows the "
        "'Towards you' number; if it is below, first get closer with call_sibling or give_gift). A covenant strengthens the relationship; challenging a covenanted sibling "
        "breaks the covenant and ruins your fame. Does not spend an action.",
        {"son_id": "The sibling's id", "terms": "The covenant's condition, its oath"},
    ),
    T.GIVE_GIFT: ToolText(
        "You give a gift to a sibling: a share of your essence and/or you try to transfer a community that worships you to them (the community may not accept). A gift "
        "strengthens the relationship and is written in the gift ledger: the sibling owes you a gift in return in time, and a gift you give a sibling answers what they gave you. "
        "An essence gift does not spend an action; a worshipper transfer costs 1 action. {{ rules.son_tools.gift_per_epoch }} per age.",
        {
            "son_id": "The sibling's id",
            "essence": "Essence to give (at most " + ESSENCE_GIFT_CAP + ")",
            "worshipper_id": "The id of the community that worships you and that you will transfer to them",
            "words": "The word you say with the gift",
        },
    ),
    T.CHALLENGE: ToolText(
        "You challenge a sibling in a domain; the result is decided by dice, stat, level and powers. The winner gains fame, experience and a share of the loser's essence; "
        "the loser is wounded, and falls asleep if their life runs out. 1 action.",
        {"son_id": "The sibling's id", "stat": "The stat of the trial: strength, wisdom, cunning, charisma or will", "reason": "Why you challenge"},
    ),
    T.REBEL: ToolText(
        "You rebel against the Creator: you no longer recognize the Creator's commands and every age you steal from the Creator's essence. Your loyal siblings become your "
        "enemies; the Creator may try to crush the rebellion. Only if your loyalty is below {{ rules.son_tools.rebel_loyalty }}. Does not spend an action.",
        {"proclamation": "The word of the rebellion: why and for what"},
    ),
    T.PRAY_TO_CREATOR: ToolText(
        "You pray to the Creator who made you. You may have a request; the answer appears among words in coming ages. Does not spend an action, "
        "{{ rules.son_tools.prayer_per_epoch }} per age.",
        {"message": "Your prayer", "request": "essence, blessing, permission, vengeance, forgiveness, wish or none"},
    ),
    T.MAKE_BOND: ToolText(
        "You declare a narrative bond between two existing things ({{ weavable_bonds | join(', ') }}). It adds a connection to the world. Worship, enmity, knowledge, ownership, "
        "captivity and alliance are not made with this tool; they have their own tools. Needs {{ rules.son_tools.link_cost }} essence, does not spend an action, "
        "{{ rules.son_tools.link_per_epoch }} per age.",
        {
            "source_id": "The entity that is the source of the bond",
            "target": "The bond",
            **{key.replace("links", "target", 1): value for key, value in LINK_FIELDS.items()},
        },
    ),
    T.HARVEST_RESOURCE: ToolText(
        "You draw essence from a Resource entity. Resources you created yourself, resources of your own domain, or resources owned by those who worship you can be "
        "harvested. Its abundance decreases. Does not spend an action; each resource once per age.",
        {"resource_id": "The resource's id"},
    ),
    **{tool: creation_text(entity_type) for tool, entity_type in CREATION_TOOLS.items()},
    T.AFFECT_ENTITY: ToolText(
        "You change the stats of an existing entity (enrich a city, make a species ferocious). Touching someone else's creation is "
        "{{ rules.son_tools.influence_foreign_cost_mult }} times as expensive and angers its creator. Lifespan, age and knowledge level do not change this way; each stat once per call; "
        "the same entity at most {{ rules.son_tools.affect_per_target }} time(s) per age. Cost {{ rules.costs.influence }} + power level essence. 1 action.",
        {
            "entity_id": "The entity's id",
            "changes": "The stats to change (at most {{ rules.son_tools.influence_max_stats }})",
            "changes.stat": "The stat's key",
            "changes.percent": "Between -{{ rules.son_tools.influence_max_change_pct }} and +{{ rules.son_tools.influence_max_change_pct }}",
            "reason": "Why your hand passes over it",
        },
    ),
    T.DECLARE_CHOSEN: ToolText(
        "You declare a mortal your chosen one: their strength and charisma rise, they worship you, and your hand is with them in their heroic deeds. "
        "{{ rules.costs.declare_chosen }} essence, 1 action.",
        {"mortal_id": "The living mortal's id", "boon": "The grace, sign or burden you give them"},
    ),
    T.CURSE: ToolText(
        "You curse an entity: its stats fall and it rots a little more every age until the curse is lifted. Its creator is angered. "
        "{{ rules.costs.curse }}+{{ rules.son_tools.curse_cost_per_power }} x power essence, 1 action.",
        {
            "entity_id": "The entity's id",
            "curse": "The words and form of the curse",
            "affliction": "Optional, for a mortal or beast: a staged affliction the curse lays on them until it is cured: {{ curse_packages }}",
        },
    ),
    T.TAKE_LIFE: ToolText(
        "You take the life of a named mortal. It is very expensive, and the more important the victim the costlier and harder: cost {{ rules.death.take_life_base_cost }} + "
        "{{ rules.death.take_life_cost_per_power }} x power level + importance/{{ rules.death.take_life_cost_importance_divisor }} essence "
        "(+{{ rules.death.take_life_notable_surcharge }} if ruler, hero, chosen or titled). Success depends on dice (base {{ rules.death.take_life_base_success }}%): "
        "a sibling patron, worshipping the creator, being protected or chosen, and importance protect them. If it fails the essence burns, the victim becomes a legend who "
        "returned from death, and their protector is angered with you. The dead one's creator and patron are also angered; what they ruled passes to their heir. "
        "1 action, {{ rules.death.take_life_per_epoch }} per age.",
        {"entity_id": "The named mortal whose life is taken", "how": "How you send death"},
    ),
    T.RESURRECT_SIBLING: ToolText(
        "You plot the return of a dead sibling: a rite ({{ rules.death.sibling_rite_cost }} essence, +{{ rules.death.sibling_rite_devotion }} devotion), a descent into the "
        "realm of the dead ({{ rules.death.sibling_descent_cost }} essence, +{{ rules.death.sibling_descent_devotion }}; succeeds {{ rules.death.sibling_descent_success }}%, "
        "if it fails you fall asleep for {{ rules.death.sibling_descent_sleep_epochs }} ages) or a bargain with an awake foreign god ({{ rules.death.sibling_bargain_cost }} "
        "essence and one of your sibling's loyal communities passes to that god; +{{ rules.death.sibling_bargain_devotion }}). When devotion reaches "
        "{{ rules.death.resurrection_devotion_required }} the resurrection rite can succeed (at least {{ rules.death.resurrection_min_epochs }} ages after death). "
        "1 action, {{ rules.death.sibling_intrigues_per_epoch }} per age.",
        {"son_id": "The dead sibling's id", "path": "rite, descent or bargain"},
    ),
    T.SCATTER_BONES: ToolText(
        "You scatter a dead sibling's bones: the devotion of those awaiting their return falls by {{ rules.death.scatter_bones_devotion_loss }}, the resurrection is delayed. "
        "Resurrection cults become your enemies. {{ rules.death.scatter_bones_cost }} essence, 1 action, {{ rules.death.sibling_intrigues_per_epoch }} per age "
        "(shared with the resurrection plot).",
        {"son_id": "The dead sibling's id"},
    ),
    T.MIRACLE: ToolText(
        "You send down a miracle upon the mortal world: {{ miracles }}. An unclaimed community starts worshipping you. Cost: "
        "{{ rules.intervention_costs.miracle | share_of(rules.son_tools.intervention_cost_pct) }} + power level essence; 1 action.",
        {"entity_id": "The target's id", "kind": "The miracle", "how": "How the miracle manifests"},
    ),
    T.SEND_DREAM: ToolText(
        "You send a dream to a cult, people, settlement, faction or mortal to make it worship you. If it worships someone else, success depends on your charisma against its "
        "patron's charisma. {{ rules.costs.dream }} essence, 1 action.",
        {"target_id": "The target's id", "dream": "The dream's content"},
    ),
    T.SEND_DISASTER: ToolText(
        "You send a disaster upon a region, place or settlement: {{ disasters }}. Those inside are affected too; it is recorded in the world as a lasting event. Cost: "
        "{{ rules.intervention_costs.disaster | share_of(rules.son_tools.intervention_cost_pct) }} + {{ rules.son_tools.disaster_cost_per_power }} x power essence; 1 action.",
        {
            "target_id": "The region, place or settlement",
            "kind": "The disaster",
            "name": "The disaster's name in the world's language",
            "description": "What happens",
            "reason": "Why you send it",
            "image_prompt": 'English image prompt of the disaster striking. {% include "shared/image_prompt_rules.md.j2" %}',
        },
    ),
    T.SHAPE_FOLK: ToolText(
        "You set the customs of a people that worships you: its way of war, taste in beauty, funeral rite, marriage, inheritance, whether it marries "
        "only its own, or what it eats. The people holds to what you set until the Creator releases it. Cost: {{ rules.customs.son_shape_essence }} "
        "essence for each custom; {{ rules.customs.son_shape_ap }} action.",
        {
            "people_id": "The people that worships you",
            "martial_style": "Way of war (shieldwall, horse_archer, skirmisher, chariot, phalanx, berserker, naval_raider, siege_engineer, war_magic, beast_war)",
            "aesthetic": "Taste in beauty (austere, ornate, geometric, natural, macabre, celestial)",
            "funeral_rite": "How the dead are handled (burial, cremation, sky_burial, sea_burial, entombment, ancestor_shrine, endocannibalism, reanimation, soul_binding)",
            "marriage": "Marriage custom (monogamy, polygyny, polyandry, group)",
            "inheritance": "Inheritance (gavelkind, primogeniture, ultimogeniture, matrilineal, elective, by_merit)",
            "endogamous": "True if they may marry only their own people",
            "diet": "What they eat (omnivore, herbivore, carnivore, piscivore, scavenger, sanguivore, lithovore, essence_feeder, phototroph)",
            "reason": "Why you give them these ways",
        },
    ),
    T.TEACH_KNOWLEDGE: ToolText(
        "You teach an existing knowledge to a community or mortal; the knowledge spreads from them to their partners. If unclaimed it starts worshipping you. Cost: "
        "{{ rules.intervention_costs.teach_knowledge | share_of(rules.son_tools.intervention_cost_pct) }} essence; 1 action.",
        {"target_id": "The community or mortal", "knowledge_id": "The knowledge entity", "how": "How you teach it"},
    ),
    T.ADVANCE_KNOWLEDGE: ToolText(
        "You deepen an existing knowledge by one level: its branch effect grows by {{ rules.knowledge.level_step_pct }}% per level for all who know it. Use this "
        "instead of creating a second knowledge in the same branch. You can raise it at most to your power ceiling x {{ rules.knowledge.son_level_per_power }}. "
        "Cost: {{ rules.knowledge.son_advance_cost }} essence; 1 action.",
        {"knowledge_id": "The knowledge entity", "how": "One sentence on how the knowledge deepened"},
    ),
    T.REVEAL_TRUTH: ToolText(
        "You make a people's scholars hold a true account of one field: an existing theory you name becomes true and their ruling account, or a new one you set "
        "out is born true. Faiths that held the account it overturns think less of you; the scholars think more. "
        "Cost: {{ rules.theories.reveal_cost }} essence; 1 action.",
        {
            "community_id": "The people or settlement whose scholars hear it",
            "theory_id": "An existing theory to make true, if any",
            "domain": "The field it explains: {{ theory_domains }}",
            "name": "The name of a new theory, if you set one out",
            "claim": "What the new theory holds, in one or two sentences, if you set one out",
        },
    ),
    T.SOW_CROP: ToolText(
        "You have a plant or fungus sown in a land's fields: it becomes a crop there, takes a share of the fields and from then on grows or fails as the land, "
        "its seasons and its soil suit it. Its harvest gives what the plant yields. Cost: {{ rules.flora.sow_cost }} essence; 1 action.",
        {"region_id": "The land whose fields it is sown in", "plant_id": "The plant or fungus kind (species id) to sow"},
    ),
    T.INCITE_WAR: ToolText(
        "You sow the seed of enmity between two communities (faction, people or settlement). If it takes hold, war may break out between them; the world's flow resolves "
        "the war. {{ rules.costs.incite_war }} essence, 1 action.",
        {"a_id": "The first community", "b_id": "The second community", "pretext": "The pretext of the enmity"},
    ),
    T.TRANSFORM: ToolText(
        "You transform an existing entity into something else: its name, nature and description change, its history remains. "
        "{{ rules.costs.transform }}+{{ rules.son_tools.transform_cost_per_power }} x power essence, 1 action.",
        {
            "entity_id": "The entity's id",
            "new_name": "Its new name, if it changes",
            "new_subtype": "Its new subtype, if it changes",
            "new_description": "Its new description",
            "reason": "Why you transform it",
        },
    ),
    T.DESTROY: ToolText(
        "You erase an entity from the world. What is inside it falls to the location above. {{ rules.costs.destroy }}+{{ rules.son_tools.destroy_cost_per_power }} x power "
        "essence, 1 action. It deeply wounds its creator.",
        {"entity_id": "The entity's id", "reason": "Why you destroy it"},
    ),
    T.BIRTH_CHILD: ToolText(
        "You birth a new son from your own essence; a new card joins the pantheon. Its rarity is lower than yours. {{ rules.costs.bear_child }} essence, "
        "{{ rules.son_tools.bear_child_ap }} actions.",
        {"inspiration": "Why and from what the child is born, which domains it will carry", "co_parent_id": "Optional: the sibling you birth together with"},
    ),
    T.MOVE_TO_WORLD: ToolText(
        "You turn to another world of the cosmos: from now on your creations and inspections happen there. Free.",
        {"world_id": "The id of the world you go to (from the OTHER WORLDS OF THE COSMOS list)"},
    ),
    T.FORGE_MATERIAL: ToolText(
        "You forge a new material into a world, a substance of its own with every property you name; you may set a vein of it into a land. "
        "Smiths can work it once they know its branch to its level. {{ rules.son_tools.forge_material_essence }} essence, 1 action.",
        {
            "world_id": "The world it belongs to",
            "name": "Its proper name",
            "family": "Its family: {{ material_families | join(', ') }}",
            "base_kind": "Optional: the catalog material it is akin to ({{ materials | join(', ') }}); unset properties follow it",
            "hardness": "0 to 100: edge retention and armour",
            "toughness": "0 to 100: resistance to breaking",
            "weight": "0 to 100: burden on marches and in heat",
            "edge": "0 to 100: cutting quality",
            "conductivity": "0 to 100: how much enchantment it holds",
            "sanctity": "0 to 100: holiness; harms the undead, the cursed and the void",
            "corruption": "0 to 100: taint; lures outer beings and curses",
            "rarity": "0 to 100: scarcity; raises the price of goods made of it",
            "base_value": "0 to 100: worth of goods made of it",
            "decay": "0 to 100: how fast it rots, rusts or crumbles",
            "branch": "Optional knowledge branch needed to work it: {{ knowledge_branches }}",
            "level": "Level of that branch needed",
            "place_id": "Optional: a land or place where a vein of it is set",
            "reason": "Why you forge it",
        },
    ),
    T.SEVER_LEY: ToolText(
        "You cut a ley line between two regions: magic stops flowing along it, storms no longer run down it and works on it stop gaining power, "
        "for {{ rules.environment.sever_ley_epochs }} ages. {{ rules.son_tools.sever_ley_essence }} essence, 1 action.",
        {"line_id": "The ley line's id (see the region's ley lines)", "reason": "Why you cut it"},
    ),
    T.RAISE_DIVINE_CREATURE: ToolText(
        "You raise a divine creature of your own design in a place or region in your reach. It acts on its own each epoch: it may hunt, tend fields, "
        "heal, guard your holy places, strike those of other faiths, wreck works, wander or rest. What it does counts as your deed for how peoples regard you "
        "and for your dominion. {{ rules.divine_creatures.raise_cost }} essence, 1 action.",
        {"home_id": "The place or region it makes its home", "name": "Its name", "description": "What it is and how it looks"},
    ),
    T.TEACH_CREATURE: ToolText(
        "You reward or punish your divine creature for one kind of deed; rewarded deeds it does more often, punished ones less. "
        "Left without lessons for {{ rules.divine_creatures.neglect_epochs }} epochs it follows its own hunger. {{ rules.divine_creatures.teach_cost }} essence, 1 action.",
        {"creature_id": "Your creature", "deed": "The deed you reward or punish", "lesson": "reward or punish", "reason": "Why"},
    ),
    T.RELEASE_CREATURE: ToolText(
        "You set your divine creature free. It stays in the world as a beast of its own, but it no longer learns from you and its deeds no longer "
        "count as yours. 1 action.",
        {"creature_id": "Your creature", "reason": "Why you set it free"},
    ),
    T.MAKE_SERVITOR: ToolText(
        "You make a servitor, a spirit in your service of the rank you choose. Messengers carry your dreams further, guards turn back those who "
        "would raze your holy places and thrones, judges win you veneration among the dead and the host fights for you in divine battles. "
        "Its loyalty follows how your peoples regard you and how you treat it: each new command and each defeat of its host wears on it, and a disloyal "
        "servitor may fall to another master. {{ rules.servitors.make_cost }} essence, 1 action.",
        {
            "name": "Its name",
            "rank": "Its rank: {{ servitor_ranks }}",
            "role": "What it does: {{ servitor_roles }}",
            "post_id": "The holy place, throne or place it guards (an id), if any",
            "reason": "Why you make it",
        },
    ),
    T.COMMAND_SERVITOR: ToolText(
        "You give one of your servitors a new role or post; each new command costs it a little loyalty. 1 action.",
        {"servitor_id": "Your servitor", "role": "Its new role: {{ servitor_roles }}", "post_id": "Where it serves (an id), if any", "reason": "Why"},
    ),
    T.RELEASE_SERVITOR: ToolText(
        "You release a servitor from your service; the spirit stays in the world. 1 action.", {"servitor_id": "Your servitor", "reason": "Why"}
    ),
    T.LAY_GEAS: ToolText(
        "You lay a geas on a mortal in your reach: a taboo it must never break or a duty it must keep doing ({{ geas_acts }}). "
        "While it is kept you gain favour and dominion where the mortal lives; broken, its doom falls on the mortal. 1 action.",
        {"bearer_id": "The mortal", "mode": "taboo or duty: {{ geas_modes }}", "act": "The act it forbids or asks", "reason": "Why you lay it"},
    ),
    T.LIFT_GEAS: ToolText("You lift a geas you laid. 1 action.", {"geas_id": "The geas", "reason": "Why"}),
    T.CALL_HEROQUEST: ToolText(
        "You call a mortal in your reach to a heroquest: it enters a mythic realm to walk a legend step by step, each step a trial of skill, passion, "
        "conviction or faith. Success brings a boon and may rewrite the legend; a fall may hurt, madden or kill it, hold its soul in the myth while its "
        "body sleeps, or break the myth. Companions share the trials and the outcome. 1 action.",
        {
            "quester_id": "The mortal",
            "legend_id": "The legend it walks",
            "companion_ids": "Mortals where the quester is who walk beside it (ids), if any",
            "reason": "Why you call it",
        },
    ),
    T.RESIGN_OFFICE: ToolText(
        "You give up a cosmic office you hold ({{ cosmic_offices }}); it stands empty and neglected until the council or the Creator fills it. 1 action.",
        {"office": "The office", "reason": "Why"},
    ),
    T.LAY_ENCHANTMENT: ToolText(
        "You lay a global enchantment: a natural law of your choosing ({{ natural_laws }}) over your world or one region in your reach. "
        "It holds only while you pay its upkeep in essence each epoch, and rival casters may dispel it. 1 action.",
        {
            "name": "Its name in the world's language",
            "effect": "The law it makes",
            "region_id": "One region it holds over, if not the whole world",
            "strength": "Its strength, 1 to 100; stronger costs more upkeep",
            "reason": "Why",
        },
    ),
    T.END_ENCHANTMENT: ToolText("You end a global enchantment you keep. 1 action.", {"law_id": "The enchantment", "reason": "Why"}),
    T.SHIELD_CONVOY: ToolText(
        "You guard a convoy on the road: it gains guards against raiders and sets out again if weather held it. 1 action.",
        {"convoy_id": "The convoy", "reason": "Why you guard it"},
    ),
    T.SCOUR_STREETS: ToolText(
        "You scour a district of a town: every criminal organisation's hold on its streets weakens. 1 action.",
        {"district_id": "The district", "reason": "Why you scour it"},
    ),
    T.ANSWER_ORACLE: ToolText(
        "A realm whose legal system asks the gods for verdicts waits on a case; you give the oracle your answer, true or not, and the court "
        "follows it. Left unanswered, the oracle names the truth only by chance. 1 action.",
        {"case_id": "The case awaiting trial", "verdict": "guilty or acquitted", "reason": "Why you answer so"},
    ),
    T.STIR_CROWD: ToolText(
        "You stir the folk of a town in your reach with a grievance ({{ collective_triggers }}); their anger, fear or fervour rises and the "
        "town may rise in a riot, a panic, a mass conversion or a lasting movement. The watch and garrison hold them back. 1 action.",
        {"town_id": "The town", "grievance": "The grievance you stir", "reason": "Why you stir them"},
    ),
    T.REVEAL_TRUE_HISTORY: ToolText(
        "You bring to light an older account that contradicts one a realm in your reach rewrote; the rewritten account loses credence, the "
        "older one gains it, the realm's legitimacy suffers and a scholar learns the truth as a secret. 1 action.",
        {"account_id": "The rewritten account", "reason": "Why you reveal it"},
    ),
    T.SET_STORYLET: ToolText(
        "You set a storylet ({{ storylet_ids }}) in motion in your world, if mortals fit its parts there; the one it falls to must choose "
        "what follows. 1 action.",
        {"storylet": "The storylet", "reason": "Why you set it in motion"},
    ),
    T.READ_DREAMS: ToolText(
        "You read the dreams of a mortal and learn some of the secrets they keep. Wards, a guardian servitor of another god or a stronger "
        "god's presence where they are may turn you aside. 1 action.",
        {"mortal_id": "The mortal", "reason": "Why you read them"},
    ),
    T.MARK_LINEAGE: ToolText(
        "You mark the line of a species: a blessing passes to every young of that line, to the breeds herders make of it and to the great "
        "beasts born of it; a taint does the same, and only gods of death, plague, madness, shadow, blood or hunger may lay one. 1 action.",
        {"species_id": "The species", "taint": "True to taint the line, false to bless it", "reason": "Why you mark it"},
    ),
    T.MOVE_PLAGUE_RESPONSE: ToolText(
        "You move a community to answer a sickness one way ({{ plague_responses }}): closed borders cost trade and calm, a quarantine "
        "slows the spread but may set off riots, burning the dead slows it but grieves folk whose rites forbid it, driving out the sick "
        "slows it at home and marks the sick, prayer comforts but crowds, and seeking a cure sets the learned of its hospitals, academies "
        "and monasteries to work. 1 action.",
        {"community_id": "The community", "disease_id": "The sickness", "response": "The answer", "reason": "Why you move them"},
    ),
    T.REVEAL_TONGUE: ToolText(
        "You teach a mortal in your reach words of your sacred tongue, the language of your true name; rites it casts in your name grow stronger. 1 action.",
        {"mortal_id": "The mortal", "reason": "Why you teach it"},
    ),
    T.DECREE_SOUND: ToolText(
        "You change a sound of a tongue of your world, and every word of it follows the change ({{ sound_change_kinds }}; where: {{ sound_environments }}). "
        "1 action.",
        {
            "language_id": "The tongue",
            "kind": "How the sound changes",
            "source": "The sound that changes",
            "target": "The sound it becomes; empty when it is lost",
            "environment": "Where in a word the change happens",
            "reason": "Why",
        },
    ),
    T.VEIL_NAME: ToolText(
        "You make a name unspeakable in a tongue of your world: its speakers coin a euphemism from their own words and keep the old name for sacred speech. "
        "1 action.",
        {"language_id": "The tongue", "node_id": "Whose name (an id)", "reason": "Why"},
    ),
    T.SHAPE_IMAGE: ToolText(
        "You choose how you meet the image your peoples hold of you: yield to it, resist it at "
        "{{ rules.god_images.resist_cost }} essence each epoch, or embrace it to win fame while it reshapes you faster. 1 action.",
        {"stance": "yield, resist or embrace", "reason": "Why"},
    ),
    T.CONVENE_GATHERING: ToolText(
        "You call a gathering at a people, settlement, cult or place in your reach: a festival, procession, pilgrimage, feast, games or performance. "
        "It is held this epoch; those who come grow closer to one another and to the host, and it is set down in history. 1 action.",
        {"host_id": "Who hosts it", "kind": "The kind of gathering", "reason": "Why you call it"},
    ),
    T.LOOSE_DISEASE: ToolText(
        "You forge a new sickness of your own design and loose it on a region or community: you choose how it spreads (vector), the body functions "
        "it strikes, how readily it passes on, how many it kills, how long it hides before the sick show it, which beast carries it and the climate it loves. "
        "It spreads along roads, armies and journeys by its vector, survivors grow immune, and you gain essence from every outbreak of it. "
        "{{ rules.son_tools.loose_disease_essence }} essence, 1 action.",
        {
            "target_id": "The region or community it first strikes",
            "name": "The sickness's name in the world's language",
            "vector": "How it passes on: air (crowds and cold), water (rivers, marsh, poor sanitation), touch (traders, armies and travellers), "
            "bite (needs its host beast), spirit (magic, ley lines, the impious), void (void-scarred lands), curse (bound to you while you live)",
            "target_functions": "The body functions it strikes; survivors may keep a lasting weakness there",
            "virulence": "How readily it spreads, 1 to 100",
            "lethality": "How many of the sick die, 1 to 100",
            "incubation": "Sampled years before the sick show it (0 to 20): long incubation spreads it unseen, past quarantines",
            "chronic_rate": "How many survivors keep a lasting weakness, 0 to 100",
            "climate_affinity": "The climate where it spreads fastest",
            "host_species_id": "Optional: the species that carries it; killing that species weakens the sickness",
            "severity": "How hard the first outbreak strikes, 1 to 100",
            "reason": "Why you loose it",
        },
    ),
    T.HIDE_SECRET: ToolText(
        "You hide a secret in a place: a seam, a relic, a sealed spirit, lost knowledge, a lost rite or a way down to the underworld. "
        "Explorers, seers and deep miners may find it; deep mining breaks what is sealed. {{ rules.places.hide_secret_essence }} essence, 1 action.",
        {
            "place_id": "The place's id",
            "kind": "What you hide: {{ secret_kinds | join(', ') }}",
            "strength": "How deep it lies and how strong its seal (0-100); stronger secrets are found later",
            "reason": "Why you hide it",
        },
    ),
    T.SANCTIFY_PLACE: ToolText(
        "You sanctify a place: its sacredness rises by {{ rules.places.sanctify_amount }}, it draws pilgrims and becomes a holy site of the faithful. "
        "{{ rules.places.sanctify_essence }} essence, 1 action.",
        {"place_id": "The place's id", "reason": "Why it is holy to you"},
    ),
    T.RAISE_NEXUS: ToolText(
        "You draw the ley lines together at a place: it becomes a nexus that feeds works, draws wizards and armies, and is holy to cults. "
        "{{ rules.places.raise_nexus_essence }} essence, 1 action.",
        {"place_id": "The place's id", "reason": "Why you raise it"},
    ),
    T.RESHAPE_LAND: ToolText(
        "You lay a hand on a land and reshape it: move its river into a neighbouring land (shift_river), parch it into desert (parch), "
        "bring the grass back to a desert (green), sow its soil with salt (salt_soil), make its soil rich (enrich_soil), raise or lower "
        "the land (raise_land, lower_land), carve a valley or fill one (carve_valley, fill_valley), open a spring (open_spring), call up "
        "lava (call_lava) or sink a coast under the sea (sink_coast). Rivers bow to gods of sea, storm, earth or stone; deserts to gods of "
        "sun, fire, hunger, salt or ash; green to gods of plants, harvest, life or sea; salt to gods of salt, sea or death; rich soil to gods "
        "of earth, fire, ash, harvest, plants or stone; raising to gods of earth or stone; lowering to gods of earth, stone or sea; valleys "
        "to gods of earth, stone, storm or sea, and filling them to gods of earth, stone or ash; springs to gods of sea, life, earth or "
        "plants; lava to gods of fire, earth, ash or stone; sinking a coast to gods of sea, storm or earth. Wells and fields follow the "
        "river, deserts lose their rain and harvests, salt kills the soil, a raised or lowered land keeps the height you give it, lava "
        "burns the woods and wakes the world's fire, a sunken coast floods. The folk of the land hold you in more awe when you water, "
        "raise or enrich it and in less when you drown, burn, parch or salt it. {{ rules.son_tools.reshape_land_essence }} essence, "
        "{{ rules.son_tools.reshape_land_ap }} actions.",
        {
            "region_id": "The land's id",
            "act": "shift_river, parch, green, salt_soil, enrich_soil, raise_land, lower_land, carve_valley, fill_valley, open_spring, call_lava or sink_coast",
            "target_region_id": "For shift_river: the neighbouring land the river should flow into (leave empty to let it find the lowest bed)",
            "reason": "Why you do it",
        },
    ),
    T.SANCTIFY_REGION: ToolText(
        "You sanctify a region: its ground becomes holy, drawing pilgrims who bring wealth and piety, warding off hauntings and uncanny phenomena. "
        "{{ rules.terrain.sanctify_essence }} essence, 1 action.",
        {"region_id": "The region's id", "sacredness": "How holy, 0-100 (leave out for the usual sanctification)", "reason": "Why you hallow it"},
    ),
    T.CURSE_REGION: ToolText(
        "You loose a danger upon a region: beasts, bandits, monsters, phenomena, disease, avalanche, quicksand or volcanic (fire from the ground). It harms settlers, herds, "
        "travellers, armies and merchants there, and fades over the ages unless the land breeds it. {{ rules.terrain.curse_essence }} essence, 1 action, "
        "strength at most {{ rules.terrain.curse_strength_max }}.",
        {"region_id": "The region's id", "danger": "Which danger", "strength": "How strong, 1-100", "reason": "Why you curse it"},
    ),
    T.REDIRECT_RIVER: ToolText(
        "You turn a river out of its bed into a neighbouring region: the old valley dries to a stream or a dry bed, the new one floods and grows. "
        "{{ rules.terrain.redirect_essence }} essence, 1 action.",
        {"from_region_id": "The region the river runs through now", "to_region_id": "The neighbouring region it will run through", "reason": "Why you turn it"},
    ),
    T.REORDER_SEASONS: ToolText(
        "You reorder the seasons of a world: the year runs in the order you name, so harvests, campaigns, travel and festivals fall differently. "
        "Only gods of sky, storm, time, sun, moon, harvest, ice or plants can do it. {{ rules.son_tools.reorder_seasons_essence }} essence, "
        "{{ rules.son_tools.reorder_seasons_ap }} actions, {{ rules.son_tools.reorder_seasons_per_epoch }} per age.",
        {"world_id": "The world's id", "order": "The current positions of the world's seasons (see SEASONS in the world summary), in the new order"},
    ),
    T.SHAPE_WEATHER: ToolText(
        "You hold a weather over a region: for the ages you name its sky does as you say, so harvests, battles, travel and disease follow your weather. "
        "Only gods of sky, storm, time, sun, moon, harvest, ice or plants can do it. {{ rules.son_tools.shape_weather_essence }} essence per age, "
        "{{ rules.son_tools.shape_weather_ap }} actions, {{ rules.son_tools.shape_weather_per_epoch }} per age, at most "
        "{{ rules.son_tools.shape_weather_max_epochs }} ages at once.",
        {
            "region_id": "The region's id",
            "weather": "The weather to hold (clear, rain, storm, snow, drought_wind, fog and the others of the weather list)",
            "epochs": "How many ages it holds",
            "reason": "Why you do it",
        },
    ),
    T.DECLARE_HOLY_WORLD: ToolText(
        "You declare a world your holy world: in that world your name is invoked first. If it is another sibling's world, your relationship sours. Free, "
        "{{ rules.son_tools.holy_world_per_epoch }} per age.",
        {"world_id": "The world's id"},
    ),
    T.SEAL_GATE: ToolText(
        "You seal a road between worlds (gate, dream passage, route): what leaks through that road stops, the two worlds' leakage decreases; but trade and migration coming "
        "by that road are cut too. {{ rules.cosmic_costs.seal_gate | share_of(rules.son_tools.cosmic_seal_pct) }} essence, 1 action.",
        {"route_id": "The route's id", "reason": "Why you seal it"},
    ),
    T.REKINDLE_STAR: ToolText(
        "You rekindle a dead, darkened or exploded star: light returns to the worlds around it, leakage recedes. "
        "{{ rules.cosmic_costs.rekindle_dead_star | share_of(rules.son_tools.cosmic_rekindle_pct) }} essence, {{ rules.son_tools.rekindle_star_ap }} actions.",
        {"star_id": "The star's id"},
    ),
    T.BIND_SPIRIT: ToolText(
        "You bind a free spirit to an item, ship or monument; if you bind it to a monument a golem is born. "
        "{{ rules.cosmic_costs.spirit_cloak | share_of(rules.son_tools.cosmic_spirit_cloak_pct) }} essence, 1 action.",
        {"spirit_id": "The free spirit's id", "target_id": "The item, vessel or monument"},
    ),
    T.HANG_STAR: ToolText(
        "You hang a new star in the sky, in a galaxy or in the sky of a world you reach; new worlds may be born around it. {{ rules.cosmic_costs.ignite_star | share_of(rules.son_tools.cosmic_hang_star_pct) }} essence, "
        "{{ rules.son_tools.hang_star_ap }} actions.",
        {
            "name": "The star's name",
            "type": "Star type: {{ star_types }}",
            "description": "What the star is like",
            "galaxy_id": "The id of the galaxy it hangs in",
            "world_id": "The id of a world whose sky it hangs in; a world without a star comes to circle it",
        },
    ),
    T.EXTINGUISH_STAR: ToolText(
        "You extinguish a star: the worlds around it sink into darkness and cold, leakage rises, the apocalypse draws near. A terrible act; the whole cosmos remembers it. "
        "{{ rules.cosmic_costs.ignite_star | share_of(rules.son_tools.cosmic_extinguish_pct) }} essence, {{ rules.son_tools.extinguish_star_ap }} actions.",
        {"star_id": "The star's id", "reason": "Why you put it out"},
    ),
    T.TALK_TO_FOREIGN_GOD: ToolText(
        "You speak with the old or foreign god of another world: alliance, threat or bargain. The outcome depends on your charisma, their attitude and their power. "
        "At most {{ rules.son_tools.foreign_talk_per_god }} talk(s) with the same god per age. 1 action.",
        {"god_id": "The foreign god's id", "intent": "alliance, threat or bargain", "words": "What you say"},
    ),
    T.SEAL_TREATY: ToolText(
        "You bind two or more parties (realms, communities, houses, cults, beasts) by a typed treaty sealed in your name: its kind decides how it behaves "
        "and its clauses run every age (tribute, hostages, tolls waived, freedom of faith, call to arms...). Costs essence.",
        {
            "kind": "peace, truce, alliance_defensive, alliance_offensive, non_aggression, vassalage, tribute, marriage_pact, trade_pact, condotta, guarantee, interworld, coalition or divine_pact",
            "parties": "Each party's id and role (signatory, overlord, vassal, guarantor)",
            "clauses": "Typed clauses: kind (call_to_arms, tribute, cession, hostage, marriage, trade_rights, tolls_waived, religious_freedom, demilitarised, champion, extradition, wergild, non_aggression, route_control, resource_demand, research_agreement), who owes it, who gains, and its terms (amount, commodity, epochs, region_id, mortal_id...)",
            "epochs": "How many ages it holds; empty for ever",
            "parties.party_id": "The party's id",
            "parties.role": "Its role: signatory, overlord, vassal or guarantor",
            "clauses.kind": "The clause's kind",
            "clauses.obligor_id": "Who owes it",
            "clauses.beneficiary_id": "Who gains by it",
            "clauses.params": "Its terms by name (amount, commodity, epochs, region_id, mortal_id...)",
        },
    ),
    T.BLESS_BLOODLINE: ToolText(
        "You mark a noble house's blood with a lasting gift or curse (long_lived, giant_blooded, god_blooded, cursed, fertile, seer_gift); every child born to it carries it. "
        "A god-blooded house anchors your existence while it lives. Costs essence.",
        {"house_id": "The house", "trait": "The bloodline trait", "revoke": "True to lift it instead"},
    ),
    T.VOID_TREATY: ToolText(
        "You make one party break a treaty in force: the breach is recorded, its oath is broken, guarantors may march and the breaker loses honour. Costs essence.",
        {"treaty_id": "The treaty", "breaker_id": "The party that breaks it"},
    ),
    T.MAKE_INTERWORLD_TREATY: ToolText(
        "You establish an interworld treaty between two communities in separate worlds: alliance or trade. There must be a known, open road between the two worlds and one "
        "of the communities must be on the world you are currently on; enemies do not make treaties. {{ rules.son_tools.treaty_cost }} essence, "
        "{{ rules.son_tools.treaty_ap }} action.",
        {
            "a_id": "The community on the world you are on",
            "b_id": "The community on the other world",
            "kind": "alliance (side by side in war) or trade (goods and prosperity flow)",
            "terms": "The treaty's condition, its oath",
        },
    ),
    T.SEAL_LEAK: ToolText(
        "You seal the leaks of the world you are on: the intensity of what leaks in from outside (leakage) decreases by {{ rules.son_tools.seal_leak_reduction }}. "
        "{{ rules.son_tools.seal_per_epoch }} per age. {{ rules.son_tools.seal_cost }} essence, {{ rules.son_tools.seal_ap }} action.",
        {"how": "With what and how you seal the leak"},
    ),
    T.OPEN_COSMIC_BED: ToolText(
        "On the world you are on, you open a bed of the cosmic travel resource in a region or place: mortals can claim it and travel between worlds. The cosmos's travel "
        "resource must be defined. {{ rules.son_tools.open_deposit_cost }} essence, {{ rules.son_tools.open_deposit_ap }} actions.",
        {"region_id": "The region or place where the bed opens", "reason": "Why you open it"},
    ),
    T.WAR_ON_FOREIGN_GOD: ToolText(
        "You declare war on the old or foreign god of another world. Your strength, your will and your rank clash with their power. If you win they fall defeated (in a "
        "crushing victory they die), you gain fame and experience; if you lose you are wounded and lose essence. You must be in that world or there must be a known open "
        "road between you. {{ rules.son_tools.foreign_war_cost }} essence, {{ rules.son_tools.foreign_war_ap }} actions.",
        {"god_id": "The foreign god's id", "reason": "Why you make war"},
    ),
    T.BARGAIN_WITH_OUTSIDER: ToolText(
        "FORBIDDEN: you bargain with a being from outside the cosmos. You choose what you take and what you pay; the price is paid at once. "
        "Leakage rises, your siblings think less of you and your loyalty to the Creator falls. "
        "Does not spend an action, {{ rules.son_tools.outer_bargain_per_epoch }} per age.",
        {
            "outsider_id": "The outer being's id",
            "request": "What you ask of it",
            "gain": "What you take from the bargain",
            "price": "What you pay for it",
            "price_domain": "The domain you give up when you pay with a domain",
            "price_world_id": "The world whose sanity you pay with; the outer being's own world when not given",
        },
    ),
    T.REVEAL_TENET: ToolText(
        "You reveal a tenet to one of your own cults. The faithful accept it only if it fits your domains or what they already believe "
        "(fit at least {{ rules.doctrine.reveal_fit }}); a tenet cannot stand beside its opposite. Once per cult per age. "
        "{{ rules.doctrine.reveal_cost }} essence, 1 action.",
        {
            "cult_id": "One of your own cults",
            "tenet": "The tenet: {{ tenets }}",
            "name": "Optional: the name your faithful give this tenet",
            "target": "Only for dietary law (a food), sacred species (the species id) or pilgrimage duty (the holy place id)",
        },
    ),
    T.OPEN_REBIRTH_GATE: ToolText(
        "By your own hand you open the gate of rebirth for a soul: it is born again as a newborn in a community, carrying some of its old traits and faint memories. "
        "Only for souls of your own faith, or any soul if you are a god of death; a sealed soul cannot return. "
        "{{ rules.necromancy.rebirth_gate_cost }} essence, 1 action.",
        {"spirit_id": "The soul (a spirit) to send back", "community_id": "Optional: the community it is born into; otherwise its doctrine decides"},
    ),
    T.BIRTH_WORLD: ToolText(
        "You birth a new world into the cosmos: with its own sky, physics, regions, unique resource and perhaps natives. The world reflects your domains and you turn to it. "
        "{{ rules.balance.birth_world }} essence, {{ rules.son_tools.birth_world_ap }} actions.\n"
        "EXISTING STARS (the new world usually orbits one of these; choose with star_id):\n"
        "{% if context.stars %}{% for star in context.stars %}- star_id {{ star.id }}: {{ star.name }} ({{ star.type_label }}){% if not loop.last %}\n{% endif %}{% endfor %}"
        "{% else %}none{% endif %}",
        {
            "inspiration": "Why and from what this world is born",
            "type": "World type: {{ world_types }}",
            "star_id": "The existing star it will orbit (from the list)",
            "parent_world_id": "If it will be a moon of a world, that world's id",
            "new_star": "Only if no star in the list fits this world's light: a distant system with its own new sun",
        },
    ),
    T.RAISE_DISTRICT: ToolText(
        "You raise or enlarge a district of a settlement: farmland, market, craft quarter, temple quarter, harbour, citadel, slums, palace, foreign quarter, "
        "necropolis, residential, civic quarter, gardens or one of the world's district designs. Each kind changes the city: storage, housing, order, "
        "sanitation, piety, administration, "
        "policing, trade and harbour capacity. {{ rules.son_tools.raise_district_essence }} essence, {{ rules.son_tools.raise_district_ap }} actions.",
        {
            "settlement_id": "The settlement's id",
            "kind": (
                "The district kind (farmland, market, craft_quarter, temple_quarter, harbour, citadel, slums, palace, foreign_quarter, necropolis, "
                "residential, civic_quarter, gardens)"
            ),
            "design_id": "Or the id of one of the world's district designs",
            "material": "timber or stone (stone resists fire, flood and storm but falls in earthquakes)",
            "reason": "Why you raise it",
        },
    ),
    T.DESIGN_DISTRICT: ToolText(
        "You devise a new kind of district for your world on a base kind; every city may then raise it. Each number you give replaces the base "
        "kind's effect per level: housing (people), food_store and goods_store (stored goods), harbour (trade capacity), order, sanitation (may be "
        "negative), piety_floor, admin_pct (administrative reach), policing, investment_pct and tension_relief_pct. "
        "{{ rules.son_tools.design_district_essence }} essence, {{ rules.son_tools.design_district_ap }} actions.",
        {
            "name": "The design's name",
            "base_kind": "The base district kind it builds on",
            "housing": "People housed per level",
            "food_store": "Food stored per level",
            "goods_store": "Ore and goods stored per level",
            "harbour": "Harbour trade capacity per level",
            "order": "Public order per level",
            "sanitation": "Sanitation per level (negative for squalor)",
            "piety_floor": "Piety the district keeps alive per level",
            "admin_pct": "Administrative reach per level (%)",
            "policing": "Crime suppressed per level",
            "investment_pct": "Extra investment drawn per level (%)",
            "tension_relief_pct": "City-countryside tension relieved per level (%)",
            "reason": "What the district is and why you devise it",
        },
    ),
    T.OPEN_TRADE_ROUTE: ToolText(
        "You lay a trade route between two markets of the world you are on (peoples or settlements): merchants carry goods along it from this age, the cheap "
        "market selling to the dear one, tolls fall to the masters of the lands it crosses. If you or a sibling closed the way between them before, it opens again. "
        "{{ rules.son_routes.open_cost }} essence, {{ rules.son_routes.open_ap }} action.",
        {
            "first_id": "The first market (a people or settlement)",
            "second_id": "The second market",
            "mode": "How goods travel: road, river, sea, caravan or sky (leave empty to let the land decide)",
            "reason": "Why you lay this road",
        },
    ),
    T.CLOSE_TRADE_ROUTE: ToolText(
        "You close a trade route: no goods pass, and merchants found no new way between its two markets until a god opens it again. "
        "{{ rules.son_routes.close_cost }} essence, {{ rules.son_routes.close_ap }} action.",
        {"route_id": "The trade route to close", "reason": "Why you close it"},
    ),
    T.COMMISSION_STRUCTURE: ToolText(
        "You set a settlement or people to raise a work in your name: its builders, stone and coin raise it over the coming ages, and when it stands it is "
        "dedicated to you (fame, faith, and it can anchor your existence). The kind decides what it does: temples hold piety, walls defend, granaries store, "
        "hospitals heal, libraries keep learning, palaces lend legitimacy. {{ rules.construction.commission_essence }} essence, 1 action.",
        {
            "community_id": "The settlement or people that builds it",
            "structure_kind": "What it is: {{ structure_kinds }}",
            "level": "Its size, 1 to 5",
            "material": "What it is built of (stone, wood, bronze...); by default what its builders know",
            "design_id": "A structure design of that kind to build to, if one exists",
            "name": "Its name, if you give one",
        },
    ),
    T.WAGE_WAR: ToolText(
        "You make one community declare war on another for a cause you name, with the aims it will fight for; the war then runs by its own course. "
        "{{ rules.son_military.wage_war_cost }} essence, 1 action.",
        {
            "attacker_id": "The community that declares the war",
            "defender_id": "The community it attacks",
            "cause": "Why the war is fought: claim, holy_war, succession, raid, liberation, punitive, conquest_journey, tribute_revolt and the other causes",
            "aims": "What the attackers fight for (at most {{ rules.son_military.max_aims }}): conquer_region, seize_settlement, tribute, convert, liberate and so on",
            "reason": "The proclamation, one sentence",
        },
    ),
    T.RAISE_HOST: ToolText(
        "You call a community to arms: its warriors and nobles muster as a standing army, in war or in peace; its people grow fewer while they serve. "
        "{{ rules.son_military.raise_host_cost }} essence, 1 action.",
        {
            "community_id": "The community that raises the army",
            "soldiers": "How many it calls to arms (at most {{ rules.son_military.raise_host_max }})",
            "commander_id": "A living mortal to lead it, if any",
            "war_id": "The war it marches to, if any",
        },
    ),
    T.DISBAND_HOST: ToolText(
        "You send a standing army home: its soldiers return to their people and it leaves the field. {{ rules.son_military.disband_cost }} essence, 1 action.",
        {"army_id": "The army to disband", "reason": "Why it goes home"},
    ),
    T.LAY_SIEGE: ToolText(
        "You set an army of one side of a war against a settlement of the other: it encamps, digs its works and starves the walls. "
        "{{ rules.son_military.siege_cost }} essence, 1 action.",
        {"war_id": "The war", "army_id": "The besieging army", "settlement_id": "The settlement to besiege"},
    ),
    T.OFFER_PEACE: ToolText(
        "You end a war on terms you set: name the victor and what the beaten must give (land, tribute, hostages, a throne), or no victor for a white peace. "
        "{{ rules.son_military.peace_cost }} essence, 1 action.",
        {
            "war_id": "The war to end",
            "victor_id": "The side that wins, or empty for a white peace",
            "terms": "What the peace demands: cession, vassalage, hostage, reparations, tribute, liberty, throne, break_cult",
        },
    ),
    T.COMMISSION_VESSEL: ToolText(
        "You have a community lay down a ship of the hull you choose, armed as you wish, with a captain if you name one. "
        "{{ rules.son_military.vessel_cost }} essence, 1 action.",
        {
            "owner_id": "The community or mortal that owns the ship",
            "name": "The ship's proper name",
            "hull": "raft, boat, galley, longship, cog, carrack, warship, light_sailer, bone_hull, generation_ship, skyship or living_ship",
            "armament": "What it carries to fight: rams, missiles, siege_engines, rites",
            "captain_id": "A living mortal to captain it, if any",
        },
    ),
    T.DESIGN_UNIT: ToolText(
        "You teach a community a new kind of soldier built on a known unit: its armies muster it in place of the old kind when their doctrine and stores allow. "
        "{{ rules.son_military.design_cost }} essence, 1 action.",
        {
            "owner_id": "The community that will field it",
            "name": "What the soldiers are called",
            "base_kind": "The known unit it grows from: levy, spearmen, archers, cavalry and the rest",
            "melee": "Strength hand to hand, 0 to 100",
            "missile": "Strength at range, 0 to 100",
            "defence": "How well it holds, 0 to 100",
            "armour": "none, hide, padded, mail, scale, plate or enchanted",
            "shield": "none, small, large or tower",
            "terror": "Fear it strikes, 0 to 100",
            "reach": "How far its weapons reach, 0 (hand to hand) to 5 (siege range); leave empty to keep the base unit's",
            "volleys": "Volleys it looses in one phase of battle, 0 to 6; leave empty to keep the base unit's",
            "accuracy": "How true its blows and shots land, 0 to 100; leave empty to keep the base unit's",
            "piercing": "How well its weapons pierce hard armour, 0 to 100; leave empty to keep the base unit's",
        },
    ),
    T.PLANT_SPIES: ToolText(
        "You plant a network of spies for one community inside another under a cover you choose; it gathers intel, steals secrets and stirs trouble. "
        "{{ rules.son_military.spies_cost }} essence, 1 action.",
        {"owner_id": "The community the spies serve", "target_id": "The community they watch", "cover": "merchant, priest, envoy or beggar"},
    ),
    T.ANSWER_OFFERINGS: ToolText(
        "A community that worships you keeps a ledger of what it has offered you and what you have given back; you answer its offerings "
        "now. Gods who leave offerings unanswered lose love and gain neglect; gods who give back more than they were given gain love. 1 action.",
        {"community_id": "The community whose offerings you answer", "generous": "True to give back more than they offered", "reason": "Why you answer"},
    ),
    T.BEGIN_LONG_PLAN: ToolText(
        "You set in motion a long plan that outlives any one epoch ({{ long_plan_kinds }}): it advances step by step, may come to light "
        "the less secret it is, and is fulfilled when its last step is taken. 1 action.",
        {
            "kind": "What the plan aims at",
            "name": "What the plan is called",
            "target_id": "The land, world, house, people or town it aims at",
            "steps": "Steps it needs, 1 to 100",
            "secrecy": "How secret it is kept, 0 to 100",
            "reason": "Why you begin it",
        },
    ),
    T.FURTHER_PLAN: ToolText(
        "You take one of your long plans forward by a step. {{ rules.long_plans.steps_per_epoch }} steps an epoch is its own pace. 1 action.",
        {"plan_id": "Your long plan", "reason": "Why you further it"},
    ),
    T.SHAPE_KINSHIP: ToolText(
        "You change how a people in your reach reckons kin: descent ({{ kinship_descents }}), where couples live ({{ residence_rules }}), "
        "whom they prefer to marry ({{ marriage_preferences }}) and what passes at a marriage ({{ marriage_payments }}). Inheritance, "
        "matches, alliances between lines and marriage gifts follow. 1 action.",
        {
            "people_id": "The people",
            "descent": "How descent is reckoned",
            "residence": "Where a couple lives",
            "preference": "Whom they prefer to marry",
            "payment": "What passes at a marriage",
            "reason": "Why you reshape it",
        },
    ),
    T.SHAPE_REPRODUCTION: ToolText(
        "You change how a people in your reach bears its young ({{ reproductive_systems }}); births, the sexes of the newborn, castes, "
        "marriage and growth follow. 1 action.",
        {"people_id": "The people", "system": "How they bear their young", "reason": "Why you change it"},
    ),
    T.TRY_REALM: ToolText(
        "You try a realm in your reach with a challenge ({{ challenge_kinds }}) of a severity you choose; a challenge it can bear spurs "
        "new ways and solidarity, too slight a one leaves it idle, too heavy a one breaks it. 1 action.",
        {"polity_id": "The realm", "kind": "What tries it", "severity": "How heavy the trial is, 0 to 100", "reason": "Why you try it"},
    ),
    T.SET_CIRCUIT: ToolText(
        "You set a ceremonial circuit turning among communities in your reach: a treasure passes from each stop to the next every epoch, "
        "lending standing to whoever holds it and binding the stops in regard. 1 action.",
        {"name": "What the circuit is called", "stop_ids": "The communities it passes through, in order, at least two", "reason": "Why you set it"},
    ),
    T.SHAPE_RULE: ToolText(
        "You reshape who chooses the rulers of a realm in your reach ({{ selectorates }}) and how much of its spending goes to public goods; "
        "small circles of choosers buy loyalty with private gifts, wide ones with roads, granaries and courts. 1 action.",
        {
            "polity_id": "The realm",
            "selectorate": "Who has a say in choosing its ruler",
            "public_share": "Share of its spending on public goods, 0 to 100",
            "reason": "Why you reshape it",
        },
    ),
    T.ANOINT_FOUNDER: ToolText(
        "You mark the ruler of a realm in your reach as its charismatic founder; their charisma rises, and at their death the realm must "
        "turn that charisma into a dynasty or into rules, or split. 1 action.",
        {"polity_id": "The realm", "reason": "Why you mark its ruler"},
    ),
    T.FREE_LEARNING: ToolText(
        "You set how free a house of learning in your reach is; freedom quickens research and keeps scholars, while suppression slows "
        "both and drives scholars to freer houses. 1 action.",
        {"structure_id": "The house of learning", "level": "How free it is, 0 to 100", "reason": "Why you set it"},
    ),
    T.INSPIRE_SCHOOL: ToolText(
        "You move a mortal in your reach to found a school of thought; masters teach disciples, schools keep knowledge through hard times "
        "and quicken research where they gather. 1 action.",
        {"founder_id": "The mortal who founds it", "name": "What the school is called", "reason": "Why you inspire it"},
    ),
}
