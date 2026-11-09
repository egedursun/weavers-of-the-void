from collections.abc import Callable

from aerona.domain.enums.agent import AgentKind, PendingJobKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import ReputationLabel
from aerona.domain.enums.world import CosmosSize, LanguageTexture, LoreLanguage, TechnologyEra
from aerona.prompts.contexts import (
    agent,
    blocks,
    chronicle,
    chronicler,
    cosmos,
    council,
    fate,
    genesis,
    imagery,
    localisation,
    mortal,
    narrative,
    opportunities,
    son_turn,
)
from aerona.prompts.contexts.base import EmptyContext, LoreContext, PromptContext, RulesContext
from aerona.prompts.contexts.common import (
    ChronicleRow,
    EntityLineItem,
    LabelValue,
    LexiconWord,
    NamedRecord,
    NamingRuleItem,
    SonBrief,
    WorldItem,
)
from aerona.prompts.data.images import CosmosSubjectKind
from aerona.prompts.ids import PromptId
from aerona.rules.registry import Rules

RULES = Rules()
LORE = LoreLanguage.TURKISH
P = PromptId

ENTITY = EntityLineItem(id=12, name="Vesh Hollow", type_label="Place", subtype="salt cave", power_level=4, location="Orrun Coast")
PEOPLE = EntityLineItem(id=30, name="Kael", type_label="People", subtype="tide folk", power_level=5)
NAMING = NamingRuleItem(
    vowels="aeo", consonants="kshrv", forbidden_sounds=["u"], syllable_patterns=["CV", "CVC"], endings=["-esh"], sample_names=["Vesh", "Karo"]
)
SON = SonBrief(id=2, name="Ozzeh", title="Who Makes the Salt Weep", domain_1="Salt", domain_2="Sea")
WORLD = WorldItem(id=1, name="Aerona")
OTHER_WORLD = WorldItem(id=2, name="Vel")
ROWS = [ChronicleRow(age=3, text="The tide folk raised a bone wall.")]
EVENT_ROWS = [fate.AgeEventRow(text="A war began at the salt coast.", repeats=3), fate.AgeEventRow(text="A seer died.")]
HEADER = "WORLD: Aerona — Age 5."
STAR = cosmos.StarLine(id=1, name="Ka", type_label="Yellow dwarf", planets=[WORLD])
MEMBER = council.CouncilMember(
    id=2,
    name="Ozzeh",
    title="the Weeper",
    rarity_label="Rare",
    domain_1="Salt",
    domain_2="Sea",
    rebel=True,
    temperament="Cold and patient",
    speech_style="Short, salted words",
    obsession="To drown the moon",
    loyalty=30,
    ambition=70,
    wrath=40,
    plan="Raise a sea temple",
    current_world="Vel",
)
GRAPH_SON = cosmos.GraphNode(kind=cosmos.GraphNodeKind.SON, id=2, name="Ozzeh", title="the Weeper")
GRAPH_ENTITY = cosmos.GraphNode(
    kind=cosmos.GraphNodeKind.ENTITY,
    id=12,
    name="Vesh Hollow",
    type_label="place",
    subtype="salt cave",
    status_label="dead",
    description="A cave  of white salt.",
)


def world_header() -> blocks.WorldHeaderContext:
    return blocks.WorldHeaderContext(
        rules=RULES,
        world_name="Aerona",
        age=5,
        world_year=500,
        god_name="Ul",
        god_title="the Salt",
        god_temperament="Distant",
        god_note="No bone may be burned.",
        mood=blocks.CreatorMood(contentment=50, anger=90, attention=20, loneliness=60),
        epic=blocks.EpicSummary(title="The Brine", line="Salt remembers."),
        prohibitions=["no burning of bone"],
        desire="To be remembered",
        cosmology="The world rests on a salt lake.",
        tone="Grim and bright",
        naming_rule=NAMING,
        dialects=[blocks.WorldNaming(id=1, name="Aerona", naming=NAMING), blocks.WorldNaming(id=2, name="Vel", naming=NAMING)],
        doom=60,
        doom_threshold=100,
        climate=blocks.ClimateLine(name="Drought", since_age=3, description="the rivers thin"),
        age_star=blocks.AgeStar(id=4, name="Ka", domain="Salt", sky_world="Vel"),
        laws=[blocks.LawLine(id=8, name="The Return", description="The dead return as salt.")],
    )


def entity_detail() -> blocks.EntityDetailContext:
    return blocks.EntityDetailContext(
        entity=ENTITY,
        author=blocks.EntityAuthor.SON,
        author_son=NamedRecord(id=2, name="Ozzeh"),
        age=3,
        world=OTHER_WORLD,
        domain="Salt",
        tags=["cave"],
        stats=[LabelValue(label="Danger", value="40")],
        description="A cave of white salt.",
        history="It sang once.",
        fate_note="Kept.",
        outgoing=[blocks.BondLine(label="loves", other=blocks.BondEndpoint(kind=NodeKind.SON, id=2, name="Ozzeh"), description="old love")],
        incoming=[blocks.BondLine(label="fears", other=blocks.BondEndpoint(kind=NodeKind.ENTITY, id=30, name="Kael"))],
        contents=[PEOPLE],
        lexicon=[LexiconWord(word="vesh", meaning="salt", kind="noun")],
        society=blocks.SocietyLines(
            tier_label="kingdom",
            sanity=30,
            clouded=True,
            classes=[blocks.ClassShare(label="Farmers", share=50, satisfaction=40)],
            relations=[blocks.CommunityRelationLine(id=31, name="Vor", label="enemy", value=-50, blood_feud=True)],
            wars=[blocks.WarLine(id=40, name="Salt War", clashes=2)],
        ),
        facts=["Vesh Hollow is made of salt"],
    )


def son_memory() -> blocks.SonMemoryContext:
    return blocks.SonMemoryContext(
        rules=RULES,
        plan="Drown the moon",
        plan_age=2,
        plan_years=5,
        plan_stale=True,
        closed_since_plan=["The salt feud ended."],
        words=[blocks.MemoryWord(age=4, from_father=True, sender="Ul", intent_label="command", text="Rise.")],
        creations=[blocks.MemoryCreation(entity=ENTITY, other_world="Vel", fate_note="Rejected for cliché")],
        creations_total=1,
        current_world=WORLD,
        repeats=[blocks.RepeatBucket(label="place/cave", count=3)],
        worshippers=[NamedRecord(id=30, name="Kael")],
        extra_worshippers=2,
        recollections=ROWS,
        about=ROWS,
        beliefs=[blocks.FolkBeliefLine(people="Kael", name="Salt Mother", story="She weeps the sea.")],
    )


