from enum import StrEnum


class ActKindTrait(StrEnum):
    FAMINE_ACTS = "famine_acts"
    FEARSOME = "fearsome"
    WAR_ACTS = "war_acts"


class AgeGradeTrait(StrEnum):
    UNWED_GRADES = "unwed_grades"


class AllocationModeTrait(StrEnum):
    CENTRES = "centres"
    SHARING = "sharing"
    STATE_BUYERS = "state_buyers"


class AssistiveAidTrait(StrEnum):
    GROUND_LENS = "ground_lens"


class AttackRangeTrait(StrEnum):
    WHOLE_TOWN = "whole_town"


class BiologyVariantTrait(StrEnum):
    SKYLESS = "skyless"


class BodySystemTrait(StrEnum):
    BLOODLESS = "bloodless"


class BreachCauseTrait(StrEnum):
    ACCORD_BREAKING = "accord_breaking"


class BuildingFormTrait(StrEnum):
    FIXED_FORMS = "fixed_forms"


class CaptiveFateTrait(StrEnum):
    BOUND = "bound"


class CaptiveStatusTrait(StrEnum):
    FREEING_STATUSES = "freeing_statuses"
    RESCUE_STATUSES = "rescue_statuses"
    AFTER_CAPTIVITY = "after_captivity"


class CharmPowerTrait(StrEnum):
    WARDS = "wards"


class ClauseKindTrait(StrEnum):
    METHOD_CLAUSES = "method_clauses"
    PEACEFUL = "peaceful"


class CommandTokenTrait(StrEnum):
    OWNED_TOKENS = "owned_tokens"


class CommanderTraitTrait(StrEnum):
    AGGRESSIVE = "aggressive"
    CAREFUL = "careful"
    CLASH_AGGRESSIVE = "clash_aggressive"
    DECAPITATORS = "decapitators"


class ConstructionStateTrait(StrEnum):
    COUNTED_STATES = "counted_states"


class ContestStakeTrait(StrEnum):
    NOTED = "noted"


class CoopPurposeTrait(StrEnum):
    POOLING = "pooling"
    RELIEVING = "relieving"
    WORKING = "working"


class CouncilMotionTrait(StrEnum):
    ORDER_LASTING = "order_lasting"


class CultivationMethodTrait(StrEnum):
    RITE_PATHS = "rite_paths"


class DeathRoleTrait(StrEnum):
    HANDLING = "handling"
    SACRED = "sacred"
    TENDING = "tending"


class DuelContextTrait(StrEnum):
    DUEL_CONTEXTS = "duel_contexts"
    CUSTOMARY = "customary"
    AT_WAR = "at_war"


class EmotionTrait(StrEnum):
    AFRAID = "afraid"
    ANGRY = "angry"
    STIRRED = "stirred"
    GRIEVING = "grieving"
    HOPEFUL = "hopeful"


class ExpeditionGroundTrait(StrEnum):
    DARK_GROUNDS = "dark_grounds"


class ExtractionKindTrait(StrEnum):
    ARTISAN_KINDS = "artisan_kinds"
    TAKES_FROM_RUINS = "takes_from_ruins"


class FactionActionKindTrait(StrEnum):
    DEFIANT = "defiant"


class FactionKindTrait(StrEnum):
    BODY_KINDS = "body_kinds"
    GANGS = "gangs"
    GUILDS = "guilds"
    HERALDRY_GUILDS = "heraldry_guilds"
    MOVEMENTS = "movements"
    ORDERS = "orders"
    TRADES = "trades"
    TREASON_KINDS = "treason_kinds"
    UNDERWRITES = "underwrites"
    WARLIKE = "warlike"


class FurnishingCategoryTrait(StrEnum):
    FURNISHING_FIRE = "furnishing_fire"


class GatheringKindTrait(StrEnum):
    ENGINE_KINDS = "engine_kinds"
    POTLATCH_FEASTS = "potlatch_feasts"
    RULER_KINDS = "ruler_kinds"
    SON_KINDS = "son_kinds"


class GiftStateTrait(StrEnum):
    OBLIGING = "obliging"


class GroupKindTrait(StrEnum):
    LEADING = "leading"


class HazardKindTrait(StrEnum):
    WORKS_HAZARDS = "works_hazards"


class HiddenTruthKindTrait(StrEnum):
    GIFTED_TRUTHS = "gifted_truths"


class HouseDutyTrait(StrEnum):
    CARE_DUTIES = "care_duties"
    SERVED_DUTIES = "served_duties"


class IdentityLayerTrait(StrEnum):
    GROUP_LAYERS = "group_layers"


class InheritanceCustomTrait(StrEnum):
    DISCRETION = "discretion"


