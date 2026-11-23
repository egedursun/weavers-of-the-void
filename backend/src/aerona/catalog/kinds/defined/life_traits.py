from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.life_traits import (
    ActKindTrait,
    AgeGradeTrait,
    AllocationModeTrait,
    AssistiveAidTrait,
    AttackRangeTrait,
    BiologyVariantTrait,
    BodySystemTrait,
    BreachCauseTrait,
    BuildingFormTrait,
    CaptiveFateTrait,
    CaptiveStatusTrait,
    CharmPowerTrait,
    ClauseKindTrait,
    CommanderTraitTrait,
    CommandTokenTrait,
    ConstructionStateTrait,
    ContestStakeTrait,
    CoopPurposeTrait,
    CouncilMotionTrait,
    CultivationMethodTrait,
    DeathRoleTrait,
    DuelContextTrait,
    EmotionTrait,
    ExpeditionGroundTrait,
    ExtractionKindTrait,
    FactionActionKindTrait,
    FactionKindTrait,
    FurnishingCategoryTrait,
    GatheringKindTrait,
    GiftStateTrait,
    GroupKindTrait,
    HazardKindTrait,
    HiddenTruthKindTrait,
    HouseDutyTrait,
    IdentityLayerTrait,
    InheritanceCustomTrait,
    InteractionKindTrait,
    IntoxicantTrait,
    JobTrait,
    JourneyIntentTrait,
    KnowledgeBranchTrait,
    LandActTrait,
    LeisureKindTrait,
    LifeStageTrait,
    LineTraitTrait,
    MadeMindStanceTrait,
    MediumTrait,
    MemoryKindTrait,
    MetabolismTrait,
    MindUpkeepTrait,
    MishapKindTrait,
    OathKindTrait,
    ObservationMethodTrait,
    OfficeDutyTrait,
    OfficeKindTrait,
    OrderKindTrait,
    PackageKindTrait,
    PassionKindTrait,
    PopulationInstrumentTrait,
    PowerOriginTrait,
    PowerStateTrait,
    PreparednessKindTrait,
    PunishmentKindTrait,
    RebuildCauseTrait,
    RecordFormTrait,
    RegionalStandingTrait,
    RelationTypeTrait,
    RightKindTrait,
    RumourDistortionTrait,
    SettleModeTrait,
    SizeClassTrait,
    SkillKindTrait,
    SourceLocusTrait,
    SpeciesClassTrait,
    SpeechVenueTrait,
    SpellFormTrait,
    SpellTechniqueTrait,
    StanceTrait,
    StarvationStageTrait,
    StructureSectionTrait,
    TacticTrait,
    TaxKindTrait,
    TechniqueTrait,
    ThoughtKindTrait,
    TradeModeTrait,
    TradePolicyKindTrait,
    TradeRouteStatusTrait,
    TreatyKindTrait,
    UnitHonourKindTrait,
    VehicleFamilyTrait,
    WarCauseTrait,
    WarEndingTrait,
    WarTerrainTrait,
    WeatherEffectTrait,
    WitnessModeTrait,
    WorksKindTrait,
    WorldEndTrait,
    WorldTypeTrait,
    YouthPurposeTrait,
)

ACT_KIND_TRAIT = total(
    ActKindTrait,
    {
        ActKindTrait.FAMINE_ACTS: Defined("Famine acts", checked_by=(), used_by=("catalog.life_traits.ACT_KIND_TRAITS", "engine.mind.ethics.FAMINE_ACTS")),
        ActKindTrait.FEARSOME: Defined("Fearsome", checked_by=(), used_by=("catalog.life_traits.ACT_KIND_TRAITS", "engine.renown.currencies.FEARSOME")),
        ActKindTrait.WAR_ACTS: Defined("War acts", checked_by=(), used_by=("catalog.life_traits.ACT_KIND_TRAITS", "engine.mind.ethics.WAR_ACTS")),
    },
)

AGE_GRADE_TRAIT = total(
    AgeGradeTrait,
    {
        AgeGradeTrait.UNWED_GRADES: Defined(
            "Unwed grades", checked_by=(), used_by=("catalog.life_traits.AGE_GRADE_TRAITS", "engine.customs.grades.UNWED_GRADES")
        ),
    },
)

ALLOCATION_MODE_TRAIT = total(
    AllocationModeTrait,
    {
        AllocationModeTrait.CENTRES: Defined("Centres", checked_by=(), used_by=("catalog.life_traits.ALLOCATION_MODE_TRAITS", "engine.orders.economy.CENTRES")),
        AllocationModeTrait.SHARING: Defined("Sharing", checked_by=(), used_by=("catalog.life_traits.ALLOCATION_MODE_TRAITS", "engine.orders.economy.SHARING")),
        AllocationModeTrait.STATE_BUYERS: Defined(
            "State buyers",
            checked_by=(),
            used_by=("catalog.life_traits.ALLOCATION_MODE_TRAITS", "engine.competition.structure.STATE_BUYERS", "engine.orders.pressures.PLANNED"),
        ),
    },
)

ASSISTIVE_AID_TRAIT = total(
    AssistiveAidTrait,
    {
        AssistiveAidTrait.GROUND_LENS: Defined(
            "Ground lens", checked_by=(), used_by=("catalog.life_traits.ASSISTIVE_AID_TRAITS", "engine.crafts.aids.GROUND_LENS")
        ),
    },
)

ATTACK_RANGE_TRAIT = total(
    AttackRangeTrait,
    {
        AttackRangeTrait.WHOLE_TOWN: Defined(
            "Whole town", checked_by=(), used_by=("catalog.life_traits.ATTACK_RANGE_TRAITS", "engine.ecology.beast_acts.WHOLE_TOWN")
        ),
    },
)

BIOLOGY_VARIANT_TRAIT = total(
    BiologyVariantTrait,
    {
        BiologyVariantTrait.SKYLESS: Defined("Skyless", checked_by=(), used_by=("catalog.life_traits.BIOLOGY_VARIANT_TRAITS", "engine.cosmos.omens.SKYLESS")),
    },
)

BODY_SYSTEM_TRAIT = total(
    BodySystemTrait,
    {
        BodySystemTrait.BLOODLESS: Defined("Bloodless", checked_by=(), used_by=("catalog.life_traits.BODY_SYSTEM_TRAITS", "engine.body.systems.BLOODLESS")),
    },
)

BREACH_CAUSE_TRAIT = total(
    BreachCauseTrait,
    {
        BreachCauseTrait.ACCORD_BREAKING: Defined(
            "Accord breaking", checked_by=(), used_by=("catalog.life_traits.BREACH_CAUSE_TRAITS", "engine.concealment.truths.ACCORD_BREAKING")
        ),
    },
)

BUILDING_FORM_TRAIT = total(
    BuildingFormTrait,
    {
        BuildingFormTrait.FIXED_FORMS: Defined(
            "Fixed forms", checked_by=(), used_by=("catalog.life_traits.BUILDING_FORM_TRAITS", "engine.structures.types.FIXED_FORMS")
        ),
    },
)

CAPTIVE_FATE_TRAIT = total(
    CaptiveFateTrait,
    {
        CaptiveFateTrait.BOUND: Defined("Bound", checked_by=(), used_by=("catalog.life_traits.CAPTIVE_FATE_TRAITS", "engine.tongues.pidgins.BOUND")),
    },
)