def world_summary() -> blocks.WorldSummaryContext:
    return blocks.WorldSummaryContext(
        rules=RULES,
        for_son=True,
        header=HEADER,
        pantheon="son#2 Ozzeh",
        threads="thread#3 (Age 2, never advanced): The salt sings.",
        events="[Age 4] A war began.",
        multi_world=True,
        cosmos_lines="- world#2 Vel",
        foreign_gods=[
            blocks.ForeignGodLine(id=1, name="Mor", title="the Old", power=40, attitude=-20, strength=50, will=40, charisma=30, cunning=20, powers=["Shield"])
        ],
        routes=[blocks.RouteLine(id=1, world_a="Aerona", world_b="Vel", method_label="Light sail", duration=3)],
        geography="- #12 Vesh Hollow (Place, P4)",
        geography_total=1,
        geography_cut=True,
        languages="- #20 Veshi",
        map="1 known regions.",
        legends=[ENTITY],
    )


def chronicler_user() -> chronicler.ChroniclerUserContext:
    return chronicler.ChroniclerUserContext(
        lore_language=LORE,
        rules=RULES,
        world_header=HEADER,
        age=5,
        worlds=[WORLD, OTHER_WORLD],
        missing_worlds=[OTHER_WORLD],
        previous_names=["Age of Brine"],
        continuity=chronicler.ChroniclerContinuity(
            current=chronicler.ChroniclerLink(age=4, name="Ehmel", who="scribe of the Kael"),
            streak=2,
            chain=[chronicler.ChroniclerLink(age=4, name="Ehmel", who="scribe of the Kael")],
        ),
        name_kinds=[
            chronicler.NameKind(name="Kael", type_label="People", subtype="tide folk"),
            chronicler.NameKind(name="Ehmel", type_label="Mortal", mortal=True),
        ],
        previous_verdicts=["A story ended."],
        events=[fate.WorldEvents(world_id=1, world_name="Aerona", rows=EVENT_ROWS), fate.WorldEvents(rows=[])],
        engine_notes=["Population grew."],
        pending=[ENTITY],
        facts=FACT_SHEET,
    )


FACT_SHEET = chronicler.ChroniclerFactSheet(
    creator=chronicler.FactActor(ref="creator", id=1, name="Haevaron", deeds=["drew essence (3 times)"], deed_count=3),
    sons=[
        chronicler.FactActor(
            ref="son-2", id=2, name="Vesaelon", world="Aerona", deeds=["healed the Kael"], deed_count=1, records=[chronicler.FactRecord(id=5, name="Kael")]
        ),
        chronicler.FactActor(ref="son-3", id=3, name="Aeron"),
    ],
    outcomes=[
        chronicler.FactOutcome(ref="war-1", kind=chronicler.ContestKind.WAR, contest="Salt War", winner_id=5, winner="Kael", loser_id=6, loser="Orrin"),
        chronicler.FactOutcome(ref="conflict-2", kind=chronicler.ContestKind.DUEL, winner_id=2, winner="Vesaelon", loser_id=3, loser="Aeron"),
    ],
    draws=[chronicler.FactDraw(son="Aeron", text="drew essence from the tide well")],
    events=[chronicler.FactEvent(ref="event-9", category="disaster", world="Aerona", text="A flood drowned the lowlands", repeats=2)],
    verdicts=[chronicler.FactVerdict(ref="verdict-4", text="A story closed: the salt feud ended.")],
    rejected=["Ehremisael Salt Well"],
)


def chronicler_audit_fix() -> chronicler.ChroniclerAuditFixContext:
    return chronicler.ChroniclerAuditFixContext(
        lore_language=LORE,
        rules=RULES,
        facts=FACT_SHEET,
        findings=[
            chronicler.AuditFindingItem(kind="rejected_mentioned", name="Ehremisael Salt Well", sentence="The well was dug.", world="Aerona"),
            chronicler.AuditFindingItem(kind="son_skipped", name="Aeron"),
            chronicler.AuditFindingItem(kind="event_skipped", detail="A flood drowned the lowlands"),
            chronicler.AuditFindingItem(kind="verdict_skipped", detail="A story closed."),
            chronicler.AuditFindingItem(kind="winner_as_loser", detail="Salt War", stated="Orrin", actual="Kael"),
            chronicler.AuditFindingItem(kind="active_as_silent", name="Haevaron", actual="3"),
            chronicler.AuditFindingItem(kind="deed_miscredited", name="Kael", stated="Haevaron", actual="Vesaelon"),
            chronicler.AuditFindingItem(kind="number_contradiction", detail="Haevaron", stated="2", actual="3"),
        ],
        narrative="Vesaelon walked among the Kael.",
        worlds=[WORLD, OTHER_WORLD],
        sections={1: "The tide came late."},
    )


def son_turn_system() -> son_turn.SonTurnSystemContext:
    return son_turn.SonTurnSystemContext(
        lore_language=LORE,
        rules=RULES,
        son_name="Ozzeh",
        son_title="the Weeper",
        god_name="Ul",
        world_name="Aerona",
        rarity_label="Rare",
        stars=2,
        level=3,
        domain_1="Salt",
        domain_2="Sea",
        existence=son_turn.ExistenceProfile(nature="brine", state_label="concrete", manifestation="a wet shadow", true_name="Oz"),
        appearance="Tall and white",
        temperament="Cold",
        obsession="The moon",
        fear="Fire",
        speech_style="Short",
        secret="He drowned a brother",
        stats=[son_turn.StatValue(label="Strength", value=50)],
        passions=son_turn.Passions(loyalty=30, ambition=70, wrath=40, mercy=10),
        hp=40,
        max_hp=80,
        essence=30,
        max_essence=90,
        faith=10,
        fame=5,
        existence_value=40,
        existence_band_label="Solid",
        existence_band_effect="no penalty",
        anchor=son_turn.AnchorLine(id=12, name="Vesh Hollow", status_label="canon"),
        powers="- Salt Memory: remembers",
        action_points=3,
        paid_tools=["create_place"],
        free_tools=["write_plan"],
        power_ceiling=5,
        sky_calendar="slingshot orbits open in Age 7",
        tools=["create_place", "challenge", "curse"],
        reputation_line="- HOW YOU SEE YOUR FATHER: loved",
        rebel_prone=True,
        creator_wishes="- FATHER'S PASSIONS: order",
        sanity=30,
        clouded=True,
    )


