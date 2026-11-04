from enum import StrEnum


class UnitFamily(StrEnum):
    INFANTRY = "infantry"
    MISSILE = "missile"
    MOUNTED = "mounted"
    BEAST = "beast"
    ENGINEER = "engineer"
    MAGIC = "magic"
    NAVAL = "naval"
    EXOTIC = "exotic"


class UnitKind(StrEnum):
    LEVY = "levy"
    SPEARMEN = "spearmen"
    HEAVY_INFANTRY = "heavy_infantry"
    SHIELD_WALL = "shield_wall"
    PIKEMEN = "pikemen"
    SKIRMISHERS = "skirmishers"
    BERSERKERS = "berserkers"
    TEMPLE_GUARD = "temple_guard"
    SLINGERS = "slingers"
    ARCHERS = "archers"
    CROSSBOWMEN = "crossbowmen"
    HORSE_ARCHERS = "horse_archers"
    JAVELINEERS = "javelineers"
    LIGHT_CAVALRY = "light_cavalry"
    HEAVY_CAVALRY = "heavy_cavalry"
    BEAST_RIDERS = "beast_riders"
    CHARIOTS = "chariots"
    WAR_BEASTS = "war_beasts"
    BOUND_BEASTS = "bound_beasts"
    SKY_MOUNTS = "sky_mounts"
    SAPPERS = "sappers"
    SIEGE_ENGINES = "siege_engines"
    WAR_MAGES = "war_mages"
    PRIESTS = "priests"
    NECROMANCERS = "necromancers"
    GALLEYS = "galleys"
    LONGSHIPS = "longships"
    WARSHIPS = "warships"
    FIRE_SHIPS = "fire_ships"
    SKYSHIPS = "skyships"
    GOLEMS = "golems"
    VOID_SPAWN = "void_spawn"
    GHOST_HOST = "ghost_host"


class ArmourType(StrEnum):
    NONE = "none"
    HIDE = "hide"
    PADDED = "padded"
    MAIL = "mail"
    SCALE = "scale"
    PLATE = "plate"
    ENCHANTED = "enchanted"


class ShieldType(StrEnum):
    NONE = "none"
    SMALL = "small"
    LARGE = "large"
    TOWER = "tower"


class Stance(StrEnum):
    MARCH = "march"
    FORAGE = "forage"
    ENTRENCH = "entrench"
    BESIEGE = "besiege"
    GARRISON = "garrison"
    RAID = "raid"
    RETREAT = "retreat"


class Tactic(StrEnum):
    HOLD_LINE = "hold_line"
    FRONTAL_ASSAULT = "frontal_assault"
    DOUBLE_ENVELOPMENT = "double_envelopment"
    FEIGNED_RETREAT = "feigned_retreat"
    FLANK_CAVALRY = "flank_cavalry"
    MISSILE_ATTRITION = "missile_attrition"
    SHIELD_WALL = "shield_wall"
    WEDGE = "wedge"
    NIGHT_RAID = "night_raid"
    AMBUSH = "ambush"
    SKIRMISH_HARASS = "skirmish_harass"
    RIVER_DEFENCE = "river_defence"
    SIEGE_ASSAULT = "siege_assault"


class BattlePhase(StrEnum):
    SCOUTING = "scouting"
    PLAN = "plan"
    MISSILE = "missile"
    CHARGE = "charge"
    MELEE = "melee"
    RITES = "rites"
    PURSUIT = "pursuit"
    AFTERMATH = "aftermath"


class OutcomeClass(StrEnum):
    DECISIVE = "decisive"
    VICTORY = "victory"
    PYRRHIC = "pyrrhic"
    STALEMATE = "stalemate"
    ROUT = "rout"
    MASSACRE = "massacre"
    REFUSED = "refused"


class CommanderTrait(StrEnum):
    AGGRESSIVE_ASSAULTER = "aggressive_assaulter"
    DEFENSIVE_GENIUS = "defensive_genius"
    CAVALRY_MASTER = "cavalry_master"
    WINTER_CAMPAIGNER = "winter_campaigner"
    HILL_FIGHTER = "hill_fighter"
    SIEGE_EXPERT = "siege_expert"
    RECKLESS = "reckless"
    CAUTIOUS = "cautious"
    INSPIRING = "inspiring"
    BRUTAL = "brutal"


class SiegeAction(StrEnum):
    BLOCKADE = "blockade"
    BOMBARD = "bombard"
    MINE = "mine"
    ASSAULT = "assault"
    NEGOTIATE = "negotiate"


class DefenderAction(StrEnum):
    SALLY = "sally"
    REPAIR = "repair"
    RATION = "ration"
    SEEK_RELIEF = "seek_relief"


class StarvationStage(StrEnum):
    NONE = "none"
    RATIONING = "rationing"
    FAMINE = "famine"
    TABOO_BROKEN = "taboo_broken"