CAPTIVE_STATUS_TRAIT = total(
    CaptiveStatusTrait,
    {
        CaptiveStatusTrait.FREEING_STATUSES: Defined(
            "Freeing statuses", checked_by=(), used_by=("catalog.life_traits.CAPTIVE_STATUS_TRAITS", "engine.services.war.FREEING_STATUSES")
        ),
        CaptiveStatusTrait.RESCUE_STATUSES: Defined(
            "Rescue statuses", checked_by=(), used_by=("catalog.life_traits.CAPTIVE_STATUS_TRAITS", "engine.services.war.RESCUE_STATUSES")
        ),
        CaptiveStatusTrait.AFTER_CAPTIVITY: Defined(
            "After captivity", checked_by=(), used_by=("agents.context.operations_lines.AFTER_CAPTIVITY", "catalog.life_traits.CAPTIVE_STATUS_TRAITS")
        ),
    },
)

CHARM_POWER_TRAIT = total(
    CharmPowerTrait,
    {
        CharmPowerTrait.WARDS: Defined("Wards", checked_by=(), used_by=("catalog.life_traits.CHARM_POWER_TRAITS", "engine.folkways.mishaps.WARDS")),
    },
)

CLAUSE_KIND_TRAIT = total(
    ClauseKindTrait,
    {
        ClauseKindTrait.METHOD_CLAUSES: Defined(
            "Method clauses", checked_by=(), used_by=("catalog.life_traits.CLAUSE_KIND_TRAITS", "engine.minds.war_methods.METHOD_CLAUSES")
        ),
        ClauseKindTrait.PEACEFUL: Defined("Peaceful", checked_by=(), used_by=("catalog.life_traits.CLAUSE_KIND_TRAITS", "engine.polity.treaties.PEACEFUL")),
    },
)

COMMAND_TOKEN_TRAIT = total(
    CommandTokenTrait,
    {
        CommandTokenTrait.OWNED_TOKENS: Defined(
            "Owned tokens", checked_by=(), used_by=("catalog.life_traits.COMMAND_TOKEN_TRAITS", "engine.constructs.orders.OWNED_TOKENS")
        ),
    },
)

COMMANDER_TRAIT_TRAIT = total(
    CommanderTraitTrait,
    {
        CommanderTraitTrait.AGGRESSIVE: Defined(
            "Aggressive", checked_by=(), used_by=("catalog.life_traits.COMMANDER_TRAIT_TRAITS", "engine.military.campaign.AGGRESSIVE")
        ),
        CommanderTraitTrait.CAREFUL: Defined(
            "Careful", checked_by=(), used_by=("catalog.life_traits.COMMANDER_TRAIT_TRAITS", "engine.military.campaign.CAREFUL")
        ),
        CommanderTraitTrait.CLASH_AGGRESSIVE: Defined(
            "Clash aggressive", checked_by=(), used_by=("catalog.life_traits.COMMANDER_TRAIT_TRAITS", "engine.military.clash.AGGRESSIVE")
        ),
        CommanderTraitTrait.DECAPITATORS: Defined(
            "Decapitators", checked_by=(), used_by=("catalog.life_traits.COMMANDER_TRAIT_TRAITS", "engine.phases.casualties.DECAPITATORS")
        ),
    },
)

CONSTRUCTION_STATE_TRAIT = total(
    ConstructionStateTrait,
    {
        ConstructionStateTrait.COUNTED_STATES: Defined(
            "Counted states", checked_by=(), used_by=("catalog.life_traits.CONSTRUCTION_STATE_TRAITS", "engine.structures.needs.COUNTED_STATES")
        ),
    },
)

CONTEST_STAKE_TRAIT = total(
    ContestStakeTrait,
    {
        ContestStakeTrait.NOTED: Defined("Noted", checked_by=(), used_by=("catalog.life_traits.CONTEST_STAKE_TRAITS", "engine.relations.contests.NOTED")),
    },
)

COOP_PURPOSE_TRAIT = total(
    CoopPurposeTrait,
    {
        CoopPurposeTrait.POOLING: Defined("Pooling", checked_by=(), used_by=("catalog.life_traits.COOP_PURPOSE_TRAITS", "engine.crafts.insurance.POOLING")),
        CoopPurposeTrait.RELIEVING: Defined("Relieving", checked_by=(), used_by=("catalog.life_traits.COOP_PURPOSE_TRAITS", "engine.customs.relief.RELIEVING")),
        CoopPurposeTrait.WORKING: Defined("Working", checked_by=(), used_by=("catalog.life_traits.COOP_PURPOSE_TRAITS", "engine.customs.town_life.WORKING")),
    },
)

COUNCIL_MOTION_TRAIT = total(
    CouncilMotionTrait,
    {
        CouncilMotionTrait.ORDER_LASTING: Defined(
            "Order lasting", checked_by=(), used_by=("catalog.life_traits.COUNCIL_MOTION_TRAITS", "engine.divine.council_order.ORDER_LASTING")
        ),
    },
)

CULTIVATION_METHOD_TRAIT = total(
    CultivationMethodTrait,
    {
        CultivationMethodTrait.RITE_PATHS: Defined(
            "Rite paths", checked_by=(), used_by=("catalog.life_traits.CULTIVATION_METHOD_TRAITS", "engine.living.lines.RITE_PATHS")
        ),
    },
)

DEATH_ROLE_TRAIT = total(
    DeathRoleTrait,
    {
        DeathRoleTrait.HANDLING: Defined("Handling", checked_by=(), used_by=("catalog.life_traits.DEATH_ROLE_TRAITS", "engine.death_work.seed.HANDLING")),
        DeathRoleTrait.SACRED: Defined("Sacred", checked_by=(), used_by=("catalog.life_traits.DEATH_ROLE_TRAITS", "engine.death_work.seed.SACRED")),
        DeathRoleTrait.TENDING: Defined("Tending", checked_by=(), used_by=("catalog.life_traits.DEATH_ROLE_TRAITS", "engine.death_work.handling.TENDING")),
    },
)

DUEL_CONTEXT_TRAIT = total(
    DuelContextTrait,
    {
        DuelContextTrait.DUEL_CONTEXTS: Defined(
            "Duel contexts", checked_by=(), used_by=("catalog.life_traits.DUEL_CONTEXT_TRAITS", "services.player.military_depth.DUEL_CONTEXTS")
        ),
        DuelContextTrait.CUSTOMARY: Defined(
            "Customary", checked_by=(), used_by=("catalog.life_traits.DUEL_CONTEXT_TRAITS", "engine.phases.warfare.CUSTOMARY_CONTEXTS")
        ),
        DuelContextTrait.AT_WAR: Defined("At war", checked_by=(), used_by=("catalog.life_traits.DUEL_CONTEXT_TRAITS", "tools.mortal.w52_agent_f.AT_WAR")),
    },
)

EMOTION_TRAIT = total(
    EmotionTrait,
    {
        EmotionTrait.AFRAID: Defined("Afraid", checked_by=(), used_by=("catalog.collective.CROWD_FEELINGS", "catalog.life_traits.EMOTION_TRAITS")),
        EmotionTrait.ANGRY: Defined("Angry", checked_by=(), used_by=("catalog.collective.CROWD_FEELINGS", "catalog.life_traits.EMOTION_TRAITS")),
        EmotionTrait.STIRRED: Defined("Stirred", checked_by=(), used_by=("catalog.collective.CROWD_FEELINGS", "catalog.life_traits.EMOTION_TRAITS")),
        EmotionTrait.GRIEVING: Defined("Grieving", checked_by=(), used_by=("catalog.collective.CROWD_FEELINGS", "catalog.life_traits.EMOTION_TRAITS")),
        EmotionTrait.HOPEFUL: Defined("Hopeful", checked_by=(), used_by=("catalog.collective.CROWD_FEELINGS", "catalog.life_traits.EMOTION_TRAITS")),
    },
)

