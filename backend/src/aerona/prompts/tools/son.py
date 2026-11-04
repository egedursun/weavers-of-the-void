from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.domain.enums.entity import EntityType
from aerona.prompts.tools.ids import SonToolId
from aerona.prompts.tools.shared import IMAGE_PROMPT_FIELD, LINK_FIELDS, WORD_FIELDS
from aerona.prompts.tools.text import ToolText

T = SonToolId

CREATION_DESCRIPTION = (
    "Creates a {{ entity.label }} ({{ entity.examples | join(', ') }}). "
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
    "description": "3 to 7 sentences. Concrete, sensory, strange details; how it was born, what it is connected with, how mortals know it.",
    "domain": "If empty, your first domain. The domain used in this creation; one of: {{ domains | join(', ') }}. Your own domains are cheap.",
    "power_level": "Between 1 and 10{% if context.power_ceiling %}; your ceiling is {{ context.power_ceiling }}{% endif %}. Increases the cost.",
    "stats": "Optional stats; leave out any you do not want to set",
    **LINK_FIELDS,
    "image_prompt": IMAGE_PROMPT_FIELD,
    "tags": "Short tags",
    "thread_id": "Which open story (thread#) this creation advances",
    "co_creator_id": "To create together with a covenanted sibling, their id: they pay half the cost, the creation belongs to both of you",
    "location_id": (
        "The id of the entity it is inside ({{ container_labels | join(', ') }})"
        "{% if entity.location_required %}. It must have a location: if you leave it empty it is inferred from the region, place or settlement among your bonds "
        "(or from where the community you bond to is located){% endif %}"
    ),
}

WORSHIPPED_SON_FIELD = {"worshipped_son_id": "Whom they worship (son id){% if entity.type == 'cult' %}; you if empty{% endif %}. Faith flows this way."}

LEGEND_CATEGORY_FIELD = "What the legend would become if belief ever made it walk the world: {{ legend_categories | join(', ') }}; creature for a beast or monster, spirit for a ghost or soul, resource for a sacred spring or vein, relic for a weapon or treasure"
COMMODITY_FIELD = "What its people draw from it: {{ commodities | join(', ') }}; ore feeds forges and coin, grain, livestock and fish feed mouths, timber feeds fuel and ships; empty if none"
MATERIAL_FIELD = "What it is made of or yields, if a material: {{ materials | join(', ') }}; it sets hardness, edge, weight, holiness and taint"

