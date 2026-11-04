from aerona.prompts.tools.ids import MortalToolId
from aerona.prompts.tools.shared import IMAGE_PROMPT_FIELD, WORD_FIELDS
from aerona.prompts.tools.text import ToolText

T = MortalToolId
M = "rules.mortal_tools"

NAME_FIELD = "A name from your own language"
DESCRIPTION_FIELD = "What it is, how it came to be, what makes it strange and concrete"

MORTAL_TOOL_TEXTS: dict[MortalToolId, ToolText] = {
    T.LOOK_AT_WORLD: ToolText(
        "Shows your land, those near you, your language, what you know, what you own and recent events more widely than the prompt. Free."
    ),
    T.INSPECT_ENTITY: ToolText("Shows the details of an entity. Free.", {"id": "The entity's id"}),
    T.SEARCH_ENTITIES: ToolText("Searches entities. Free.", {"query": "A word in the name or description"}),
    T.FOUND_LANGUAGE: ToolText(
        "You give birth to your own language: its name, kind (spoken language, sacred language, script, sign language…), sound structure and first words. From now on "
        "you speak this language. 1 action.",
        {
            "name": NAME_FIELD,
            "subtype": "spoken language, sacred language, script, sign language…",
            "description": "Its sound structure, its script, who speaks it, what is forbidden to say",
            **WORD_FIELDS,
            "image_prompt": (
                "English photoreal prompt: an object showing this script or language, e.g. carved tablet, manuscript, inscription, with lighting and camera. "
                '{% include "shared/image_prompt_rules.md.j2" %}'
            ),
        },
    ),
    T.COIN_WORDS: ToolText(
        "You add new words to the language you speak (meaning, type, origin). Free, {{ " + M + ".coin_word_per_epoch }} times per age, at most "
        "{{ " + M + ".coin_word_max_words }} words each time.",
        dict(WORD_FIELDS),
    ),
    T.PRODUCE_ITEM: ToolText(
        "You produce an item from resources you own or that lie on your land: weapon, armour, shield, tool, jewellery, sacred relic. The resources' abundance decreases; "
        "quality depends on your craft and the resources' might. "
        "A named mortal needs a craft skill of at least {{ rules.skills.tool_min_craft }} (smithing, carpentry, masonry and the like). 1 action.",
        {
            "name": NAME_FIELD,
            "category": "weapon, armour, shield, tool, jewellery, sacred relic, instrument or book",
            "subtype": "e.g. bone spear, salt armour",
            "description": DESCRIPTION_FIELD,
            "resource_ids": "The resources it is made from (at most {{ " + M + ".craft_max_resources }})",
            "material": "What it is made of: {{ materials | join(', ') }}; it must come from one of those resources or your people's stores, and your people must be able to work it",
            "owner_id": "Who will carry the item (a mortal or you); if empty, you",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.BUILD_STRUCTURE: ToolText(
        "You build a monument: temple, tower, wall, bridge, monument, tomb, mine, harbour, library. It can be dedicated to a god."
        " A named mortal needs a craft skill of at least {{ rules.skills.tool_min_craft }} (smithing, carpentry, masonry and the like). 1 action.",
        {
            "name": NAME_FIELD,
            "subtype": "temple, tower, wall, bridge, tomb, mine, harbour, library…",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own settlement, place or region; if empty, where you are",
            "dedicated_son_id": "The god it is dedicated to, if any",
            "material": "What it is built of (stone, wood, clay, glass…); holy stone makes a temple shine, soft wood rots; it must be in your people's stores",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.CREATE_CULTURE: ToolText(
        "You give birth to a tradition of your community (festival, taboo, funeral rite), a legend, a work of art (song, statue, fresco, book, play; by honouring your god "
        "it strengthens him) or a law (statute, penalty, custom; a just law reduces rebellion). 1 action.",
        {
            "kind": "tradition (rite, festival, taboo), legend (a tale), artwork (song, statue, fresco, book, play) or law (statute, penalty, custom)",
            "name": NAME_FIELD,
            "subtype": "What exactly it is",
            "description": DESCRIPTION_FIELD,
            "related_ids": "Existing records it tells of (at most {{ " + M + ".culture_max_related }})",
            "law_kind": "For a law: what it rules (succession_rule, tax_rate, penal_code, levy_law, slavery, tolls, sumptuary...); required for laws",
            "law_params": "For a law: its terms by name (rate, share, theft, murder, status, level...); only the terms its kind has",
            "image_prompt": 'English photoreal prompt: the ritual being performed or a scene of the legend. {% include "shared/image_prompt_rules.md.j2" %}',
            "legend_category": "Only for a legend: what it would become if belief made it real: {{ legend_categories | join(', ') }}",
        },
    ),
    T.DISCOVER_RESOURCE: ToolText(
        "You discover a new resource on your land (ore vein, healing herb, sacred spring, bone bed…) and own it. 1 action, "
        "{{ " + M + ".discover_resource_per_epoch }} per age.",
        {
            "name": NAME_FIELD,
            "subtype": "ore vein, healing herb, sacred spring, bone bed…",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own region or a place in your region",
            "domain": "One of: {{ domains | join(', ') }}",
            "image_prompt": IMAGE_PROMPT_FIELD,
            "commodity": "What your people draw from it: {{ commodities | join(', ') }}; ore feeds forges and weapons; empty if none",
            "material": "If it is a seam or a grove, its material: {{ materials | join(', ') }}",
            "mechanics": "The resource's strange rules, at most {{ rules.mechanics.resource_max }} (empty: read from its name and text): {{ resource_mechanics }}",
        },
    ),
    T.CLAIM_RESOURCE: ToolText(
        "You claim an ownerless resource on your land. If you take someone else's resource, enmity is born between you. Free, {{ "
        + M
        + ".claim_per_epoch }} per age.",
        {"resource_id": "The resource's id"},
    ),
    T.FOUND_SETTLEMENT: ToolText(
        "You split off a branch of your population (or your disciples) and found a new settlement (village, fortress, harbour, monastery, camp); those who migrate leave "
        "you. In your own region or a neighbouring region. 1 action.",
        {
            "name": NAME_FIELD,
            "subtype": "village, fortress, harbour, monastery, camp…",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own region or a neighbouring region",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.ESTABLISH_TRADE: ToolText(
        "You establish trade with a community nearby or in a neighbouring region; the prosperity of both of you increases. 1 action.",
        {"target_id": "The community's id", "goods": "What you give and what you take"},
    ),
    T.DECLARE_WAR: ToolText(
        "You declare war on a community or a creature. The flow of the world resolves the war; your weapons and your god lend you strength. 1 action.",
        {"target_id": "The community or creature", "reason": "Why you go to war"},
    ),
    T.WORSHIP: ToolText(
        "You worship a god (a son) or change your god; if you give son_id 0 you worship the creator god directly, the father of all the sons. Your old god does not forget "
        "this. Free, {{ " + M + ".worship_per_epoch }} per age.",
        {"son_id": "The son's id, or 0 for the creator", "offering": "Your offering and vow"},
    ),
    T.PRAY_TO_CREATOR: ToolText(
        "You pray directly to the creator god above the sons, the father of all worlds. Your prayer reaches him; if he answers you will see it in your dream and his grace "
        "will descend. Free, {{ " + M + ".pray_creator_per_epoch }} per age.",
        {"prayer": "Your prayer", "request": "What you ask of him"},
    ),
    T.DEVELOP_KNOWLEDGE: ToolText(
        "Your community develops a new piece of knowledge (a technology, craft, school or method). Branch: {{ knowledge_branches }}. If it is built on knowledge you already "
        "have it is stronger. A named mortal needs a learned skill of at least {{ rules.skills.tool_min_lore }} (lore, writing, healing and the like). 1 action.",
        {
            "name": NAME_FIELD,
            "branch": "The knowledge's branch",
            "description": "What it is, how it was found, which material or observation it rests on",
            "base_ids": "Knowledge you know that it is built on (at most {{ " + M + ".knowledge_max_prereqs }})",
            "resource_id": "The resource it relies on",
            "image_prompt": 'English photoreal prompt: people practicing this technique, tools, materials, setting. {% include "shared/image_prompt_rules.md.j2" %}',
        },
    ),
    T.LEARN_KNOWLEDGE: ToolText(
        "You learn a piece of knowledge known by your trade partner, ally or neighbour. Free, {{ " + M + ".learn_per_epoch }} per age.",
        {"knowledge_id": "The knowledge's id", "from_id": "Who teaches it"},
    ),
    T.DIPLOMACY: ToolText(
        "Diplomacy with another community: alliance (stands with you in war), peace (tries to end enmity), tribute (demands wealth from the weak) or marriage (unites the "
        "lineages). 1 action.",
        {"target_id": "The community's id", "kind": "alliance, peace, tribute or marriage", "terms": "Your terms"},
    ),
    T.GO_ON_ADVENTURE: ToolText(
        "You embark on an adventure: hunting a dangerous creature (the flow of the world resolves the fight at the end of the age; your weapons count) or seizing an item "
        "from someone else's hands (your agility and wits against its owner's defence). 1 action.",
        {"target_id": "The species to hunt or the item to seize", "goal": "What you set out to do"},
    ),
    T.FIND_ROUTE: ToolText(
        "You search for the way to another world. The way you find depends on what you know: gate lore an ancient gate, sky navigation a sail route, pathfinding folding, "
        "magic a dream road. Rarely you may discover a world no one has known. 1 action.",
        {"how": "How you search for the way: observation, sacrifice, dream, old maps…"},
    ),
    T.EXPLORE_LAND: ToolText(
        "You set out to explore beyond the known lands: you find either a new region not on the map (valley, plateau, island, coastline, inland sea) or, in your own or a "
        "neighbouring region, a place no one has set foot on (cave, lake, pass, forest, well). Success depends on your wits (your craft if you are a community) and your "
        "path knowledge (seafaring, pathfinding, astronomy). If you are a community your pioneers can settle there and found a new settlement. 1 action, "
        "{{ rules.exploration.tool_per_epoch }} per age.",
        {
            "kind": "region (new lands not on the map) or place (a new place in your own or a neighbouring region)",
            "name": "An original proper name; fitting your language's naming rule",
            "subtype": "valley, island, cave, lake, pass…",
            "description": "What you found, how you found it, what the first to set foot there saw",
            "location_id": "Only for a place: the region it lies in (your own or a neighbouring one); if empty, your own region",
            "settle": "If you are a community, your pioneers settle there and found a new settlement",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.RESURRECTION_RITE: ToolText(
        "You perform a rite for your dead god's return: prayer (+{{ rules.death.prayer_devotion }} devotion), wealth offering ({{ rules.death.offering_cost }} from your "
        "wealth, prosperity or craft; +{{ rules.death.offering_devotion }}), blood sacrifice ({{ rules.death.sacrifice_population_pct }}% of your population; "
        "+{{ rules.death.sacrifice_devotion }}) or life sacrifice (a named mortal offers itself or your people offer it; +{{ rules.death.self_sacrifice_devotion }}). "
        "A rite held in the region where your god's bones lie counts {{ '%g' | format(rules.death.pilgrimage_multiplier_pct / 100) }} times. When devotion is full the resurrection "
        "rite may succeed. 1 action, {{ rules.death.rite_per_epoch }} per age.",
        {
            "son_id": "The dead god's (son's) id",
            "kind": "prayer, wealth, blood or life",
            "victim_id": "The named mortal offered in a life sacrifice (if empty, yourself if you are a mortal)",
        },
    ),
    T.BUILD_SHIP: ToolText(
        "You build an inter-world ship (requires shipbuilding knowledge). Its power depends on your craft, your mining and your metallurgy. 1 action.",
        {"name": NAME_FIELD, "subtype": "light-sail, bone-hulled, generation ship…", "description": DESCRIPTION_FIELD, "image_prompt": IMAGE_PROMPT_FIELD},
    ),
    T.LAUNCH_EXPEDITION: ToolText(
        "You organize an expedition to another world along a known route: to found a colony, open trade, explore, conquer or go on pilgrimage. The journey may take several "
        "ages; on the way there may be pirates, storms, creatures and disappearance. 1 action.",
        {
            "route_id": "The route's id",
            "intent": "colony, trade, exploration, conquest or pilgrimage",
            "percent": "What percent of your community sets out (for colony or conquest; at most {{ "
            + M
            + ".expedition_max_pct }}); default {{ "
            + M
            + ".expedition_default_pct }}",
            "vessel_id": "The ship or vessel to use",
        },
    ),
    T.TAME_SPECIES: ToolText(
        "You try to tame a creature species on your land. If you succeed it serves you in war, transport and trade; flying or gigantic ones can carry you between worlds. "
        "Dangerous and intelligent species are hard. 1 action.",
        {"species_id": "The species' id", "how": "How you tame it"},
    ),
    T.WEAVE_CHIMERA: ToolText(
        "With biomancy you merge two creature species in your world, near you (at most {{ rules.creatures.chimera_weave_distance }} steps), into a single chimera (requires "
        "biomancy knowledge). The chimera carries the traits of both species; but it may get out of control. 1 action.",
        {"a_id": "The first species", "b_id": "The second species", "name": NAME_FIELD, "goal": "Why you weave it"},
    ),
    T.BIND_SPIRIT: ToolText(
        "With magic you bind a free spirit in your own or a neighbouring region to an item, ship or monument there (requires magic knowledge). The item becomes ensouled; "
        "bound to a monument, stone walks and a golem is born. 1 action.",
        {"spirit_id": "The free spirit's id", "target_id": "The item, vessel or monument"},
    ),
    T.SEARCH_RUINS: ToolText(
        "You search a ruin, a remnant or the bones of a dead god on your land: you may find lost knowledge, an ownerless item, or awaken something sleeping. 1 action.",
        {"target_id": "The id of a place that is a ruin, remnant or god's corpse", "how": "How you search"},
    ),
    T.SABOTAGE: ToolText(
        "You secretly harm a community: poison (population or life decreases), arson (prosperity, defence, wealth decrease) or discord (you break off one of its allies from "
        "it). If you are caught you become enemies. 1 action.",
        {"target_id": "The community's id", "kind": "poison, arson or discord", "how": "How you do it"},
    ),
    T.PREACH: ToolText(
        "You spread your god's word to a neighbouring community; if it takes hold they too worship your god and your disciples increase. It is hard among those who worship "
        "another god. 1 action.",
        {"target_id": "The community or mortal", "sermon": "Your sermon"},
    ),
    T.CHALLENGE_GOD: ToolText(
        "You stand up to a god (a son): your strength, agility, wits and weapons against his might. If you win the god is wounded, his fame shaken and you become a legend; "
        "if you lose you die or are cursed. 1 action.",
        {"son_id": "The god's id", "reason": "Why you defy him"},
    ),
    T.DENY_GOD: ToolText(
        "You deny your god: you stop worshipping him and become godless. Your god's existence weakens, and the father of the gods cannot draw strength from godless "
        "communities. 1 action.",
        {"reason": "Why you turn away"},
    ),
    T.PROPHESY: ToolText(
        "You make a prophecy: you say something that will happen in the future. If it comes true Fate records it and your reputation (charisma) rises; if it is misread it "
        "is shaken. 1 action, {{ " + M + ".prophesy_per_epoch }} per age.",
        {
            "name": "The prophecy's name, from your own language",
            "saying": "The words of the prophecy: imagistic but testable; who or what, and when",
            "related_ids": "Records the prophecy concerns (at most {{ " + M + ".prophecy_max_related }})",
        },
    ),
    T.ESCAPE: ToolText(
        "If you are a captive you try to escape your captors; your agility and wits decide. If caught you are wounded. 1 action.",
        {"how": "How you try to escape"},
    ),
    T.PAY_RANSOM: ToolText(
        "You pay a ransom to the captors for a captured member of yours (bound to you or a mortal from your land): your wealth or prosperity decreases, theirs increases, the "
        "captive returns. 1 action.",
        {"captive_id": "The captive's id"},
    ),
    T.RESCUE_CAPTIVE: ToolText(
        "You try to rescue a captive by force: your strength against the captors' defence. Failure breeds enmity. 1 action.",
        {"captive_id": "The captive's id", "plan": "How you mean to free them"},
    ),
    T.RAISE_ARMY: ToolText(
        "You raise an army from your population (or your disciples); the soldiers leave the population (one without population hires mercenaries and pays from its "
        "wealth). It joins your ongoing war and protects you. Its equipment depends on your craft and what you know. One army per community. 1 action.",
        {
            "name": "The army's name, from your own language",
            "percent": "What percent of the population takes up arms (at most {{ "
            + M
            + ".raise_army_max_pct }}); default {{ "
            + M
            + ".raise_army_default_pct }}",
        },
    ),
    T.APPOINT_COMMANDER: ToolText(
        "You appoint a named mortal (bound to you or from your land) at the head of your army; the commander's strength and charisma reflect on the army. Free, "
        "{{ " + M + ".appoint_commander_per_epoch }} per age.",
        {"mortal_id": "The named mortal's id"},
    ),
    T.BUILD_SPY_NETWORK: ToolText(
        "You build a spy network inside a nearby community: you learn its secrets and gain an advantage in war; if caught, relations sour and war may break out. 1 action.",
        {"target_id": "The community's id", "cover": "The spies' cover: merchant, pilgrim, apprentice…"},
    ),
    T.BARTER: ToolText(
        "You barter with a community or a named mortal: you give resources, items or vessels you own and take what it owns (if you want nothing it is a gift). The value "
        "of the offer, the relationship between you and a die decide acceptance; a successful barter warms the relationship. {{ " + M + ".barter_ap }} action.",
        {
            "target_id": "The community or mortal",
            "give_ids": "Things you own and will give (at most {{ " + M + ".barter_max_items }})",
            "take_ids": "Things it owns that you want (at most {{ " + M + ".barter_max_items }})",
            "terms": "The barter's words",
        },
    ),
    T.LEND: ToolText(
        "You lend to a community or a named mortal: the amount, what is lent and the term (how many ages until repayment). The amount is deducted from your wealth or "
        "prosperity and passes to it (if you have no wealth or prosperity you cannot lend; at most {{ " + M + ".debt_max_amount }}, term at most "
        "{{ "
        + M
        + ".debt_max_term }} ages). Nobody collects; but if it is not paid on time it enters the chronicle and relations cool. {{ "
        + M
        + ".debt_ap }} action.",
        {
            "debtor_id": "The borrower",
            "amount": "The debt amount (at most {{ " + M + ".debt_max_amount }})",
            "what": "What is lent: grain, silver, salt, ship hire…",
            "term_ages": "In how many ages it will be repaid (at most {{ " + M + ".debt_max_term }}); if empty, {{ " + M + ".debt_default_term }}",
        },
    ),
    T.REPAY_DEBT: ToolText(
        "You repay your debt to someone: if you have wealth or prosperity the debt amount passes to them (otherwise you repay in kind); the debt closes and relations warm "
        "(even if overdue). {{ " + M + ".debt_ap }} action.",
        {"creditor_id": "Who you owe"},
    ),
    T.ADOPT: ToolText(
        "You adopt another named mortal: it counts as of your lineage and enters the chronicle. It must be younger than you and near you. "
        "{{ " + M + ".adopt_per_epoch }} per age, {{ " + M + ".adopt_ap }} action.",
        {"child_id": "The named mortal you adopt", "reason": "Why and how you adopt"},
    ),
}