def opportunities_son() -> opportunities.SonOpportunitiesContext:
    o = opportunities
    pair = o.RecordPair(a=NamedRecord(id=30, name="Kael"), b=NamedRecord(id=31, name="Vor"))
    lines: list[o.SonOpportunity] = [
        o.BreatheLife(
            lifeless=True, peoples=1, settlements=0, mortals=0, species=1, organizations=0, empty_regions=[NamedRecord(id=9, name="Orrun")], few_mortals=True
        ),
        o.NewEmptyWorld(world_id=2, world_name="Vel", world_type_label="Ocean world", empty_ages=2, regions=[o.ValuedRecord(id=50, name="Deep", value=60)]),
        o.NarrowLands(world_name="Aerona", regions=2, communities=8, per_region=4.0, crowded=[o.ValuedRecord(id=9, name="Orrun", value=5)]),
        o.IsolatedWorld(hidden_route=True),
        o.StagnantCosmos(last_birth_age=1),
        o.DeadSibling(name="Mara", death_age=3, devotion=40, remaining=2, corpse_id=77, cult=o.ValuedRecord(id=78, name="Mara's Wait", value=40)),
        o.DeadSibling(name="Tesh", death_age=2, devotion=10, enemy=True),
        o.RivalSiblings(rivals=[o.ValuedRecord(id=3, name="Tesh", value=-40)]),
        o.RivalMortals(mortals=[o.TargetMortal(id=60, name="Arro", patron="Tesh", cost=40, chance=55)]),
        o.Unclaimed(communities=[NamedRecord(id=31, name="Vor")]),
        o.RivalWorshippers(communities=[o.PatronedRecord(id=32, name="Ash", patron="Tesh")]),
        o.OwnWorshippers(communities=[NamedRecord(id=30, name="Kael")]),
        o.Hostilities(pairs=[pair]),
        o.TeachableKnowledge(knowledge=[o.BranchRecord(id=70, name="Salt Reading", branch_label="Astronomy")]),
        o.TeachableKnowledge(),
        o.Languageless(communities=[NamedRecord(id=31, name="Vor")]),
        o.Languageless(),
        o.UnownedResources(resources=[NamedRecord(id=80, name="Brine Vein")]),
        o.RivalCreations(creations=[NamedRecord(id=81, name="Ash Tower")]),
        o.RebelsAgainstYou(records=[NamedRecord(id=82, name="Grey Sect")]),
        o.YourEnemies(records=[NamedRecord(id=83, name="Burnt Band")]),
        o.Godless(communities=[NamedRecord(id=84, name="Free Folk")]),
        o.RebelSiblings(siblings=[NamedRecord(id=3, name="Tesh")]),
        o.LowLoyalty(),
        o.Existence(fading=True, value=15),
        o.Existence(fading=False, value=60),
        o.WorshipperWars(wars=[NamedRecord(id=40, name="Salt War")]),
        o.HungryWorshippers(communities=[NamedRecord(id=30, name="Kael")]),
        o.Wonders(wonders=[NamedRecord(id=85, name="The White Arch")]),
        o.StaleThreads(threads=[o.StaleThread(id=3, text="The salt sings.")]),
        o.LongThreads(thread_ids=[4]),
        o.PendingProphecies(prophecies=[o.ProphecyRecord(id=90, name="The Drowning", age=2, own=True)]),
        o.OpenThreads(thread_ids=[3, 4]),
        o.Silence(never_spoken=True),
    ]
    return o.SonOpportunitiesContext(rules=RULES, lines=lines)


def opportunities_mortal() -> opportunities.MortalOpportunitiesContext:
    o = opportunities
    lines: list[o.MortalOpportunity] = [
        o.TradePartners(communities=[NamedRecord(id=31, name="Vor")]),
        o.Enemies(enemies=[NamedRecord(id=32, name="Ash")], can_sabotage=True),
        o.TenseNeighbours(neighbours=[o.ValuedRecord(id=33, name="Grey", value=-30)], can_sabotage=True),
        o.LearnableKnowledge(knowledge=[o.PatronedRecord(id=70, name="Salt Reading", patron="Vor")]),
        o.LandResources(resources=[NamedRecord(id=80, name="Brine Vein")]),
        o.DangerousCreatures(species=[NamedRecord(id=86, name="Salt Wyrm")]),
        o.NoKnowledge(),
        o.NoLanguage(),
        o.BloodFeuds(communities=[NamedRecord(id=32, name="Ash")]),
        o.LovingNeighbours(neighbours=[o.ValuedRecord(id=31, name="Vor", value=60)]),
        o.AtWar(wars=[NamedRecord(id=40, name="Salt War")]),
        o.GranaryEmptying(food=20, bread_price=180),
        o.Discontent(class_label="farmer", satisfaction=20),
        o.Remains(remains=[NamedRecord(id=87, name="Old Wall")]),
        o.DeadGod(name="Mara", death_age=3, devotion=40, corpse="Mara's Bones"),
        o.UnknownLands(reasons=[o.ExplorationReasonKind(kind="hunger"), o.ExplorationReasonKind(kind="explorer", explorer_name="Arro")], can_settle=True),
        o.UnknownLands(),
        o.SkyOpen(roadless_worlds=["Vel"]),
        o.SkyUnknown(worlds=["Vel"]),
        o.OpenRoute(),
        o.DefyGod(sons=[NamedRecord(id=3, name="Tesh")]),
        o.BurdensomeGod(name="Tesh"),
        o.NoGod(candidates=[SON]),
    ]
    return o.MortalOpportunitiesContext(rules=RULES, lines=lines)