class InteractionKindTrait(StrEnum):
    FRIENDLY_TALK = "friendly_talk"
    TALK_FREE = "talk_free"


class IntoxicantTrait(StrEnum):
    DRINKS = "drinks"
    STIMULATES = "stimulates"


class JobTrait(StrEnum):
    BOUND_JOBS = "bound_jobs"
    MADE_MIND_TRADES = "made_mind_trades"


class JourneyIntentTrait(StrEnum):
    CROWD_INTENTS = "crowd_intents"
    PASSENGER_INTENTS = "passenger_intents"
    SURVEYING = "surveying"


class KnowledgeBranchTrait(StrEnum):
    CRAFT_BRANCHES = "craft_branches"
    EXPLORATION_BRANCHES = "exploration_branches"
    KNOWLEDGE_FOR_EXPLORING = "knowledge_for_exploring"
    NATURAL_BRANCHES = "natural_branches"
    RECKONED = "reckoned"
    ROAD_BRANCHES = "road_branches"


class LandActTrait(StrEnum):
    FEARED = "feared"
    LIFTS = "lifts"
    SOIL_ACTS = "soil_acts"
    WELCOMED = "welcomed"


class LeisureKindTrait(StrEnum):
    TRAVEL_PURSUITS = "travel_pursuits"


class LifeStageTrait(StrEnum):
    CARED_FOR = "cared_for"
    DUTIES_YOUNG = "duties_young"
    GROWING = "growing"
    GROWN = "grown"
    OLD = "old"
    UNDER_AGE = "under_age"
    YOUNG = "young"


class LineTraitTrait(StrEnum):
    SHAPING_TRAITS = "shaping_traits"
    SPREADING = "spreading"


class MadeMindStanceTrait(StrEnum):
    KEEPING_STANCES = "keeping_stances"


class MediumTrait(StrEnum):
    INSTANT = "instant"
    OPEN_MEDIA = "open_media"
    OVERLAND = "overland"


class MemoryKindTrait(StrEnum):
    CARES = "cares"
    GRIEVANCES = "grievances"
    HARMS = "harms"
    TRAUMA_KINDS = "trauma_kinds"


class MetabolismTrait(StrEnum):
    SELF_FED = "self_fed"


class MindUpkeepTrait(StrEnum):
    REALMS_SELF_KEPT = "realms_self_kept"
    SELF_KEPT = "self_kept"


class MishapKindTrait(StrEnum):
    FRIGHTS = "frights"
    LOSSES = "losses"


class OathKindTrait(StrEnum):
    LOYAL_OATHS = "loyal_oaths"
    TIMED = "timed"


class ObservationMethodTrait(StrEnum):
    TRUSTED_BY_FAITH = "trusted_by_faith"


class OfficeDutyTrait(StrEnum):
    DUTY_TOWNS = "duty_towns"
    PIETY_DUTIES = "piety_duties"
    UNREST_DUTIES = "unrest_duties"


class OfficeKindTrait(StrEnum):
    COUNCIL = "council"
    KEPT_OFFICES = "kept_offices"
    MANY_SEATS = "many_seats"
    SEATS_KEPT = "seats_kept"


class OrderKindTrait(StrEnum):
    TARGETED_ORDERS = "targeted_orders"
    WEAPON_ORDERS = "weapon_orders"


class PackageKindTrait(StrEnum):
    BEAST_CURSES = "beast_curses"
    HIDDEN_BY_BEARER = "hidden_by_bearer"


class PassionKindTrait(StrEnum):
    TENDER = "tender"


class PopulationInstrumentTrait(StrEnum):
    HARSH = "harsh"
    PULLS = "pulls"


class PowerOriginTrait(StrEnum):
    BORN_ORIGINS = "born_origins"
    GIFTED_ORIGINS = "gifted_origins"


class PowerStateTrait(StrEnum):
    QUIET = "quiet"
    USABLE = "usable"


class PreparednessKindTrait(StrEnum):
    FIRE_SHIELDS = "fire_shields"


class PunishmentKindTrait(StrEnum):
    MIND_PUNISHMENTS = "mind_punishments"


class RebuildCauseTrait(StrEnum):
    SEIZING = "seizing"


class RecordFormTrait(StrEnum):
    RECORDED_FORMS = "recorded_forms"


class RegionalStandingTrait(StrEnum):
    GREAT = "great"


class RelationTypeTrait(StrEnum):
    FRIENDLY = "friendly"


class RightKindTrait(StrEnum):
    COPIED = "copied"
    PORTION = "portion"


class RumourDistortionTrait(StrEnum):
    STEP_KINDS = "step_kinds"
    SWAPS = "swaps"