EXPEDITION_GROUND_TRAIT = total(
    ExpeditionGroundTrait,
    {
        ExpeditionGroundTrait.DARK_GROUNDS: Defined(
            "Dark grounds", checked_by=(), used_by=("catalog.life_traits.EXPEDITION_GROUND_TRAITS", "engine.operations.expeditions.DARK_GROUNDS")
        ),
    },
)

EXTRACTION_KIND_TRAIT = total(
    ExtractionKindTrait,
    {
        ExtractionKindTrait.ARTISAN_KINDS: Defined(
            "Artisan kinds",
            checked_by=(),
            used_by=("catalog.life_traits.EXTRACTION_KIND_TRAITS", "engine.economy.extraction.ARTISAN_KINDS", "engine.phases.resources.SEAM_KINDS"),
        ),
    },
)

FACTION_ACTION_KIND_TRAIT = total(
    FactionActionKindTrait,
    {
        FactionActionKindTrait.DEFIANT: Defined(
            "Defiant", checked_by=(), used_by=("catalog.life_traits.FACTION_ACTION_KIND_TRAITS", "engine.factions.agenda.DEFIANT")
        ),
    },
)

FACTION_KIND_TRAIT = total(
    FactionKindTrait,
    {
        FactionKindTrait.BODY_KINDS: Defined(
            "Body kinds", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.labour.bodies.BODY_KINDS")
        ),
        FactionKindTrait.GANGS: Defined("Gangs", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.youth.groups.GANGS")),
        FactionKindTrait.GUILDS: Defined("Guilds", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.belonging.values.GUILDS")),
        FactionKindTrait.HERALDRY_GUILDS: Defined(
            "Heraldry guilds", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.collective.heraldry.GUILDS")
        ),
        FactionKindTrait.MOVEMENTS: Defined("Movements", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.youth.groups.MOVEMENTS")),
        FactionKindTrait.ORDERS: Defined(
            "Orders",
            checked_by=(),
            used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.collective.heraldry.ORDERS", "engine.honours.persons.ORDER_KINDS"),
        ),
        FactionKindTrait.TREASON_KINDS: Defined(
            "Treason kinds", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.polity.justice.TREASON_KINDS")
        ),
        FactionKindTrait.WARLIKE: Defined("Warlike", checked_by=(), used_by=("catalog.life_traits.FACTION_KIND_TRAITS", "engine.relations.book.WARLIKE")),
    },
)

FURNISHING_CATEGORY_TRAIT = total(
    FurnishingCategoryTrait,
    {
        FurnishingCategoryTrait.FURNISHING_FIRE: Defined(
            "Furnishing fire", checked_by=(), used_by=("catalog.life_traits.FURNISHING_CATEGORY_TRAITS", "engine.kinds.crafts_life.FURNISHING_FIRE")
        ),
    },
)

GATHERING_KIND_TRAIT = total(
    GatheringKindTrait,
    {
        GatheringKindTrait.ENGINE_KINDS: Defined(
            "Engine kinds", checked_by=(), used_by=("catalog.life_traits.GATHERING_KIND_TRAITS", "tools.mortal.gatherings.ENGINE_KINDS")
        ),
        GatheringKindTrait.POTLATCH_FEASTS: Defined(
            "Potlatch feasts", checked_by=(), used_by=("catalog.life_traits.GATHERING_KIND_TRAITS", "engine.cycles.gifts.POTLATCH_FEASTS")
        ),
        GatheringKindTrait.RULER_KINDS: Defined(
            "Ruler kinds", checked_by=(), used_by=("catalog.life_traits.GATHERING_KIND_TRAITS", "tools.mortal.gatherings.RULER_KINDS")
        ),
        GatheringKindTrait.SON_KINDS: Defined(
            "Son kinds", checked_by=(), used_by=("catalog.life_traits.GATHERING_KIND_TRAITS", "tools.son.gatherings.SON_KINDS")
        ),
    },
)

GIFT_STATE_TRAIT = total(
    GiftStateTrait,
    {
        GiftStateTrait.OBLIGING: Defined("Obliging", checked_by=(), used_by=("catalog.life_traits.GIFT_STATE_TRAITS", "engine.cycles.gifts.OBLIGING")),
    },
)

GROUP_KIND_TRAIT = total(
    GroupKindTrait,
    {
        GroupKindTrait.LEADING: Defined("Leading", checked_by=(), used_by=("catalog.life_traits.GROUP_KIND_TRAITS", "engine.relations.pecking.LEADING")),
    },
)

HAZARD_KIND_TRAIT = total(
    HazardKindTrait,
    {
        HazardKindTrait.WORKS_HAZARDS: Defined(
            "Works hazards", checked_by=(), used_by=("catalog.life_traits.HAZARD_KIND_TRAITS", "engine.economy.extraction.WORKS_HAZARDS")
        ),
    },
)

HIDDEN_TRUTH_KIND_TRAIT = total(
    HiddenTruthKindTrait,
    {
        HiddenTruthKindTrait.GIFTED_TRUTHS: Defined(
            "Gifted truths", checked_by=(), used_by=("catalog.life_traits.HIDDEN_TRUTH_KIND_TRAITS", "engine.concealment.truths.GIFTED_TRUTHS")
        ),
    },
)

HOUSE_DUTY_TRAIT = total(
    HouseDutyTrait,
    {
        HouseDutyTrait.CARE_DUTIES: Defined("Care duties", checked_by=(), used_by=("catalog.life_traits.HOUSE_DUTY_TRAITS", "engine.daily.seed.CARE_DUTIES")),
        HouseDutyTrait.SERVED_DUTIES: Defined(
            "Served duties", checked_by=(), used_by=("catalog.life_traits.HOUSE_DUTY_TRAITS", "engine.daily.seed.SERVED_DUTIES")
        ),
    },
)

IDENTITY_LAYER_TRAIT = total(
    IdentityLayerTrait,
    {
        IdentityLayerTrait.GROUP_LAYERS: Defined(
            "Group layers", checked_by=(), used_by=("catalog.life_traits.IDENTITY_LAYER_TRAITS", "engine.belonging.effects.GROUP_LAYERS")
        ),
    },
)

INHERITANCE_CUSTOM_TRAIT = total(
    InheritanceCustomTrait,
    {
        InheritanceCustomTrait.DISCRETION: Defined(
            "Discretion", checked_by=(), used_by=("catalog.life_traits.INHERITANCE_CUSTOM_TRAITS", "engine.kin_dynamics.heirs.DISCRETION")
        ),
    },
)

INTERACTION_KIND_TRAIT = total(
    InteractionKindTrait,
    {
        InteractionKindTrait.FRIENDLY_TALK: Defined(
            "Friendly talk", checked_by=(), used_by=("catalog.life_traits.INTERACTION_KIND_TRAITS", "engine.relations.interactions.FRIENDLY_TALK")
        ),
        InteractionKindTrait.TALK_FREE: Defined(
            "Talk free", checked_by=(), used_by=("catalog.life_traits.INTERACTION_KIND_TRAITS", "engine.relations.interactions.TALK_FREE")
        ),
    },
)

INTOXICANT_TRAIT = total(
    IntoxicantTrait,
    {
        IntoxicantTrait.DRINKS: Defined("Drinks", checked_by=(), used_by=("catalog.life_traits.INTOXICANT_TRAITS", "engine.customs.intoxicants.DRINKS")),
        IntoxicantTrait.STIMULATES: Defined(
            "Stimulates", checked_by=(), used_by=("catalog.life_traits.INTOXICANT_TRAITS", "engine.customs.intoxicants.STIMULATING")
        ),
    },
)

JOB_TRAIT = total(
    JobTrait,
    {
        JobTrait.BOUND_JOBS: Defined("Bound jobs", checked_by=(), used_by=("catalog.life_traits.JOB_TRAITS", "engine.demography.labour.BOUND_JOBS")),
        JobTrait.MADE_MIND_TRADES: Defined(
            "Made mind trades", checked_by=(), used_by=("catalog.life_traits.JOB_TRAITS", "engine.labour.founding.MADE_MIND_TRADES")
        ),
    },
)

JOURNEY_INTENT_TRAIT = total(
    JourneyIntentTrait,
    {
        JourneyIntentTrait.CROWD_INTENTS: Defined(
            "Crowd intents", checked_by=(), used_by=("catalog.life_traits.JOURNEY_INTENT_TRAITS", "tools.mortal.cosmos.CROWD_INTENTS")
        ),
        JourneyIntentTrait.PASSENGER_INTENTS: Defined(
            "Passenger intents", checked_by=(), used_by=("catalog.life_traits.JOURNEY_INTENT_TRAITS", "engine.cosmos.routes.PASSENGER_INTENTS")
        ),
        JourneyIntentTrait.SURVEYING: Defined(
            "Surveying", checked_by=(), used_by=("catalog.life_traits.JOURNEY_INTENT_TRAITS", "engine.cosmos.survey.SURVEYING")
        ),
    },
)

KNOWLEDGE_BRANCH_TRAIT = total(
    KnowledgeBranchTrait,
    {
        KnowledgeBranchTrait.CRAFT_BRANCHES: Defined(
            "Craft branches", checked_by=(), used_by=("catalog.life_traits.KNOWLEDGE_BRANCH_TRAITS", "engine.factions.guilds.CRAFT_BRANCHES")
        ),
        KnowledgeBranchTrait.EXPLORATION_BRANCHES: Defined(
            "Exploration branches",
            checked_by=(),
            used_by=("catalog.life_traits.KNOWLEDGE_BRANCH_TRAITS", "engine.gods.mortal_opportunities.EXPLORATION_BRANCHES"),
        ),
        KnowledgeBranchTrait.KNOWLEDGE_FOR_EXPLORING: Defined(
            "Knowledge for exploring",
            checked_by=(),
            used_by=("catalog.life_traits.KNOWLEDGE_BRANCH_TRAITS", "engine.phases.exploration.KNOWLEDGE_FOR_EXPLORING"),
        ),
        KnowledgeBranchTrait.NATURAL_BRANCHES: Defined(
            "Natural branches", checked_by=(), used_by=("catalog.life_traits.KNOWLEDGE_BRANCH_TRAITS", "engine.lore.research.NATURAL_BRANCHES")
        ),
        KnowledgeBranchTrait.RECKONED: Defined(
            "Reckoned", checked_by=(), used_by=("catalog.life_traits.KNOWLEDGE_BRANCH_TRAITS", "engine.crafts.reckoning.RECKONED")
        ),
        KnowledgeBranchTrait.ROAD_BRANCHES: Defined(
            "Road branches", checked_by=(), used_by=("catalog.life_traits.KNOWLEDGE_BRANCH_TRAITS", "engine.gods.mortal_opportunities.ROAD_BRANCHES")
        ),
    },
)

LAND_ACT_TRAIT = total(
    LandActTrait,
    {
        LandActTrait.FEARED: Defined("Feared", checked_by=(), used_by=("catalog.life_traits.LAND_ACT_TRAITS", "engine.environment.shaping.FEARED")),
        LandActTrait.LIFTS: Defined("Lifts", checked_by=(), used_by=("catalog.life_traits.LAND_ACT_TRAITS", "engine.environment.shaping.LIFTS")),
        LandActTrait.SOIL_ACTS: Defined("Soil acts", checked_by=(), used_by=("catalog.life_traits.LAND_ACT_TRAITS", "engine.environment.shaping.SOIL_ACTS")),
        LandActTrait.WELCOMED: Defined("Welcomed", checked_by=(), used_by=("catalog.life_traits.LAND_ACT_TRAITS", "engine.environment.shaping.WELCOMED")),
    },
)

LEISURE_KIND_TRAIT = total(
    LeisureKindTrait,
    {
        LeisureKindTrait.TRAVEL_PURSUITS: Defined(
            "Travel pursuits", checked_by=(), used_by=("catalog.life_traits.LEISURE_KIND_TRAITS", "engine.daily.life.TRAVEL_PURSUITS")
        ),
    },
)

LIFE_STAGE_TRAIT = total(
    LifeStageTrait,
    {
        LifeStageTrait.CARED_FOR: Defined(
            "Cared for", checked_by=(), used_by=("catalog.life_traits.LIFE_STAGE_TRAITS", "engine.daily.life.CARED_FOR", "engine.fortune.everyday.FRAIL")
        ),
        LifeStageTrait.DUTIES_YOUNG: Defined("Duties young", checked_by=(), used_by=("catalog.life_traits.LIFE_STAGE_TRAITS", "engine.kin.duties.YOUNG")),
        LifeStageTrait.GROWING: Defined(
            "Growing",
            checked_by=(),
            used_by=(
                "agents.context.childhood_lines.GROWING",
                "catalog.life_traits.LIFE_STAGE_TRAITS",
                "engine.daily.life.YOUNG",
                "engine.folkways.mishaps.YOUNG",
                "engine.folkways.nutrition.YOUNG",
                "engine.households.formation.YOUNG",
                "tools.mortal.childhood.GROWING",
            ),
        ),
        LifeStageTrait.GROWN: Defined("Grown", checked_by=(), used_by=("catalog.life_traits.LIFE_STAGE_TRAITS", "engine.powers.phase.GROWN")),
        LifeStageTrait.OLD: Defined(
            "Old", checked_by=(), used_by=("catalog.life_traits.LIFE_STAGE_TRAITS", "engine.households.formation.OLD", "engine.mind.wider_needs.OLD")
        ),
        LifeStageTrait.YOUNG: Defined(
            "Young",
            checked_by=(),
            used_by=("catalog.life_traits.LIFE_STAGE_TRAITS", "engine.belonging.peers.YOUNG", "engine.childhood.life.GROWING", "engine.storyteller.arcs.YOUNG"),
        ),
    },
)

LINE_TRAIT_TRAIT = total(
    LineTraitTrait,
    {
        LineTraitTrait.SHAPING_TRAITS: Defined(
            "Shaping traits", checked_by=(), used_by=("catalog.life_traits.LINE_TRAIT_TRAITS", "engine.living.world.SHAPING_TRAITS")
        ),
        LineTraitTrait.SPREADING: Defined("Spreading", checked_by=(), used_by=("catalog.life_traits.LINE_TRAIT_TRAITS", "engine.living.lines.SPREADING")),
    },
)

MADE_MIND_STANCE_TRAIT = total(
    MadeMindStanceTrait,
    {
        MadeMindStanceTrait.KEEPING_STANCES: Defined(
            "Keeping stances", checked_by=(), used_by=("catalog.life_traits.MADE_MIND_STANCE_TRAITS", "engine.minds.law.KEEPING_STANCES")
        ),
    },
)

MEDIUM_TRAIT = total(
    MediumTrait,
    {
        MediumTrait.INSTANT: Defined("Instant", checked_by=(), used_by=("catalog.life_traits.MEDIUM_TRAITS", "engine.communication.post.INSTANT")),
        MediumTrait.OPEN_MEDIA: Defined("Open media", checked_by=(), used_by=("catalog.life_traits.MEDIUM_TRAITS", "engine.communication.post.OPEN_MEDIA")),
        MediumTrait.OVERLAND: Defined("Overland", checked_by=(), used_by=("catalog.life_traits.MEDIUM_TRAITS", "engine.communication.post.OVERLAND")),
    },
)

MEMORY_KIND_TRAIT = total(
    MemoryKindTrait,
    {
        MemoryKindTrait.CARES: Defined("Cares", checked_by=(), used_by=("catalog.life_traits.MEMORY_KIND_TRAITS", "engine.minds.phase.CARES")),
        MemoryKindTrait.GRIEVANCES: Defined(
            "Grievances", checked_by=(), used_by=("catalog.life_traits.MEMORY_KIND_TRAITS", "engine.folkways.witchcraft.GRIEVANCES")
        ),
        MemoryKindTrait.HARMS: Defined("Harms", checked_by=(), used_by=("catalog.life_traits.MEMORY_KIND_TRAITS", "engine.minds.phase.HARMS")),
        MemoryKindTrait.TRAUMA_KINDS: Defined(
            "Trauma kinds", checked_by=(), used_by=("catalog.life_traits.MEMORY_KIND_TRAITS", "engine.body.afflictions.TRAUMA_KINDS")
        ),
    },
)

METABOLISM_TRAIT = total(
    MetabolismTrait,
    {
        MetabolismTrait.SELF_FED: Defined("Self fed", checked_by=(), used_by=("catalog.life_traits.METABOLISM_TRAITS", "engine.living.profiles.SELF_FED")),
    },
)

MIND_UPKEEP_TRAIT = total(
    MindUpkeepTrait,
    {
        MindUpkeepTrait.REALMS_SELF_KEPT: Defined(
            "Realms self kept", checked_by=(), used_by=("catalog.life_traits.MIND_UPKEEP_TRAITS", "engine.made.realms.SELF_KEPT")
        ),
        MindUpkeepTrait.SELF_KEPT: Defined("Self kept", checked_by=(), used_by=("catalog.life_traits.MIND_UPKEEP_TRAITS", "engine.augments.SELF_KEPT")),
    },
)

MISHAP_KIND_TRAIT = total(
    MishapKindTrait,
    {
        MishapKindTrait.FRIGHTS: Defined("Frights", checked_by=(), used_by=("catalog.life_traits.MISHAP_KIND_TRAITS", "engine.fortune.everyday.FRIGHTS")),
        MishapKindTrait.LOSSES: Defined("Losses", checked_by=(), used_by=("catalog.life_traits.MISHAP_KIND_TRAITS", "engine.fortune.everyday.LOSSES")),
    },
)

OATH_KIND_TRAIT = total(
    OathKindTrait,
    {
        OathKindTrait.LOYAL_OATHS: Defined(
            "Loyal oaths", checked_by=(), used_by=("catalog.life_traits.OATH_KIND_TRAITS", "engine.relations.passions.LOYAL_OATHS")
        ),
        OathKindTrait.TIMED: Defined("Timed", checked_by=(), used_by=("catalog.life_traits.OATH_KIND_TRAITS", "engine.polity.oaths.TIMED")),
    },
)

OBSERVATION_METHOD_TRAIT = total(
    ObservationMethodTrait,
    {
        ObservationMethodTrait.TRUSTED_BY_FAITH: Defined(
            "Trusted by faith", checked_by=(), used_by=("catalog.life_traits.OBSERVATION_METHOD_TRAITS", "engine.forecasting.works.TRUSTED_BY_FAITH")
        ),
    },
)

OFFICE_DUTY_TRAIT = total(
    OfficeDutyTrait,
    {
        OfficeDutyTrait.DUTY_TOWNS: Defined(
            "Duty towns", checked_by=(), used_by=("catalog.life_traits.OFFICE_DUTY_TRAITS", "engine.mythic.offices.DUTY_TOWNS")
        ),
        OfficeDutyTrait.PIETY_DUTIES: Defined(
            "Piety duties", checked_by=(), used_by=("catalog.life_traits.OFFICE_DUTY_TRAITS", "engine.mythic.offices.PIETY_DUTIES")
        ),
        OfficeDutyTrait.UNREST_DUTIES: Defined(
            "Unrest duties", checked_by=(), used_by=("catalog.life_traits.OFFICE_DUTY_TRAITS", "engine.mythic.offices.UNREST_DUTIES")
        ),
    },
)

OFFICE_KIND_TRAIT = total(
    OfficeKindTrait,
    {
        OfficeKindTrait.COUNCIL: Defined(
            "Council",
            checked_by=(),
            used_by=("catalog.life_traits.OFFICE_KIND_TRAITS", "engine.polity.enactment.COUNCIL", "engine.polity.governance.COUNCIL_OFFICES"),
        ),
        OfficeKindTrait.KEPT_OFFICES: Defined(
            "Kept offices", checked_by=(), used_by=("catalog.life_traits.OFFICE_KIND_TRAITS", "engine.military.mole_hunts.KEPT_OFFICES")
        ),
        OfficeKindTrait.MANY_SEATS: Defined(
            "Many seats", checked_by=(), used_by=("catalog.life_traits.OFFICE_KIND_TRAITS", "engine.polity.offices.MANY_SEATS")
        ),
        OfficeKindTrait.SEATS_KEPT: Defined(
            "Seats kept",
            checked_by=(),
            used_by=("catalog.life_traits.OFFICE_KIND_TRAITS", "engine.polity.offices.KEPT_OFFICES", "engine.regime.patronage.SEATS_KEPT"),
        ),
    },
)

ORDER_KIND_TRAIT = total(
    OrderKindTrait,
    {
        OrderKindTrait.TARGETED_ORDERS: Defined(
            "Targeted orders", checked_by=(), used_by=("catalog.life_traits.ORDER_KIND_TRAITS", "services.integrity.invariants.TARGETED_ORDERS")
        ),
        OrderKindTrait.WEAPON_ORDERS: Defined(
            "Weapon orders", checked_by=(), used_by=("catalog.life_traits.ORDER_KIND_TRAITS", "engine.minds.war_methods.WEAPON_ORDERS")
        ),
    },
)

PACKAGE_KIND_TRAIT = total(
    PackageKindTrait,
    {
        PackageKindTrait.BEAST_CURSES: Defined(
            "Beast curses", checked_by=(), used_by=("catalog.life_traits.PACKAGE_KIND_TRAITS", "engine.transform.beings.BEAST_CURSES")
        ),
    },
)

PASSION_KIND_TRAIT = total(
    PassionKindTrait,
    {
        PassionKindTrait.TENDER: Defined("Tender", checked_by=(), used_by=("catalog.life_traits.PASSION_KIND_TRAITS", "engine.relations.passions.TENDER")),
    },
)

POPULATION_INSTRUMENT_TRAIT = total(
    PopulationInstrumentTrait,
    {
        PopulationInstrumentTrait.HARSH: Defined(
            "Harsh", checked_by=(), used_by=("catalog.life_traits.POPULATION_INSTRUMENT_TRAITS", "engine.numbers.policies.HARSH")
        ),
        PopulationInstrumentTrait.PULLS: Defined(
            "Pulls", checked_by=(), used_by=("catalog.life_traits.POPULATION_INSTRUMENT_TRAITS", "engine.numbers.policies.PULLS")
        ),
    },
)

POWER_ORIGIN_TRAIT = total(
    PowerOriginTrait,
    {
        PowerOriginTrait.BORN_ORIGINS: Defined(
            "Born origins", checked_by=(), used_by=("catalog.life_traits.POWER_ORIGIN_TRAITS", "engine.powers.society.BORN_ORIGINS")
        ),
        PowerOriginTrait.GIFTED_ORIGINS: Defined(
            "Gifted origins", checked_by=(), used_by=("catalog.life_traits.POWER_ORIGIN_TRAITS", "engine.powers.kinds.GIFTED_ORIGINS")
        ),
    },
)

POWER_STATE_TRAIT = total(
    PowerStateTrait,
    {
        PowerStateTrait.QUIET: Defined("Quiet", checked_by=(), used_by=("catalog.life_traits.POWER_STATE_TRAITS", "engine.powers.phase.QUIET")),
        PowerStateTrait.USABLE: Defined(
            "Usable", checked_by=(), used_by=("catalog.life_traits.POWER_STATE_TRAITS", "engine.couplings.deep.USABLE_POWERS", "engine.powers.use.USABLE")
        ),
    },
)

PREPAREDNESS_KIND_TRAIT = total(
    PreparednessKindTrait,
    {
        PreparednessKindTrait.FIRE_SHIELDS: Defined(
            "Fire shields", checked_by=(), used_by=("catalog.life_traits.PREPAREDNESS_KIND_TRAITS", "engine.agrarian.book.FIRE_SHIELDS")
        ),
    },
)

PUNISHMENT_KIND_TRAIT = total(
    PunishmentKindTrait,
    {
        PunishmentKindTrait.MIND_PUNISHMENTS: Defined(
            "Mind punishments", checked_by=(), used_by=("catalog.life_traits.PUNISHMENT_KIND_TRAITS", "engine.minds.sentences.MIND_PUNISHMENTS")
        ),
    },
)

REBUILD_CAUSE_TRAIT = total(
    RebuildCauseTrait,
    {
        RebuildCauseTrait.SEIZING: Defined(
            "Seizing", checked_by=(), used_by=("catalog.life_traits.REBUILD_CAUSE_TRAITS", "engine.agrarian.resilience.SEIZING")
        ),
    },
)

RECORD_FORM_TRAIT = total(
    RecordFormTrait,
    {
        RecordFormTrait.RECORDED_FORMS: Defined(
            "Recorded forms", checked_by=(), used_by=("catalog.life_traits.RECORD_FORM_TRAITS", "engine.media.press.RECORDED_FORMS")
        ),
    },
)

REGIONAL_STANDING_TRAIT = total(
    RegionalStandingTrait,
    {
        RegionalStandingTrait.GREAT: Defined("Great", checked_by=(), used_by=("catalog.life_traits.REGIONAL_STANDING_TRAITS", "engine.polity.crises.GREAT")),
    },
)

RELATION_TYPE_TRAIT = total(
    RelationTypeTrait,
    {
        RelationTypeTrait.FRIENDLY: Defined("Friendly", checked_by=(), used_by=("catalog.life_traits.RELATION_TYPE_TRAITS", "engine.relations.book.FRIENDLY")),
    },
)

RIGHT_KIND_TRAIT = total(
    RightKindTrait,
    {
        RightKindTrait.COPIED: Defined("Copied", checked_by=(), used_by=("catalog.life_traits.RIGHT_KIND_TRAITS", "engine.crafts.rights.COPIED")),
        RightKindTrait.PORTION: Defined("Portion", checked_by=(), used_by=("catalog.life_traits.RIGHT_KIND_TRAITS", "engine.crafts.rights.PORTIONS")),
    },
)

RUMOUR_DISTORTION_TRAIT = total(
    RumourDistortionTrait,
    {
        RumourDistortionTrait.STEP_KINDS: Defined(
            "Step kinds", checked_by=(), used_by=("catalog.life_traits.RUMOUR_DISTORTION_TRAITS", "tools.son.events.STEP_KINDS")
        ),
        RumourDistortionTrait.SWAPS: Defined("Swaps", checked_by=(), used_by=("catalog.life_traits.RUMOUR_DISTORTION_TRAITS", "tools.son.events.SWAPS")),
    },
)

SETTLE_MODE_TRAIT = total(
    SettleModeTrait,
    {
        SettleModeTrait.UPKEPT: Defined("Upkept", checked_by=(), used_by=("catalog.life_traits.SETTLE_MODE_TRAITS", "engine.cosmos.world_views.UPKEPT")),
    },
)

SIZE_CLASS_TRAIT = total(
    SizeClassTrait,
    {
        SizeClassTrait.DRAUGHT: Defined("Draught", checked_by=(), used_by=("catalog.life_traits.SIZE_CLASS_TRAITS", "engine.ecology.profiles.DRAUGHT")),
        SizeClassTrait.GREAT: Defined("Great", checked_by=(), used_by=("catalog.life_traits.SIZE_CLASS_TRAITS", "engine.ecology.profiles.GREAT")),
        SizeClassTrait.KEPT_SIZES: Defined(
            "Kept sizes", checked_by=(), used_by=("catalog.life_traits.SIZE_CLASS_TRAITS", "engine.ecology.profiles.KEPT_SIZES")
        ),
        SizeClassTrait.RIDEABLE: Defined(
            "Rideable", checked_by=(), used_by=("catalog.life_traits.SIZE_CLASS_TRAITS", "engine.ecology.beasts.RIDEABLE", "engine.genetics.pools.LARGE")
        ),
        SizeClassTrait.SHELLED: Defined("Shelled", checked_by=(), used_by=("catalog.life_traits.SIZE_CLASS_TRAITS", "engine.ecology.profiles.SHELLED")),
        SizeClassTrait.SLEEPERS: Defined("Sleepers", checked_by=(), used_by=("catalog.life_traits.SIZE_CLASS_TRAITS", "engine.ecology.profiles.SLEEPERS")),
    },
)

SKILL_KIND_TRAIT = total(
    SkillKindTrait,
    {
        SkillKindTrait.HUNT_SKILLS: Defined(
            "Hunt skills", checked_by=(), used_by=("catalog.life_traits.SKILL_KIND_TRAITS", "engine.mind.aspirations.HUNT_SKILLS")
        ),
        SkillKindTrait.INTRIGUE_SKILLS: Defined(
            "Intrigue skills", checked_by=(), used_by=("catalog.life_traits.SKILL_KIND_TRAITS", "engine.mind.aspirations.INTRIGUE_SKILLS")
        ),
        SkillKindTrait.NEEDS_TRAVEL_SKILLS: Defined(
            "Needs travel skills", checked_by=(), used_by=("catalog.life_traits.SKILL_KIND_TRAITS", "engine.mind.needs.TRAVEL_SKILLS")
        ),
        SkillKindTrait.TRAVEL_SKILLS: Defined(
            "Travel skills", checked_by=(), used_by=("catalog.life_traits.SKILL_KIND_TRAITS", "engine.mind.aspirations.TRAVEL_SKILLS")
        ),
    },
)

SOURCE_LOCUS_TRAIT = total(
    SourceLocusTrait,
    {
        SourceLocusTrait.LAND_LOCI: Defined("Land loci", checked_by=(), used_by=("catalog.life_traits.SOURCE_LOCUS_TRAITS", "engine.powers.sources.LAND_LOCI")),
    },
)

SPECIES_CLASS_TRAIT = total(
    SpeciesClassTrait,
    {
        SpeciesClassTrait.PLANT_CLASSES: Defined(
            "Plant classes", checked_by=(), used_by=("catalog.life_traits.SPECIES_CLASS_TRAITS", "engine.plants.bodies.PLANT_CLASSES")
        ),
        SpeciesClassTrait.ROAMING: Defined(
            "Roaming", checked_by=(), used_by=("catalog.life_traits.SPECIES_CLASS_TRAITS", "engine.folk_knowledge.truth.ROAMING")
        ),
    },
)

SPEECH_VENUE_TRAIT = total(
    SpeechVenueTrait,
    {
        SpeechVenueTrait.CROWD_VENUES: Defined(
            "Crowd venues", checked_by=(), used_by=("catalog.life_traits.SPEECH_VENUE_TRAITS", "engine.speech.oratory.CROWD_VENUES")
        ),
    },
)

SPELL_FORM_TRAIT = total(
    SpellFormTrait,
    {
        SpellFormTrait.BREACHING: Defined("Breaching", checked_by=(), used_by=("catalog.life_traits.SPELL_FORM_TRAITS", "engine.powers.war.BREACHING")),
    },
)

SPELL_TECHNIQUE_TRAIT = total(
    SpellTechniqueTrait,
    {
        SpellTechniqueTrait.HARMING: Defined(
            "Harming", checked_by=(), used_by=("catalog.life_traits.SPELL_TECHNIQUE_TRAITS", "engine.minds.war_methods.HARMING")
        ),
    },
)

STANCE_TRAIT = total(
    StanceTrait,
    {
        StanceTrait.LAYING: Defined("Laying", checked_by=(), used_by=("catalog.life_traits.STANCE_TRAITS", "engine.military.engineering.LAYING")),
        StanceTrait.PATROLS: Defined("Patrols", checked_by=(), used_by=("catalog.life_traits.STANCE_TRAITS", "engine.economy.route_dangers.PATROLS")),
    },
)

STARVATION_STAGE_TRAIT = total(
    StarvationStageTrait,
    {
        StarvationStageTrait.HUNGRY: Defined("Hungry", checked_by=(), used_by=("catalog.life_traits.STARVATION_STAGE_TRAITS", "engine.phases.warfare.HUNGRY")),
    },
)

STRUCTURE_SECTION_TRAIT = total(
    StructureSectionTrait,
    {
        StructureSectionTrait.BREACHED_DECKS: Defined(
            "Breached decks", checked_by=(), used_by=("catalog.life_traits.STRUCTURE_SECTION_TRAITS", "engine.structures.damage.BREACHED_DECKS")
        ),
        StructureSectionTrait.BREACHES: Defined(
            "Breaches", checked_by=(), used_by=("catalog.life_traits.STRUCTURE_SECTION_TRAITS", "engine.structures.damage.BREACHES")
        ),
        StructureSectionTrait.TALL: Defined(
            "Tall", checked_by=(), used_by=("catalog.life_traits.STRUCTURE_SECTION_TRAITS", "engine.structures.integrity.TALL")
        ),
    },
)

TACTIC_TRAIT = total(
    TacticTrait,
    {
        TacticTrait.GUNS_TACTICS: Defined("Guns tactics", checked_by=(), used_by=("catalog.life_traits.TACTIC_TRAITS", "engine.military.clash.GUNS_TACTICS")),
        TacticTrait.HIDDEN_TACTICS: Defined(
            "Hidden tactics", checked_by=(), used_by=("catalog.life_traits.TACTIC_TRAITS", "engine.military.clash.HIDDEN_TACTICS")
        ),
        TacticTrait.LINE_TACTICS: Defined("Line tactics", checked_by=(), used_by=("catalog.life_traits.TACTIC_TRAITS", "engine.military.clash.LINE_TACTICS")),
        TacticTrait.SKIRMISH_TACTICS: Defined(
            "Skirmish tactics", checked_by=(), used_by=("catalog.life_traits.TACTIC_TRAITS", "engine.military.clash.SKIRMISH_TACTICS")
        ),
        TacticTrait.STRIKE_TACTICS: Defined(
            "Strike tactics", checked_by=(), used_by=("catalog.life_traits.TACTIC_TRAITS", "engine.military.battle.STRIKE_TACTICS")
        ),
    },
)

TAX_KIND_TRAIT = total(
    TaxKindTrait,
    {
        TaxKindTrait.HEAD_TAXES: Defined("Head taxes", checked_by=(), used_by=("catalog.life_traits.TAX_KIND_TRAITS", "engine.polity.revenue.HEAD_TAXES")),
        TaxKindTrait.SHARE_TAXES: Defined("Share taxes", checked_by=(), used_by=("catalog.life_traits.TAX_KIND_TRAITS", "engine.polity.revenue.SHARE_TAXES")),
    },
)

TECHNIQUE_TRAIT = total(
    TechniqueTrait,
    {
        TechniqueTrait.ENGINEERING: Defined(
            "Engineering", checked_by=(), used_by=("catalog.life_traits.TECHNIQUE_TRAITS", "engine.phases.factions.ENGINEERING")
        ),
        TechniqueTrait.TOOL_METALS: Defined(
            "Tool metals", checked_by=(), used_by=("catalog.life_traits.TECHNIQUE_TRAITS", "engine.environment.columns.TOOL_TECHNIQUES")
        ),
        TechniqueTrait.FINANCE: Defined("Finance", checked_by=(), used_by=("catalog.life_traits.TECHNIQUE_TRAITS", "engine.phases.factions.FINANCE")),
        TechniqueTrait.PLACE_VALUE_RECKONING: Defined(
            "Place value reckoning", checked_by=(), used_by=("catalog.life_traits.TECHNIQUE_TRAITS", "engine.crafts.numbers.PLACE_VALUE_RECKONING")
        ),
    },
)

THOUGHT_KIND_TRAIT = total(
    ThoughtKindTrait,
    {
        ThoughtKindTrait.SHAME_KINDS: Defined(
            "Shame kinds", checked_by=(), used_by=("catalog.life_traits.THOUGHT_KIND_TRAITS", "engine.mind.ethics.SHAME_KINDS")
        ),
    },
)

TRADE_MODE_TRAIT = total(
    TradeModeTrait,
    {
        TradeModeTrait.ICE_MODES: Defined(
            "Ice modes", checked_by=(), used_by=("catalog.life_traits.TRADE_MODE_TRAITS", "engine.economy.route_dangers.ICE_MODES")
        ),
        TradeModeTrait.LAND_MODES: Defined(
            "Land modes",
            checked_by=(),
            used_by=("catalog.life_traits.TRADE_MODE_TRAITS", "engine.economy.cargo.LAND_MODES", "engine.vehicles.production.LAND_MODES"),
        ),
        TradeModeTrait.WATER_MODES: Defined(
            "Water modes", checked_by=(), used_by=("catalog.life_traits.TRADE_MODE_TRAITS", "engine.economy.cargo.WATER_MODES", "engine.water.ice.WATER_MODES")
        ),
    },
)

TRADE_POLICY_KIND_TRAIT = total(
    TradePolicyKindTrait,
    {
        TradePolicyKindTrait.BARRING: Defined(
            "Barring", checked_by=(), used_by=("catalog.life_traits.TRADE_POLICY_KIND_TRAITS", "engine.finance.policy.BARRING")
        ),
    },
)

TRADE_ROUTE_STATUS_TRAIT = total(
    TradeRouteStatusTrait,
    {
        TradeRouteStatusTrait.LIVE_STATUSES: Defined(
            "Live statuses", checked_by=(), used_by=("catalog.life_traits.TRADE_ROUTE_STATUS_TRAITS", "engine.economy.routes.LIVE_STATUSES")
        ),
        TradeRouteStatusTrait.CARRYING: Defined(
            "Carrying", checked_by=("catalog.life_traits.CARRYING_ROUTES",), used_by=("catalog.life_traits.TRADE_ROUTE_STATUS_TRAITS",)
        ),
    },
)

TREATY_KIND_TRAIT = total(
    TreatyKindTrait,
    {
        TreatyKindTrait.ALLIANCES: Defined(
            "Alliances",
            checked_by=(),
            used_by=("catalog.life_traits.TREATY_KIND_TRAITS", "engine.phases.diplomacy.ALLIANCES", "engine.polity.mediation.ALLIANCE_KINDS"),
        ),
        TreatyKindTrait.DEFENSIVE: Defined("Defensive", checked_by=(), used_by=("catalog.life_traits.TREATY_KIND_TRAITS", "engine.polity.treaties.DEFENSIVE")),
        TreatyKindTrait.KEPT_KINDS: Defined("Kept kinds", checked_by=(), used_by=("catalog.life_traits.TREATY_KIND_TRAITS", "engine.polity.regard.KEPT_KINDS")),
        TreatyKindTrait.MUTUAL: Defined("Mutual", checked_by=(), used_by=("catalog.life_traits.TREATY_KIND_TRAITS", "engine.polity.accords.MUTUAL")),
        TreatyKindTrait.OFFENSIVE: Defined("Offensive", checked_by=(), used_by=("catalog.life_traits.TREATY_KIND_TRAITS", "engine.polity.treaties.OFFENSIVE")),
    },
)

UNIT_HONOUR_KIND_TRAIT = total(
    UnitHonourKindTrait,
    {
        UnitHonourKindTrait.GLORIOUS: Defined(
            "Glorious", checked_by=(), used_by=("catalog.life_traits.UNIT_HONOUR_KIND_TRAITS", "engine.honours.units.GLORIOUS")
        ),
    },
)

VEHICLE_FAMILY_TRAIT = total(
    VehicleFamilyTrait,
    {
        VehicleFamilyTrait.SIEGE: Defined("Siege", checked_by=(), used_by=("catalog.life_traits.VEHICLE_FAMILY_TRAITS", "engine.vehicles.fleet.SIEGE")),
    },
)

WAR_CAUSE_TRAIT = total(
    WarCauseTrait,
    {
        WarCauseTrait.CASUS_BELLI_REVOLT_CAUSES: Defined(
            "Casus belli revolt causes", checked_by=(), used_by=("catalog.life_traits.WAR_CAUSE_TRAITS", "engine.services.casus_belli.REVOLT_CAUSES")
        ),
        WarCauseTrait.HOLY_CAUSES: Defined(
            "Holy causes", checked_by=(), used_by=("catalog.life_traits.WAR_CAUSE_TRAITS", "engine.factions.orders.HOLY_CAUSES")
        ),
    },
)

WAR_ENDING_TRAIT = total(
    WarEndingTrait,
    {
        WarEndingTrait.SIGNED_ENDINGS: Defined(
            "Signed endings",
            checked_by=(),
            used_by=("catalog.life_traits.WAR_ENDING_TRAITS", "engine.environment.notable.SIGNED_ENDINGS", "engine.services.war_resolution.SIGNED_ENDINGS"),
        ),
    },
)

WAR_TERRAIN_TRAIT = total(
    WarTerrainTrait,
    {
        WarTerrainTrait.LAND_UNFIT: Defined(
            "Land unfit", checked_by=(), used_by=("catalog.life_traits.WAR_TERRAIN_TRAITS", "engine.cosmos.world_views.LAND_UNFIT")
        ),
    },
)

WEATHER_EFFECT_TRAIT = total(
    WeatherEffectTrait,
    {
        WeatherEffectTrait.FALLING_EFFECTS: Defined(
            "Falling effects", checked_by=(), used_by=("catalog.life_traits.WEATHER_EFFECT_TRAITS", "engine.economy.route_dangers.FALLING_EFFECTS")
        ),
    },
)

WITNESS_MODE_TRAIT = total(
    WitnessModeTrait,
    {
        WitnessModeTrait.FIRST_HAND: Defined(
            "First hand", checked_by=(), used_by=("catalog.life_traits.WITNESS_MODE_TRAITS", "engine.lore.rumours.FIRST_HAND", "engine.lore.witnesses.PRESENT")
        ),
    },
)

WORKS_KIND_TRAIT = total(
    WorksKindTrait,
    {
        WorksKindTrait.ROUTE_WORKS: Defined(
            "Route works", checked_by=(), used_by=("catalog.life_traits.WORKS_KIND_TRAITS", "engine.works.building.ROUTE_WORKS")
        ),
    },
)

WORLD_END_TRAIT = total(
    WorldEndTrait,
    {
        WorldEndTrait.GONE_FROM_SKY: Defined(
            "Gone from sky", checked_by=(), used_by=("catalog.life_traits.WORLD_END_TRAITS", "engine.cosmos.world_ends.GONE_FROM_SKY")
        ),
        WorldEndTrait.LIFELESS: Defined("Lifeless", checked_by=(), used_by=("catalog.life_traits.WORLD_END_TRAITS", "engine.cosmos.world_ends.LIFELESS")),
    },
)

WORLD_TYPE_TRAIT = total(
    WorldTypeTrait,
    {
        WorldTypeTrait.BELTS: Defined("Belts", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.economy.extraction.BELTS")),
        WorldTypeTrait.BROKEN_WORLDS: Defined(
            "Broken worlds",
            checked_by=(),
            used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.physics_control.BROKEN_WORLDS", "engine.phases.physics.BROKEN"),
        ),
        WorldTypeTrait.BURIED_WORLDS: Defined(
            "Buried worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.lifeforms.BURIED_WORLDS")
        ),
        WorldTypeTrait.COLD_WORLDS: Defined(
            "Cold worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.ecology.fossils.COLD_WORLDS")
        ),
        WorldTypeTrait.DIVINE_WORLDS: Defined(
            "Divine worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.formation.DIVINE_WORLDS")
        ),
        WorldTypeTrait.GAS_WORLDS: Defined("Gas worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.orbits.GAS_WORLDS")),
        WorldTypeTrait.GIANTS: Defined("Giants", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.economy.extraction.GIANTS")),
        WorldTypeTrait.HARSH_WORLDS: Defined(
            "Harsh worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.lifeforms.HARSH_WORLDS")
        ),
        WorldTypeTrait.LIFELESS_WORLDS: Defined(
            "Lifeless worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.orbits.LIFELESS_WORLDS")
        ),
        WorldTypeTrait.SKYLESS_WORLDS: Defined(
            "Skyless worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.cosmos.orbits.SKYLESS_WORLDS")
        ),
        WorldTypeTrait.TWO_SEASON_WORLDS: Defined(
            "Two season worlds", checked_by=(), used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.environment.seasons.TWO_SEASON_WORLDS")
        ),
        WorldTypeTrait.VOLCANIC_WORLDS: Defined(
            "Volcanic worlds",
            checked_by=(),
            used_by=("catalog.life_traits.WORLD_TYPE_TRAITS", "engine.environment.geology.MOLTEN_WORLDS", "engine.environment.geomorph.VOLCANIC_WORLDS"),
        ),
    },
)

YOUTH_PURPOSE_TRAIT = total(
    YouthPurposeTrait,
    {
        YouthPurposeTrait.DELINQUENT: Defined(
            "Delinquent", checked_by=(), used_by=("catalog.life_traits.YOUTH_PURPOSE_TRAITS", "engine.youth.groups.DELINQUENT")
        ),
        YouthPurposeTrait.UNRULY: Defined("Unruly", checked_by=(), used_by=("catalog.life_traits.YOUTH_PURPOSE_TRAITS", "engine.youth.groups.UNRULY")),
    },
)
