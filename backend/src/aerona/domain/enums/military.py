from enum import StrEnum


class UnitFamily(StrEnum):
    INFANTRY = "infantry"
    MISSILE = "missile"
    MOUNTED = "mounted"
    VEHICLE = "vehicle"
    BEAST = "beast"
    ENGINEER = "engineer"
    MAGIC = "magic"
    EXOTIC = "exotic"
    AIR = "air"
    SPACE = "space"
    ELECTRONIC = "electronic"
    SPECIAL = "special"


class UnitKind(StrEnum):
    LEVY = "levy"
    LINE_INFANTRY = "line_infantry"
    HEAVY_INFANTRY = "heavy_infantry"
    SHIELD_INFANTRY = "shield_infantry"
    PIKE_INFANTRY = "pike_infantry"
    LIGHT_INFANTRY = "light_infantry"
    SHOCK_INFANTRY = "shock_infantry"
    GUARD_INFANTRY = "guard_infantry"
    MARINES = "marines"
    SLINGERS = "slingers"
    ARCHERS = "archers"
    CROSSBOW_INFANTRY = "crossbow_infantry"
    JAVELINEERS = "javelineers"
    GUNNERS = "gunners"
    GRENADIERS = "grenadiers"
    LIGHT_CAVALRY = "light_cavalry"
    HEAVY_CAVALRY = "heavy_cavalry"
    MOUNTED_ARCHERS = "mounted_archers"
    MOUNTED_GUNNERS = "mounted_gunners"
    BEAST_RIDERS = "beast_riders"
    SKY_RIDERS = "sky_riders"
    CHARIOTS = "chariots"
    VEHICLE_CREW = "vehicle_crew"
    SIEGE_CREW = "siege_crew"
    ARTILLERY_CREW = "artillery_crew"
    NAVAL_CREW = "naval_crew"
    SKY_CREW = "sky_crew"
    VOID_CREW = "void_crew"
    WAR_BEASTS = "war_beasts"
    BOUND_BEASTS = "bound_beasts"
    SAPPERS = "sappers"
    ENGINEERS = "engineers"
    BATTLE_CASTERS = "battle_casters"
    SUPPORT_CASTERS = "support_casters"
    SUMMONERS = "summoners"
    CONSTRUCTS = "constructs"
    SUMMONED_HOST = "summoned_host"
    MECHANISED_INFANTRY = "mechanised_infantry"
    SPECIAL_FORCES = "special_forces"
    PARTISANS = "partisans"
    PEACEKEEPERS = "peacekeepers"
    MEDICS = "medics"
    DRONE_OPERATORS = "drone_operators"
    SIGNALS_TROOPS = "signals_troops"
    POWERED_TROOPERS = "powered_troopers"
    DROP_TROOPS = "drop_troops"
    PILOTS = "pilots"


class ArmourType(StrEnum):
    NONE = "none"
    HIDE = "hide"
    PADDED = "padded"
    MAIL = "mail"
    SCALE = "scale"
    PLATE = "plate"
    ENCHANTED = "enchanted"
    BALLISTIC = "ballistic"
    COMPOSITE = "composite"
    POWERED = "powered"
    FORCE_FIELD = "force_field"


class ShieldType(StrEnum):
    NONE = "none"
    SMALL = "small"
    LARGE = "large"
    TOWER = "tower"
    RIOT = "riot"
    ENERGY = "energy"


class Stance(StrEnum):
    MARCH = "march"
    FORAGE = "forage"
    ENTRENCH = "entrench"
    BESIEGE = "besiege"
    GARRISON = "garrison"
    RAID = "raid"
    RETREAT = "retreat"


RESTING = frozenset({Stance.ENTRENCH, Stance.GARRISON, Stance.BESIEGE})


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
    FEINT = "feint"
    ARTILLERY_BARRAGE = "artillery_barrage"
    ARMOURED_THRUST = "armoured_thrust"
    AIR_SUPERIORITY = "air_superiority"
    BLOCKADE = "blockade"
    GUERRILLA = "guerrilla"
    ELECTRONIC_WARFARE = "electronic_warfare"
    ORBITAL_BOMBARDMENT = "orbital_bombardment"
    DROP_ASSAULT = "drop_assault"
    INFILTRATION = "infiltration"


class BattlePhase(StrEnum):
    SCOUTING = "scouting"
    PLAN = "plan"
    COMMAND = "command"
    MISSILE = "missile"
    CHARGE = "charge"
    MELEE = "melee"
    RESERVES = "reserves"
    RITES = "rites"
    PURSUIT = "pursuit"
    SALVAGE = "salvage"
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


class CommandArea(StrEnum):
    FIRE = "fire"
    SHOCK = "shock"
    MANOEUVRE = "manoeuvre"
    SIEGE = "siege"
    LOGISTICS = "logistics"


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
    SEIZE_ROUTE = "seize_route"


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


class MoraleState(StrEnum):
    STEADY = "steady"
    SHAKEN = "shaken"
    WAVERING = "wavering"
    ROUTING = "routing"
    BROKEN = "broken"
    RALLIED = "rallied"


class Formation(StrEnum):
    LINE = "line"
    COLUMN = "column"
    WEDGE = "wedge"
    SQUARE = "square"
    LOOSE = "loose"
    SHIELDWALL = "shieldwall"
    DISPERSED = "dispersed"
    ENTRENCHED = "entrenched"
    ECHELON = "echelon"
    CONVOY = "convoy"
    SCREEN = "screen"
    LAYERED = "layered"


class TargetClass(StrEnum):
    SOFT = "soft"
    HARD = "hard"