def mortal_context() -> mortal.MortalContextContext:
    return mortal.MortalContextContext(
        rules=RULES,
        world_header=HEADER,
        world_line="YOUR CURRENT WORLD: world#1 Aerona",
        self_detail="#30 Kael (People, P5)",
        character=[LabelValue(label="governance", value="elders")],
        god=mortal.MortalGod(kind=mortal.MortalGodKind.SON, id=2, name="Ozzeh", title="the Weeper", domain_1="Salt", domain_2="Sea"),
        folk_gods=[mortal.FolkGodName(name="Salt Mother", son_id=2, story="She weeps the sea.")],
        language=mortal.MortalLanguage(id=20, name="Veshi", words=[LexiconWord(word="vesh", meaning="salt")]),
        land=mortal.MortalLand(id=9, name="Orrun", elevation_label="lowland", coastal=True, neighbours=[NamedRecord(id=10, name="Kor")]),
        near=[ENTITY],
        recent_events=ROWS,
        known=[mortal.KnowledgeItem(id=70, name="Salt Reading", branch_label="Astronomy")],
        world_knowledge=[mortal.KnowledgeItem(id=71, name="Bone Smithing", branch_label="Metallurgy")],
        resources=[mortal.OwnedResource(id=80, name="Brine Vein", abundance=60)],
        items=[NamedRecord(id=88, name="Bone Spear")],
        mentions=ROWS,
        languages="- #20 Veshi",
        other_worlds="- world#2 Vel",
        routes=[blocks.RouteLine(id=1, world_a="Aerona", world_b="Vel", method_label="Light sail", duration=3)],
        expeditions=[mortal.ExpeditionLine(intent_label="Colony", remaining=2, people=300)],
    )


def new_world() -> cosmos.NewWorldContext:
    return cosmos.NewWorldContext(
        lore_language=LORE,
        rules=RULES,
        cosmos_name="Aerona",
        world_header=HEADER,
        cosmos_lines="- world#1 Aerona",
        main_world=WORLD,
        stars=[STAR],
        foreign_gods=[cosmos.ForeignGodBrief(name="Mor", title="the Old", world_id=1, domains="Ash/Bone")],
        placement=cosmos.PlacementKind.EXISTING_STAR,
        star_id=1,
        creator_son=SON,
        god_name="Ul",
        world_type_label="Ocean world",
        world_type_key="ocean",
        inspiration="A drowned bell",
        banned_names=["Vesh", "Kael"],
        cosmic_resource=None,
    )


def turn_continuation() -> son_turn.TurnContinuationContext:
    return son_turn.TurnContinuationContext(
        reason=son_turn.TurnInterruption.CONNECTION_ERROR,
        error_detail="socket closed",
        done=[son_turn.DoneAction(tool="create_place", summary="Created: #12 Vesh Hollow")],
        long_jobs=[son_turn.LongJobNote(tool="write_epic", summary="Epic written: The Salt Road")],
    )


def all_warnings() -> list[fate.PrescreenWarning]:
    kinds = fate.PrescreenKind
    return [
        fate.PrescreenWarning(kind=kinds.UNBOUND),
        fate.PrescreenWarning(kind=kinds.SHORT_DESCRIPTION),
        fate.PrescreenWarning(kind=kinds.CONFUSABLE_NAME, other_name="Vesh"),
        fate.PrescreenWarning(kind=kinds.OFF_DOMAIN_POWER, power_level=8, domain="Fire"),
        fate.PrescreenWarning(kind=kinds.LOCATION_IN_OTHER_WORLD),
    ]


def son_powers() -> genesis.SonPowersContext:
    return genesis.SonPowersContext(
        lore_language=LORE,
        world_name="Aerona",
        world_header=HEADER,
        name="Ozzeh",
        title="the Weeper",
        rarity_label="Rare",
        domain_1="Salt",
        domain_2="Sea",
        appearance="Tall",
        temperament="Cold",
        obsession="The moon",
        secret="A drowned brother",
    )


def summon() -> genesis.SummonSonContext:
    return genesis.SummonSonContext(
        lore_language=LORE,
        world_name="Aerona",
        world_header=HEADER,
        target_world_line="YOUR CURRENT WORLD: world#2 Vel",
        god_name="Ul",
        pantheon=[SON],
        threads="thread#3: The salt sings.",
        recent_events="[Age 4] A war began.",
        parent=SON,
        co_parent=SON,
        inspiration="A drowned bell",
        rarity=Rarity.COMMON,
        rarity_label="Common",
    )


def awaken() -> genesis.AwakenPeoplesContext:
    return genesis.AwakenPeoplesContext(lore_language=LORE, rules=RULES, world_name="Aerona", world_summary="SUMMARY", map="MAP", count=2, earlier=["Kael"])


def revelation() -> genesis.RevelationContext:
    return genesis.RevelationContext(
        lore_language=LORE,
        god_name="Ul",
        world_name="Aerona",
        target_world=OTHER_WORLD,
        target_world_line="YOUR CURRENT WORLD: world#2 Vel",
        world_summary="SUMMARY",
        entity_types=[
            genesis.RevelationType(type_label="celestial", stats=["brightness"], locations=[]),
            genesis.RevelationType(type_label="place", locations=["region"]),
        ],
        first_star=True,
    )


def naming() -> narrative.NamingContext:
    return narrative.NamingContext(
        lore_language=LORE,
        world_name="Aerona",
        target_world="Vel",
        world_header=HEADER,
        records=["#13 [World engine] battle", "#14 [World engine] hero"],
        dialect_warnings=[narrative.DialectWarning(id=13, name="Uvo", root="uvo", letters=["u"])],
    )


def voices() -> narrative.VoicesContext:
    return narrative.VoicesContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        world_header=HEADER,
        age=5,
        age_events="A war began.",
        historians=[
            narrative.HistorianEntry(
                people=PEOPLE, society="Civilization tier: kingdom", previous_historian="Ehmel", previous_age=4, previous_opening="The salt woke"
            )
        ],
        beliefs=[
            narrative.BeliefPair(
                people_id=30,
                people_name="Kael",
                son_id=2,
                son_name="Ozzeh",
                son_title="the Weeper",
                domain_1="Salt",
                domain_2="Sea",
                known_name="Salt Mother",
                worshipped=True,
            ),
            narrative.BeliefPair(people_id=30, people_name="Kael", son_id=0, son_name="Ul", son_title="the Creator", domain_1="All", domain_2="All"),
        ],
    )


