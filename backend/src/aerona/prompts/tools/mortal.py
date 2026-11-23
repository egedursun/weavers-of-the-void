from aerona.catalog.laws import law_terms_guide
from aerona.domain.enums.culture import CalendarSlot, LegendArchetype, TraditionFunction
from aerona.domain.enums.mind import ActKind
from aerona.prompts.tools.ids import MortalToolId
from aerona.prompts.tools.shared import IMAGE_PROMPT_FIELD, WORD_FIELDS
from aerona.prompts.tools.text import ToolText

T = MortalToolId
M = "rules.mortal_tools"

NAME_FIELD = "A name from your own language"
DESCRIPTION_FIELD = "What it is, how it came to be, what makes it distinctive and concrete"

MORTAL_TOOL_TEXTS: dict[MortalToolId, ToolText] = {
    T.COMMISSION_ARTWORK: ToolText(
        "You commission a work of art. It moves the views of those who hold it, raises the standing of whom it portrays,"
        " and a realm or town pays for it from its treasury. 1 action.",
        {
            "name": "A proper name for it, in the world's naming language",
            "medium": "What kind of work: {{ art_media }}; a performed work lasts only while someone can perform it",
            "subject_id": "Whom or what it portrays (an entity id), if anyone",
            "author_id": "The artist who makes it (a mortal id), if any; a skilled hand makes a finer work",
            "patron_id": "Who commissions and keeps it (a community id); you if empty",
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
            "workings.damage_type": "For destruction: the kind of harm it deals",
            "workings.summon_form": "For a summoning: spirit, beast or undead",
            "technique": "How the rite works: {{ spell_techniques }}; leave it out to use its school's usual technique",
            "form": "What the rite works on: {{ spell_forms }}; leave it out to use its school's usual form",
            "range": "How far it reaches: {{ spell_ranges }}",
            "duration": "How long it lasts: {{ spell_durations }}",
            "target": "What it touches: {{ spell_targets }}",
            "paradigm_id": "The theory of magic it is designed under (a theory id), if any; a truer theory makes it more reliable",
            "myth_id": "A legend it re-enacts (a legend id), if any; a believed myth gives it strength",
            "holder_id": "Ignored: you devise it yourself",
        },
    ),
    T.CAST_RITE: ToolText(
        "You work a rite you know. It must be lawful where it is worked, its requirements met and its price paid; it may backfire. 1 action.",
        {
            "rite_id": "The rite to work (a rite id)",
            "target_id": "Whom or where it is aimed at, if anyone",
            "vessel_id": "Ignored: you work it yourself",
        },
    ),
    T.SOCIALISE: ToolText(
        "You spend time with another mortal where you are, in the way you choose. It moves how each of you feels about the other. 1 action.",
        {"target_id": "The mortal", "interaction": "What you do with them"},
    ),
    T.CHALLENGE_TO_CONTEST: ToolText(
        "You challenge another mortal where you are to a contest of wit "
        "for a stake. The winner gains renown; a famous contest may become the subject of an artwork. 1 action.",
        {"target_id": "The mortal you challenge", "kind": "The contest", "stake": "What is at stake"},
    ),
    T.CHOOSE_METHOD: ToolText(
        "You choose how your community does one kind of work. A method needs its techniques, knowledge and energy; it changes output, "
        "quality, tool wear and pollution, and a method that needs fewer hands puts some out of work. 1 action.",
        {"method": "The method to take up"},
    ),
    T.TEND_HOME: ToolText(
        "As head of your household or its head's spouse, you decide for it: improve your home, take on or let go a servant, "
        "apprentice a child to a master, take in a lodger, match an unmarried member with another household, sell a furnishing, "
        "or move the household to a richer place nearby. Your purse, your home and your people must allow it. 1 action.",
        {"choice": "What your household does"},
    ),
    T.HIRE_SERVANT: ToolText(
        "As head of your household or its head's spouse, you take someone of your town who is free into the service of your household, "
        "on the terms you set: a wage your household pays each epoch, board, or bondage where your law allows it. "
        "You may give the servant duties of the house. 1 action.",
        {
            "household_id": "Your household",
            "terms": "The terms of service: wage, board or bound",
            "wage": "The wage your household pays each epoch when the terms are a wage",
            "duties": "Duties of the house the servant keeps: food, water, fuel, cleaning, textiles, childcare, eldercare, animals, repairs, sickcare or household_rites",
        },
    ),
    T.TAKE_LEISURE: ToolText(
        "You give part of your time to a pursuit you enjoy, at a place if you name one: it lifts your mood and eases your stress, "
        "and a pursuit of travel spends your coin at the place you visit. 1 action.",
        {
            "kind": "The pursuit: conversation, games, sport, music, crafts, collecting, reading, excursion, tourism, drinking, worship_extra, rest, media, dance, storytelling or hunting",
            "venue_id": "Where you pursue it, if anywhere in particular",
        },
    ),
    T.SET_HOUSE_DUTIES: ToolText(
        "As head of your household or its head's spouse, you decide who in your household keeps which duty of the house. "
        "Duties can go only to members and servants of your household; the load of each falls on whoever keeps it. 1 action.",
        {
            "household_id": "Your household",
            "assignments": "Who keeps which duty",
            "assignments.member_id": "A member or servant of your household",
            "assignments.duty": "The duty: food, water, fuel, cleaning, textiles, childcare, eldercare, animals, repairs, sickcare or household_rites",
        },
    ),
    T.CALL_ON_KIN: ToolText(
        "You call on kin of one role for what you need. Kin answer as far as your people's duties bind that role to you: "
        "support for food, coin or care, hosting for shelter, protection for protection. "
        "Kin whom no strong duty binds may refuse, and a refusal counts as a breached duty. 1 action.",
        {
            "role": "Which kin: parent, child, sibling, grandparent, grandchild, parent_sibling_first_line, parent_sibling_second_line, "
            "sibling_child, cousin_parallel, cousin_cross, parent_in_law, child_in_law, sibling_in_law, co_spouse, chosen_kin, godparent, sworn_kin or foster_kin",
            "need": "What you need: food, coin, care, shelter or protection",
        },
    ),
    T.CONVENE_KIN_GROUP: ToolText(
        "You call your kin group together on one matter: choose_head to choose a head, share_land to share the yield of the kin's land "
        "with members in need, feud to answer harm done to its members, marriage to tighten the rule against marrying within the kin, "
        "or migrate to bring its members to where you are. 1 action.",
        {
            "group_id": "A kin group you belong to",
            "agenda": "The matter: choose_head, share_land, feud, marriage or migrate",
        },
    ),
    T.RAISE_CHILD: ToolText(
        "As a parent of a child or the head of its household, you raise it by the ways you weigh: "
        "they move what the child will value, and harsh ways leave stress. 1 action.",
        {
            "child_id": "The child you raise",
            "techniques": "The ways you raise it, each with a weight",
            "techniques.technique": "The way: example, instruction, praise, shame, punishment, ritual_ordeal, storytelling, play, "
            "apprenticeship, schooling, peer_group or age_set",
            "techniques.weight": "How much of the upbringing goes this way, from 0 to 100",
        },
    ),
    T.FOUND_SCHOOL_METHOD: ToolText(
        "You set the way a school teaches: its theory sets how fast its pupils learn, and its depth whether it teaches few things deeply or many broadly. 1 action.",
        {
            "school_id": "The school",
            "theory": "The theory: rote, dialectic, apprenticeship, discovery, ritual_transmission, examination, network_learning or mind_transfer",
            "depth": "From 0 for breadth to 100 for depth",
        },
    ),
    T.SEEK_RECOGNITION: ToolText(
        "As a parent of a child whose standing among your people is less than full, you have it recognised by the way your people allow, "
        "paying what that way costs; a recognised child inherits and may hold office as one born in full standing. 1 action.",
        {
            "child_id": "Your child",
            "path": "The way: recognition, adoption, payment, rite or none",
        },
    ),
    T.TAKE_RESTRAINT_VOW: ToolText(
        "You take a vow of restraint of your own will. Breaking it costs you honour. 1 action.",
        {
            "kind": "The vow: celibacy or fidelity",
            "term": "For how many epochs, from 0 for life to 10",
        },
    ),
    T.LEAD_YOUTH: ToolText(
        "In your years of youth, you take the lead of a youth group of your town and turn it to a purpose: "
        "its purpose moves the town's order, crime or unrest and what its members come to value. 1 action.",
        {
            "group_id": "The youth group of your town",
            "purpose": "The purpose: sport, service, courtship, defence, faith, mischief, crime or politics",
        },
    ),
    T.REFORM_YOUTH: ToolText(
        "As an elder of your town, you set a youth group to a measure: schooling raises its members' learning, service and sport turn it to those, "
        "and discipline raises its standing and turns trouble to defence. 1 action.",
        {
            "group_id": "The youth group of your town",
            "measure": "The measure: schooling, service, sport or discipline",
        },
    ),
    T.SET_POPULATION_POLICY: ToolText(
        "As the ruler of a realm, you set its policy on its numbers: an aim and the instruments that serve it, each with a strength. "
        "Instruments shift births, movement, health and grievance in the realm's towns; enforcing them costs the treasury, and harsh ones meet resistance. 1 action.",
        {
            "aim": "The aim: grow, hold, shrink, rebalance_age, rebalance_class, settle_land, empty_land, keep_kind, mix_kinds or none",
            "instruments": "The instruments, each with a strength",
            "instruments.instrument": "The instrument: birth_reward, birth_tax, union_law, child_limit, child_support, inheritance_rule, settlement_grant, "
            "migration_permit, migration_ban, expulsion, resettlement, recruitment_abroad, health_campaign, faith_teaching or made_birth",
            "instruments.strength": "Its strength, from 0 to 100",
            "target_node_id": "A people or place within your realm the policy aims at, or none for the whole realm",
            "reason": "Why you set it",
        },
    ),
    T.OPEN_SHOP: ToolText(
        "You open a shop in your town for the goods you name. It sells from its stock each season for its margin; "
        "a town with shops is supplied better than one without. 1 action.",
        {
            "form": "The form: stall, shop, house_trade, peddler, market_hall, warehouse_outlet, order_house or network_store",
            "goods_kinds": "The goods it carries",
            "structure_id": "A building of your town it opens in, or none",
        },
    ),
    T.PROMOTE: ToolText(
        "You spread word of your wares or brand. Reach raises a brand's reputation each season at a cost; "
        "claims that are not true may be found out, costing reputation and honour, and a fine where fair dealing is law. 1 action.",
        {
            "medium": "The medium: crier, sign, display, patronage, gift or media",
            "claim_accuracy": "How true the claims are, from 0 to 100",
            "reach": "How far the word goes, from 0 to 100",
            "commodity": "The good it speaks of, or none",
            "brand_id": "Your brand it speaks of, or none",
        },
    ),
    T.LEASE_OUT: ToolText(
        "You lease land, a building, a vessel, an item or a beast you own to another for a rent each season and a term. "
        "If the lessee cannot pay, the lease ends in eviction, a debt or a case at court as you set. 1 action.",
        {
            "thing_id": "The thing you own",
            "lessee_id": "Who takes it",
            "rent": "The rent each season, from 0 to 100",
            "term": "How many epochs it runs, from 1 to 10",
            "on_default": "What follows an unpaid rent: eviction, court or debt",
        },
    ),
    T.BEGIN_WORKS: ToolText(
        "As the ruler of a realm, you begin public works on a route, region or town of your realm, setting a budget aside from the treasury. "
        "They advance a stage each season their labour is paid or pressed; paid labour costs the treasury, corvée and bound labour raise grievance, "
        "and finished works change roads, bridges, water, walls, stores, harbours or prosperity. 1 action.",
        {
            "kind": "The works: road, bridge, canal, rail_line, aqueduct, dam, drainage, harbour_works, walls, granary_system, sewer, power_line, "
            "network_line, terraforming_stage, megastructure_stage or grown_works",
            "route_or_region_id": "The route, region or town they lie on",
            "labour": "The labour: paid, corvee, bound, made_minds or constructs",
            "budget": "What the treasury sets aside for them",
        },
    ),
    T.FUND_WORKS: ToolText(
        "You give from your own wealth to public works being built. 1 action.",
        {"works_id": "The works", "amount": "How much you give"},
    ),
    T.FOUND_ENTERPRISE: ToolText(
        "As the ruler of a realm, you found a state enterprise: it earns for the treasury each season, a monopoly earns more and starves rival shops, "
        "and a corrupt manager may skim it. 1 action.",
        {
            "sector": "The good it deals in, or none",
            "form": "The form: monopoly, royal_works, state_company, licence_holder, arsenal or mint",
            "manager_id": "Who manages it: an official, a company or a made mind, or none",
        },
    ),
    T.FORM_CARTEL: ToolText(
        "You bind sellers of one good in a market into a compact, for an organisation you head that sells there. The compact raises "
        "prices while its discipline holds; it weakens each epoch and breaks when cheating pays, and a law against cartels can expose and fine it. 1 action.",
        {
            "member_ids": "The sellers who join, your own organisation among them",
            "goods_kind": "The good they agree on",
            "market_id": "The market town",
            "aim": "What they agree on: price, quota, territory or bid_rigging",
            "terms": "The price or the quota they agree, or none",
        },
    ),
    T.START_PRICE_WAR: ToolText(
        "An organisation you head sells a good below its usual price in a market to drive its rivals out. It pays for the cut each epoch "
        "from its treasury, and its rivals lose too; whoever runs out first loses, and beaten rivals go before the court for their debts. 1 action.",
        {"market_id": "The market town", "goods_kind": "The good", "cut": "How far below the usual price you sell, in a hundred"},
    ),
    T.REPORT_CARTEL: ToolText(
        "You tell of a compact between sellers. Where the law forbids cartels it is broken and its members are fined; where it does not, "
        "it is no longer secret. 1 action.",
        {"cartel_id": "The compact you tell of"},
    ),
    T.ARGUE_DOCTRINE: ToolText(
        "As one of a faith's clergy, argue how it should hold the divine on one axis; your theology decides whether it is heard. 1 action.",
        {
            "faith_id": "The faith you serve",
            "conception_axis": "The axis ({{ conception_axes | join(', ') }})",
            "stance": "How the divine is on it: for count {{ divine_counts | join(', ') }}; for nearness {{ divine_nearness | join(', ') }}; "
            "for personhood {{ divine_personhood | join(', ') }}; for creator {{ creator_places | join(', ') }}",
        },
    ),
    T.DRIVE_OFF_GROUP: ToolText(
        "Drive at a group of creatures in your land: hunt them to thin their numbers, drive them off with fire or noise into the next land, "
        "or appease them with an offering so they leave your towns be for a while. 1 action.",
        {"group_id": "The group", "means": "How you drive at them ({{ drive_means | join(', ') }})"},
    ),
    T.WARN_COAST: ToolText(
        "Warn the coast you stand on of the sea by a way your people watch the waters, so that a wave in the coming epoch finds them ready "
        "and kills fewer. 1 action.",
        {"region_id": "The coast you stand on", "method": "How you watch the waters ({{ observation_methods | join(', ') }})"},
    ),
    T.DIG_DEEPER: ToolText(
        "Dig deeper beneath the land you stand on, adding {{ rules.underground.dig_step }} to its mining; the next layer of its ground "
        "({{ rock_kinds | join(', ') }}) is reached when the mining goes deep enough. 1 action.",
        {"region_id": "The land you stand on"},
    ),
    T.DIVERT_RIVER: ToolText(
        "Turn the river of the land you stand on through a canal of your people into a neighbouring land. Fields and wells follow the "
        "water; a realm downstream that loses it holds the turning against those who rule your land. 1 action.",
        {"region_id": "The land you stand on", "to_region_id": "The neighbouring land the river should flow into"},
    ),
    T.SEAL_DEPTH: ToolText(
        "Seal the deep beneath a place in the land you stand on ({{ seal_kinds | join(', ') }}, though no mortal makes a god's seal). "
        "A pact names an oath you swore to those below, a power names a power you hold and a grown barrier names a living line your people keep. 1 action.",
        {
            "place_id": "The place whose deep you seal",
            "kind": "What holds the seal",
            "oath_id": "For a pact: your oath",
            "power_id": "For a power: your power",
            "line_id": "For a grown barrier: your people's living line",
        },
    ),
    T.BORE: ToolText(
        "Bore down to a body of water or a trap beneath the land you stand on ({{ underground_strata | join(', ') }}); only the aquifer, the "
        "ocean under the ice and a reservoir can be bored. A bore into water may flood. 1 action.",
        {"region_id": "The land you stand on", "stratum": "What you bore to"},
    ),
    T.DRILL_RESERVOIR: ToolText(
        "Drill the reservoir beneath the land you stand on for fuel; it yields {{ rules.underground.reservoir_draw }} at a time and may blow out "
        "under high pressure. 1 action.",
        {"region_id": "The land you stand on"},
    ),
    T.COMMEMORATE: ToolText(
        "Mark the land you stand on with a memory of what happened there ({{ region_memory_kinds | join(', ') }}); the land keeps it at "
        "magnitude {{ rules.land_memory.commemorate_magnitude }}. 1 action.",
        {"region_id": "The land you stand on", "memory": "What the land should remember", "title": "What it is called"},
    ),
    T.CLEANSE_LAND: ToolText(
        "Lift poison from the land you stand on, by works, by a rite or by a power ({{ cleansing_methods | join(', ') }}). Works lift "
        "{{ rules.scars.cleanse_works_depth }}, a rite {{ rules.scars.cleanse_rite_depth }} and a power {{ rules.scars.cleanse_power_depth }} of "
        "its depth; a power needs land with magic density of at least {{ rules.scars.cleanse_power_magic }}. 1 action.",
        {"region_id": "The land you stand on", "method": "How you cleanse it"},
    ),
    T.CONFER_HONOUR: ToolText(
        "As head of a realm, faith or order, confer one of its honours on someone for a deed on record. They gain renown, goodwill toward "
        "it and its privileges. 1 action.",
        {"honour_kind_id": "The honour", "holder_id": "The one you honour", "deed_incident_id": "The deed it rewards"},
    ),
    T.REVOKE_HONOUR: ToolText(
        "As head of the realm, faith or order that conferred it, take an honour back; its holder is shamed. 1 action.",
        {"honour_id": "The honour held"},
    ),
    T.FOUND_HONOUR: ToolText(
        "As head of a realm, faith or order, found a new honour it can confer, ranked above those it has, with its privileges and a "
        "limit on holders (0 for none). 1 action.",
        {
            "conferrer_id": "The realm, faith or order you head",
            "name_reason": "The name of the honour",
            "privileges": "What it grants ({{ honour_privileges | join(', ') }})",
            "limit": "How many may hold it at once, 0 for any number",
        },
    ),
    T.USE_FERTILITY_MEANS: ToolText(
        "Take up a means your people know to prevent, seek or end conception. Where your people frown on it you use it in secret, and it "
        "may come to light. 1 action.",
        {"means": "The means you take up"},
    ),
    T.PLACE_GRAVE_GOODS: ToolText(
        "Lay things you own with the dead in a grave where you are. They leave you and stay with the dead. 1 action.",
        {"grave_id": "The grave", "item_ids": "The things you lay"},
    ),
    T.ROB_GRAVE: ToolText(
        "Rob a grave where you are of the goods laid in it. A watched or trapped grave may catch you, a cursed one may answer where the land "
        "allows, and the kin and people of the dead hold it against you. 1 action.",
        {"grave_id": "The grave"},
    ),
    T.GUARD_GRAVE: ToolText(
        "Pay to set a guard over a grave where you are: hidden, sealed, watched, trapped, or, where the laws of the land allow, cursed or warded. 1 action.",
        {"grave_id": "The grave", "guard": "The guard to set"},
    ),
    T.INTERPRET: ToolText(
        "Skilled in tongues, you carry the words of an exchange between two sides who share none, faithfully or slanted toward your own "
        "side. A slant may win your side more and may come to light, wronging the other and you with it. 1 action.",
        {"event_id": "The exchange", "slant": "Whether you slant it toward your own side"},
    ),
    T.STIR_FEELING: ToolText(
        "You stir a feeling in the place you are in or in your own household, the further the more charismatic you are. Strong feelings "
        "spread to those around and along bonds, feed crowds and lean the choices of a town. 1 action.",
        {"place_or_household_id": "The place you are in, or your household", "feeling": "The feeling"},
    ),
    T.FAVOUR_CHILD: ToolText(
        "You favour one of your children, or of the house you head. Where the custom of inheritance leaves a choice, the favoured child "
        "comes first to it; the others may grow rivals. 1 action.",
        {"child_id": "The child"},
    ),
    T.DISOWN: ToolText(
        "You cast one of your children, or of the house you head, out of the family: they lose their place in the house and the inheritance, "
        "may found a line of their own, and hold it against you. It can be mended. 1 action.",
        {"member_id": "The one you cast out", "reason": "Why: disobedience, marriage, faith, crime or rivalry"},
    ),
    T.RECONCILE_KIN: ToolText(
        "You take back one you cast out of the family, restoring their place. 1 action.",
        {"member_id": "The one you take back"},
    ),
    T.PROTECT_AREA: ToolText(
        "You set a land or a site within it under protection, barring uses there. Barred uses fall by the protection's strength and its "
        "wardens, and the land and its wildlife recover; want around it draws poachers, and towns whose livelihood it bars grow poorer and "
        "restless. Protection by law needs one who rules the land. 1 action.",
        {
            "region_or_site_id": "The land, or a site within it",
            "basis": "By what right: law, faith, custom, charter or divine_decree",
            "banned_uses": "The uses barred: hunting, logging, farming, mining, settlement, entry, fishing or building",
        },
    ),
    T.PROTECT_SPECIES: ToolText(
        "You set a living kind under protection. A hunting ban spares it; a trade ban starves its poachers of buyers; a breeding programme "
        "raises its numbers; reintroduction brings it back to lands it left that can still hold it; a habitat guard lets its lands' forests "
        "regrow. 1 action.",
        {
            "species_id": "The living kind",
            "measures": "The measures: hunting_ban, trade_ban, breeding_programme, reintroduction or habitat_guard",
            "basis": "By what right: law, faith, custom, charter or divine_decree",
        },
    ),
    T.REINTRODUCE: ToolText(
        "You try to bring a living kind back to a land it left, if that land can still hold it. It may not take. 1 action.",
        {"species_id": "The living kind", "region_id": "The land"},
    ),
    T.SET_LAND_USE_RULE: ToolText(
        "As one who rules a settlement you set a rule for its land, for the whole place or one district. Rules of use decide which districts "
        "may grow there and ease the nuisance next to homes; limits cap how high homes rise or how dense districts grow; a required material "
        "or fire spacing cuts the spread of fire; frontage and green share make districts more desirable. Every rule raises the cost of "
        "building, and a weakly enforced rule on valuable land is evaded. 1 action.",
        {
            "settlement_id": "The settlement",
            "district_id": "One district; leave empty for the whole place",
            "rule": "The rule: allowed_uses, banned_uses, height_limit, density_limit, build_material, fire_spacing, frontage_rule or green_share",
            "values": "What the rule names: kinds (district kinds) for allowed or banned uses, level for a height or density limit, material for a build material",
        },
    ),
    T.PROVIDE_SERVICE: ToolText(
        "As one who rules a settlement you found or fund one of its services. A service reaches its districts as far as its budget pays for "
        "them: refuse and street cleaning keep it clean, water distribution brings water, night watch keeps order, burial grounds take the "
        "dead, market inspection keeps the markets honest, lighting cuts night crime and lengthens trade. 1 action.",
        {
            "settlement_id": "The settlement",
            "service": "The service: refuse, lighting, water_distribution, street_cleaning, night_watch, burial_ground or market_inspection",
            "provider_id": "A body you lead that pays for it; leave empty for the settlement itself",
            "budget": "What it may spend each epoch",
        },
    ),
    T.JOIN_SETTLEMENTS: ToolText(
        "As one who rules several settlements of one world you join them into one city around the first, which keeps the others as quarters. "
        "Under one council or the core's rule the core's laws spread to them; under one council their unrest is shared. 1 action.",
        {
            "settlement_ids": "The settlements; the first is the core",
            "governance": "How it is governed: one_council, federated_councils or ruled_by_core",
        },
    ),
    T.LAUNCH_CAMPAIGN: ToolText(
        "As the leader of a realm you send one of its hosts along a way to another world. Its carriers set how many cross; some are lost "
        "on the crossing; on arrival it must win the space around the world before it can land, and once landed it is supplied along the "
        "way, starving if the space is lost. 1 action.",
        {"attacker_id": "The realm that sends it", "target_world_id": "The world it goes to", "route_id": "The way it crosses", "army_id": "The host"},
    ),
    T.CONTEST_ORBIT: ToolText(
        "As the leader of a realm whose host is at a world you fight for the space around it, by the host's vessels and numbers. Who holds it "
        "may strike the enemy below, take a toll of every way that reaches the world, and cut the enemy's signals. 1 action.",
        {"world_id": "The world", "fleet_id": "The host that fights"},
    ),
    T.LEAD_MIGRATION: ToolText(
        "You lead the people of the settlement you live in or rule to another world joined to yours by an open way. They leave over epochs, "
        "as many as the way carries and the world they seek lets in. 1 action.",
        {
            "community_id": "The settlement",
            "to_world_id": "The world they seek",
            "cause": "Why they go: flight, land_hunger, faith_call, exile, labour_draw, world_dying or resettlement",
        },
    ),
    T.BEGIN_MASS_WEAPON: ToolText(
        "As the leader of a realm, organisation, faith or league you begin making a weapon whose harm reaches a whole settlement, region "
        "or world. It needs the means its harm and reach call for, costs the treasury each epoch, and passes through stages its rivals "
        "may see and answer by making their own. 1 action.",
        {
            "holder_id": "Whose arsenal it joins",
            "harm": "Its harm: blast, fire, poison, disease, radiation, swarm, field, rite or divine_relic",
            "reach": "Its reach: settlement, region or world",
        },
    ),
    T.DECLARE_POSTURE: ToolText(
        "As the leader of an arsenal's holder you declare how it would use its weapons, toward one rival or all. A credible posture holds "
        "rivals back from attacking; a posture with no ready weapon behind it may be exposed as a bluff. 1 action.",
        {
            "holder_id": "Whose posture it is",
            "toward_id": "Toward whom; leave empty for all",
            "posture": "The posture: none, declared, ambiguous, first_use, retaliation_only or shared_with_league",
        },
    ),
    T.USE_MASS_WEAPON: ToolText(
        "As the leader of an arsenal's holder you loose a ready weapon of mass harm on a target within its reach. It kills across its "
        "reach, may burn, sicken or leave its harm in the land, is remembered by those it struck and brings the end of the world nearer. 1 action.",
        {"weapon_id": "The weapon", "target_id": "What it strikes: a settlement, or a place within its region or world"},
    ),
    T.CLEAR_REMNANTS: ToolText(
        "You pay to clear what war left in a land, which harms those who live there until it fades or is cleared. 1 action.",
        {"region_id": "The land", "budget": "What you spend, from 100"},
    ),
    T.SET_OCCUPATION_RULE: ToolText(
        "As the ruler of an occupier you set how an occupied land is ruled. Each rule sets what you take, how fast your control grows, "
        "how much the locals resent it and what ruling them costs; civil rule and annexation extend your laws over the land and bring "
        "settlers, and annexation takes the land once your control is high enough. 1 action.",
        {"occupation_id": "The occupation", "rule": "The rule: military, civil_by_occupier, local_puppet, annexation or protectorate"},
    ),
    T.COLLABORATE: ToolText(
        "Living under an occupation, you serve the occupier for a reward. Those who serve cut the cost of ruling and, informing or "
        "policing, the partisans' raids; the partisans may come to know and kill them, and a liberated land may judge them. 1 action.",
        {"occupation_id": "The occupation", "kind": "How you serve: administration, police, informing, trade, militia or propaganda"},
    ),
    T.IMPOSE_MEASURE: ToolText(
        "As the ruler of an occupier you impose a measure on an occupied land. Measures cut the partisans' raids while they last; most "
        "raise resentment, and hostages, collective punishment and deportation are remembered against you. Deportation carries people "
        "off as captives; requisition takes from the towns' treasuries; an amnesty offer lowers resistance. 1 action.",
        {
            "occupation_id": "The occupation",
            "measure": "The measure: curfew, hostages, collective_punishment, deportation, requisition, ban_on_gathering or amnesty_offer",
            "strength": "How hard it is pressed, from 1 to 100",
        },
    ),
    T.EXPOSE_COLLABORATOR: ToolText(
        "Living under an occupation, you expose one who serves the occupier, so that the partisans know them. 1 action.",
        {"collaboration_id": "The service to expose"},
    ),
    T.RAISE_RESTORATION: ToolText(
        "From the old lands of a fallen realm, or by your claim to it, you begin a movement to raise it again under its old name, "
        "laws and rights. Its memory fades unless it is kept, grows with grievance and rises when strong enough. 1 action.",
        {
            "fallen_polity_id": "The fallen realm",
            "bases": "The grounds: bloodline, faith, law, memory or foreign_backing",
            "territory_ids": "The old lands it seeks; empty seeks them all",
        },
    ),
    T.RESTORE_POLITY: ToolText(
        "As the leader of a restoration whose memory is strong enough, you raise the fallen realm again, unless the realms that hold "
        "its old lands are steady enough to put the rising down. Old laws that no longer fit cost the new realm stability. 1 action.",
        {"restoration_id": "The restoration"},
    ),
    T.PROMOTE_CULT: ToolText(
        "You promote the cult of yourself, or of the ruler of the realm you live or serve in, by instruments. The cult lends the ruler "
        "legitimacy and quiets dissent at a cost to the treasury and to the public's sincerity, which falls when the cult runs ahead of "
        "the realm's results; a ban on criticism punishes mockery. 1 action.",
        {
            "leader_id": "The leader",
            "instruments": "The instruments: images_in_public, official_biography, holidays, oaths_of_loyalty, naming_of_places, teaching_in_schools, staged_gatherings or ban_on_criticism",
        },
    ),
    T.TEAR_DOWN_CULT: ToolText(
        "As the ruler of a realm you tear down the cult of a leader in it. 1 action.",
        {"cult_id": "The cult"},
    ),
    T.OPEN_RECKONING: ToolText(
        "As the ruler of a realm you open a reckoning with the servants of a fallen regime by the measures you choose. Harsh measures may "
        "drive the old servants to revolt or flight; weak ones leave them in power and the victims aggrieved. 1 action.",
        {
            "polity_id": "Your realm",
            "fallen_regime_id": "The fallen ruler or regime, if one is named",
            "measures": "The measures: tribunal, truth_inquiry, office_bar, amnesty, amnesty_for_confession, restitution, reparation_to_victims, memorial or record_opening",
        },
    ),
    T.TRY_SERVANT: ToolText(
        "As the ruler of the realm you bring one to trial in an open reckoning for deeds the record ties to them; the tribunal convicts or acquits at once. 1 action.",
        {"reckoning_id": "The reckoning", "accused_id": "The accused", "incident_ids": "The recorded deeds you name"},
    ),
    T.CALL_REFERENDUM: ToolText(
        "As the ruler of a realm, town or league you put a question to its people, voted by those its law lets vote. A binding vote "
        "changes the law or the state at once; a vote that does not bind presses the ruler, who loses legitimacy by ignoring it. 1 action.",
        {
            "polity_id": "The realm, town or league whose people vote",
            "subject": "What is asked: law, constitution, independence, union, treaty, war, transition, recall or faith",
            "question_target_id": "What the question is about: the law, the town that would leave, the realm to join, the treaty, the foe, the office holder or the faith",
            "binding": "Whether the result binds",
        },
    ),
    T.CAMPAIGN_FOR_VOTE: ToolText(
        "You campaign for one side of a vote still to be held: with money, through an outlet you own, by a speech you gave that was "
        "heard, or by fraud, which may be found out and void the vote. 1 action.",
        {"referendum_id": "The vote", "side": "yes or no", "means": "money, media, speech or fraud"},
    ),
    T.LEAVE_OFFICE: ToolText(
        "You leave an office of a realm you hold, or the headship of an organisation, by your own choice, handing it to one you name "
        "or to the rule of succession, on the conditions you ask. One who leaves keeps some standing and may come back while the office "
        "stands empty or weak. 1 action.",
        {
            "office_id": "The office of a realm you hold, if you leave one",
            "org_id": "The organisation you head, if you leave its headship",
            "kind": "How you leave: abdication, retirement, resignation, withdrawal_to_religion or exile_by_choice",
            "in_favour_of_id": "Whom you hand it to, or none to leave it to succession",
            "conditions": "What you keep: keep_title, keep_lands, pension or safe_conduct",
        },
    ),
    T.RETURN_TO_OFFICE: ToolText(
        "You come back to an office you left, while it stands empty or weak; one who retired does not come back. 1 action.",
        {"departure_id": "The leaving you take back"},
    ),
    T.FOUND_LEAGUE: ToolText(
        "As the ruler of a realm you found a standing league with other realms at peace with each other. Members pay dues, vote by "
        "the basis you choose and are bound by what passes; the aims decide its organs and what it does for its members. 1 action.",
        {
            "polity_ids": "The founding realms, yours among them",
            "aims": "What it is for: defence, trade, customs_union, currency_union, law, faith, peace, research or migration",
            "vote_basis": "How it decides: one_member_one_vote, by_population, by_dues or by_veto_holders",
        },
    ),
    T.JOIN_LEAGUE: ToolText(
        "As the ruler of a realm you ask a league to take it in; its assembly votes at once. 1 action.",
        {"league_id": "The league", "polity_id": "Your realm"},
    ),
    T.TABLE_LEAGUE_MOTION: ToolText(
        "As the ruler of a voting member you lay a motion before an organ of the league; it is voted at once by the league's basis, "
        "and a veto blocks it. What passes binds the members as far as they obey. 1 action.",
        {
            "league_id": "The league",
            "organ": "Which organ hears it: assembly, council, court, secretariat or force",
            "kind": "What is moved: admit, expel, sanction, common_tariff, common_force, ruling, budget or mediation",
            "subject_id": "Whom or what it concerns: a realm to admit, expel, sanction or mediate, a foe for the common force, or a law to rule on",
        },
    ),
    T.LIST_SECURITY: ToolText(
        "You list claims on an issuer you rule or head on an exchange: shares in its results, or bonds, annuities or notes it pays "
        "interest on and repays when they fall due, or futures. The issuer pays the listing fee and holds every unit until it sells "
        "them. 1 action.",
        {
            "issuer_id": "The issuer",
            "kind": "What is listed: share, bond, annuity, note or future",
            "amount": "How many units",
            "exchange_id": "The exchange",
        },
    ),
    T.TRADE_SECURITY: ToolText(
        "You buy a listed claim from its largest holder or sell yours back to its issuer at the price of the exchange. You may buy partly "
        "on credit up to the exchange's margin; if the price falls far, what you hold on credit is sold off and you owe the rest. 1 action.",
        {"security_id": "The listed claim", "amount": "How many units", "side": "buy or sell"},
    ),
    T.SET_MONETARY_POLICY: ToolText(
        "You set the policy of a monetary authority you hold or rule: its rate and its aim. Lenders take the rate as their base a season "
        "later; a low rate raises borrowing and prices, a high rate the reverse. Issuing to fund the state fills the treasury and lowers "
        "trust; a peg holds the currency to another currency or a good while reserves last. 1 action.",
        {
            "authority_id": "The authority",
            "rate": "Its policy rate, from 0 to 100",
            "aim": "Its aim: stable_value, cheap_credit, fund_the_state, peg, growth or none",
            "peg_currency_id": "The currency to hold it to, for a peg",
            "peg_goods_kind": "The good to hold it to, for a peg, instead of a currency",
        },
    ),
    T.FOUND_MONETARY_AUTHORITY: ToolText(
        "As the ruler of a currency's issuer you set someone over it as its monetary authority, with an independence that decides how "
        "far rulers can press it to issue before wars and elections, and an aim. 1 action.",
        {
            "currency_id": "The currency",
            "holder_id": "Who holds the authority: a ruler, an office, a temple, a bank, a company or a council",
            "independence": "How far it stands apart from rulers, from 0 to 100",
            "aim": "Its aim: stable_value, cheap_credit, fund_the_state, peg, growth or none",
        },
    ),
    T.FOUND_WORKER_BODY: ToolText(
        "You found a body of the workers of your town for one or more trades: it gathers members and dues into a strike fund, bargains "
        "with those who hire them and can call them out. The law of the town decides whether it is banned, tolerated, recognised or "
        "compulsory. 1 action.",
        {
            "form": "Its form: craft_union, industrial_union, general_union, companion_society, mutual_aid, worker_cooperative or made_mind_collective",
            "trades": "The trades it speaks for: farming, herding, fishing, mining, crafting, trade, soldiering, clergy, scholarship, building, service, idle, transport, administration, gathering, industry or arts",
            "settlement_id": "Your town",
        },
    ),
    T.BARGAIN_CONTRACT: ToolText(
        "You bargain for a worker body you lead with one who hires its trade. Terms follow the strength of each side: the body's members, "
        "fund, solidarity and standing in law against the hirer's riches and the bound workers or made minds who could do the work. A much "
        "stronger hirer may lock the workers out; a body far weaker may take to a strike instead of agreeing. 1 action.",
        {
            "worker_body_id": "The body you lead",
            "hirer_id": "The one who hires its trade",
            "demands": "What you press for: wage, hours, safety, rest, keep or recognition",
        },
    ),
    T.CALL_DISPUTE: ToolText(
        "You call the members of a worker body you lead out against the one who hires its first trade. Output stops in that trade while it "
        "lasts; the fund pays those out until it is spent, and the hirer loses each epoch. 1 action.",
        {
            "worker_body_id": "The body you lead",
            "act": "How they press: strike, go_slow, boycott, occupation_of_works or sabotage",
            "demand": "What they press for: wage, hours, safety, rest, keep or recognition",
        },
    ),
    T.LOCK_OUT: ToolText(
        "As a hirer, or the head of one, you shut a worker body's members out of your works until they yield. You lose what they would "
        "have made; their fund pays them while it lasts. 1 action.",
        {
            "hirer_id": "Yourself or the organisation you head that hires them",
            "worker_body_id": "The body whose members you shut out",
            "demand": "What you press for: wage, hours, safety, rest, keep or recognition",
        },
    ),
    T.CAST_ORG_VOTE: ToolText(
        "You cast your vote on the decision body of an organisation where you hold a seat, for or against a course; your vote joins those "
        "who back the same course, and the body votes at once. A course passes when it gains the quorum. 1 action.",
        {
            "org_id": "The organisation whose body you sit on",
            "motion": "The course voted on: grow, hold, specialise, diversify, expand_abroad, integrate_up, integrate_down, lobby, research or withdraw",
            "vote": "Your vote: for or against",
        },
    ),
    T.SEEK_HEADSHIP: ToolText(
        "You stand for the headship of an organisation you belong to or own. Where the headship is bought you pay for it at once; where it is "
        "chosen, you gather backers on its body and win when the term ends and its selection rule chooses you. 1 action.",
        {"org_id": "The organisation"},
    ),
    T.SPLIT_ORG: ToolText(
        "You lead your clique out of an organisation and found a rival, taking members and a share of its holdings as large as the clique's "
        "votes. A clique needs enough of the body's votes to leave with a share. 1 action.",
        {"org_id": "The organisation", "clique_id": "The clique you lead", "name_reason": "The name of the new organisation"},
    ),
    T.BID_FOR_ORG: ToolText(
        "You bid, for an organisation you head or a realm you rule, to take in another organisation. Its body may accept, or resist a hostile "
        "bid by seeking a friendly buyer or setting harsher terms; a closed bid joins its members, holdings and debts to yours. 1 action.",
        {
            "acquirer_id": "The organisation you head, or the realm you rule for an absorption",
            "target_id": "The organisation you bid for",
            "kind": "The bid: merger, friendly_acquisition, hostile_takeover, buyout or absorption_by_polity",
            "price": "The price you offer, or none to offer its worth",
        },
    ),
    T.FUND_RESEARCH: ToolText(
        "You set aside a budget from an organisation you head to research a technique its home could reach next, or a design. Its staff "
        "draw on the budget each epoch; when the work is done the organisation holds what it found, secret until it leaks out or is stolen. 1 action.",
        {
            "org_id": "The organisation you head",
            "technique": "The technique to pursue, or none when you pursue a design",
            "design_id": "The design to pursue, or none when you pursue a technique",
            "budget": "The treasury you set aside",
        },
    ),
    T.FILE_INSOLVENCY: ToolText(
        "You take an organisation you head before its realm's court for its debts: creditors claim, its holdings are weighed and shared, and "
        "the case ends by the path you ask for. 1 action.",
        {
            "org_id": "The organisation you head",
            "path": "How it is settled: liquidation, restructuring, rescue_by_owner, rescue_by_polity or seizure_by_creditor",
        },
    ),
    T.FOUND_OUTLET: ToolText(
        "You found an outlet in your town that puts out word to its audience each season. Its reach grows with its staff and medium; "
        "its stance and lean colour what it tells, and its trust falls when what it spreads is found false. 1 action.",
        {
            "name": "The outlet's name",
            "medium_id": "A recorded medium it uses, or none",
            "stance": "A value it leans on, or none",
            "lean": "How far it leans, from -100 against to 100 for",
            "funding": "How it is paid for: sales, patronage, advertising or state",
        },
    ),
    T.PUBLISH_ITEM: ToolText(
        "Your outlet puts out an item. When it reports a happening, its accuracy follows what happened and your slant; "
        "slanted items move the opinion of its audience on their subject. 1 action.",
        {
            "outlet_id": "Your outlet",
            "kind": "The item: news, opinion, record_of_event, entertainment, instruction, promotion, devotion or official",
            "subject_incident_id": "The happening it tells of, or none",
            "subject_node_id": "Whom or what it speaks of, or none",
            "slant": "How it leans, from -100 against to 100 for",
        },
    ),
    T.CENSOR_OUTLET: ToolText(
        "As the ruler of a realm, you act on an outlet in it: censor halves its reach, license also costs it trust, seize takes it for the realm, close ends it. 1 action.",
        {"outlet_id": "The outlet", "measure": "The measure: censor, license, seize or close"},
    ),
    T.EXPOSE_HYPOCRISY: ToolText(
        "You show that someone professes a value and acts against it, naming happenings that show it if you know them. If the gap between "
        "what they profess and what they do is wide enough, they lose trust and standing, and those who follow them for that value may "
        "leave. 1 action.",
        {
            "target_id": "Whom you expose",
            "value_axis": "The value they profess",
            "evidence_incident_ids": "Happenings that show them acting against it, if you know any",
        },
    ),
    T.FORECAST: ToolText(
        "You read the coming weather of your land by one of the ways your people read it ({{ observation_methods | join(', ') }}). How true "
        "the reading is follows how well that way reads the weather; name a season to also read whether it will come early, on time, late, "
        "or fail next year. 1 action.",
        {"method": "The way you read it", "season_position": "Optional: the position of a season of your world (0 to 7) whose coming you read"},
    ),
    T.WORK_WEATHER: ToolText(
        "You work the weather of your land toward rain, dry, calm, cold or warmth ({{ weather_aims | join(', ') }}) by a way you know "
        "({{ weather_work_methods | join(', ') }}), at a cost in coin that grows with its strength. The land downwind takes the opposite, "
        "and those harmed there may turn against you and make you stop. 1 action.",
        {"aim": "What you work the weather toward", "method": "How you work it", "strength": "How strongly, 1 to 100"},
    ),
    T.STUDY_FOSSILS: ToolText(
        "You study a bed of remains found in your land and read it one way ({{ fossil_readings | join(', ') }}). Read as deep time, the theories "
        "you hold grow stronger, and with living craft a kind whose remains are well preserved may be raised again; read otherwise, your "
        "people tell it, revere it, work it as a substance or grind it into remedies. 1 action.",
        {"bed_id": "The bed of remains you study", "reading": "How you read it"},
    ),
    T.DREDGE: ToolText(
        "You pay to dredge the harbour of the land you live in: each point of silting you clear costs coin, and a clear harbour keeps its "
        "ships coming. 1 action.",
        {"region_id": "The land whose harbour you dredge; your own if empty", "budget": "How much coin you spend on it"},
    ),
    T.GIVE_SPEECH: ToolText(
        "You speak in your town. At the assembly a speech moves the realm's standing, in the square or camp it stirs or calms the crowd, "
        "at the temple it moves the faithful; its force follows your charisma and the reach of the venue. 1 action.",
        {
            "venue": "Where: assembly, court, temple, square, school, camp or outlet",
            "aim": "To what end: persuade, teach, mock, mourn, rally, defend or accuse",
            "audience_node_id": "Whom you speak to or of, or none",
        },
    ),
    T.SATIRISE: ToolText(
        "You mock someone in public. Where your people allow mocking such a one, it costs them honour and gains you some; "
        "where they do not, it gives offence, and mocking a ruler where speech is censored is punished. 1 action.",
        {"target_id": "Whom you mock", "venue": "Where: assembly, court, temple, square, school, camp or outlet"},
    ),
    T.TEACH_LORE: ToolText(
        "You teach what your people know of a domain to someone. A learner of another people brings its accuracy closer to yours where yours is higher; "
        "a learner of your own people deepens what you all know. 1 action.",
        {
            "domain": "The domain: weather, sky, matter, land, waters, plants, animals, body, illness, mind, society, number or time",
            "learner_id": "Whom you teach",
        },
    ),
    T.TEST_LORE: ToolText(
        "You put one of your people's classes to the test against the world. A class they had wrong is put right and their knowledge grows more accurate; "
        "testing something harmful taken for harmless costs you health. 1 action.",
        {
            "domain": "The domain: weather, sky, matter, land, waters, plants, animals, body, illness, mind, society, number or time",
            "class_id": "The class you test",
        },
    ),
    T.ENDOW: ToolText(
        "You give part of your wealth as an endowment that serves a beneficiary every epoch for its purpose, and you keep it as its trustee. "
        "It raises your renown while it serves and goes on after you. 1 action.",
        {
            "beneficiary_id": "What or whom it serves: a town, a building, a school, a temple, a people or a being",
            "purpose": "Its purpose: relief, learning, worship, health, works, art, kin, memory or research",
            "capital": "How much of your wealth you give to it",
        },
    ),
    T.AUDIT_ENDOWMENT: ToolText(
        "You audit an endowment. What its trustee kept for themselves comes to light; they lose honour and you take their place as trustee. 1 action.",
        {"endowment_id": "The endowment you audit"},
    ),
    T.PLOT_SCHEME: ToolText(
        "You begin a scheme against someone ({{ plot_kinds }}). "
        "Friends join as agents, power gathers from skill in intrigue and deception, and it strikes against the target's spymaster and intuition. "
        "Each epoch it may be discovered. One scheme at a time. 1 action.",
        {"kind": "The scheme", "target_id": "Whom or what it is aimed at"},
    ),
    T.HOLD_GATHERING: ToolText(
        "You hold a gathering of the kind you choose where you live, this epoch, and name the guests you most want; others come by friendship, "
        "kinship, duty and distance. Those who come grow closer, may fall in love, quarrel or learn each other's secrets. A feast costs coin for each guest. "
        "Councils, summits and tournaments are for rulers. One gathering planned at a time. 1 action.",
        {"kind": "The kind of gathering", "guest_ids": "Whom you invite by name"},
    ),
    T.DELVE_SITE: ToolText(
        "You walk a site that has rooms, room by room. A room may hold a trap, a guardian, a puzzle or a hazard, and things, spirits or beasts within; "
        "you take what you win and stop at the first room you cannot pass. Reaching its last room wins renown. 1 action.",
        {"site_id": "The site you walk"},
    ),
    T.UNDERTAKE_HEROQUEST: ToolText(
        "You set out on a heroquest: you enter a mythic realm and walk a legend of your people step by step, each step a trial of skill, passion, "
        "conviction or faith. You need renown, a faithful people and a legend to walk. Following the people's version helps; departing from it may "
        "win another boon and rewrites the legend. A fall may hurt, madden or kill you, leave you stuck in the mythic realm, unable to act, or break "
        "the myth. Companions share the trials and the outcome. 1 action.",
        {
            "legend_id": "The legend you walk (a legend id); leave it out to walk your people's own",
            "companion_ids": "Mortals where you are who walk beside you (ids), if any",
        },
    ),
    T.PARLEY: ToolText(
        "As a commander you parley with the commander of an enemy army in your land before battle; it may end in a truce. 1 action.",
        {"foe_id": "The enemy army you parley with (an id)"},
    ),
    T.OFFER_TERMS: ToolText(
        "As a commander besieging a town you offer it terms: it may surrender with its honour, and you are bound not to sack it. 1 action.",
        {"town_id": "The besieged town (an id)"},
    ),
    T.DECLARE_CLOSURE: ToolText(
        "As a ruler you close the waters and hunting grounds of your realm to let their stock return. 1 action.",
        {"kind": "The closure you declare: {{ closure_kinds }}"},
    ),
    T.CREATE_OFFICE: ToolText(
        "As a ruler you make a new office in your realm, paid from its treasury, to hold those who want a place. 1 action.",
        {"kind": "The kind of office", "title": "Its title, if it has one of its own"},
    ),
    T.SEEK_TRUE_NAME: ToolText(
        "You seek a true name, your own if you have lost it or another's, from someone in your land who keeps it: a beast or a mortal who "
        "knows it. Learning a name gives you power over its bearer. 1 action.",
        {"keeper_id": "Who you seek it from (an id)", "bearer_id": "Whose true name you seek (an id); leave it out to seek your own"},
    ),
    T.TAKE_LONGEVITY: ToolText(
        "You take longevity magic: it adds years to your life each epoch it is paid in vis of the form you choose, and you come to need it; "
        "when the vis runs out the added years are lost. 1 action.",
        {"form": "The vis it uses: {{ spell_forms }}"},
    ),
    T.FOUND_ENCHANTMENT: ToolText(
        "You lay a global enchantment over your world: a natural law of your choosing ({{ natural_laws }}). It holds only while you, your order or your "
        "people pay its upkeep in vis each epoch, and rival casters may dispel it. Needs spellcraft of {{ rules.global_enchantments.mage_skill }}. 1 action.",
        {
            "name": "Its name in your language",
            "effect": "The law it makes",
            "form": "The vis that keeps it: {{ spell_forms }}",
            "strength": "Its strength, 1 to 100",
        },
    ),
    T.CLAIM_TURF: ToolText(
        "As leader of a criminal organisation you claim a district of your town: your organisation collects there, and rivals on the same "
        "streets may fight you for them. 1 action.",
        {"district_id": "The district of your town"},
    ),
    T.BRIBE_OFFICIAL: ToolText(
        "As leader of a criminal organisation you put an official on your payroll: you pay a bribe each epoch and the realm's pressure on "
        "you is turned aside. 1 action.",
        {"official_id": "The official"},
    ),
    T.OPEN_TRADING_POST: ToolText(
        "As leader of a merchant house you open a trading post in a foreign town: it stores goods, gathers informants who learn its secrets "
        "and settles your folk there. 1 action.",
        {"host_id": "The foreign town"},
    ),
    T.SEND_CONVOY: ToolText(
        "As leader of a merchant house you send a convoy along a route from your town; it may be raided, lost or delayed, and "
        "brings goods, migrants and missionaries when it arrives. 1 action.",
        {"route_id": "The trade route"},
    ),
    T.CORNER_MARKET: ToolText(
        "As leader of a merchant house you buy up a good in your home market to raise its price; a fair-market law or an association holding the "
        "good's monopoly undoes part of it. 1 action.",
        {"commodity": "The good"},
    ),
    T.CALL_TRIBUNAL: ToolText(
        "As leader of a magical order you call its tribunal against a mortal for breaking one of the order's laws; it may fine them, strip "
        "their rank or cast them out. 1 action.",
        {"accused_id": "The accused", "law": "The law they broke"},
    ),
    T.REGISTER_DEED: ToolText(
        "You register a contract with another party in your realm's registry ({{ registry_kinds }}); where the realm keeps a written code "
        "its courts make the other party pay what is owed, and elsewhere it rests on who is stronger. 1 action.",
        {"counterparty_id": "The other party", "kind": "The kind of contract", "amount": "What they owe you"},
    ),
    T.APPEAL_CONVICTION: ToolText(
        "You carry your latest conviction to the next court above the one that judged you, paying its fee; it may overturn the conviction "
        "and free you. 1 action.",
        {},
    ),
    T.CLAIM_BOUNTY: ToolText(
        "As the best hunter of the realm that outlawed someone, you hunt them down for the bounty; you bring them to prison or kill them. 1 action.",
        {"outlaw_id": "The outlaw"},
    ),
    T.GRANT_PARDON: ToolText(
        "As ruler you pardon someone held in prison or outlawed; pardoning one wrongly condemned earns renown, pardoning a friend is read as "
        "corruption. 1 action.",
        {"mortal_id": "Who you pardon"},
    ),
    T.POST_BOUNTY: ToolText(
        "You pay coin onto the bounty of an outlaw; whoever hunts them down is paid it with the realm's own bounty. 1 action.",
        {"outlaw_id": "The outlaw", "amount": "The coin you put up"},
    ),
    T.CHOOSE_STORYLET: ToolText(
        "You make the choice a storylet waits on you for, by its number among the choices your context lists; what follows is decided by "
        "the choice, and some choices lead to more. Left too long, you choose by your nature without thinking. 1 action.",
        {"run_id": "The storylet waiting for you", "choice": "The number of your choice"},
    ),
    T.ROUSE_CROWD: ToolText(
        "You speak to the folk of your town about a grievance ({{ collective_triggers }}); your sway makes it easier for each to join once "
        "others have, and the town may rise in a riot, a panic or a lasting movement. Its guards and garrison hold them back. 1 action.",
        {"grievance": "What you speak about"},
    ),
    T.STIR_CROWD: ToolText(
        "You call the folk of the town you are in to one act ({{ collective_acts }}); your sway feeds the feeling the act grows from "
        "({{ crowd_feelings }}), and whether they follow depends on how many already feel it and on the guards that hold them back. "
        "A demonstration presses a demand without violence, a boycott refuses trade with those the town blames, an exodus leaves "
        "together, a jubilation rejoices. 1 action.",
        {"settlement_id": "The town you are in", "act": "What you call them to"},
    ),
    T.COMMISSION_ACCOUNT: ToolText(
        "As ruler you have your realm issue its official account of an event; you choose whom it praises and whom it blames, and the further "
        "it strays from what happened the more a scholar may one day expose. 1 action.",
        {"collection_id": "The event", "praise_ids": "Whom the account praises", "blame_ids": "Whom the account blames"},
    ),
    T.STRIKE_MEMORY: ToolText(
        "As ruler you strike a figure from your realm's records: its accounts omit them, public mentions of them are removed and works made of them "
        "for the realm are destroyed. Their fame fades unless the folk or foreigners keep it. 1 action.",
        {"figure_id": "Whom you remove from the realm's records"},
    ),
    T.DRAW_DESIGN: ToolText(
        "You draw a new vehicle type for your realm or town on a frame it knows how to build, giving more weight to one part "
        "({{ design_components }}); it is entered in the atlas under its name, its sections, mounts, speed, reach, cargo, arms and crew "
        "follow from the frame, its parts and their materials, and new vehicles are built to it. 1 action.",
        {"frame": "The frame it is built on; one of: {{ vehicle_frames }}", "emphasis": "The part you favour"},
    ),
    T.HUNT_MOLES: ToolText(
        "As spymaster you hunt for moles at your court; you may catch a foreign agent, clear an official, or wrongly accuse one, who may "
        "then be purged or defect. 1 action.",
        {},
    ),
    T.ANSWER_SICKNESS: ToolText(
        "As ruler of a realm, or as a healer of your community, you set how it answers a sickness ({{ plague_responses }}): closed borders "
        "cost trade and calm, a quarantine slows the spread but may set off riots, burning the dead slows it but grieves folk whose rites "
        "forbid it, driving out the sick slows it at home and turns folk against the sick, prayer comforts but crowds, seeking a cure sets the learned "
        "to work, and cleaning water and carrying away refuse costs treasury, cuts the routes by water, food and goods, and leaves works that keep "
        "cutting them; your order backs it even where no theory of your healers does. Each answer cuts only the routes it reaches. "
        "You may also treat it with a kind of cure ({{ cure_classes | join(', ') }}); a cure works only on the kind of thing the "
        "sickness is, one that fails costs your healers trust, cutting it out may kill or infect where healers know little, and an antiviral "
        "needs advanced medicine and loses its hold faster when overused. 1 action.",
        {"disease_id": "The sickness", "response": "The answer", "cure_class": "The kind of cure you treat it with, or none"},
    ),
    T.SEEK_CURE: ToolText(
        "You work at a cure for a sickness at the hospital, academy or monastery where you live; your medicine adds to the search, and the "
        "cure, once found, belongs to your community and can be sold along its trade routes. A search by a kind of cure that fits what the "
        "sickness is goes faster, and one that does not fit goes slower. Or you seek relief there for a condition you or your close kin "
        "bear, whatever its cause; your medicine decides whether it eases. 1 action.",
        {
            "disease_id": "The sickness, or none when you seek relief for a condition",
            "condition_id": "The condition to seek relief for, or none when you work at a cure for a sickness",
            "cure_class": "The kind of cure you seek ({{ cure_classes | join(', ') }}), or none",
        },
    ),
    T.MAKE_WILL: ToolText(
        "You write your will: the heirs who receive what you own when you die, and the share of it each receives. The shares add up to 100. "
        "Kin you leave out may contest it; where your people do not pass property by will, the law may set it aside. A new will replaces the old. 1 action.",
        {"heirs": "The living heirs you name", "shares": "The share each heir receives, in the same order, adding up to 100"},
    ),
    T.FIND_CARRIER: ToolText(
        "With deep medicine you find that a mortal in your land carries a sickness without falling ill; once found, a carrier spreads it no further. 1 action.",
        {"mortal_id": "The mortal you suspect", "disease_id": "The sickness"},
    ),
    T.DECIPHER_SCRIPT: ToolText(
        "You work at the dead script of a tongue: progress grows with your languages skill, the texts that survive, any bilingual text and the "
        "living tongues related to it. Partial readings can go wrong. 1 action.",
        {"language_id": "The dead tongue"},
    ),
    T.PROCLAIM_TONGUE: ToolText(
        "As ruler of a realm you set a policy on a tongue across it ({{ language_policies }}): an official tongue spreads among your subjects, a "
        "suppressed one fades but its speakers lose cohesion and grow restless, a revived one is taught again. 1 action.",
        {"language_id": "The tongue", "policy": "The policy"},
    ),
    T.REFORM_SCRIPT: ToolText(
        "You reform the script of your people's tongue one step along its chain toward fewer signs. Needs some languages skill. 1 action.",
        {},
    ),
    T.SEARCH_MAGIC_SITES: ToolText(
        "With spellcraft of {{ rules.magic_sites.search_skill }} or more, you search the land around you for hidden magic sites. "
        "A site you find is held by your community and adds to its holiness; some yield reagents, some strengthen rites, some guard, some open a way to another world. 1 action.",
        {},
    ),
    T.DIG_SITE: ToolText(
        "With lore enough, you begin a dig at an old site, the remains of an earlier creation or a wreck, and lead it. "
        "It goes through five stages; each needs a skill and sometimes a technique, "
        "and each may hold a risk or a find that passes to your realm. 1 action.",
        {"site_id": "The site you dig"},
    ),
    T.PRESS_LEVERAGE: ToolText(
        "You lean on someone you hold a hook on, or who owes you a favour, with one demand: marriage, step down, support, vote, law, "
        "appointment, silence or payment. Appointment puts you in a vacant office of the realm they rule; silence keeps them from "
        "testifying before a court that tries you. "
        "A weak hook is spent and a strong one may wear weak; a favour called in may be refused. 1 action.",
        {"target_id": "Whom you press", "demand": "What you demand"},
    ),
    T.SEND_DISPATCH: ToolText(
        "You send a message to someone: proposal, demand, threat, insult, gift notice, declaration, report, plea, intelligence, order or warning, "
        "by one of these: {{ mortal_media | join(', ') }}. It takes time by distance, medium and season; spies may read or seize it, "
        "outlaws may waylay it, and in another tongue it may be misread. 1 action.",
        {
            "recipient_id": "To whom",
            "content": "What it says",
            "medium": "How it travels",
            "army_id": "For an order to a commander: the army it moves",
            "region_id": "For an order to a commander: the land the army is to go to",
        },
    ),
    T.BARGAIN_WITH_ESTATE: ToolText(
        "As the ruler of a realm, you grant one of its estates a privilege ({{ estate_privileges }}) to win its loyalty, or take one back at a cost in loyalty. "
        "At most {{ rules.mortal_tools.estate_bargain_per_epoch | several('bargain', 'bargains') }} an age. 1 action.",
        {"estate_id": "The estate", "privilege": "The privilege", "grant": "True to grant it, false to take it back"},
    ),
    T.PROPOSE_LAW: ToolText(
        "As a ruler or a holder of a council office, you bring a typed law (or a new wording of one already in force) before your realm. "
        "It does not pass at once: each epoch it moves by the weight of those for it against those against it, under the realm's way of deciding, "
        "and it fails if it stalls. Hooks you hold over council members may win their votes. 1 action.",
        {
            "kind": "What the law rules, by its kind",
            "params": "The law's terms by name, only those its kind has; leave out a term to keep its default. Terms of each kind: " + law_terms_guide(),
        },
    ),
    T.ACCUSE: ToolText(
        "You accuse a mortal of your settlement of a crime and stand as a witness against them. "
        "The case is tried in a later epoch in the way the realm's penal code sets, and a true charge is easier to prove than a false one. 1 action.",
        {"accused_id": "Whom you accuse", "crime": "The crime you charge them with"},
    ),
    T.ISSUE_DEMAND: ToolText(
        "As ruler or regent you demand something of another realm: {{ crisis_demands }}. A person to hand over is named as the subject. "
        "A crisis opens: other realms back a side, the weaker side backs down or concedes, and if neither yields it becomes war. 1 action.",
        {
            "target_id": "The realm you make the demand of",
            "demand": "What you demand: cede_region, release_vassal, convert, pay, hand_over, disarm or open_trade",
            "subject_id": "The land to cede, the vassal to release or the person to hand over, if the demand names one",
        },
    ),
    T.BACK_CRISIS: ToolText(
        "As ruler or regent you put your realm behind one side of a crisis between other realms; backers weigh on who yields and join the war if it comes. 1 action.",
        {"crisis_id": "The crisis", "side": "Which side you back: demander or target"},
    ),
    T.ISSUE_MANDATE: ToolText(
        "As ruler or regent you issue a mandate: {{ mandate_kinds }}. Unmet mandates cost you legitimacy, and harsh ones weigh on your people. 1 action.",
        {
            "kind": "produce, export_ban, build, famine_relief, curfew, slum_clearance, prepare, enclosure, ration or corvee",
            "settlement_id": "The settlement it is laid on, if any",
            "commodity": "The good to produce, ban or send",
            "district": "The quarter to build",
            "amount": "How much to produce or send",
        },
    ),
    T.ASSIGN_TASK: ToolText(
        "As ruler or regent you set an officer of your council to a task: {{ council_tasks }}. 1 action.",
        {"office_id": "The office", "task": "The task", "target_id": "The realm or land the task aims at, if any"},
    ),
    T.SEIZE_TITLE: ToolText(
        "As the ruler of a realm, you take up a title whose lands your realm mostly holds by right and whose seat you hold: "
        "you usurp it from its holder, at a cost in legitimacy, or restore it if it lies dormant. 1 action.",
        {"title_id": "The title to take"},
    ),
    T.BUY_WORKSHOP: ToolText(
        "You buy a workshop of your community from whoever owns it, paying its price from your wealth or treasury. "
        "Its profit (what it sells, less inputs, wages, upkeep and taxes) then comes to you, and so do its losses. 1 action.",
        {"kind": "The kind of workshop to buy"},
    ),
    T.LAY_TRADE_POLICY: ToolText(
        "You lay or change a trade policy of the realm you rule: a tariff on a good (raising its price and your treasury, guarding your own makers), "
        "a subsidy on a good your people make (paid from your treasury), or an embargo on a partner or a good (smugglers may run it). 1 action.",
        {
            "kind": "Tariff, subsidy or embargo",
            "commodity": "The good, or none for every good",
            "partner_id": "The realm or market it is aimed at, or none for all",
            "rate_pct": "The rate for a tariff or subsidy",
        },
    ),
    T.SPECULATE: ToolText(
        "You buy up a share of a good in your market and hold it back, hoping its price rises. You sell when it does, or after a few epochs; "
        "if prices fall you may be ruined. Hoarding food while people go hungry is judged by those who see it. 1 action.",
        {"commodity": "The good to buy up"},
    ),
    T.TRADE_LORE: ToolText(
        "You trade a piece of lore you hold (a technique, a hidden site, knowledge of a land or a prophecy) to a neighbour who lacks it. "
        "Rarer lore is worth more, and each telling makes it less rare. You may name the price: wealth, favour, renown, exchange or service. "
        "Exchange takes a piece of lore the buyer holds and you lack; service is a deed the buyer must do before the lore passes. "
        "Otherwise the buyer pays as it can. 1 action.",
        {
            "buyer_id": "Who receives the lore",
            "kind": "The kind of lore",
            "key": "Which piece: the technique key, or site, region or prophecy",
            "subject_id": "The site, land or prophecy, if any",
            "price": "The price, if you name it",
        },
    ),
    T.PERSUADE: ToolText(
        "You try to bring another being round by an appeal of one kind: belief, self_interest, authority, evidence, fear, feeling or bond. "
        "You may aim at a belief, a decision, a faith, a vote, a treaty, a surrender or a confession: a surrender is sought from the ruler of a town "
        "your side besieges and works only once its defenders falter; a confession is sought from one you hold accused. An appeal to a bond fails "
        "where none ties you. Your oratory, how well the appeal fits them, their stubbornness and their passions decide it. 1 action.",
        {
            "target_id": "The being you try to persuade",
            "appeal": "How you argue",
            "aim": "What you seek from them",
            "axis": "For a belief: the belief at stake",
            "toward": "For a belief: how far toward it (-100 to 100)",
            "subject_id": "For a surrender: the town besieged",
        },
    ),
    T.SWEAR_KINSHIP: ToolText(
        "You swear kinship with a friend where you are, by the rite you name, and become sworn kin: you owe each other aid and vengeance "
        "as blood kin do, and breaking it is oathbreaking. You both must count each other as friends. 1 action.",
        {"target_id": "The friend you swear kinship with", "rite": "The rite by which you swear it"},
    ),
    T.FOSTER_CHILD: ToolText(
        "You send a child of yours, still young, to be raised in another household, whose head becomes its fosterer: the child grows loyal "
        "to that house and the two houses are bound. 1 action.",
        {"child_id": "Your child", "household_id": "The household that raises the child"},
    ),
    T.FOUND_SCHOOL: ToolText(
        "You found a school of thought, a creed that spreads from person to person and town to town, and can move a realm. 1 action.",
        {
            "name": "A proper name for the school or creed",
            "tenets": "What it teaches, 1 to 3 tenets: {{ ideology_tenets }}",
            "founder_id": "Ignored: you found it yourself",
        },
    ),
    T.LOOK_AT_WORLD: ToolText(
        "Shows your land, those near you, your language, what you know, what you own and recent events more widely than the prompt. Free."
    ),
    T.INSPECT_ENTITY: ToolText("Shows the details of an entity. Free.", {"id": "The entity's id"}),
    T.SEARCH_ENTITIES: ToolText("Searches entities. Free.", {"query": "A word in the name or description"}),
    T.RECOUNT: ToolText(
        "Tells the people you live among what you know of a happening you saw or took part in, step by step as you know it; they pass it on "
        "as your account. 1 action.",
        {"incident_id": "The happening's id", "step_offset": "Where to start in its steps when they run past one page"},
    ),
    T.FOUND_LANGUAGE: ToolText(
        "You create your own language: its name, its kind, its sound structure and first words. From now on you speak this language. 1 action.",
        {
            "name": NAME_FIELD,
            "subtype": "What kind of language it is",
            "description": "Its sound structure, its script if it has one, and who speaks it",
            **WORD_FIELDS,
            "image_prompt": ('English image prompt: this language or script in use among those who use it. {% include "shared/image_prompt_rules.md.j2" %}'),
        },
    ),
    T.COIN_WORDS: ToolText(
        "You add new words to the language you speak (meaning, type, origin). Free, {{ " + M + ".coin_word_per_epoch }} times per age, at most "
        "{{ " + M + ".coin_word_max_words }} words each time.",
        dict(WORD_FIELDS),
    ),
    T.PRODUCE_ITEM: ToolText(
        "You produce an item from resources you own or that lie on your land. The resources' abundance decreases; "
        "quality depends on your craft and the resources' might. "
        "A named mortal needs a craft skill of at least {{ rules.skills.tool_min_craft }}. 1 action.",
        {
            "name": NAME_FIELD,
            "category": "weapon, armour, shield, tool, jewellery, sacred relic, instrument or book",
            "subtype": "What kind of item it is",
            "description": DESCRIPTION_FIELD,
            "resource_ids": "The resources it is made from (at most {{ " + M + ".craft_max_resources }})",
            "material": "What it is made of: {{ materials | join(', ') }}; it must come from one of those resources or your people's stores, and your people must be able to work it",
            "owner_id": "Who will carry the item (a mortal or you); if empty, you",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.BUILD_STRUCTURE: ToolText(
        "You build a structure of one of your world's structure kinds. It can be dedicated to a god."
        " A named mortal needs a craft skill of at least {{ rules.skills.tool_min_craft }}. 1 action.",
        {
            "name": NAME_FIELD,
            "structure_kind": "What it is and what it does: {{ structure_kinds }}",
            "subtype": "Its own name for this kind of structure",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own settlement, place or region; if empty, where you are",
            "dedicated_son_id": "The god it is dedicated to, if any",
            "material": "What it is built of, from your people's stores; a holy material raises a temple's sanctity and a soft one decays sooner",
            "channels_ley": "True if it is raised to draw on the ley lines; it gains strength only where a line runs",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.CREATE_CULTURE: ToolText(
        "You create a tradition of your community, a legend, a work of art (by honouring your god it strengthens that god) or a law "
        "(a just law reduces rebellion). 1 action.",
        {
            "kind": "tradition, legend, artwork or law",
            "name": NAME_FIELD,
            "subtype": "What exactly it is",
            "description": DESCRIPTION_FIELD,
            "related_ids": "Existing records it tells of (at most {{ " + M + ".culture_max_related }})",
            "law_kind": "For a law: what it rules, one of: {{ law_kinds }}; required for laws",
            "law_params": "For a law: its terms by name, only those its kind has; leave out a term to keep its default. Terms of each kind: "
            + law_terms_guide(),
            "image_prompt": 'English image prompt: the tradition, legend, artwork or law as it appears in the world. {% include "shared/image_prompt_rules.md.j2" %}',
            "legend_category": "Only for a legend: what it would become if belief made it real: {{ legend_categories | join(', ') }}",
            "archetype": "Only for a legend: the kind of tale, which sets its lesson: " + ", ".join(item.value for item in LegendArchetype),
            "tradition_kind": "Only for a tradition: what kind of custom it is: " + ", ".join(item.value for item in TraditionFunction),
            "calendar_slot": "Only for a tradition kept at a set time: " + ", ".join(item.value for item in CalendarSlot),
            "taboo_target": "Only for a taboo: the good those who hold the taboo will not touch",
            "taboo_act": "Only for a taboo: the deed those who hold the taboo will not do: " + ", ".join(item.value for item in ActKind),
        },
    ),
    T.DISCOVER_RESOURCE: ToolText(
        "You discover a new resource on your land and own it. 1 action, {{ " + M + ".discover_resource_per_epoch }} per age.",
        {
            "name": NAME_FIELD,
            "subtype": "What kind of resource it is",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own region or a place in your region",
            "domain": "One of: {{ domains | join(', ') }}",
            "image_prompt": IMAGE_PROMPT_FIELD,
            "commodity": "What your people draw from it: {{ commodities | join(', ') }}; ore goes to metalworking",
            "material": "If it is a seam or a grove, its material: {{ materials | join(', ') }}",
            "mechanics": "The resource's particular rules, at most {{ rules.mechanics.resource_max }} (empty: read from its name and text): {{ resource_mechanics }}",
        },
    ),
    T.CLAIM_RESOURCE: ToolText(
        "You claim an ownerless resource on your land. If you take someone else's resource, your relation with its owner turns hostile. Free, {{ "
        + M
        + ".claim_per_epoch }} per age.",
        {"resource_id": "The resource's id"},
    ),
    T.FOUND_SETTLEMENT: ToolText(
        "You split off a branch of your population (or your disciples) and found a new settlement; those who migrate leave you. In your own region or a neighbouring region. 1 action.",
        {
            "name": NAME_FIELD,
            "subtype": "What kind of settlement it is",
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
        "You declare war on a community or a creature. The world's course decides the war; your weapons and your god lend you strength. 1 action.",
        {"target_id": "The community or creature", "reason": "Why you go to war"},
    ),
    T.WORSHIP: ToolText(
        "You worship a god (a son) or change your god; if you give son_id 0 you worship the creator god directly, maker of all the sons. Your old god's favour toward you "
        "falls. Free, {{ " + M + ".worship_per_epoch }} per age.",
        {"son_id": "The son's id, or 0 for the creator", "offering": "Your offering and vow"},
    ),
    T.PRAY_TO_CREATOR: ToolText(
        "You pray directly to the creator god above the sons, the maker of all worlds. Your prayer reaches the creator; any answer comes later. Free, {{ "
        + M
        + ".pray_creator_per_epoch }} per age.",
        {"prayer": "Your prayer", "request": "What you ask of the creator"},
    ),
    T.DEVELOP_KNOWLEDGE: ToolText(
        "Your community develops a new piece of knowledge (a technology, craft, school or method). Branch: {{ knowledge_branches }}. If it is built on knowledge you already "
        "have it is stronger. A named mortal needs a learned skill of at least {{ rules.skills.tool_min_lore }}. 1 action.",
        {
            "name": NAME_FIELD,
            "branch": "The knowledge's branch",
            "description": "What it is, how it was found, which material or observation it rests on",
            "base_ids": "Knowledge you know that it is built on (at most {{ " + M + ".knowledge_max_prereqs }})",
            "resource_id": "The resource it relies on",
            "image_prompt": 'English image prompt: those who practise this technique, with what they use and where. {% include "shared/image_prompt_rules.md.j2" %}',
        },
    ),
    T.LEARN_KNOWLEDGE: ToolText(
        "You learn a piece of knowledge known by your trade partner, ally or neighbour. Free, {{ " + M + ".learn_per_epoch }} per age.",
        {
            "knowledge_id": "The knowledge's id",
            "from_id": "Who teaches it: a community or mortal that knows it and that you trade with, are allied to, rule, or share a region with",
        },
    ),
    T.CHOOSE_RESEARCH: ToolText(
        "You choose which technique your community's scholars work on next, from the ones within reach. The chosen technique advances at full pace, the others slowly. "
        "Your current research and its choices are in your context. Free.",
        {"technique": "The technique to research; one of the choices within your reach"},
    ),
    T.PROPOSE_THEORY: ToolText(
        "You set out a theory: your community's account of one field. Whether it is true is hidden; a true one helps the work it guides and a false one meets "
        "anomalies until a rival overturns it. Free.",
        {
            "domain": "The field it explains: {{ theory_domains }}",
            "name": NAME_FIELD,
            "claim": "What it holds, in one or two sentences",
        },
    ),
    T.INVENT_ART_FORM: ToolText(
        "You invent an art form others can take up, practise and master. A named mortal needs a fitting skill of at least {{ rules.art_forms.invent_skill }}. Free.",
        {
            "discipline": "Its discipline: {{ art_disciplines }}",
            "name": NAME_FIELD,
            "description": "What it is and how it is practised",
            "structure": "Its shape, keyed by the discipline's parts: {{ art_structures }}; each value a short phrase",
        },
    ),
    T.DIPLOMACY: ToolText(
        "Diplomacy with another community: alliance (stands with you in war), peace (tries to end enmity), tribute (demands wealth from the weak) or marriage (unites the "
        "lineages). 1 action.",
        {"target_id": "The community's id", "kind": "alliance, peace, tribute or marriage", "terms": "Your terms"},
    ),
    T.GO_ON_ADVENTURE: ToolText(
        "You embark on an adventure: hunting a dangerous creature (the world's course decides the fight at the end of the age; your weapons count) or seizing an item "
        "from someone else's hands (your agility and wits against its owner's defence). 1 action.",
        {"target_id": "The species to hunt or the item to seize", "goal": "What you set out to do"},
    ),
    T.FIND_ROUTE: ToolText(
        "You search for the way to another world. The way you find depends on what you know: gate lore an ancient gate, sky navigation a sail route, pathfinding folding, "
        "magic a dream road. Rarely you may discover a world no one has known. 1 action.",
        {"how": "How you search for the way"},
    ),
    T.EXPLORE_LAND: ToolText(
        "You set out to explore beyond the known lands: you find either a new region not on the map or, in your own or a neighbouring region, a place no one has set foot on. Success depends on your wits (your craft if you are a community) and your "
        "path knowledge (seafaring, pathfinding, astronomy). If you are a community your pioneers can settle there and found a new settlement. 1 action, "
        "{{ rules.exploration.tool_per_epoch }} per age.",
        {
            "kind": "region (new lands not on the map) or place (a new place in your own or a neighbouring region)",
            "name": "An original proper name; fitting your language's naming rule",
            "subtype": "What kind of land or place it is",
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
        "A rite held in the region where your god's remains lie counts {{ '%g' | format(rules.death.pilgrimage_multiplier_pct / 100) }} times. When devotion is full the resurrection "
        "rite may succeed. 1 action, {{ rules.death.rite_per_epoch }} per age.",
        {
            "son_id": "The dead god's (son's) id",
            "kind": "prayer, wealth, blood or life",
            "victim_id": "The named mortal offered in a life sacrifice (if empty, yourself if you are a mortal)",
        },
    ),
    T.BUILD_SHIP: ToolText(
        "You build an inter-world ship (requires shipbuilding knowledge). Its power depends on your craft, your mining and your metallurgy. 1 action.",
        {"name": NAME_FIELD, "subtype": "the kind of ship, in your own words", "description": DESCRIPTION_FIELD, "image_prompt": IMAGE_PROMPT_FIELD},
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
    T.KEEP_PET: ToolText(
        "You take one beast of a small tame kind your people keep as your own companion. It stays at your side, comforts you, and if its kind hunts or guards "
        "it sharpens your hunting; its death lowers your mood. Free.",
        {"species_id": "The kind it is of, from those your people keep; leave empty to take any"},
    ),
    T.TRAIN_HERD: ToolText(
        "You train a herd your people keep, for war, for the hunt or for guarding, with your own beast handling (at least "
        "{{ rules.husbandry.train_skill }}). Trained war beasts join your people's armies, hunters bring home more and guards keep raiders off. 1 action.",
        {"species_id": "The kind of the herd, from those your people keep", "training": "What you train it for"},
    ),
    T.MERGE_SPECIES: ToolText(
        "With biomancy you merge two creature species in your world, near you (at most {{ rules.creatures.species_merge_distance | several('step', 'steps') }}), into a single merged (requires "
        "biomancy knowledge). The merged species carries the traits of both species; but it may get out of control. 1 action.",
        {"a_id": "The first species", "b_id": "The second species", "name": NAME_FIELD, "goal": "Why you make it"},
    ),
    T.BIND_SPIRIT: ToolText(
        "With magic you bind a free spirit in your own or a neighbouring region to an item, ship or monument there (requires magic knowledge). The item becomes ensouled; "
        "bound to a monument, the monument moves and acts. 1 action.",
        {"spirit_id": "The free spirit's id", "target_id": "The item, vessel or monument"},
    ),
    T.SEARCH_RUINS: ToolText(
        "You search a ruin, a remnant or the remains of a dead god on your land: you may find lost knowledge, an ownerless item, or bring a curse on yourself. 1 action.",
        {"target_id": "The id of a place that is a ruin, a remnant or where a god died", "how": "How you search"},
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
        "You stand up to a god (a son): your strength, agility, wits and weapons against the god's might. If you win the god is wounded, their fame shaken and you become a legend; "
        "if you lose you die or are cursed. 1 action.",
        {"son_id": "The god's id", "reason": "Why you defy this god"},
    ),
    T.DENY_GOD: ToolText(
        "You deny your god: you stop worshipping that god and become godless. Your god's existence weakens, and the creator of the gods cannot draw strength from godless "
        "communities. 1 action.",
        {"reason": "Why you turn away"},
    ),
    T.PROPHESY: ToolText(
        "You make a prophecy: you say something that will happen in the future. If it comes true it is tracked and your reputation (charisma) rises; if it is misread it "
        "is shaken. 1 action, {{ " + M + ".prophesy_per_epoch }} per age.",
        {
            "predicate": "What exactly must happen for the prophecy to come true, which the world itself will check: {{ prophecy_predicates }}",
            "subject_id": "The one the foretelling names: a person, a place, a house, a realm, or the first side of a war",
            "second_id": "For a war: the second side",
            "archetype": "For who will rule: the kind of legend the coming ruler must fit",
            "sky_kind": "For a sign in the sky: which sign",
            "event_kind": "For a foretold happening: what kind",
            "within_epochs": "In how many ages it must come true; if it does not, your standing falls and your followers' devotion drops",
            "consequence": "What it means when it comes true: {{ prophecy_consequences }}",
            "consequence_id": "Whom the consequence touches",
            "name": "The prophecy's name, from your own language",
            "saying": "The words of the prophecy: testable; who or what, and when",
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
    T.ENACT_LAW: ToolText(
        "As ruler or regent you lay down a typed law for your whole realm: its kind decides what it rules and its terms decide how. "
        "In a realm that decides by council, assembly or divine will, the law goes before them as a proposal instead of passing at once. "
        "1 action, {{ " + M + ".enact_law_per_epoch }} per age.",
        {
            "kind": "What the law rules; one of: {{ law_kinds }}",
            "params": "The law's terms by name, only those its kind has; leave out a term to keep its default. Terms of each kind: " + law_terms_guide(),
            "name": "The law's name, if it should have one of its own",
        },
    ),
    T.PROPOSE_TREATY: ToolText(
        "You offer a typed treaty to another community or realm; it takes force when they accept. 1 action, {{ " + M + ".propose_treaty_per_epoch }} per age.",
        {
            "target_id": "The community or realm you offer it to",
            "kind": "peace, truce, alliance_defensive, alliance_offensive, non_aggression, vassalage (you become the vassal), tribute, marriage_pact, trade_pact, condotta, guarantee, interworld, coalition, divine_pact, naval_limit or arms_limit",
            "clauses": "Typed clauses with who owes, who gains and their terms by name, as each clause kind requires",
            "epochs": "How many ages it should hold",
            "clauses.kind": "The clause's kind",
            "clauses.obligor_id": "Who owes it",
            "clauses.beneficiary_id": "Who gains by it",
            "clauses.params": "Its terms by name, as the clause kind requires",
        },
    ),
    T.SWEAR_OATH: ToolText(
        "You swear an oath ({{ oath_kinds }}); keeping it wins honour, breaking it costs honour and a god's favour. "
        "Free, {{ " + M + ".swear_oath_per_epoch }} per age.",
        {"kind": "The oath", "recipient_id": "To whom or against whom, if anyone (for a pilgrimage: the holy place)", "words": "The words of the oath"},
    ),
    T.ACCEPT_TREATY: ToolText("You accept a treaty offered to you; it takes force at once. Free.", {"treaty_id": "The offered treaty"}),
    T.BREAK_TREATY: ToolText(
        "You break a treaty your people are bound by: the other parties' trust in you falls, guarantors may march and your rulers lose honour. 1 action.",
        {"treaty_id": "The treaty you break"},
    ),
    T.APPOINT_OFFICER: ToolText(
        "As ruler or regent you fill a seat of your realm (chancellor, marshal, treasurer, high_judge, spymaster, governor, ambassador) with a living named mortal, "
        "or leave it empty. Free, {{ " + M + ".appoint_officer_per_epoch }} per age.",
        {"office": "The office to fill", "mortal_id": "The mortal who takes the seat; empty to dismiss the holder"},
    ),
    T.SET_TAX: ToolText(
        "As ruler or regent you set the tax your realm's cities pay (0 to 50%); high taxes fill the treasury and stir unrest. Free, "
        "{{ " + M + ".set_tax_per_epoch }} per age.",
        {"rate": "The share of the cities' output taken in tax (%)"},
    ),
    T.BUILD_SPY_NETWORK: ToolText(
        "You build a spy network inside a nearby community: you learn its secrets and gain an advantage in war; if caught, relations sour and war may break out. 1 action.",
        {"target_id": "The community's id", "cover": "The spies' cover"},
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
        "{{ " + M + ".debt_max_term }} ages). Nobody collects; but if it is not paid on time relations cool. {{ " + M + ".debt_ap }} action.",
        {
            "debtor_id": "The borrower",
            "amount": "The debt amount (at most {{ " + M + ".debt_max_amount }})",
            "what": "What is lent: a good, coin, labour or a service",
            "term_ages": "In how many ages it will be repaid (at most {{ " + M + ".debt_max_term }}); if empty, {{ " + M + ".debt_default_term }}",
        },
    ),
    T.REPAY_DEBT: ToolText(
        "You repay your debt to someone: if you have wealth or prosperity the debt amount passes to them (otherwise you repay in kind); the debt closes and relations warm "
        "(even if overdue). {{ " + M + ".debt_ap }} action.",
        {"creditor_id": "Who you owe"},
    ),
    T.ADOPT: ToolText(
        "You adopt another named mortal: it counts as of your lineage. It must be younger than you and near you. "
        "{{ " + M + ".adopt_per_epoch }} per age, {{ " + M + ".adopt_ap }} action.",
        {"child_id": "The named mortal you adopt", "reason": "Why and how you adopt"},
    ),
    T.BESTOW_GIFT: ToolText(
        "You give someone a gift from your purse, or from your realm's if you rule one, on an occasion ({{ gift_occasions | join(', ') }}). It raises your "
        "standing and their regard. The occasion sets what is owed back: a gift at a birth binds the child to you, one to the bereaved is owed back "
        "at your own losses, amends settle a wrong and can end a feud, a patron's gift is repaid in loyalty, and a guest gift seals guest right. "
        "An unanswered gift costs its receiver face, and one who hates you may refuse it as an insult. 1 action.",
        {
            "receiver_id": "Who receives it",
            "value": "Coin it is worth",
            "item_id": "A thing of yours to give with it, or empty",
            "occasion": "The occasion of the gift",
        },
    ),
    T.ANSWER_GIFT: ToolText(
        "You answer a gift someone gave you, so you owe them nothing; answer a rank-claiming gift with more or lose face. An answer worth "
        "{{ rules.gifts.exceed_ratio_pct }}% of the gift or more exceeds it and puts the first giver in your debt; two houses answering each other "
        "so spend their coin and raise their standing. 1 action.",
        {"gift_id": "The gift you owe", "value": "Coin your answer is worth, or empty to match what custom asks"},
    ),
    T.RELEASE_DEBT: ToolText(
        "You release someone from the return they owe you for a gift; your standing rises and they owe you gratitude instead. 1 action.",
        {"gift_id": "The gift whose return you forgive"},
    ),
    T.REFUSE_GIFT: ToolText(
        "You refuse a gift someone gave you; you owe them nothing, but the giver takes it as an insult. 1 action.",
        {"gift_id": "The gift you refuse"},
    ),
    T.MAKE_OFFERING: ToolText(
        "You make an offering to your god from your purse; the offerings your people have made rise, and the god is bound to answer it. 1 action.",
        {"value": "Coin the offering is worth"},
    ),
    T.FREE_BOUND: ToolText(
        "As ruler you free a share of the bound of a town of your realm ({{ manumission_paths }}); those freed by purchase or service "
        "rise as craftsfolk, the rest work the land. 1 action.",
        {"town_id": "The town", "share": "Share of its bound you free, 1 to 100", "path": "By what way they go free"},
    ),
    T.LAY_CORVEE: ToolText(
        "As ruler you summon a share of the workers of a town of your realm to forced labour on a great work being raised; the work "
        "goes faster, the harvest suffers, unrest rises and the town's grievance rises. 1 action.",
        {"town_id": "The town", "work_id": "The work being raised", "share": "Share of its workers, 0 to 100; 0 lifts the labour"},
    ),
    T.BEGIN_REALM_PLAN: ToolText(
        "As ruler you set your realm on a long plan ({{ long_plan_kinds }}) paid from its treasury each epoch; it outlives you and passes "
        "to whoever rules after. 1 action.",
        {
            "kind": "What the plan aims at",
            "name": "What the plan is called",
            "target_id": "The land, world, house, people or town it aims at",
            "steps": "Steps it needs, 1 to 100",
            "secrecy": "How secret it is kept, 0 to 100",
        },
    ),
    T.SEEK_PATRON: ToolText(
        "You become the client of a patron; where institutions are weak, patrons place their clients in office and sway votes for them. 1 action.",
        {"patron_id": "The patron you seek"},
    ),
    T.BUY_OFFICE: ToolText(
        "You buy an empty seat of your realm at the price of offices; the seat repays its buyer over the years and raises corruption. 1 action.",
        {"office_id": "The seat you buy"},
    ),
    T.SIT_EXAMINATION: ToolText(
        "You sit the examinations of your realm; with enough learning in law, letters or lore you earn a credential that opens offices. 1 action.",
        {},
    ),
    T.JOIN_SCHOOL: ToolText(
        "You join a school of thought as a disciple of its master; masters teach and the school keeps its learning. 1 action.", {"school_id": "The school"}
    ),
    T.PURGE_CIRCLE: ToolText(
        "As ruler you cast a member of your ruling circle out of the circle and of every seat they hold. 1 action.",
        {"mortal_id": "The member you purge"},
    ),
    T.GUARD_THRONE: ToolText(
        "As ruler you choose how you guard your rule against your own army: rotating commanders lowers their power and the army's morale, "
        "a parallel guard costs upkeep, promotion by loyalty favours your clients, hostages hold the ambitious back. Each measure lowers "
        "the chance of a coup. 1 action.",
        {
            "rotation": "Rotate commanders and governors",
            "parallel_guard": "Keep a guard of your own beside the army",
            "loyalty_promotion": "Promote by loyalty over merit",
            "hostages": "Keep hostages from the powerful",
        },
    ),
    T.STEER_MARRIAGES: ToolText(
        "As head of a house you set its marriages to follow a long design across generations, toward an inherited gift or a union with a claim on a realm; love matches, childless couples and exposure stand in its way. 1 action.",
        {
            "name": "What the design is called",
            "locus": "The inherited trait the design breeds for",
            "allele": "The form of that trait it wants",
            "claim_polity_id": "The realm whose claimants the house should marry",
            "target_share": "Share of the house that should carry it, 1 to 100",
            "steps": "Steps the design needs, 1 to 100",
        },
    ),
    T.ENCLOSE_COMMONS: ToolText(
        "You enclose a common of your land for yourself; it yields you coin each epoch, while those who used it lose their living, "
        "grow restless and drift to the cities. 1 action.",
        {"commons_id": "The common you enclose"},
    ),
    T.RULE_COMMONS: ToolText(
        "You set a council over a common of your land; a common ruled by its users wears down far more slowly when many depend on it. 1 action.",
        {"commons_id": "The common the council rules"},
    ),
    T.OPEN_GROUND: ToolText(
        "Open a ground for your people to catch from in the land you stand on ({{ catch_grounds | join(', ') }}), worked with gear it allows "
        "({{ catch_gear | join(', ') }}). Shores and beds are worked from the land itself; land game and fowl from a kind of beast that lives there. 1 action.",
        {"region_id": "The land you stand on", "ground": "What you catch", "gear": "What you catch it with", "kind_id": "For game and fowl: the kind you hunt"},
    ),
    T.BUILD_PONDS: ToolText(
        "Build fish ponds for your town by its river; they yield fish without taking from the wild, eat grain and are ruined by floods. 1 action.",
        {"settlement_id": "Your town"},
    ),
    T.CHANGE_GEAR: ToolText(
        "Change the gear a ground of your land is worked with ({{ catch_gear | join(', ') }}); gear the ground does not allow is refused. 1 action.",
        {"source_id": "What the ground draws on", "region_id": "The land of the ground", "gear": "The new gear"},
    ),
    T.SET_COMMONS_RULE: ToolText(
        "As ruler of a realm, set how a common in it is ruled ({{ commons_rules | join(', ') }}). Under state rule your officials hold its use to "
        "the quota and its yield goes to your treasury; under licensed rule its use is sold as permits at the price you name. 1 action.",
        {
            "commons_id": "The common",
            "rule": "How it is ruled",
            "quota": "Use allowed each epoch, 0 to 200",
            "licence_price": "Coin a permit costs for each point of quota",
        },
    ),
    T.RESERVE_GAME: ToolText(
        "You reserve the game of your land for your own hunts; the reserve protects its beasts from hunting, but the hungry poach "
        "and the folk resent the law. 1 action.",
        {"species_id": "The beast the reserve protects, or none for all game", "strictness": "How strictly it is kept, 0 to 100"},
    ),
    T.POACH_GAME: ToolText(
        "You take game from a reserve in your land that is not yours; it feeds you and earns a little coin, but it breaks the holder's law. 1 action.",
        {"reserve_id": "The reserve you poach in"},
    ),
    T.PLANT_PERENNIAL: ToolText(
        "You plant a long-lived planting in your land ({{ perennial_kinds }}); it bears only after epochs, then yields you coin each epoch "
        "until war or neglect cuts it down. 1 action.",
        {"kind": "What you plant", "species_id": "The plant you set, if any"},
    ),
    T.SEND_AID: ToolText(
        "As ruler you send aid to a town ({{ aid_kinds }}); the town owes your realm a favour and a gift in return and its folk love your god "
        "more, but a rival may turn the aid away. 1 action.",
        {"settlement_id": "The town you aid", "kind": "What you send"},
    ),
    T.PLAN_REBUILDING: ToolText(
        "You draw the plan for rebuilding your town after its ruin; a planned rebuilding costs more and takes longer, but it is built sturdier, with wider streets, and burns less. 1 action.",
        {},
    ),
    T.PREPARE_TOWN: ToolText(
        "You pay to raise one of your town's works against disaster ({{ preparedness_kinds }}); each level lowers the losses of the disaster "
        "it guards against. 1 action.",
        {"kind": "The work you raise"},
    ),
    T.DRAFT_UNIT_TYPE: ToolText(
        "As one who knows war, you set out a new kind of soldier for your realm or town: a named type for a battlefield role, with the "
        "loadout, doctrine and formation its makers can give it; its armies muster it from then on. Needs tactics or strategy of "
        "{{ rules.unit_types.draft_skill }}. 1 action.",
        {
            "role": "The battlefield role it fills; one of: {{ unit_roles }}",
            "name": "What the soldiers are called; left empty, your people names them in its own tongue",
            "description": "What sets these soldiers apart, in your words",
        },
    ),
    T.FORGE_MODEL: ToolText(
        "You make a new equipment model for your realm or town: a named weapon, armour, shield or piece of materiel, as good as your "
        "metalworking or engineering and your craft allow, made of your town's own material; its metalworkers make it from then on. 1 action.",
        {
            "family": "What kind of piece it is; one of: {{ equipment_families }}",
            "name": "What the model is called; left empty, your people names it in its own tongue",
            "description": "What sets the model apart, in your words",
        },
    ),
    T.CREATE_DISH: ToolText(
        "You first cook a new dish for your people, or for your town if you belong to no people, made in a way they know; their towns cook it from their stores from then on, "
        "and how it is made sets how it nourishes, delights and keeps. 1 action.",
        {
            "method": "How it is made; one of: {{ cooking_methods }}",
            "course": "When it is eaten; one of: {{ dish_courses }}",
            "ingredients": "One to four foods it is made of; each one of: {{ foods }}",
            "name": "What the dish is called; left empty, your people names it in its own tongue",
            "description": "What sets the dish apart, in your words",
        },
    ),
    T.DRAW_STRUCTURE_TYPE: ToolText(
        "As a builder, you draw a building type for your people, or for your town if you belong to no people, for one kind of structure, "
        "with the form and storeys you choose; its builders raise that kind to it from then on. Needs engineering of {{ rules.integrity.draw_skill }}. 1 action.",
        {
            "structure_kind": "The kind of structure it is a type of; one of: {{ structure_kinds }}",
            "form": "Its building form, if you choose; one of: {{ building_forms }}",
            "storeys": "How many storeys it rises, if you choose",
            "name": "What the type is called; left empty, your people names it in its own tongue",
            "description": "What sets the type apart, in your words",
        },
    ),
    T.LEAD_EXPEDITION: ToolText(
        "You lead an expedition with your companions into a site, a land, an underworld or another realm; each leg uses provisions, and light on dark ground; "
        "running short raises danger and stress, and those who return bring finds and renown. You travel by one way your people's bodies can use "
        "({{ movement_modes }}); a way that finds little passage in the land you seek adds legs. 1 action.",
        {"target_id": "Where you go", "mode": "How you travel; leave empty to take the way with the best passage"},
    ),
    T.MAKE_CAMP: ToolText(
        "You make your expedition camp now; the party rests off fatigue and stress for a ration each, though a night ambush may come. 1 action.",
        {},
    ),
    T.ORDER_FORMATION: ToolText(
        "As the commander of a formation or of its army, you give it an order ({{ echelon_orders }}); a formation on standing orders loses "
        "organisation, one ordered to attack fights harder, to hold digs in, to manoeuvre regains order and to resupply is fed first. 1 action.",
        {"echelon_id": "The formation", "order": "The order"},
    ),
    T.PETITION_SPIRIT: ToolText(
        "You petition a spirit office ({{ petition_kinds }}); the office reads it after a delay and grants or denies it, and a denied "
        "petition may be appealed to the office above. A suit is brought against an offended spirit under that office. 1 action.",
        {"spirit_id": "The spirit office you petition", "kind": "What you ask for"},
    ),
    T.OFFER_TO_SPIRIT: ToolText(
        "You bring an offering to a spirit that dwells in a place; a content spirit grants favour to its community. 1 action.",
        {"spirit_id": "The spirit"},
    ),
    T.SEEK_VISION: ToolText(
        "You seek a direct experience of the divine; it comes only to a mind of wisdom that holds piety dear, and it draws followers. 1 action.",
        {},
    ),
    T.CONSULT_DIVINER: ToolText(
        "As ruler you have your court diviners read the omens on a question ({{ divination_questions }}); if you heed diviners you act on "
        "what they read. 1 action.",
        {"question": "What you ask"},
    ),
    T.PREACH_END_TIME: ToolText(
        "As a mystic or seer you preach that the end is near in your town; the faithful gather, stop working as the day nears and, when it "
        "passes, read the prophecy anew, become a sect or disperse. 1 action.",
        {},
    ),
    T.FORGE_WORK: ToolText(
        "You make a forgery ({{ forgery_kinds }}): a work, a relic, a charter or a town's brand to copy, a realm whose coin you counterfeit or whose "
        "seal passes your false orders, or a title whose lineage you forge to claim it. It may serve as the real thing until the expert of its kind "
        "sees through it; then you are tried for its crime. 1 action.",
        {"original_id": "What you copy, or the realm or title you forge against", "kind": "The kind of forgery, or empty to let what you copy decide"},
    ),
    T.REVIEW_WORK: ToolText(
        "As a critic of renown you judge a work before the market: praise raises its price and the standing of its movement, a pan sinks them, "
        "by up to {{ rules.art_market.critic_price_swing_pct }}% as your renown allows. 1 action.",
        {"artwork_id": "The work you judge"},
    ),
    T.CLAIM_RIGHT: ToolText(
        "You claim a right ({{ right_kinds }}) over something you made or know: a work, a song, a name, a dish you created or a technique you hold. "
        "Or you take a right staked in a contest you won, or a right your partner's line passes with your union. Others who use it then owe you "
        "or infringe it. 1 action.",
        {
            "kind": "The kind of right",
            "name": "What the right is called",
            "subject_id": "The work, rite, house or realm it covers, or empty",
            "dish_id": "The dish a right to a recipe covers, or empty",
            "technique": "The technique a right to a technique covers, or empty",
            "contest_id": "A contest you won in which the right was staked, or empty",
            "marriage_id": "Your union through which the right passes, or empty",
        },
    ),
    T.BUY_WORK: ToolText("You buy a work of art at its market price from whoever holds it. 1 action.", {"artwork_id": "The work"}),
    T.FOUND_CLUB: ToolText(
        "You found a club in your town ({{ club_kinds }}); it plays matches, gathers fans and may come to sway the town. A club of animal "
        "contests keeps and breeds the beasts of its sport and needs a town that keeps them; a club of games of the mind trains its players and draws patrons. 1 action.",
        {"kind": "What the club plays, or empty to let it be chosen"},
    ),
    T.FIX_CONTEST: ToolText(
        "You arrange that a club of a match you name wins its next contest, for a wager or a patron. If it is found out, by "
        "{{ rules.clubs.fixing_detect_pct }}% chance, the wagers are void, both clubs lose standing, you are tried for it and the crowd may rise. 1 action.",
        {"match_id": "A match between the clubs", "side": "The club of that match that is to win"},
    ),
    T.TAKE_CONTRACT: ToolText(
        "You take an open contract on a beast of your world; you study it and hunt it each epoch until it falls or you are too hurt to go on. 1 action.",
        {"contract_id": "The contract"},
    ),
    T.COMMAND_CONSTRUCT: ToolText(
        "You give a construct you command a new first order ({{ order_kinds }}), aimed at a target or at no one. 1 action.",
        {"construct_id": "The construct", "kind": "The order", "target_id": "Whom or what it aims at, or empty"},
    ),
    T.FORECAST_SEASONS: ToolText(
        "As one learned in the sky, you read when a long season of your world will end; your people may heed you and store food. 1 action.",
        {"long_season_id": "The id of the long season (see the long seasons of your world)"},
    ),
    T.SET_ECONOMIC_ORDER: ToolText(
        "As ruler of a realm, you set its economic order, or that of one good it makes: who owns, how goods are allotted, how labour is "
        "bound and how the product is shared. 1 action.",
        {
            "polity_id": "The realm you rule",
            "sector": "The good whose order you set, or empty for the whole realm",
            "ownership": "Who owns land and works: household, kin_group, community, temple, ruler, state, private, cooperative, company, common or none",
            "allocation": "How goods are allotted: market, redistribution, command, obligation, gift, need or abundance",
            "labour": "How labour is bound: free, kin, corvee, serf, bound, enslaved, conscripted, cooperative or made",
            "distribution": "How the product is shared: by_holding, by_office, by_need, by_work, by_share, equal or by_prestige",
            "reason": "Why you set it",
        },
    ),
    T.BEGIN_TRANSITION: ToolText(
        "As ruler of a realm, you proclaim a change of its economic order; holdings move in stages to their new hands, and those who lose "
        "them resist unless they are paid. 1 action.",
        {
            "polity_id": "The realm you rule",
            "sector": "The good whose order changes, or empty for the whole realm",
            "kind": "The change: collectivisation, nationalisation, privatisation, land_reform, enclosure, emancipation, decollectivisation or "
            "restoration_of_holdings",
            "compensation": "What the losers are paid: none, partial or full",
            "reason": "Why you change it",
        },
    ),
    T.CHANGE_MONEY: ToolText(
        "With the accounting of a money changer, you take up the changing of coin at your market and keep a share of the spread. 1 action.",
        {},
    ),
    T.SABOTAGE_REMAKING: ToolText(
        "You set back a plan that remakes the land you live from: its progress falls back and the land it touches goes back a step. 1 action.",
        {"plan_id": "The plan"},
    ),
    T.SWEAR_VENGEANCE: ToolText(
        "You swear vengeance on one who killed your kin; you start a pursuit of vengeance, which may end in their fall, in yours or in neither. 1 action.",
        {"foe_id": "The one who killed your kin"},
    ),
    T.PURIFY_SELF: ToolText(
        "You seek purification in the way your people knows, paying what it costs; if it takes, you are pure again and may join gatherings and "
        "unions. 1 action.",
        {},
    ),
    T.ACCUSE_OF_WITCHCRAFT: ToolText(
        "You accuse a neighbour of your town of witchcraft; the court tries them in a later epoch by the way your realm tries cases, and the charge "
        "may be true or false. 1 action.",
        {"accused_id": "Whom you accuse"},
    ),
    T.MAKE_CHARM: ToolText(
        "You make an item you own a charm (protection, fertility, luck or healing); it calms you whether or not its power is real. 1 action.",
        {"power": "The charm's power"},
    ),
    T.JOIN_COOPERATIVE: ToolText(
        "You join a cooperative of your town and pool your means with its members; it eases their want. 1 action.",
        {"faction_id": "The cooperative"},
    ),
    T.LEAD_REVIVAL: ToolText(
        "You lead a movement of your own people against those who press on it, choosing its way ({{ revival_ways }}) and its goal "
        "({{ revival_goals }}); you become its prophet. Restoring may seek any goal; synthesis seeks the old god or the language; adopting "
        "seeks rule by the people itself; waiting seeks rule, land or the foreigners gone; withdrawing seeks the language or the old god. "
        "1 action.",
        {"people_id": "Your people", "way": "The way the movement takes", "goal": "What it seeks"},
    ),
    T.SEEK_CITIZENSHIP: ToolText(
        "As a foreigner in your realm, you pay to become its citizen and gain the rights citizens hold. 1 action.",
        {},
    ),
    T.BUY_INSURANCE: ToolText(
        "You insure your life with an insurer of your town: you pay a premium each epoch, and when you die it pays your household. 1 action.",
        {"insurer_id": "The insurer"},
    ),
    T.INVENT_GAME: ToolText(
        "You make up a game for your people and name it in their tongue; it may spread to their neighbours. 1 action.",
        {"kind": "What sort of game it is"},
    ),
    T.JOIN_ROAD_FOLK: ToolText(
        "You bring your town into the culture of a busy road between worlds: it comes to share that culture's ways and speech. 1 action.",
        {"culture_id": "The culture of the road"},
    ),
    T.SEEK_SANCTUARY: ToolText(
        "If you are hunted as an outlaw or accused before a court, you claim sanctuary in a temple of your town, or with a town whose custom "
        "welcomes guests. While you are sheltered no one may seize or punish you; your pursuer may wait, bargain, surround the refuge or break in. 1 action.",
        {},
    ),
    T.MOCK_THE_RULER: ToolText(
        "You mock the ruler of your realm in public. Where the court tolerates mockery it costs the ruler standing and its folk approve of the "
        "ruler less; where it does not, you may be imprisoned. 1 action.",
        {},
    ),
    T.JOIN_PROGRAMME: ToolText(
        "If you are skilled in science, engineering or computing, you work on your realm's programme toward a technique and speed it on. 1 action.",
        {"programme_id": "The programme"},
    ),
    T.TEND_CULTURE: ToolText(
        "You tend a ferment culture of your town, or start one if it has none of that kind; a kept culture makes the town's baked, cured, fermented,"
        " pickled and brewed food better. 1 action.",
        {"kind": "The culture: yeast, starter, mould, lactic or vinegar"},
    ),
    T.MAKE_MIND: ToolText(
        "You make a mind in a thing near you, by the method you name, with the will and purpose you give it; your skill sets how well it turns out. 1 action.",
        {"target_id": "The thing that will hold the mind", "method": "How you make it", "will": "How much will you give it", "purpose": "What it is for"},
    ),
    T.FREE_MIND: ToolText(
        "You release a mind of your making from service. 1 action.",
        {"mind_id": "The mind"},
    ),
    T.BIND_MIND: ToolText(
        "You bind a mind of your making to obey your word. 1 action.",
        {"mind_id": "The mind"},
    ),
    T.SAVE_MIND: ToolText(
        "You save the state of your mind, or of one you made, so it can be restored later. 1 action.",
        {"mind_id": "The mind", "medium": "What holds the saved state"},
    ),
    T.RESTORE_MIND: ToolText(
        "You restore a mind from a state you hold, into a seat you name or its own body. It remembers nothing after the state was taken. 1 action.",
        {"state_id": "The saved state", "seat_id": "Where the mind will run, or empty for its own body"},
    ),
    T.COPY_MIND: ToolText(
        "You copy your mind, or one you made, into another seat; the copy is a little less faithful than the source. 1 action.",
        {"mind_id": "The mind", "seat_id": "Where the copy will run"},
    ),
    T.TRANSFER_MIND: ToolText(
        "You move your mind, or one you made, into another seat. 1 action.",
        {"mind_id": "The mind", "seat_id": "Its new seat"},
    ),
    T.MERGE_MINDS: ToolText(
        "You merge two minds of yours or of your making into one; the second ends as itself. 1 action.",
        {"mind_ids": "The two minds, the one that stays first"},
    ),
    T.INSTALL_AUGMENT: ToolText(
        "You take an augment into your own body, in the part you name or across the whole body. 1 action.",
        {"body_part": "The part it goes in, or empty for the whole body", "kind": "What the augment does", "make": "How it is made"},
    ),
    T.REMOVE_AUGMENT: ToolText(
        "You have one of your augments taken out. 1 action.",
        {"augment_id": "The augment"},
    ),
    T.LINK_TO: ToolText(
        "You link your mind with another's, so the two share what they think. 1 action.",
        {"target_id": "The one you link with"},
    ),
    T.RUN_REMOTE_BODY: ToolText(
        "You run a made body from afar as if it were your own. 1 action.",
        {"body_id": "The made body"},
    ),
    T.BUILD_NETWORK: ToolText(
        "You build a network from your home, carried the way you name, open to whom you choose, and bring the members you name onto it. 1 action.",
        {"carrier": "How it carries what it carries", "access": "Who may use it", "member_ids": "Who else joins at once"},
    ),
    T.JOIN_NETWORK: ToolText(
        "You bring your home onto a network. 1 action.",
        {"network_id": "The network"},
    ),
    T.CUT_NETWORK: ToolText(
        "You cut one member off a network, or bring the whole network down for an epoch. 1 action.",
        {"network_id": "The network", "node_id": "The member to cut off, or empty to bring it all down"},
    ),
    T.INTRUDE: ToolText(
        "You try to break into a network, store, mind or made thing for the aim you name; you may be found and identified. 1 action.",
        {"target": "What kind of thing you break into", "target_id": "The thing", "aim": "What you want from it"},
    ),
    T.DEFEND_SYSTEM: ToolText(
        "You harden a network or store against intrusion. 1 action.",
        {"system_id": "The network or store"},
    ),
    T.LEAK_RECORDS: ToolText(
        "You let out the secrets a store holds, so they become known. 1 action.",
        {"store_id": "The store"},
    ),
    T.PUBLISH: ToolText(
        "You publish a true record about someone or something, kept in your home. 1 action.",
        {"subject_id": "What the record is about"},
    ),
    T.FORGE_RECORD: ToolText(
        "You write a false record about someone or something and pass it as genuine. 1 action.",
        {"subject_id": "What the false record is about"},
    ),
    T.FOUND_COMPANY: ToolText(
        "You found a company in your home and hold all its shares. 1 action.",
        {"name": "Its name"},
    ),
    T.CHARTER_COMPANY: ToolText(
        "As ruler of a realm, you charter a company to work in it. 1 action.",
        {"company_id": "The company"},
    ),
    T.BUY_SHARES: ToolText(
        "You buy parts of a company for coin. 1 action.",
        {"company_id": "The company", "share": "How many of its hundred parts you buy"},
    ),
    T.BUILD_REPLICATOR: ToolText(
        "You start a self-making line in your land that feeds on the stock you name and makes what you name. It can drift and spread. 1 action.",
        {"output": "What it makes", "feedstock": "What it feeds on"},
    ),
    T.CONTAIN_REPLICATOR: ToolText(
        "You tighten the containment of a self-making line. 1 action.",
        {"line_id": "The line"},
    ),
    T.FABRICATE: ToolText(
        "You set more of your town's goods to be fabricated rather than made by hand. 1 action.",
        {},
    ),
    T.LICENSE_PATTERN: ToolText(
        "You pay for the right to use a pattern. 1 action.",
        {"pattern_id": "The pattern"},
    ),
    T.STUDY_RELIC: ToolText(
        "You study a relic of a making your people have lost, to learn how it works. 1 action.",
        {"item_id": "The relic"},
    ),
    T.SALVAGE: ToolText(
        "You take what can be used from a salvage site. 1 action.",
        {"site_id": "The site"},
    ),
    T.BUILD_REALM: ToolText(
        "You make a realm kept running by the host you name, for the purpose you name, at the time ratio you set. 1 action.",
        {"host_id": "What holds it", "purpose": "What it is for", "ratio": "How fast it runs against world time (%)"},
    ),
    T.ENTER_REALM: ToolText(
        "You go into a made realm; your mind runs there. 1 action.",
        {"realm_id": "The made realm"},
    ),
    T.CONFINE_IN_REALM: ToolText(
        "As ruler, you confine someone's mind in a made realm. 1 action.",
        {"target_id": "Whom you confine", "realm_id": "The made realm"},
    ),
    T.WITHDRAW_PEOPLE: ToolText(
        "As ruler, you move a people's minds into a made realm. 1 action.",
        {"people_id": "The people", "realm_id": "The made realm"},
    ),
    T.SET_SURVEILLANCE: ToolText(
        "As ruler, you set what your realm's watch looks for. 1 action.",
        {"focus": "What the watch looks for"},
    ),
    T.SET_PROVISION: ToolText(
        "As ruler, you set how your realm provides for its people once goods can be fabricated: by market, ration, for all, by status, by standing or in common. 1 action.",
        {"level": "How goods are given out"},
    ),
    T.USE_POWER: ToolText(
        "You use a power you hold, on someone or on yourself. Each use strains you; past your limit it harms you. 1 action.",
        {"power_id": "The power", "target_id": "Whom or what you use it on, or empty for yourself"},
    ),
    T.TRAIN_POWER: ToolText(
        "You train a power you hold to master it better. 1 action.",
        {"power_id": "The power"},
    ),
    T.TEST_FOR_GIFTS: ToolText(
        "As ruler, you have the people of your town tested for hidden gifts. 1 action.",
        {},
    ),
    T.LINK_MINDS: ToolText(
        "You link your power with another who holds one; linked, you are stronger together and share the strain. 1 action.",
        {"partner_id": "Whom you link with"},
    ),
    T.FORESEE: ToolText(
        "You use a power over time to see what may come. 1 action.",
        {"power_id": "The power"},
    ),
    T.KEEP_SECRET_OF: ToolText(
        "You take up the keeping of a hidden truth you know of. 1 action.",
        {"truth_id": "The hidden truth"},
    ),
    T.INVESTIGATE: ToolText(
        "You look into a hidden truth you have heard of, for an aim of your own. 1 action.",
        {"truth_id": "The hidden truth", "aim": "What you want: expose, exploit, destroy_the_hidden, join_the_hidden or understand"},
    ),
    T.COVER_UP: ToolText(
        "As one who holds it, you cover up a hidden truth in your town so fewer believe what they heard. 1 action.",
        {"truth_id": "The hidden truth"},
    ),
    T.SET_POWER_LAW: ToolText(
        "As ruler, you set how your realm treats those with powers and powers over minds. 1 action.",
        {
            "level": "Those with powers are: free, registered, licensed, conscripted, hunted or banned",
            "mind_powers": "Powers over minds are: allowed, licensed or banned",
        },
    ),
    T.BREED_LINE: ToolText(
        "You breed a kind of life over generations toward traits you choose, making a living line of your own. 1 action.",
        {
            "species_id": "The kind of life you breed from",
            "name": "Name of the line",
            "traits": "Traits you aim for, each with a strength from -100 to 100",
            "traits.trait": "The trait: yield, hardiness, climate_tolerance, disease_resistance, strength, speed, size, regeneration, lifespan, docility, potency, fibre, venom, flight, aquatic, void_hardy, gift, nervous_system or sapience",
            "traits.strength": "How strongly, from -100 to 100",
        },
    ),
    T.DESIGN_LINE: ToolText(
        "You make a living line by a way of living craft from organisms you can reach. Each trait you add makes the line less stable. "
        "A source with a written genome also carries its own inherited leanings into the line. 1 action.",
        {
            "name": "Name of the line",
            "method": "How: selective_breeding, cultivation, shaping, engineering, synthesis, binding, cloning, merging or induction",
            "source_ids": "The organisms it is made from",
            "traits": "Traits you aim for, each with a strength from -100 to 100",
            "traits.trait": "The trait: yield, hardiness, climate_tolerance, disease_resistance, strength, speed, size, regeneration, lifespan, docility, potency, fibre, venom, flight, aquatic, void_hardy, gift, nervous_system or sapience",
            "traits.strength": "How strongly, from -100 to 100",
            "fertility": "How it breeds: sterile, breeds_true, breeds_wild or needs_maker",
        },
    ),
    T.BANK_SAMPLE: ToolText(
        "You put a sample of a living thing into a bank of life you can reach, so its traits are kept. 1 action.",
        {
            "bank_id": "The work that keeps the bank",
            "organism_id": "The living thing you sample",
        },
    ),
    T.PLANT_LINE: ToolText(
        "You plant a line you hold in your land as a long-lived planting. 1 action.",
        {
            "line_id": "The line",
        },
    ),
    T.RAISE_LINE: ToolText(
        "You raise a line again from a sample kept in a bank you hold. 1 action.",
        {
            "sample_id": "The sample",
        },
    ),
    T.GROW_STRUCTURE: ToolText(
        "You grow a living work in your town; it grows from a seed and cannot work at full until grown. 1 action.",
        {
            "name": "Name of the work",
            "line_id": "A line of yours it is grown from, or empty",
        },
    ),
    T.GROW_VESSEL: ToolText(
        "You grow a living vessel that eats, heals, ages and bonds with you. 1 action.",
        {
            "name": "Name of the vessel",
            "line_id": "A line of yours it is grown from, or empty",
        },
    ),
    T.GROW_GEAR: ToolText(
        "You grow a living thing to be worn or wielded; it feeds on its bearer and bonds with them. 1 action.",
        {
            "name": "Name of the gear",
            "line_id": "A line of yours it is grown from, or empty",
        },
    ),
    T.GROW_ORGAN: ToolText(
        "You grow a part for a body, yours or another's here. 1 action.",
        {
            "slot": "Where it goes: part, mind, senses, skin, blood or whole_body",
            "kind": "What it does: replacement, enhancement, interface, weapon, regulator, sense, storage or cosmetic",
            "bearer_id": "Whose body, or empty for your own",
        },
    ),
    T.CLONE: ToolText(
        "You grow a clone of a body here, yours or another's: a new person with its own mind and history. 1 action.",
        {
            "source_id": "Whose body is copied",
        },
    ),
    T.HOST_SYMBIONT: ToolText(
        "You take something of a line you hold to live within you. 1 action.",
        {
            "line_id": "The line",
            "placement": "Where it lives: skin, blood, organ, nerve or mind",
            "relation": "How it lives with you: mutual, commensal, parasitic or controlling",
        },
    ),
    T.REMOVE_SYMBIONT: ToolText(
        "You have something that lives within you taken out; removal harms by where it lived. 1 action.",
        {
            "symbiont_id": "What lives within you",
        },
    ),
    T.DESIGN_DISEASE: ToolText(
        "You make a disease by design, aimed at whom you name or at no one; it may get loose among its makers. 1 action.",
        {
            "name": "Name of the disease",
            "target_id": "Whom it is made to strike, or empty",
            "lethality": "How deadly, from 1 to 100",
            "virulence": "How readily it spreads, from 1 to 100",
        },
    ),
    T.DESIGN_CURE: ToolText(
        "You culture a cure for a disease from a potent line you hold, for your town. 1 action.",
        {
            "disease_id": "The disease",
            "line_id": "The line",
        },
    ),
    T.FOUND_LIVING_WORKS: ToolText(
        "You found living works in your town that make goods by living things. 1 action.",
        {
            "method": "How: cultured_crops, grown_timber, fibre_from_life, vat_culture or bioreactor",
            "name": "Name of the works",
        },
    ),
    T.RELEASE_LINE: ToolText(
        "You let a line you hold loose into the wild, where it lives as a kind of its own. 1 action.",
        {
            "line_id": "The line",
        },
    ),
    T.RAISE_SAPIENCE: ToolText(
        "You shape a line with a designed nervous system toward thought; strong enough, its kind rises as a people. 1 action.",
        {
            "line_id": "The line",
        },
    ),
    T.LICENSE_LINE: ToolText(
        "You pay the owner of a line for a licence to grow it. 1 action.",
        {
            "line_id": "The line",
            "fee": "What you pay",
        },
    ),
    T.SET_CLONE_LAW: ToolText(
        "As ruler, you set whether clones may be made in your realm. 1 action.",
        {
            "level": "Making clones is: banned, licensed or free",
        },
    ),
    T.FOUND_FACTION: ToolText(
        "You gather others in your town into a body of a kind you choose, and you lead it; you need some renown and a little wealth. 1 action.",
        {"kind": "What kind of body; your people may found these unless their own ways say otherwise: {{ foundable_factions }}"},
    ),
    T.TAKE_CARE: ToolText(
        "You spend a little to take care this season, so the mishaps of daily life are less likely to befall you. 1 action.",
        {},
    ),
    T.INVENT_KIND: ToolText(
        "You make a new kind of thing for your people, of a category its kind of thing allows, and give it a name and a description; "
        "your people makes it, and it may pass to neighbours and trading partners. 1 action.",
        {
            "concept": "What kind of thing it is",
            "category": "The category key it belongs to; each kind of thing has categories of its own",
            "name": "Its name",
            "description": "What it is, in a sentence or two",
        },
    ),
    T.ADOPT_KIND: ToolText(
        "Your people takes up a kind of thing that another people made or holds. 1 action.",
        {"concept": "What kind of thing it is", "kind_id": "The kind to take up"},
    ),
    T.FORBID_KIND: ToolText(
        "As ruler of a realm or head of a cult, you forbid a kind of thing to those you lead. 1 action.",
        {"concept": "What kind of thing it is", "kind_id": "The kind to forbid"},
    ),
    T.TAKE_ARMS: ToolText(
        "As head of a house, or ruler of a realm if you head no house, you choose the arms it bears: field, division, line, charges, rim, supporters and motto. 1 action.",
        {
            "field": "The main colour of the field",
            "shape": "The shape of the shield",
            "division": "How the field is divided",
            "line": "The line of the division",
            "second": "The second colour of a divided field",
            "charge": "The figure set on the field",
            "charge_tincture": "The colour of that figure",
            "rim": "The border around the field",
            "arrangement": "How several figures are set out",
            "supporter": "The figure that holds up the arms",
            "supporter_pose": "How the supporters stand",
            "motto": "The words under the arms",
        },
    ),
    T.RECKON_YEARS: ToolText(
        "As ruler of a realm, you choose how its years are counted from now on. 1 action.",
        {"kind": "How years are counted", "cycle_years": "Length of a cycle in years, for counts that run in cycles"},
    ),
    T.SPEAK_FOR_NORM: ToolText(
        "You speak among your people for how a deed should be held in a given situation; the custom moves to what you ask. 1 action.",
        {"situation": "The situation the custom covers", "behaviour": "The deed it judges", "stance": "How the deed should be held"},
    ),
    T.SET_ROLE_CUSTOM: ToolText(
        "As ruler, you set your people's custom for who may hold a role and from what age. 1 action.",
        {"role": "The role", "eligibility": "Who may hold it", "min_age": "The least age to hold it", "stance": "How taking it up is held"},
    ),
    T.READ_THE_SKY: ToolText(
        "You read a body of your sky for your people; they come to hold that reading of it. 1 action.",
        {"celestial_id": "The body in the sky", "reading": "What it is taken to mean"},
    ),
    T.SET_SPEECH: ToolText(
        "As ruler, you name the tongue your people use for a register of speech. 1 action.",
        {"speech": "Where the tongue is used", "language_id": "The tongue"},
    ),
    T.TEACH_TONGUE: ToolText(
        "You teach a tongue in your town for one kind of use; more of the town come to use it so. 1 action.",
        {"language_id": "The tongue", "kind": "The use it is taught for"},
    ),
    T.KEEP_LEGACY: ToolText(
        "You keep among your people something of a people who came before: a way, a name or a belief they left. 1 action.",
        {"predecessor_id": "The people who came before", "kind": "What is kept of them"},
    ),
    T.ASSIGN_CASTE: ToolText(
        "As ruler, you set the caste of a mortal of your people. 1 action.",
        {"mortal_id": "The mortal", "caste": "The caste"},
    ),
    T.PROCLAIM_AGE: ToolText(
        "As ruler, you proclaim what age your realm lives in. 1 action.",
        {"age": "The age proclaimed"},
    ),
    T.DRAW_BLUEPRINT: ToolText(
        "You draw a design that others of your craft can build from. 1 action.",
        {"kind": "What sort of design it is", "subject": "What it is a design of"},
    ),
    T.DEVISE_USE: ToolText(
        "You devise a new way of keeping animals for a use, which herders can take up. 1 action.",
        {"use": "What the animals are kept for", "name": "The name of this way", "description": "What this way is, in a sentence or two"},
    ),
    T.RAISE_MOVEMENT: ToolText(
        "As leader of a faction, you turn it into a movement for a cause, or renew its cause; it gains support. 1 action.",
        {"cause": "What the movement stands for"},
    ),
    T.CLAIM_COURTS: ToolText(
        "As ruler, you claim a right of judgement over another realm. 1 action.",
        {"realm_id": "The other realm", "claim": "The right you claim"},
    ),
    T.DRILL_TRAIT: ToolText(
        "As commander of an army, you school yourself in a way of command. 1 action.",
        {"trait": "The way of command"},
    ),
    T.FACE_FEAR: ToolText(
        "You face one of your fears; it weakens, and may leave you. 1 action.",
        {"fear_id": "The fear"},
    ),
    T.TAKE_UP_WANT: ToolText(
        "You take up a want of your own, toward something or no one in particular. 1 action.",
        {"kind": "What you want", "target_id": "What or whom the want is toward, if anything"},
    ),
    T.EASE_PRESSURE: ToolText(
        "You ease one of your pressures. 1 action.",
        {"pressure": "The pressure to ease"},
    ),
    T.TEACH_HONOUR: ToolText(
        "As ruler, you teach your people a way of holding honour. 1 action.",
        {"model": "The way honour is held"},
    ),
    T.RESIST_DRIFT: ToolText(
        "You hold your town to its ways against one cause that moves them; its effect is halved. 1 action.",
        {"cause": "The cause you resist"},
    ),
    T.MAN_STATION: ToolText(
        "Aboard a vessel, you set how many hands work a station. 1 action.",
        {"vessel_id": "The vessel", "station": "The station", "count": "How many hands"},
    ),
    T.TRIM_SAILS: ToolText(
        "Aboard a vessel, you set its point of sail and the shot it loads. 1 action.",
        {"vessel_id": "The vessel", "point_of_sail": "How it sails to the wind", "shot": "The shot it loads"},
    ),
    T.FOUND_CIRCLE: ToolText(
        "As leader of a faction, you make it a circle of a given kind that meets in your town. 1 action.",
        {"kind": "The kind of circle"},
    ),
    T.PRESS_DEMAND: ToolText(
        "As one of noble birth, you press a demand on your ruler. 1 action.",
        {"want": "What you demand"},
    ),
    T.SWEAR_FEALTY: ToolText(
        "As ruler, you bind your realm to another as its subject. 1 action.",
        {"overlord_id": "The realm you bind yourself to", "kind": "How your realm is bound"},
    ),
    T.SET_LEVY: ToolText(
        "As ruler, you set a tax of your realm and its rate. 1 action.",
        {"kind": "The tax", "rate": "Its rate, out of 100"},
    ),
    T.RUN_RACKET: ToolText(
        "As leader of a faction, you run a racket in your town for steady income. 1 action.",
        {"kind": "The racket"},
    ),
    T.REFIT_SECTION: ToolText(
        "Aboard a vessel, you refit one of its sections to sound condition. 1 action.",
        {"vessel_id": "The vessel", "section": "The section"},
    ),
    T.SHORE_UP: ToolText(
        "You shore up a part of a building where you stand. 1 action.",
        {"structure_id": "The building", "section": "The part"},
    ),
    T.REPLAN_LAND: ToolText(
        "As ruler, you set what the land around your town is used for. 1 action.",
        {"ring": "What the land is given over to"},
    ),
    T.TEND_MAIMED: ToolText(
        "You help one person of your town who lives with a lasting harm back to work. 1 action.",
        {"kind": "The harm"},
    ),
    T.DEVISE_CUSTOM: ToolText(
        "You devise a new kind of technique, tenet, tradition, tale, item or working, built on one your world knows; the result names the bases you can build on if yours is not one. 1 action.",
        {"catalog": "Which kind of thing it is", "base": "What it is built on", "name": "Its name", "description": "What it is, in a sentence or two"},
    ),
    T.BIND_WITH_CHARM: ToolText(
        "You make a charm that someone where you are takes in, binding them to you in love, obedience or devotion until it fades; if it is found, trust in you breaks. 1 action.",
        {"target_id": "Who takes it in", "kind": "What it binds them to feel"},
    ),
    T.LIFT_AFFLICTION: ToolText(
        "As a healer or a priest, you lift an affliction from someone where you are, by one of the cures it yields to. 1 action.",
        {"affliction_id": "The affliction", "cure": "The cure you use"},
    ),
    T.CHOOSE_PATH: ToolText(
        "You take up a new path in life among those open to you where you are; each trains its own skills and leads its own way. 1 action.",
        {"path": "The path"},
    ),
    T.IMPROVE_SOIL: ToolText(
        "You work the soil of the land you live in to restore one of its stocks ({{ nutrient_kinds }}); salinity is washed out rather than "
        "raised. How much it takes depends on how easily the soil there is worked and how acid it is. Soils: {{ soil_kinds }}. 1 action.",
        {"nutrient": "The stock you restore"},
    ),
    T.APPOINT_COURT: ToolText(
        "As ruler or regent you seat a mortal of your court in one of its places ({{ court_positions }}); each place serves the ruler in its own way. 1 action.",
        {"position": "The place at court", "mortal_id": "Who takes it"},
    ),
    T.TAKE_CLIENT: ToolText(
        "You take a mortal where you are as your client, in one of these roles: {{ client_roles }}. Clients serve their patron, and a patron speaks for them. 1 action.",
        {"client_id": "The mortal", "role": "The role they take"},
    ),
    T.SET_RIGHTS: ToolText(
        "As ruler or regent you grant or take away a right ({{ member_rights }}) for one standing of your realm ({{ memberships }}). Those who lack a right grow restless. 1 action.",
        {"category": "The standing", "right": "The right", "granted": "True to grant it, false to take it away"},
    ),
    T.PRESS_CLAIM: ToolText(
        "You press a claim you hold to rule a realm, named by its basis ({{ claim_bases }}); a pressed claim grows stronger and may be fought for. 1 action.",
        {"realm_id": "The realm", "basis": "The basis of your claim"},
    ),
    T.DESIGNATE_HEIR: ToolText(
        "As ruler you name your heir from among any living mortal; under a law of designation your choice stands, though blood kin may contest it. 1 action.",
        {"heir_id": "The heir"},
    ),
    T.FOUND_COOP: ToolText(
        "You lead a body of your town to pool its members' means as a cooperative, for one purpose: {{ coop_purposes }}. 1 action.",
        {"purpose": "What the cooperative is for"},
    ),
    T.TESTIFY: ToolText(
        "You give evidence in an open case of your town, of one kind: {{ evidence_kinds }}. Sworn evidence counts for more, and a false oath is broken. 1 action.",
        {"case_id": "The case", "kind": "The kind of evidence", "sworn": "True to swear before you speak"},
    ),
    T.SET_FACTION_GOAL: ToolText(
        "As leader of a faction you set what it presses for: {{ faction_goals }}. 1 action.",
        {"goal": "The aim", "target_id": "Whom or what it aims at, if anyone"},
    ),
    T.CHALLENGE_TO_DUEL: ToolText(
        "You challenge a mortal to single combat. Kinds of duel: {{ duel_contexts }}; a duel of war, of champions or of gods needs a war "
        "between your homes, the others someone where you are. A duel may end by: {{ duel_ends }}; leave the ending empty to fight by the "
        "custom of your people. 1 action.",
        {"target_id": "Whom you challenge", "context": "What kind of duel it is", "ending": "How it ends; leave empty for your people's custom"},
    ),
    T.CLAIM_IDENTITY: ToolText(
        "You hold one of the identities you have closer, or loosen your hold on it. How much each counts for you decides whom you trust and "
        "with whom you side when your town divides. Layers: {{ identity_layers | join(', ') }}. You can claim only a layer you have. 1 action.",
        {"layer": "Which identity", "loosen": "True to loosen your hold instead of holding it closer"},
    ),
    T.MARK_BODY: ToolText(
        "You put a mark on your own body, or on someone where you are who takes it from you. Marks: {{ mark_kinds }}; an implant shows "
        "an augment the bearer carries and has not yet shown. Meanings: {{ mark_meanings }}. What a mark tells changes how others see "
        "its bearer, as the people of your town read it. 1 action.",
        {"kind": "The mark", "meaning": "What it tells", "target_id": "Who bears it; leave empty for yourself"},
    ),
    T.OPEN_DISTRICT: ToolText(
        "As one who rules a settlement, you open or enlarge a district of it of any of the kinds its world knows; each kind changes what the city stores, "
        "houses, keeps in order and pays for. 1 action.",
        {"settlement_id": "The settlement you rule", "kind": "The kind of district", "material": "What it is built of"},
    ),
    T.REBUILD: ToolText(
        "As one who rules a settlement that waits to be rebuilt after a disaster, you choose how: planned, as it comes, on a safer site nearby, or not at all, "
        "its people leaving. 1 action.",
        {"settlement_id": "The settlement you rule", "plan": "How it is rebuilt"},
    ),
    T.ABANDON_WORK: ToolText(
        "As one who rules a settlement, you call the builders away from a work still being raised there; it stands unfinished. 1 action.",
        {"structure_id": "The work"},
    ),
    T.DISMANTLE_WORK: ToolText(
        "As one who rules a settlement, you take a work there apart; a share of what it cost goes to new building and little is left. 1 action.",
        {"structure_id": "The work"},
    ),
    T.FOUND_GARDEN: ToolText(
        "You pay to lay out a garden of your town of any of the kinds there are; each keeps its own living things and gives its own good. 1 action.",
        {"kind": "The kind of garden"},
    ),
    T.PICK_LOCK: ToolText(
        "You try to get past the lock and guards of a store or vault where you are; some locks yield only to the working or the skill that made them. 1 action.",
        {"structure_id": "The store or vault"},
    ),
    T.SET_CRIME_STANCE: ToolText(
        "As the ruler of a realm, you set how it treats an organisation of crime in it: hunt it down, use it, look away for its bribes or license its trade "
        "under terms. 1 action.",
        {"faction_id": "The organisation", "stance": "How the realm treats it"},
    ),
    T.FLEE: ToolText(
        "If you are hunted, or bound and would run, you flee to a refuge that will take you in where you are: a temple, a host, an embassy, a city whose "
        "charter frees those who stay, or the wilds. 1 action.",
        {"sanctuary": "The kind of refuge you seek, or leave it empty to take the first that will have you"},
    ),
    T.HUNT_FUGITIVE: ToolText(
        "You hunt down a fugitive your realm pursues; those in sanctuary are out of your reach. 1 action.",
        {"fugitive_id": "The fugitive"},
    ),
    T.GIVE_RELIEF: ToolText(
        "As the ruler of a realm you set what relief it gives and what it spends on it each epoch; as anyone else, you give coin to the relief it already gives. "
        "1 action.",
        {"kind": "The kind of relief", "budget": "The coin it costs each epoch, or that you give"},
    ),
    T.CONSTRUCT_LANGUAGE: ToolText(
        "You make a tongue on purpose, with a regular grammar and no inherited history; your town begins to learn it, and it spreads where schools or law teach it. Needs skill in languages. 1 action.",
        {"name": "The tongue's name", "description": "What the tongue is and why it was made", "words": "Its first words", **WORD_FIELDS},
    ),
    T.REPUDIATE_DEBTS: ToolText(
        "As ruler you declare your realm's debts void; its lenders lose them, your realm is shut out of credit for years, and the lenders' realms may take it as cause for war. 1 action.",
        {},
    ),
    T.RESCUE_POLITY: ToolText(
        "As ruler you carry another realm's debts on terms: it keeps paying under your terms, gives you that share of its treasury each epoch, and owes you standing. 1 action.",
        {"polity_id": "The realm you rescue", "terms": "Share of its treasury it pays you each epoch, out of 100"},
    ),
    T.RESCHEDULE_LOAN: ToolText(
        "As a lender you put off the due date of a loan you hold, giving its borrower more time. 1 action.",
        {"loan_id": "The loan", "extra_epochs": "Epochs to put it off by"},
    ),
    T.SELL_LOAN: ToolText(
        "As a lender you sell a loan you hold to another at a discount; they collect it from then on. 1 action.",
        {"loan_id": "The loan", "buyer_id": "Who buys it"},
    ),
    T.INSURE: ToolText(
        "You buy cover from an insurer of your town against one kind of loss: cargo, house, life, crop, vessel or livestock; you pay a premium each epoch and it pays when the loss comes, if it can. 1 action.",
        {"insurer_id": "The insurer", "cover": "What the cover is against"},
    ),
    T.SEIZE_HOARDS: ToolText(
        "As ruler you seize every hoard held back in a market of your realm, returning its goods to sale; prices fall and the merchants resent it. 1 action.",
        {"settlement_id": "The market"},
    ),
    T.PLAY_MARKET: ToolText(
        "As leader of a merchant house you play your home market in a good: cornering it, dumping stock, or spreading a false report that moves its price until the truth arrives. 1 action.",
        {"commodity": "The good", "play": "How you play it"},
    ),
    T.FOUND_WORKSHOP: ToolText(
        "You found a workshop your community lacks and own it; it works its crafts from the next season, needing its inputs and energy. 1 action.",
        {"kind": "The kind of workshop"},
    ),
    T.COMPOSE_ACCOUNT: ToolText(
        "You tell a happening you know of in an account of your own, of any kind and stance; your people keep it as one telling among others, and it moves the standing of those it names. 1 action.",
        {"incident_id": "The happening you tell", "kind": "The kind of account", "stance": "How it tells those who took part"},
    ),
    T.IMPOSE_SCRIPT: ToolText(
        "As a ruler whose own tongue is written, you replace by law the script of a tongue your subjects speak with your realm's script; its speakers resent it. 1 action.",
        {"language_id": "The tongue whose script you replace"},
    ),
    T.MEDIATE: ToolText(
        "As ruler or regent you offer your realm as mediator: of a treaty in force between other realms, which then holds your standing on it "
        "and lets you settle disputes under it, or of an open crisis between two other realms, which you settle by terms both accept if both trust you. "
        "Name either a treaty or a crisis. 1 action.",
        {"treaty_id": "The treaty you stand behind", "crisis_id": "The crisis you settle"},
    ),
    T.SUSPEND_TREATY: ToolText(
        "As ruler or regent you suspend a treaty your realm is party to: its clauses rest without a breach until it resumes or lapses by its term; "
        "the other parties trust you less, though less than for a breach. 1 action.",
        {"treaty_id": "The treaty"},
    ),
    T.DECLARE_NEUTRAL: ToolText(
        "As ruler or regent you declare your realm neutral: it leaves its alliances, joins none, and trades with every side of the wars around it; "
        "whoever makes war on it alarms every realm of its world. 1 action.",
        {},
    ),
    T.PROPOSE_RESOLUTION: ToolText(
        "As ruler or regent of a member you put a resolution to your council of worlds for its members to vote on: "
        "route security, embargo, void ban, sanction, quarantine, arbitration or aid. "
        "An embargo, sanction, quarantine, arbitration or aid names what it is about: a realm, a god, a world struck by plague, a member at odds or a "
        "stricken member. 1 action.",
        {"kind": "The resolution", "target_id": "What it is about"},
    ),
    T.EXPEL_ENVOY: ToolText(
        "As ruler or regent you send home an envoy received at your court: a mark of anger short of war. 1 action.",
        {"envoy_id": "The envoy"},
    ),
    T.JAM_SIGNAL: ToolText(
        "You jam a signal station where you are, by interference, a working or sabotage: it carries nothing until the next season and is not taken. 1 action.",
        {"link_id": "The station"},
    ),
    T.CLAIM_DEED: ToolText(
        "You speak up about a deed: you lay a claim to it, as true, shared, false or inflated (the whole of a deed you shared), or you dispute "
        "a claim another has laid, which splits its renown until proof, a duel or a court settles it. 1 action.",
        {"deed_id": "The deed", "kind": "Your claim", "contest": "True to dispute the claim that stands instead of laying your own"},
    ),
    T.SET_ARMY_STANCE: ToolText(
        "You set the stance of an army you command or own. Stances: {{ army_stances }}. Winter quarters spare it attrition in a closed season and feed it on the land it holds; pursuit turns a beaten enemy's rout into losses and risks ambush; an escort guards its convoys and siege trains against raids. 1 action.",
        {"army_id": "The army", "stance": "The stance"},
    ),
    T.ASSIGN_ARMY_ROLE: ToolText(
        "You give someone near you a place on the staff of an army you command or own. Roles: {{ army_roles }}. A chaplain keeps its rites and buries its dead, a paymaster holds its chest and, if honest, keeps it from mutiny, a master of scouts spares it ambushes. 1 action.",
        {"army_id": "The army", "mortal_id": "Who takes the place", "role": "The place on the staff"},
    ),
    T.DECIDE_CAPTIVES: ToolText(
        "You decide what becomes of a band of captives your side holds. Fates: {{ captive_fates }}. Each is judged by the peoples who hear of it; the recruited join your army with little loyalty and desert easily. 1 action.",
        {"cohort_id": "The band of captives", "fate": "What becomes of them"},
    ),
    T.SUBORN_GARRISON: ToolText(
        "As a besieger, you work on someone inside a besieged place with bribes, hooks or a shared grudge to open a gate or postern; if the plot is found out, the defence grows firmer. It costs coin. 1 action.",
        {"siege_id": "The siege", "target_id": "Whom inside you work on"},
    ),
    T.ORDER_SIEGE_WORK: ToolText(
        "As a besieger, you set your army to raise a siege work now. Works: {{ siege_works }}. Assault from the air needs fliers, an attack on the networks needs knowledge of computation on both sides, a breaching rite needs casters. 1 action.",
        {"siege_id": "The siege", "work": "The work"},
    ),
    T.DEFEND_SIEGE: ToolText(
        "As a defender, you choose how your besieged place holds out this season. Defences: {{ defender_actions }}. Flooding the approaches needs a river or water works; driving out those who cannot fight is judged by every people that hears of it. 1 action.",
        {"siege_id": "The siege", "defence": "The defence"},
    ),
    T.DECIDE_FALL: ToolText(
        "As a besieger, you decide what becomes of the place if it falls. Choices: {{ fall_choices }}. A ransom spares it for a payment; deportation moves its people to your lands. 1 action.",
        {"siege_id": "The siege", "choice": "What becomes of it"},
    ),
    T.NEGOTIATE_SURRENDER: ToolText(
        "As a besieger, you offer terms to a besieged place; if it yields, the siege ends in surrender on terms you may keep or break. 1 action.",
        {"siege_id": "The siege"},
    ),
    T.RUN_OPERATION: ToolText(
        "As a realm's spymaster, you set its network on a rival realm or community. Operations: {{ spy_operations }}. Each can fail by its difficulty against your network's depth and your skill. 1 action.",
        {"target_id": "Whom you work against", "operation": "The operation"},
    ),
    T.RECRUIT_AGENT: ToolText(
        "As a realm's spymaster, you win someone living among those you spy on as an agent. Motives: {{ recruit_motives }}. Money always serves; the others must truly move them. Love holds while their bond to the handler holds; revenge holds while its target stands. 1 action.",
        {"mortal_id": "Whom you recruit", "motive": "What wins them"},
    ),
    T.GRANT_VETERANS: ToolText(
        "As a ruler, you set what your realm grants its veterans when a war ends. Grants: {{ veteran_grants }}. Each costs the treasury and wins the loyalty of the towns by its own measure. 1 action.",
        {"grant": "The grant"},
    ),
}