CREATION_EXTRA_FIELDS: dict[EntityType, dict[str, str]] = {
    EntityType.CULT: WORSHIPPED_SON_FIELD,
    EntityType.PEOPLE: WORSHIPPED_SON_FIELD,
    EntityType.SETTLEMENT: WORSHIPPED_SON_FIELD,
    EntityType.FACTION: WORSHIPPED_SON_FIELD,
    EntityType.NATURAL_LAW: {"mechanic": "The law's mechanical effect in the world (if left empty it is read from the law's text): {{ natural_laws }}"},
    EntityType.KNOWLEDGE: {
        "branch": "The knowledge's branch: {{ knowledge_branches }}",
        "learner_ids": "Communities that first learn this knowledge (at most {{ rules.son_tools.knowledge_first_learners }})",
    },
    EntityType.REGION: {"water": "True if the region is a sea or ocean (water) rather than land; default false"},
    EntityType.SPECIES: {
        "traits": "The creature's traits (at most {{ rules.son_tools.creature_max_traits }}): {{ creature_traits }}",
        "body_plan": "The creature's body: {{ body_plans }}; its wounds, armour and fighting follow this body",
    },
    EntityType.VESSEL: {
        "target_world_id": "If the gate, bridge or ship connects to another world, that world's id: a route is opened",
        "vessel_kind": "What it is: {{ vessel_kinds | join(', ') }}; a gate, ship, mount or bridge opens the matching kind of road",
    },
    EntityType.LEGEND: {"legend_category": LEGEND_CATEGORY_FIELD},
    EntityType.RESOURCE: {
        "commodity": COMMODITY_FIELD,
        "material": MATERIAL_FIELD,
        "mechanics": "The resource's strange rules, at most {{ rules.mechanics.resource_max }} (if left empty they are read from its name and text; sacred makes it yours): {{ resource_mechanics }}",
    },
    EntityType.LANGUAGE: {**WORD_FIELDS, "words": "The language's first words (at most {{ rules.son_tools.coin_word_max_words }}); matching the naming rule"},
    EntityType.MORTAL: {"title": 'Their nickname or title ("Salt Seer", "Ash Mouth"); do not bury it in the name, write it here'},
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

STATUS_FREE = "Free."
ESSENCE_GIFT_CAP = "{{ rules.son_tools.gift_max_essence }}"

SON_TOOL_TEXTS: dict[SonToolId, ToolText] = {
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
        {"plan": "Your goal spread over several ages and your next steps"},
    ),
    T.CHOOSE_ANCHOR: ToolText(
        "You choose one of your own creations as the anchor of your existence. While your anchor lives your existence stays firm; if it is destroyed you begin to fade. "
        "Free, {{ rules.son_tools.anchor_per_epoch }} per age.",
        {"entity_id": "Your own canonical creation", "reason": "Why this creation holds your existence"},
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
        "strengthens the relationship. An essence gift does not spend an action; a worshipper transfer costs 1 action. {{ rules.son_tools.gift_per_epoch }} per age.",
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
        "You rebel against your father, the creator god: you no longer recognize his commands and every age you steal from his essence. Your loyal siblings become your "
        "enemies; your father may try to crush the rebellion. Only if your loyalty is below {{ rules.son_tools.rebel_loyalty }}. Does not spend an action.",
        {"proclamation": "The word of the rebellion: why and for what"},
    ),
    T.PRAY_TO_FATHER: ToolText(
        "You pray to your father, the creator god. You may have a request; the answer appears among words in coming ages. Does not spend an action, "
        "{{ rules.son_tools.prayer_per_epoch }} per age.",
        {"message": "Your prayer", "request": "essence, blessing, permission, vengeance, forgiveness or none"},
    ),
    T.MAKE_BOND: ToolText(
        "You declare a narrative bond between two existing things ({{ weavable_bonds | join(', ') }}). It densifies the world's web. Worship, enmity, knowledge, ownership, "
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
        {"entity_id": "The entity's id", "curse": "The words and form of the curse"},
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
            "image_prompt": 'English photoreal prompt of the disaster striking. {% include "shared/image_prompt_rules.md.j2" %}',
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
    T.SEVER_LEY: ToolText(
        "You cut a ley line between two regions: magic stops flowing along it, storms no longer run down it and works on it stop gaining power, "
        "for {{ rules.environment.sever_ley_epochs }} ages. {{ rules.son_tools.sever_ley_essence }} essence, 1 action.",
        {"line_id": "The ley line's id (see the region's ley lines)", "reason": "Why you cut it"},
    ),
    T.SANCTIFY_REGION: ToolText(
        "You sanctify a region: its ground becomes holy, drawing pilgrims who bring wealth and piety, warding off hauntings and strange phenomena. "
        "{{ rules.terrain.sanctify_essence }} essence, 1 action.",
        {"region_id": "The region's id", "sacredness": "How holy, 0-100 (leave out for the usual sanctification)", "reason": "Why you hallow it"},
    ),
    T.CURSE_REGION: ToolText(
        "You loose a danger upon a region: beasts, bandits, monsters, phenomena, disease, avalanches, quicksand or volcanic fire. It harms settlers, herds, "
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
        "You hang a new star in the sky; new worlds may be born around it. {{ rules.cosmic_costs.ignite_star | share_of(rules.son_tools.cosmic_hang_star_pct) }} essence, "
        "{{ rules.son_tools.hang_star_ap }} actions.",
        {"name": "The star's name", "type": "Star type: {{ star_types }}", "description": "What the star is like"},
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
    T.STITCH_LEAK: ToolText(
        "You stitch the tears of the world you are on: the intensity of what leaks in from outside (leakage) decreases by {{ rules.son_tools.stitch_leak_reduction }}. "
        "{{ rules.son_tools.stitch_per_epoch }} per age. {{ rules.son_tools.stitch_cost }} essence, {{ rules.son_tools.stitch_ap }} action.",
        {"how": "With what and how you stitch the tear"},
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
        "FORBIDDEN: you bargain with the nameless thing that came from outside the cosmos. You gain great essence; but leakage rises, your siblings are disgusted by you, "
        "your loyalty to your father unravels and one day the price is demanded. Does not spend an action, {{ rules.son_tools.outer_bargain_per_epoch }} per age.",
        {"outsider_id": "The outer being's id", "request": "What you ask of it"},
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
}