def deepen_celestial() -> narrative.DeepenCelestialContext:
    return narrative.DeepenCelestialContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        world_header=HEADER,
        kind=narrative.CelestialKind.WORLD,
        name="Thessaly Deep",
        detail_lines=["Kind: Ocean world", "Gravity: Normal"],
        lore="The sea was the first word spoken.",
        neighbour_lines=["Its star: Ashen Eye (Red dwarf)", "A people of the world: Kael"],
        recent_events="[Age 4] A war began.",
    )


def deepen() -> narrative.DeepenEntityContext:
    return narrative.DeepenEntityContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        world_header=HEADER,
        entity_type=EntityType.PEOPLE,
        entity_detail="#30 Kael",
        creator_son=SON,
        bond_lines=["→ worships son#2 Ozzeh"],
        recent_events="[Age 4] A war began.",
    )


def creator_epic() -> narrative.CreatorEpicContext:
    return narrative.CreatorEpicContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        world_header=HEADER,
        god_name="Ul",
        known=narrative.GodKnown(title="the Salt", appearance="A white tide", temperament="Distant", note="No bone may burn."),
        cosmology="A salt lake.",
        sons=[
            narrative.EpicSon(
                name="Ozzeh", title="the Weeper", rarity_label="Rare", domain_1="Salt", domain_2="Sea", status_label="asleep", rebel=True, loyalty=30
            )
        ],
        worlds=[narrative.EpicWorld(name="Aerona", type_label="Ordinary world", age=1)],
        ages=[narrative.AgeSummary(age=1, name="Age of Brine", summary="The sea came.")],
        traces=[narrative.TraceRow(age=1, year=100, text="Ul hung a star.")],
        beliefs=[blocks.FolkBeliefLine(people="Kael", name="Old Tide", story="He sleeps under the lake.")],
    )


def creator_deepen() -> narrative.CreatorDeepenContext:
    return narrative.CreatorDeepenContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        world_header=HEADER,
        god_name="Ul",
        known=narrative.GodKnown(),
        cosmology="A salt lake.",
        epic_line="Salt remembers.",
        sons=[SON],
        traces=[],
    )


def foreign_deepen() -> narrative.ForeignGodDeepenContext:
    return narrative.ForeignGodDeepenContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        world_header=HEADER,
        name="Mor",
        home_world=narrative.HomeWorld(name="Vel", type_label="Ocean world", dialect=NAMING, cosmology="Water above."),
        known=narrative.ForeignGodKnown(
            title="the Old",
            domains="Ash/Bone",
            description="An old idol.",
            dead=True,
            death_age=4,
            status_label="dead",
            power=40,
            attitude=-20,
            contact=True,
            stats=[LabelValue(label="Strength", value="60")],
            powers=[narrative.ForeignPowerLine(name="Ash Wall", effect_label="Shield")],
            personality=[LabelValue(label="Appearance", value="Charred")],
        ),
        worshippers=[narrative.WorshipperLine(name="Vor", type_label="People", subtype="ash folk")],
        chronicle=ROWS,
    )


def son_epic() -> narrative.SonEpicContext:
    return narrative.SonEpicContext(
        lore_language=LORE,
        world_name="Aerona",
        world_header=HEADER,
        name="Ozzeh",
        title="the Weeper",
        rarity_label="Rare",
        stars=2,
        domain_1="Salt",
        domain_2="Sea",
        temperament="Cold",
        obsession="The moon",
        secret="A drowned brother",
        creations=[narrative.EpicCreation(name="Vesh Hollow", type_label="Place", subtype="salt cave", age=3, status_label="dead")],
        records=ROWS,
    )


def entity_images() -> imagery.EntityImagePromptsContext:
    ambience = imagery.WorldAmbience(type_label="Ocean world", biomes=["reef", "trench", "kelp", "ice", "isle", "storm"])
    return imagery.EntityImagePromptsContext(
        rules=RULES,
        world_name="Aerona",
        cosmology="A salt lake.",
        tone="grim",
        subjects=[
            imagery.ImageSubject(
                id=12, entity_type=EntityType.VESSEL, type_label="Vessel", subtype="bone ship", name="Gull", description="A ship of bone.", ambience=ambience
            ),
            imagery.ImageSubject(id=13, entity_type=EntityType.SPECIES, type_label="Species", name="Wyrm", description="Huge.", megafauna=True),
        ],
    )


def cosmos_images() -> imagery.CosmosImagePromptsContext:
    return imagery.CosmosImagePromptsContext(
        rules=RULES,
        world_name="Aerona",
        cosmology="A salt lake.",
        tone="grim",
        subjects=[
            imagery.CosmosSubject(number=1, kind=CosmosSubjectKind.WORLD, type_label="Ocean world", name="Vel", description="Water."),
            imagery.CosmosSubject(number=2, kind=CosmosSubjectKind.STAR, type_label="Yellow dwarf", name="Ka", description="Bright."),
            imagery.CosmosSubject(number=3, kind=CosmosSubjectKind.FOREIGN_GOD, name="Mor", title="the Old", description="An idol."),
        ],
    )


def council_session() -> council.CouncilSessionContext:
    return council.CouncilSessionContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        creator_name="Ul",
        world_header=HEADER,
        topic="The salt war",
        god_asked=True,
        members=[MEMBER, MEMBER.model_copy(update={"id": 3, "name": "Tesh", "rebel": False, "plan": None})],
        absent=["Mara"],
        multi_world=True,
        relationships=[council.CouncilRelation(a="Ozzeh", b="Tesh", label="hostility", value=-40, covenant=True)],
    )


def son_chat() -> council.SonChatContext:
    return council.SonChatContext(
        lore_language=LORE,
        rules=RULES,
        member=MEMBER,
        world_name="Aerona",
        creator_name="Ul",
        multi_world=True,
        appearance="Tall",
        fear="Fire",
        secret="A drowned brother",
        memory="MEMORY",
        history=[council.ChatLine(from_father=True, text="Are you loyal?"), council.ChatLine(from_father=False, text="Always.")],
        text="Prove it.",
    )