class SettleModeTrait(StrEnum):
    UPKEPT = "upkept"


class SizeClassTrait(StrEnum):
    DRAUGHT = "draught"
    GREAT = "great"
    KEPT_SIZES = "kept_sizes"
    RIDEABLE = "rideable"
    SHELLED = "shelled"
    SLEEPERS = "sleepers"


class SkillKindTrait(StrEnum):
    HUNT_SKILLS = "hunt_skills"
    INTRIGUE_SKILLS = "intrigue_skills"
    NEEDS_TRAVEL_SKILLS = "needs_travel_skills"
    TRAVEL_SKILLS = "travel_skills"


class SourceLocusTrait(StrEnum):
    LAND_LOCI = "land_loci"


class SpeciesClassTrait(StrEnum):
    PLANT_CLASSES = "plant_classes"
    ROAMING = "roaming"


class SpeechVenueTrait(StrEnum):
    CROWD_VENUES = "crowd_venues"


class SpellFormTrait(StrEnum):
    BREACHING = "breaching"


class SpellTechniqueTrait(StrEnum):
    HARMING = "harming"


class StanceTrait(StrEnum):
    LAYING = "laying"
    PATROLS = "patrols"


class StarvationStageTrait(StrEnum):
    HUNGRY = "hungry"


class StructureSectionTrait(StrEnum):
    BREACHED_DECKS = "breached_decks"
    BREACHES = "breaches"
    TALL = "tall"


class TacticTrait(StrEnum):
    GUNS_TACTICS = "guns_tactics"
    HIDDEN_TACTICS = "hidden_tactics"
    LINE_TACTICS = "line_tactics"
    SKIRMISH_TACTICS = "skirmish_tactics"
    STRIKE_TACTICS = "strike_tactics"


class TaxKindTrait(StrEnum):
    HEAD_TAXES = "head_taxes"
    SHARE_TAXES = "share_taxes"


class TechniqueTrait(StrEnum):
    ENGINEERING = "engineering"
    TOOL_METALS = "tool_metals"
    FINANCE = "finance"
    PLACE_VALUE_RECKONING = "place_value_reckoning"


class ThoughtKindTrait(StrEnum):
    SHAME_KINDS = "shame_kinds"


class TradeModeTrait(StrEnum):
    ICE_MODES = "ice_modes"
    LAND_MODES = "land_modes"
    WATER_MODES = "water_modes"


class TradePolicyKindTrait(StrEnum):
    BARRING = "barring"


class TradeRouteStatusTrait(StrEnum):
    LIVE_STATUSES = "live_statuses"
    CARRYING = "carrying"


class TreatyKindTrait(StrEnum):
    ALLIANCES = "alliances"
    DEFENSIVE = "defensive"
    KEPT_KINDS = "kept_kinds"
    MUTUAL = "mutual"
    OFFENSIVE = "offensive"


class UnitHonourKindTrait(StrEnum):
    GLORIOUS = "glorious"


class VehicleFamilyTrait(StrEnum):
    SIEGE = "siege"


class WarCauseTrait(StrEnum):
    CASUS_BELLI_REVOLT_CAUSES = "casus_belli_revolt_causes"
    HOLY_CAUSES = "holy_causes"


class WarEndingTrait(StrEnum):
    SIGNED_ENDINGS = "signed_endings"


class WarTerrainTrait(StrEnum):
    LAND_UNFIT = "land_unfit"


class WeatherEffectTrait(StrEnum):
    FALLING_EFFECTS = "falling_effects"


class WitnessModeTrait(StrEnum):
    FIRST_HAND = "first_hand"


class WorksKindTrait(StrEnum):
    ROUTE_WORKS = "route_works"


class WorldEndTrait(StrEnum):
    GONE_FROM_SKY = "gone_from_sky"
    LIFELESS = "lifeless"


class WorldTypeTrait(StrEnum):
    BELTS = "belts"
    BROKEN_WORLDS = "broken_worlds"
    BURIED_WORLDS = "buried_worlds"
    COLD_WORLDS = "cold_worlds"
    DIVINE_WORLDS = "divine_worlds"
    GAS_WORLDS = "gas_worlds"
    GIANTS = "giants"
    HARSH_WORLDS = "harsh_worlds"
    LIFELESS_WORLDS = "lifeless_worlds"
    SKYLESS_WORLDS = "skyless_worlds"
    TWO_SEASON_WORLDS = "two_season_worlds"
    VOLCANIC_WORLDS = "volcanic_worlds"


class YouthPurposeTrait(StrEnum):
    DELINQUENT = "delinquent"
    UNRULY = "unruly"
