from aerona.catalog.laws import law_terms_guide
from aerona.domain.enums.culture import CalendarSlot, LegendArchetype, TraditionKind
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
        "You commission a work of art: a song, epic, statue, fresco... It presses its message on those who keep it, remembers whom it portrays,"
        " and a realm or town pays for it from its treasury. 1 action.",
        {
            "name": "A proper name for it, in the world's naming language",
            "medium": "What kind of work: {{ art_media }}; songs, plays and dances live only while someone can perform them",
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
            "workings.damage_type": "For destruction: fire, cold, void or another wound",
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
        "You spend time with another mortal where you are: talk, joke, comfort, flirt, court, argue, gift, ask a favour, confide, threaten and more. "
        "It moves how each of you feels about the other. 1 action.",
        {"target_id": "The mortal", "interaction": "What you do with them"},
    ),
    T.CHALLENGE_TO_CONTEST: ToolText(
        "You challenge another mortal where you are to a contest of wit (riddles, flyting, debate, a game of skill, a trial of wisdom, song or storytelling) "
        "for a stake. The winner gains renown; a famous contest may be remembered in art. 1 action.",
        {"target_id": "The mortal you challenge", "kind": "The contest", "stake": "What is at stake"},
    ),
    T.CHOOSE_METHOD: ToolText(
        "You choose how your community does one kind of work: how it farms, fishes, fells, mines, mills, makes cloth, smelts, tans, brews, distils, "
        "dresses stone, burns charcoal, keeps food from spoiling, lights its evenings, butchers, makes cheese or presses fruit. A method needs its techniques, knowledge and energy; it changes output, "
        "quality, tool wear and pollution, and a method that needs fewer hands puts some out of work. 1 action.",
        {"method": "The method to take up"},
    ),
    T.TEND_HOME: ToolText(
        "As head of your household or its head's spouse, you decide for it: improve your home, take on or let go a servant, "
        "apprentice a child to a master, take in a lodger, match an unmarried member with another household, sell a furnishing, "
        "or move the household to a richer place nearby. Your purse, your home and your people must allow it. 1 action.",
        {"choice": "What your household does"},
    ),
    T.PLOT_SCHEME: ToolText(
        "You begin a scheme against someone: to murder, abduct, seduce, sway, fabricate a claim or a hook, steal a relic, seize a throne, poison a well, "
        "frame, elope, convert in secret, spoil a wedding, free a prisoner, sabotage a land or learn a true name. "
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
        "you take what you win and stop at the first room you cannot pass. Reaching its heart wins renown. 1 action.",
        {"site_id": "The site you walk"},
    ),
    T.UNDERTAKE_HEROQUEST: ToolText(
        "You set out on a heroquest: you enter a mythic realm and walk a legend of your people step by step, each step a trial of skill, passion, "
        "conviction or faith. You need renown, a faithful people and a legend to walk. Following the people's version helps; departing from it may "
        "win another boon and rewrites the legend. A fall may hurt, madden or kill you, hold your soul in the myth while your body sleeps, or break "
        "the myth. Companions share the trials and the outcome. 1 action.",
        {
            "legend_id": "The legend you walk (a legend id); leave it out to walk your people's own",
            "companion_ids": "Mortals where you are who walk beside you (ids), if any",
        },
    ),
    T.TAKE_LONGEVITY: ToolText(
        "You take longevity magic: it adds years to your life each epoch it is paid in vis of the form you choose, and you come to need it; "
        "when the vis runs out the borrowed years fall away. 1 action.",
        {"form": "The vis it burns: {{ spell_forms }}"},
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
        "As leader of a merchant house you send a convoy along a route from your town; it may be raided, lost at sea or delayed, and "
        "brings goods, migrants and missionaries when it arrives. 1 action.",
        {"route_id": "The trade route"},
    ),
    T.CORNER_MARKET: ToolText(
        "As leader of a merchant house you buy up a good in your home market to raise its price; a fair-market law or a guild holding the "
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
        "others have, and the town may rise in a riot, a panic or a lasting movement. The watch and garrison hold them back. 1 action.",
        {"grievance": "What you speak about"},
    ),
    T.COMMISSION_ACCOUNT: ToolText(
        "As ruler you have your realm's scribes write its account of an event; you choose whom it praises and whom it blames, and the further "
        "it strays from what happened the more a scholar may one day expose. 1 action.",
        {"collection_id": "The event", "praise_ids": "Whom the account praises", "blame_ids": "Whom the account blames"},
    ),
    T.STRIKE_MEMORY: ToolText(
        "As ruler you strike a figure from your realm's records: its accounts omit them, its inscriptions are defaced and works made of them "
        "for the realm are destroyed. Their fame fades unless the folk or foreigners keep it. 1 action.",
        {"figure_id": "Whom you strike from memory"},
    ),
    T.DRAW_DESIGN: ToolText(
        "You draw a new design for your realm or town ({{ design_kinds }}), giving more weight to one part ({{ design_components }}); "
        "its speed, reach, cargo, arms and crew follow from its parts and their materials, and new hulls and engines are built to it. 1 action.",
        {"kind": "What you design", "hull": "The hull it is for, if a vessel", "emphasis": "The part you favour"},
    ),
    T.HUNT_MOLES: ToolText(
        "As spymaster you hunt for moles at your court; you may catch a foreign agent, clear an official, or wrongly accuse one, who may "
        "then be purged or defect. 1 action.",
        {},
    ),
    T.ANSWER_SICKNESS: ToolText(
        "As ruler of a realm, or as a healer of your community, you set how it answers a sickness ({{ plague_responses }}): closed borders "
        "cost trade and calm, a quarantine slows the spread but may set off riots, burning the dead slows it but grieves folk whose rites "
        "forbid it, driving out the sick slows it at home and marks the sick, prayer comforts but crowds, seeking a cure sets the learned "
        "to work. 1 action.",
        {"disease_id": "The sickness", "response": "The answer"},
    ),
    T.SEEK_CURE: ToolText(
        "You work at a cure for a sickness at the hospital, academy or monastery where you live; your medicine adds to the search, and the "
        "cure, once found, belongs to your community and can be sold along its trade routes. 1 action.",
        {"disease_id": "The sickness"},
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
        "You lean on someone you hold a hook on, or who owes you a favour: to marry you, to step down from their offices, or to lend you support. "
        "A weak hook is spent; a favour called in may be refused. 1 action.",
        {"target_id": "Whom you press", "demand": "What you demand"},
    ),
    T.SEND_DISPATCH: ToolText(
        "You send a message to someone: a proposal, a demand, a threat, an insult, word of a gift, a declaration, a report, a plea or intelligence, "
        "by envoy, letter, herald, messenger bird or signal fire. It takes time by distance, medium and season; spies may read or seize it, "
        "outlaws may waylay it, and in another tongue it may be misread. 1 action.",
        {"recipient_id": "To whom", "content": "What it says", "medium": "How it travels"},
    ),
    T.BARGAIN_WITH_ESTATE: ToolText(
        "As the ruler of a realm, you grant one of its estates a privilege (freedom from taxes, a monopoly, a seat in council, the right to bear arms, "
        "immunity from the courts) to win its loyalty, or take one back at a cost in loyalty. "
        "At most {{ rules.mortal_tools.estate_bargain_per_epoch }} bargains an age. 1 action.",
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
        "You accuse a mortal of your settlement of a crime (theft, murder, treason, blasphemy or desertion) and stand as a witness against them. "
        "The case is tried in a later epoch in the way the realm's penal code sets, and a true charge is easier to prove than a false one. 1 action.",
        {"accused_id": "Whom you accuse", "crime": "The crime you charge them with"},
    ),
    T.ISSUE_DEMAND: ToolText(
        "As ruler or regent you demand something of another realm: a land ceded, a vassal released, its faith changed to yours, or a payment. "
        "A crisis opens: other realms back a side, the weaker side backs down or concedes, and if neither yields it becomes war. 1 action.",
        {
            "target_id": "The realm you make the demand of",
            "demand": "What you demand: cede_region, release_vassal, convert or pay",
            "subject_id": "The land to cede or the vassal to release, if the demand names one",
        },
    ),
    T.BACK_CRISIS: ToolText(
        "As ruler or regent you put your realm behind one side of a crisis between other realms; backers weigh on who yields and join the war if it comes. 1 action.",
        {"crisis_id": "The crisis", "side": "Which side you back: demander or target"},
    ),
    T.ISSUE_MANDATE: ToolText(
        "As ruler or regent you issue a mandate: a production order, a ban on exporting a good, an order to build a quarter, relief from the state "
        "granaries for a hungry land, or a curfew. Unmet mandates cost you legitimacy, and harsh ones weigh on your people. 1 action.",
        {
            "kind": "produce, export_ban, build, famine_relief, curfew or slum_clearance",
            "settlement_id": "The settlement it is laid on, if any",
            "commodity": "The good to produce, ban or send",
            "district": "The quarter to build",
            "amount": "How much to produce or send",
        },
    ),
    T.ASSIGN_TASK: ToolText(
        "As ruler or regent you set an officer of your council to a task: improving relations with a realm, training troops, collecting taxes, "
        "disrupting schemes, carrying the faith into a land, or purging corruption. 1 action.",
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
        "Rarer lore is worth more, and each telling makes it less rare. You are paid in wealth or in renown for wisdom. 1 action.",
        {
            "buyer_id": "Who receives the lore",
            "kind": "The kind of lore",
            "key": "Which piece: the technique key, or site, region or prophecy",
            "subject_id": "The site, land or prophecy, if any",
        },
    ),
    T.PERSUADE: ToolText(
        "You try to bring another mortal where you are round to your view of a belief, appealing to belief, self-interest, authority, evidence or fear. "
        "Your oratory, how well the appeal fits them, their stubbornness and their passions decide it. 1 action.",
        {"target_id": "The mortal", "appeal": "How you argue", "axis": "The belief at stake", "toward": "How far toward it (-100 to 100)"},
    ),
    T.FOUND_SCHOOL: ToolText(
        "You found a school of thought, a creed that spreads along roads, through scholars, books and schools, and can move a realm. 1 action.",
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
    T.FOUND_LANGUAGE: ToolText(
        "You give birth to your own language: its name, kind (spoken language, sacred language, script, sign language…), sound structure and first words. From now on "
        "you speak this language. 1 action.",
        {
            "name": NAME_FIELD,
            "subtype": "spoken language, sacred language, script, sign language…",
            "description": "Its sound structure, its script, who speaks it, what is forbidden to say",
            **WORD_FIELDS,
            "image_prompt": (
                "English image prompt: an object showing this script or language, e.g. carved tablet, manuscript, inscription, with lighting and composition. "
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
            "subtype": "What kind of item it is, in your people's own terms",
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
            "structure_kind": "What it is and what it does: {{ structure_kinds }}",
            "subtype": "temple, tower, wall, bridge, tomb, mine, harbour, library…",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own settlement, place or region; if empty, where you are",
            "dedicated_son_id": "The god it is dedicated to, if any",
            "material": "What it is built of (stone, wood, clay, glass…); holy stone makes a temple shine, soft wood rots; it must be in your people's stores",
            "channels_ley": "True if it is raised to draw on the ley lines (a ley gate, a star tower, a stone ring); it gains strength only where a line runs",
            "image_prompt": IMAGE_PROMPT_FIELD,
        },
    ),
    T.CREATE_CULTURE: ToolText(
        "You give birth to a tradition of your community (festival, taboo, funeral rite), a legend, a work of art (song, statue, fresco, book, play; by honouring your god "
        "it strengthens that god) or a law (statute, penalty, custom; a just law reduces rebellion). 1 action.",
        {
            "kind": "tradition (rite, festival, taboo), legend (a tale), artwork (song, statue, fresco, book, play) or law (statute, penalty, custom)",
            "name": NAME_FIELD,
            "subtype": "What exactly it is",
            "description": DESCRIPTION_FIELD,
            "related_ids": "Existing records it tells of (at most {{ " + M + ".culture_max_related }})",
            "law_kind": "For a law: what it rules (succession_rule, tax_rate, penal_code, levy_law, slavery, tolls, sumptuary...); required for laws",
            "law_params": "For a law: its terms by name, only those its kind has; leave out a term to keep its default. Terms of each kind: "
            + law_terms_guide(),
            "image_prompt": 'English image prompt: the ritual being performed or a scene of the legend. {% include "shared/image_prompt_rules.md.j2" %}',
            "legend_category": "Only for a legend: what it would become if belief made it real: {{ legend_categories | join(', ') }}",
            "archetype": "Only for a legend: the kind of tale, which sets its lesson: " + ", ".join(item.value for item in LegendArchetype),
            "tradition_kind": "Only for a tradition: what kind of custom it is: " + ", ".join(item.value for item in TraditionKind),
            "calendar_slot": "Only for a tradition kept at a set time: " + ", ".join(item.value for item in CalendarSlot),
            "taboo_target": "Only for a taboo: the good its keepers will not touch",
            "taboo_act": "Only for a taboo: the deed its keepers will not do: " + ", ".join(item.value for item in ActKind),
        },
    ),
    T.DISCOVER_RESOURCE: ToolText(
        "You discover a new resource on your land (ore vein, healing herb, sacred spring, clay pit…) and own it. 1 action, "
        "{{ " + M + ".discover_resource_per_epoch }} per age.",
        {
            "name": NAME_FIELD,
            "subtype": "ore vein, healing herb, sacred spring, clay pit…",
            "description": DESCRIPTION_FIELD,
            "location_id": "Your own region or a place in your region",
            "domain": "One of: {{ domains | join(', ') }}",
            "image_prompt": IMAGE_PROMPT_FIELD,
            "commodity": "What your people draw from it: {{ commodities | join(', ') }}; ore feeds forges and weapons",
            "material": "If it is a seam or a grove, its material: {{ materials | join(', ') }}",
            "mechanics": "The resource's particular rules, at most {{ rules.mechanics.resource_max }} (empty: read from its name and text): {{ resource_mechanics }}",
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
        "You worship a god (a son) or change your god; if you give son_id 0 you worship the creator god directly, maker of all the sons. Your old god does not forget "
        "this. Free, {{ " + M + ".worship_per_epoch }} per age.",
        {"son_id": "The son's id, or 0 for the creator", "offering": "Your offering and vow"},
    ),
    T.PRAY_TO_CREATOR: ToolText(
        "You pray directly to the creator god above the sons, the maker of all worlds. Your prayer reaches the creator; if answered, you will see it in your dream and the creator's grace "
        "will descend. Free, {{ " + M + ".pray_creator_per_epoch }} per age.",
        {"prayer": "Your prayer", "request": "What you ask of the creator"},
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
            "image_prompt": 'English image prompt: people practicing this technique, tools, materials, setting. {% include "shared/image_prompt_rules.md.j2" %}',
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
        "it sharpens your hunting; when it dies you mourn it. Free.",
        {"species_id": "The kind it is of, from those your people keep; leave empty to take any"},
    ),
    T.TRAIN_HERD: ToolText(
        "You train a herd your people keep, for war, for the hunt or for guarding, with your own beast handling (at least "
        "{{ rules.husbandry.train_skill }}). Trained war beasts join your people's armies, hunters bring home more and guards keep raiders off. 1 action.",
        {"species_id": "The kind of the herd, from those your people keep", "training": "What you train it for"},
    ),
    T.MERGE_SPECIES: ToolText(
        "With biomancy you merge two creature species in your world, near you (at most {{ rules.creatures.chimera_merge_distance }} steps), into a single chimera (requires "
        "biomancy knowledge). The chimera carries the traits of both species; but it may get out of control. 1 action.",
        {"a_id": "The first species", "b_id": "The second species", "name": NAME_FIELD, "goal": "Why you make it"},
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
        "You make a prophecy: you say something that will happen in the future. If it comes true Fate records it and your reputation (charisma) rises; if it is misread it "
        "is shaken. 1 action, {{ " + M + ".prophesy_per_epoch }} per age.",
        {
            "predicate": "What exactly must happen for the prophecy to come true, which the world itself will check: {{ prophecy_predicates }}",
            "subject_id": "The one the foretelling names: who dies, what falls, the house, the realm, or the first side of a war",
            "second_id": "For a war: the second side",
            "archetype": "For who will rule: the kind of legend the coming ruler must fit",
            "sky_kind": "For a sign in the sky: which sign",
            "event_kind": "For a foretold happening: what kind (war, birth, flood, crowning...)",
            "within_epochs": "In how many ages it must come true; if it does not, you are mocked and your cult loses heart",
            "consequence": "What it means when it comes true: {{ prophecy_consequences }}",
            "consequence_id": "Whom the consequence touches",
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
    T.ENACT_LAW: ToolText(
        "As ruler or regent you lay down a typed law for your whole realm: its kind decides what it rules and its terms decide how. "
        "In a realm that decides by council, assembly or divine will, the law goes before them as a proposal instead of passing at once. "
        "1 action, {{ " + M + ".enact_law_per_epoch }} per age.",
        {
            "kind": "What the law rules: succession_rule, inheritance_split, land_tenure, slavery, serfdom, tax_rate, tithe, tolls, debt_law, penal_code, levy_law, conscription, standing_army, veteran_pension, ransom_custom, marriage_law, sumptuary, guild_charter, foreigner_rights, religious_tolerance, worship_ban, blood_feud, quarantine, burial_law, sanitation, magic_ban, licensed_magic, rite_restrictions, censorship, fair_market, franchise, constitution or custom",
            "params": "The law's terms by name, only those its kind has; leave out a term to keep its default. Terms of each kind: " + law_terms_guide(),
            "name": "The law's name, if it should have one of its own",
        },
    ),
    T.PROPOSE_TREATY: ToolText(
        "You offer a typed treaty to another community or realm; it takes force when they accept. 1 action, {{ " + M + ".propose_treaty_per_epoch }} per age.",
        {
            "target_id": "The community or realm you offer it to",
            "kind": "peace, truce, alliance_defensive, alliance_offensive, non_aggression, vassalage (you become the vassal), tribute, marriage_pact, trade_pact, condotta, guarantee, interworld, coalition or divine_pact",
            "clauses": "Typed clauses with who owes, who gains and their terms (amount, commodity, epochs, region_id, mortal_id...)",
            "epochs": "How many ages it should hold",
            "clauses.kind": "The clause's kind",
            "clauses.obligor_id": "Who owes it",
            "clauses.beneficiary_id": "Who gains by it",
            "clauses.params": "Its terms by name (amount, commodity, epochs, region_id, mortal_id...)",
        },
    ),
    T.SWEAR_OATH: ToolText(
        "You swear an oath (fealty, vengeance, celibacy, pilgrimage, protection, silence, sworn_kinship); keeping it wins honour, breaking it brings shame and a god's wrath. "
        "Free, {{ " + M + ".swear_oath_per_epoch }} per age.",
        {"kind": "The oath", "recipient_id": "To whom or against whom, if anyone (for a pilgrimage: the holy place)", "words": "The words of the oath"},
    ),
    T.ACCEPT_TREATY: ToolText("You accept a treaty offered to you; it takes force at once. Free.", {"treaty_id": "The offered treaty"}),
    T.BREAK_TREATY: ToolText(
        "You break a treaty your people are bound by: the other parties remember the betrayal, guarantors may march and your rulers lose honour. 1 action.",
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
        "You adopt another named mortal: it counts as of your lineage and enters the chronicle. It must be younger than you and near you. "
        "{{ " + M + ".adopt_per_epoch }} per age, {{ " + M + ".adopt_ap }} action.",
        {"child_id": "The named mortal you adopt", "reason": "Why and how you adopt"},
    ),
    T.BESTOW_GIFT: ToolText(
        "You give someone a gift from your purse, or from your realm's if you rule one. It raises your standing and their regard; it binds "
        "them to answer it in time, and an unanswered gift costs them face. One who hates you may refuse it as an insult. 1 action.",
        {"receiver_id": "Who receives it", "value": "Coin it is worth", "item_id": "A thing of yours to give with it, or empty"},
    ),
    T.ANSWER_GIFT: ToolText(
        "You answer a gift someone gave you, so you owe them nothing; answer a rank-claiming gift with more or lose face. 1 action.",
        {"gift_id": "The gift you owe", "value": "Coin your answer is worth, or empty to match what custom asks"},
    ),
    T.REFUSE_GIFT: ToolText(
        "You refuse a gift someone gave you; you owe them nothing, but the giver takes it as an insult. 1 action.",
        {"gift_id": "The gift you refuse"},
    ),
    T.MAKE_OFFERING: ToolText(
        "You make an offering to your god from your purse; your people's ledger of offerings grows, and the god is bound to answer it. 1 action.",
        {"value": "Coin the offering is worth"},
    ),
    T.FREE_BOUND: ToolText(
        "As ruler you free a share of the bound of a town of your realm ({{ manumission_paths }}); those freed by purchase or service "
        "rise as craftsfolk, the rest work the land. 1 action.",
        {"town_id": "The town", "share": "Share of its bound you free, 1 to 100", "path": "By what way they go free"},
    ),
    T.LAY_CORVEE: ToolText(
        "As ruler you summon a share of the farmhands of a town of your realm to forced labour on a great work being raised; the work "
        "goes faster, the harvest suffers, unrest rises and the town remembers the labour. 1 action.",
        {"town_id": "The town", "work_id": "The work being raised", "share": "Share of its farmhands, 0 to 100; 0 lifts the labour"},
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
}