def translate() -> council.TranslateContext:
    return council.TranslateContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        language_name="Veshi",
        language_subtype="sacred language",
        language_description="The tongue of salt.",
        naming_rule=NAMING,
        syllables=["ve", "sh"],
        lexicon=[LexiconWord(word="vesh", meaning="salt", kind="noun")],
        text="The sea remembers.",
    )


def bond_suggest() -> cosmos.BondSuggestContext:
    return cosmos.BondSuggestContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        bond_types=["tells_of", "loves"],
        records=[
            cosmos.SuggestRecord(
                node=GRAPH_ENTITY,
                candidates=[
                    cosmos.BondCandidate(node=GRAPH_SON, reason=cosmos.CandidateReason.MENTIONED_TOGETHER, mentions=3),
                    cosmos.BondCandidate(node=GRAPH_SON, reason=cosmos.CandidateReason.NOTABLE_OF_WORLD),
                ],
            )
        ],
    )


def bond_related() -> cosmos.BondNameRelatedContext:
    return cosmos.BondNameRelatedContext(
        lore_language=LORE,
        rules=RULES,
        world_name="Aerona",
        bond_types=["tells_of", "loves"],
        bonds=[cosmos.RelatedBond(source=GRAPH_ENTITY, target=GRAPH_SON)],
    )


def localise() -> localisation.LocaliseContext:
    return localisation.LocaliseContext(
        lore_language=LoreLanguage.TURKISH, world_name="Aerona", lines=[localisation.EngineLine(id=4, text="The river rose over Velar.")]
    )