class WarAimKind(StrEnum):
    CONQUER_REGION = "conquer_region"
    SEIZE_SETTLEMENT = "seize_settlement"
    PRESS_CLAIM = "press_claim"
    CONVERT = "convert"
    TRIBUTE = "tribute"
    VASSALISE = "vassalise"
    LIBERATE = "liberate"
    DESTROY_CULT = "destroy_cult"
    SEIZE_RESOURCE = "seize_resource"
    SEIZE_NEXUS = "seize_nexus"
    HUMILIATE = "humiliate"
    REVENGE = "revenge"
    LOOT = "loot"
    CHANGE_GOVERNMENT = "change_government"


class CaptiveFate(StrEnum):
    HELD = "held"
    RANSOMED = "ransomed"
    ENSLAVED = "enslaved"
    SACRIFICED = "sacrificed"
    LABOUR = "labour"
    EXCHANGED = "exchanged"
    RELEASED = "released"


class DuelContext(StrEnum):
    WAR = "war"
    HONOUR = "honour"
    TRIAL = "trial"
    CHAMPION = "champion"
    GOD = "god"


class DuelEnd(StrEnum):
    YIELD = "yield"
    DISARM = "disarm"
    CRIPPLED = "crippled"
    DEATH = "death"
    EXHAUSTION = "exhaustion"


class SpyOperation(StrEnum):
    STEAL_KNOWLEDGE = "steal_knowledge"
    SABOTAGE = "sabotage"
    ASSASSINATE = "assassinate"
    INCITE = "incite"
    INTEL = "intel"
    BLACKMAIL = "blackmail"
    COUNTERFEIT = "counterfeit"


class SabotageKind(StrEnum):
    GRANARY_FIRE = "granary_fire"
    WALL_WEAKENING = "wall_weakening"
    POISON_WELLS = "poison_wells"
    ARSON = "arson"


class SpyCover(StrEnum):
    MERCHANT = "merchant"
    PRIEST = "priest"
    ENVOY = "envoy"
    BEGGAR = "beggar"


class FeudAction(StrEnum):
    RAID = "raid"
    ASSASSINATE = "assassinate"
    DEMAND_WERGILD = "demand_wergild"
    ESCALATE = "escalate"
    REST = "rest"


class ArmyRole(StrEnum):
    COMMANDER = "commander"
    SUB_COMMANDER = "sub_commander"
    QUARTERMASTER = "quartermaster"
    STANDARD_BEARER = "standard_bearer"
    SURGEON = "surgeon"


class ContractStatus(StrEnum):
    ACTIVE = "active"
    UNPAID = "unpaid"
    TURNED = "turned"
    ENDED = "ended"


class SackChoice(StrEnum):
    MERCY = "mercy"
    SACK = "sack"
    RAZE = "raze"


class SiegeWork(StrEnum):
    CIRCUMVALLATION = "circumvallation"
    TOWERS = "towers"
    RAMS = "rams"
    MINES = "mines"
    COUNTERMINES = "countermines"
    LADDERS = "ladders"


class PeaceTermKind(StrEnum):
    CESSION = "cession"
    VASSALAGE = "vassalage"
    HOSTAGE = "hostage"
    REPARATIONS = "reparations"
    TRIBUTE = "tribute"
    LIBERTY = "liberty"
    THRONE = "throne"
    BREAK_CULT = "break_cult"
    OPEN_TEMPLES = "open_temples"
    GOVERNMENT = "government"
    MARRIAGE = "marriage"
    DEMILITARISED = "demilitarised"
    TRADE_CONCESSION = "trade_concession"
    CAPTIVE_RELEASE = "captive_release"
    CHAMPION = "champion"
    WHITE_PEACE = "white_peace"


class CasualtyFate(StrEnum):
    KILLED = "killed"
    WOUNDED = "wounded"
    MAIMED = "maimed"
    CAPTURED = "captured"


class SpyOwnerKind(StrEnum):
    POLITY = "polity"
    FACTION = "faction"
    CULT = "cult"
    COMMUNITY = "community"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    CAUGHT = "caught"
    TURNED = "turned"
    DEAD = "dead"
    RETIRED = "retired"


class FeudParty(StrEnum):
    HOUSE = "house"
    COMMUNITY = "community"


class FeudStatus(StrEnum):
    ACTIVE = "active"
    MEDIATED = "mediated"
    FADED = "faded"
    ENDED = "ended"


class MutinyOutcome(StrEnum):
    GRUMBLING = "grumbling"
    REFUSAL = "refusal"
    DEPOSED = "deposed"
    BANDITRY = "banditry"
    TURNCOAT = "turncoat"


class HullClass(StrEnum):
    RAFT = "raft"
    BOAT = "boat"
    GALLEY = "galley"
    LONGSHIP = "longship"
    COG = "cog"
    CARRACK = "carrack"
    WARSHIP = "warship"
    LIGHT_SAILER = "light_sailer"
    BONE_HULL = "bone_hull"
    GENERATION_SHIP = "generation_ship"
    SKYSHIP = "skyship"
    LIVING_SHIP = "living_ship"


class VesselArmament(StrEnum):
    RAMS = "rams"
    MISSILES = "missiles"
    SIEGE_ENGINES = "siege_engines"
    RITES = "rites"


class VesselStatus(StrEnum):
    DOCKED = "docked"
    AFLOAT = "afloat"
    DAMAGED = "damaged"
    WRECKED = "wrecked"
    GHOST = "ghost"