SAMPLES: dict[PromptId, Callable[[], PromptContext]] = {
    P.IMAGE_PROMPT_RULES: EmptyContext,
    P.SECTION_KEYS_RULE: EmptyContext,
    P.NO_NUMBERS_CLAUSE: EmptyContext,
    P.LORE_LANGUAGE: lambda: LoreContext(lore_language=LORE),
    P.RATIONALE_RULE: lambda: RulesContext(rules=RULES),
    P.VERDICT_CRITERIA: EmptyContext,
    P.WORLD_HEADER: world_header,
    P.DIALECT_BLOCK: lambda: blocks.DialectBlockContext(worlds=[blocks.WorldNaming(id=1, name="Aerona", naming=NAMING)]),
    P.WORLD_LINE: lambda: blocks.WorldLineContext(
        id=2,
        name="Vel",
        type_label="Ocean world",
        star_name="Ka",
        star_type="Yellow dwarf",
        gravity="low",
        atmosphere="dense",
        time_factor=1.5,
        leak=20,
        cosmology="Water above.",
    ),
    P.COSMOS_LINES: lambda: blocks.CosmosLinesContext(
        worlds=[
            blocks.CosmosWorld(
                id=2,
                name="Vel",
                type_label="Ocean world",
                star_name="Ka",
                regions=3,
                peoples=1,
                settlements=2,
                gravity="low",
                atmosphere="dense",
                time_factor=2,
                discovery_label="legend",
            )
        ]
    ),
    P.ENTITY_LINE: lambda: blocks.EntityLineContext(entity=ENTITY.model_copy(update={"status_label": "dead"})),
    P.BOND_LINES: lambda: blocks.BondLinesContext(
        outgoing=[blocks.BondLine(label="worships", other=blocks.BondEndpoint(kind=NodeKind.CREATOR, id=0, name="Ul"))],
        incoming=[blocks.BondLine(label="hunts", other=blocks.BondEndpoint(kind=NodeKind.FOREIGN_GOD, id=1, name="Mor"), description="for sport")],
    ),
    P.SOCIETY_LINES: lambda: blocks.SocietyLinesContext(society=entity_detail().society or blocks.SocietyLines()),
    P.ENTITY_DETAIL: entity_detail,
    P.RECENT_CHRONICLE: lambda: blocks.RecentChronicleContext(rows=ROWS),
    P.THREAD_LINES: lambda: blocks.ThreadLinesContext(
        threads=[blocks.ThreadLine(id=3, age=2, worlds=["Aerona", "Vel"], advanced=2, last_age=4, text="The salt sings.", related_ids=[12, 30])],
        more=2,
        elsewhere=1,
    ),
    P.SIBLINGS: lambda: blocks.SiblingsContext(
        siblings=[
            blocks.SiblingLine(
                id=3,
                name="Tesh",
                title="the Ash",
                rarity_label="Epic",
                stars=2,
                existence_label="Solid",
                domain_1="Ash",
                domain_2="Fire",
                world="Vel",
                other_world=True,
                level=4,
                hp=30,
                max_hp=90,
                faith=12,
                fame=8,
                status_label="asleep",
                sleep_left=2,
                relation=blocks.RelationToViewer(label="hostility", value=-40),
                covenant=True,
                rebel=True,
            )
        ]
    ),
    P.POWERS: lambda: blocks.PowersContext(
        powers=[blocks.PowerLine(name="Salt Memory", effect_text="+4 essence every epoch.", unlock_level=3, description="Remembers.")]
    ),
    P.LOCATION_TREE: lambda: blocks.LocationTreeContext(nodes=[blocks.TreeNode(depth=0, entity=ENTITY), blocks.TreeNode(depth=1, entity=PEOPLE)]),
    P.LANGUAGE_LINES: lambda: blocks.LanguageLinesContext(
        languages=[
            blocks.LanguageLine(id=20, name="Veshi", word_count=12, speakers=["Kael"], words=[LexiconWord(word="vesh", meaning="salt")]),
            blocks.LanguageLine(id=21, name="Old Tongue", word_count=3, dead=True),
        ]
    ),
    P.GEOGRAPHY_LINES: lambda: blocks.GeographyLinesContext(
        known_regions=2,
        regions=[
            blocks.RegionGeography(
                id=9,
                name="Orrun",
                elevation_label="lowland",
                coastal=True,
                size_label="wide",
                terrain=["salt flat"],
                neighbours=[NamedRecord(id=10, name="Kor")],
            )
        ],
    ),
    P.WORLD_SUMMARY: world_summary,
    P.SON_MEMORY: son_memory,
    P.SKY_CALENDAR: lambda: blocks.SkyCalendarContext(age=7, period=5),
    P.BUDGET_TRAILER: lambda: blocks.BudgetTrailerContext(hidden_lines=4, hint="look with search_entities"),
    P.INSPECT_SIBLING: lambda: blocks.InspectSiblingContext(
        id=3,
        name="Tesh",
        title="the Ash",
        rarity_label="Epic",
        domain_1="Ash",
        domain_2="Fire",
        level=4,
        status_label="active",
        appearance="Charred",
        known_powers=["Ash Hand"],
        strength=60,
        wisdom=40,
        cunning=50,
        charisma=30,
        will=70,
        hp=30,
        max_hp=90,
        faith=12,
        fame=8,
        relation=blocks.RelationToViewer(label="hostility", value=-40),
        covenant=True,
        creations=[ENTITY],
    ),
    P.GENESIS_SYSTEM: lambda: genesis.GenesisContext(lore_language=LORE, rules=RULES, god_name="Ul", seed="A salt world"),
    P.GENESIS_USER: lambda: genesis.GenesisContext(
        first_son_rarities=["Common", "Rare"],
        lore_language=LORE,
        rules=RULES,
        god_name="Ul",
        seed="A salt world",
        tone="grim",
        wizard_text="CREATION SETTINGS:",
    ),
    P.GENESIS_WIZARD_SETTINGS: lambda: genesis.GenesisWizardContext(
        rules=RULES,
        template_name="Dark fantasy",
        magic=60,
        darkness=85,
        technology=TechnologyEra.IRON,
        language=LanguageTexture.GUTTURAL,
        cosmos=CosmosSize.SMALL,
    ),
    P.SON_POWERS_SYSTEM: son_powers,
    P.SON_POWERS_USER: son_powers,
    P.CREATOR_PORTRAIT_SYSTEM: lambda: genesis.CreatorPortraitContext(lore_language=LORE, world_name="Aerona", world_header=HEADER, god_name="Ul", sons=[SON]),
    P.CREATOR_PORTRAIT_USER: lambda: genesis.CreatorPortraitContext(lore_language=LORE, world_name="Aerona", world_header=HEADER, god_name="Ul", sons=[SON]),
    P.SUMMON_SON_SYSTEM: summon,
    P.SUMMON_SON_USER: summon,
    P.AWAKEN_PEOPLES_SYSTEM: awaken,
    P.AWAKEN_PEOPLES_USER: awaken,
    P.REVELATION_SYSTEM: revelation,
    P.REVELATION_USER: revelation,
    P.SON_TURN_SYSTEM: son_turn_system,
    P.SON_TURN_USER: lambda: son_turn.SonTurnUserContext(
        rules=RULES,
        age=5,
        order="Raise a temple",
        absolute_order=True,
        world_summary="WORLD",
        memory="MEMORY",
        opportunities="- Take the coast",
        action_points=3,
        resumed=True,
    ),
    P.SON_TURN_RESUME_NOTE: EmptyContext,
    P.SON_TURN_CONTINUATION: turn_continuation,
    P.CREATOR_WISHES: lambda: son_turn.CreatorWishesContext(
        passions=[son_turn.PassionHint(label="order", hint="laws, borders")],
        scenarios=[son_turn.ScenarioLine(name="A loyal pantheon", description="No son rebels.")],
    ),
    P.REPUTATION_LINE: lambda: son_turn.ReputationLineContext(
        stance=ReputationLabel.HATED, love=10, fear=70, oblivion=20, unanswered_prayers=2, passions=["order"]
    ),
    P.FATE_JUDGMENT_SYSTEM: lambda: fate.FateSystemContext(lore_language=LORE, world_name="Aerona"),
    P.FATE_JUDGMENT_USER: lambda: fate.FateJudgmentContext(
        lore_language=LORE,
        rules=RULES,
        age=5,
        min_close=1,
        new_max=2,
        close_candidates=[3],
        world_summary="SUMMARY",
        age_events="A war began.",
        engine_notes=["Population grew."],
        new_creations=["#12 Vesh Hollow"],
        pending=["#13 [World engine] battle"],
        world_records=[fate.WorldRecordLine(id=13, name="Battle of Salt", kind_label="battle")],
        prophecies=["#90 The Drowning"],
        threads=[
            fate.FateThreadLine(id=3, age=2, advancers=["Ozzeh"], advance_count=1, text="The salt sings."),
            fate.FateThreadLine(id=4, age=1, stagnant_ages=4, text="The bell."),
        ],
        pantheon=[NamedRecord(id=2, name="Ozzeh")],
        languages=[NamedRecord(id=20, name="Veshi")],
    ),
    P.FATE_EXTRA_JUDGMENT_USER: lambda: fate.FateExtraJudgmentContext(world_header=HEADER, entries=["#12 Vesh Hollow", "#13 Kor"]),
    P.FATE_PRESCREEN_WARNINGS: lambda: fate.PrescreenWarningsContext(warnings=all_warnings()),
    P.FATE_CREATION_ENTRY: lambda: fate.FateCreationEntryContext(detail="#12 Vesh Hollow", warnings=all_warnings()),
    P.AGE_EVENTS: lambda: fate.AgeEventsContext(rows=EVENT_ROWS, limit=1000, trim_min=RULES.context.budget_trim_min_chars),
    P.AGE_EVENTS_BY_WORLD: lambda: fate.AgeEventsByWorldContext(
        rules=RULES, sections=[fate.WorldEvents(world_id=1, world_name="Aerona", rows=EVENT_ROWS), fate.WorldEvents(rows=[])], limit=2000
    ),
    P.CHRONICLER_SYSTEM: lambda: chronicler.ChroniclerSystemContext(lore_language=LORE, world_name="Aerona"),
    P.CHRONICLER_CONCISE_SYSTEM: lambda: chronicler.ChroniclerSystemContext(lore_language=LORE, world_name="Aerona"),
    P.CHRONICLER_USER: chronicler_user,
    P.CHRONICLER_AUDIT_FIX_USER: chronicler_audit_fix,
    P.CHRONICLER_MISSING_WORLDS_USER: chronicler_user,
    P.CHRONICLER_LOST_AGE_USER: chronicler_user,
    P.CHRONICLER_LOST_WORLD_SECTIONS_USER: chronicler_user,
    P.NAMING_SYSTEM: naming,
    P.NAMING_USER: naming,
    P.VOICES_SYSTEM: voices,
    P.VOICES_USER: voices,
    P.DEEPEN_ENTITY_SYSTEM: deepen,
    P.DEEPEN_ENTITY_USER: deepen,
    P.DEEPEN_CELESTIAL_SYSTEM: deepen_celestial,
    P.DEEPEN_CELESTIAL_USER: deepen_celestial,
    P.CREATOR_EPIC_SYSTEM: creator_epic,
    P.CREATOR_EPIC_USER: creator_epic,
    P.CREATOR_DEEPEN_SYSTEM: creator_deepen,
    P.CREATOR_DEEPEN_USER: creator_deepen,
    P.FOREIGN_GOD_DEEPEN_SYSTEM: foreign_deepen,
    P.FOREIGN_GOD_DEEPEN_USER: foreign_deepen,
    P.SON_EPIC_SYSTEM: son_epic,
    P.SON_EPIC_USER: son_epic,
    P.ENTITY_IMAGE_PROMPTS_SYSTEM: entity_images,
    P.ENTITY_IMAGE_PROMPTS_USER: entity_images,
    P.COSMOS_IMAGE_PROMPTS_SYSTEM: cosmos_images,
    P.COSMOS_IMAGE_PROMPTS_USER: cosmos_images,
    P.COUNCIL_PERSONA: lambda: council.CouncilPersonaContext(rules=RULES, member=MEMBER),
    P.COUNCIL_AGENDA: lambda: council.CouncilAgendaContext(rules=RULES, kind=council.AgendaKind.OPEN_THREAD, subject="salt " * 100),
    P.COUNCIL_SESSION_SYSTEM: council_session,
    P.COUNCIL_SESSION_USER: council_session,
    P.SON_CHAT_SYSTEM: son_chat,
    P.SON_CHAT_USER: son_chat,
    P.TRANSLATE_SYSTEM: translate,
    P.LOCALISE_SYSTEM: localise,
    P.LOCALISE_USER: localise,
    P.TRANSLATE_USER: translate,
    P.NEW_WORLD_SYSTEM: new_world,
    P.NEW_WORLD_USER: new_world,
    P.WORLD_INSPIRATION: lambda: cosmos.WorldInspirationContext(kind=cosmos.InspirationKind.GENESIS_EXTRA_WORLD, world_number=3),
    P.BOND_NODE_LINE: lambda: cosmos.BondNodeLineContext(rules=RULES, node=GRAPH_ENTITY),
    P.BOND_SUGGEST_SYSTEM: bond_suggest,
    P.BOND_SUGGEST_USER: bond_suggest,
    P.BOND_NAME_RELATED_SYSTEM: bond_related,
    P.BOND_NAME_RELATED_USER: bond_related,
    P.MORTAL_TURN_SYSTEM: lambda: mortal.MortalTurnSystemContext(
        lore_language=LORE,
        rules=RULES,
        name="Kael",
        world_name="Aerona",
        type_label="People",
        subtype="tide folk",
        action_points=3,
        sanity=20,
        clouded=True,
        paid_tools=["produce_item"],
        free_tools=["worship"],
        captor="Vor",
    ),
    P.MORTAL_TURN_USER: lambda: mortal.MortalTurnUserContext(
        age=5, creator_name="Ul", manifestations=["Rise."], dreams=["Drown."], context="CONTEXT", opportunities="- Trade", resumed=True, actions_left=2
    ),
    P.MORTAL_TURN_CONTINUATION: turn_continuation,
    P.MORTAL_CONTEXT: mortal_context,
    P.SON_OPPORTUNITIES: opportunities_son,
    P.MORTAL_OPPORTUNITIES: opportunities_mortal,
    P.CREATOR_OPPORTUNITIES: lambda: opportunities.CreatorOpportunitiesContext(
        rules=RULES,
        unanswered_prayers=2,
        unclaimed_count=3,
        unclaimed_examples=["Vor"],
        rebel_sons=["Tesh"],
        fading_sons=[opportunities.FadingSon(name="Mara", existence=10)],
        doom=80,
        doom_threshold=100,
        godless_worlds=["Vel"],
        stale_threads=2,
        essence=500,
    ),
    P.TOOL_REJECTION: lambda: agent.ToolRejectionContext(reason="Invalid sibling."),
    P.TOOL_FAILURE_REFUND: lambda: agent.ToolFailureContext(error="boom"),
    P.SON_GATE_REJECTION: lambda: agent.SonGateContext(name="Ozzeh", state_label="asleep", sleep_left=2),
    P.MORTAL_GATE_REJECTION: lambda: agent.MortalGateContext(name="Kael", status_label="destroyed"),
    P.CAPTIVE_GATE_REJECTION: lambda: agent.CaptiveGateContext(captor="Vor"),
    P.ACTIONS_SPENT: lambda: agent.ActionsSpentContext(agent=AgentKind.SON, remaining=0),
    P.STATUS_LINE: lambda: agent.StatusLineContext(remaining=2, essence=30, max_essence=90),
    P.SLEEP_NOTICE: lambda: agent.SleepNoticeContext(asleep=True, state_label="asleep"),
    P.PENDING_LONG_JOB: lambda: agent.PendingLongJobContext(job=PendingJobKind.WORLD_BIRTH),
    P.ENTITY_STATE_REASON: lambda: agent.EntityStateContext(kind=agent.EntityStateKind.DEAD, id=12, name="Vesh Hollow", age=4),
    P.FIELD_ERROR: lambda: agent.FieldErrorContext(kind=agent.FieldErrorKind.TOO_BIG, field="power_level", limit=10, given="12"),
    P.PER_EPOCH_LIMIT: lambda: agent.PerEpochLimitContext(rule_path="son_tools.gift_per_epoch", value=1),
    P.CREATOR_SIGN: lambda: chronicle.CreatorSignContext(kind=chronicle.SignKind.WRATH, variant=5, creator="Ul", place="Orrun", disaster="a flood"),
    P.SENTIENT_DEMAND: lambda: chronicle.SentientDemandContext(resource="Tear Pearl", owner="Kael", demand_variant=7, paid=False, new_owner="Vor"),
}


def sample_context(prompt_id: PromptId) -> PromptContext:
    return SAMPLES[prompt_id]()
