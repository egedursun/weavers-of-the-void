from enum import StrEnum


class TravelMethod(StrEnum):
    ANCIENT_GATE = "ancient_gate"
    SPACE_FOLD = "space_fold"
    LIGHT_SAIL = "light_sail"
    CARRIER_MOUNT = "carrier_mount"
    DREAM_JOURNEY = "dream_journey"
    DEATH_CURRENT = "death_current"
    DIVINE_BRIDGE = "divine_bridge"
    SLINGSHOT_ORBIT = "slingshot_orbit"
    CARRIED_WITHIN = "carried_within"
    WORMHOLE = "wormhole"
    VOID_ARK = "void_ark"
    GALACTIC_GATE = "galactic_gate"
    FILAMENT_LANE = "filament_lane"
    DIMENSIONAL_RIFT = "dimensional_rift"
    PLANAR_DOOR = "planar_door"
    ROCKETRY = "rocketry"


class VehicleKind(StrEnum):
    GATE = "gate"
    SHIP = "ship"
    MOUNT = "mount"
    BRIDGE = "bridge"
    RAIL = "rail"
    ROAD_VEHICLE = "road_vehicle"
    AIRCRAFT = "aircraft"
    TELEPORT = "teleport"
    LIVING = "living"
    RIFT = "rift"
    ON_FOOT = "on_foot"


class JourneyIntent(StrEnum):
    COLONY = "colony"
    TRADE = "trade"
    EXPLORATION = "exploration"
    CONQUEST = "conquest"
    PILGRIMAGE = "pilgrimage"


class JourneyStatus(StrEnum):
    UNDERWAY = "underway"
    WAITING = "waiting"
    ARRIVED = "arrived"
    LOST = "lost"
    RECALLED = "recalled"
    STRANDED = "stranded"


class RefugeeCause(StrEnum):
    WAR = "war"
    DISASTER = "disaster"
    DECREE = "decree"


class ExplorationReason(StrEnum):
    NARROW = "narrow"
    HUNGER = "hunger"
    POVERTY = "poverty"
    EXPLORER = "explorer"
    KNOWLEDGE = "knowledge"
    SPIRIT = "spirit"


class JourneyEventKind(StrEnum):
    PIRATES = "pirates"
    VOID_STORM = "void_storm"
    CREATURE = "creature"
    LOST_WAY = "lost_way"
    DISCOVERY = "discovery"
    SACRIFICE = "sacrifice"
    MEMORY_LOSS = "memory_loss"
    DREAM_NOT_RETURNED = "dream_not_returned"
    SAIL_SNAPPED = "sail_snapped"
    BRIDGE_COLLAPSED = "bridge_collapsed"
    NOT_RELEASED = "not_released"
    STOWAWAY = "stowaway"
    OUTER_TOUCH = "outer_touch"
    DERELICT = "derelict"
    TOLL = "toll"
    CROSSING = "crossing"
    PROVISIONS = "provisions"
    OTHER = "other"
    ENCOUNTER = "encounter"
    BIRTH = "birth"
    DEATH = "death"


class HorizonStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    BORN = "born"
    WASTED = "wasted"


class RouteClosure(StrEnum):
    SEALED = "sealed"
    SEVERED = "severed"
    FORGOTTEN = "forgotten"
    WORN = "worn"
    COLLAPSED = "collapsed"
    SNAPPED = "snapped"
    SCORCHED = "scorched"


class RouteState(StrEnum):
    OPEN = "open"
    TEMPORARY = "temporary"
    MISALIGNED = "misaligned"
    SEALED = "sealed"
    SEVERED = "severed"
    COLLAPSED = "collapsed"
    SNAPPED = "snapped"
    SCORCHED = "scorched"
    UNSTABLE = "unstable"
    FORGOTTEN = "forgotten"
    WORN = "worn"


class RouteEnvironment(StrEnum):
    SEA = "sea"
    LAND = "land"
    AIR = "air"
    SPACE = "space"
    RIFT = "rift"
    NETWORK = "network"


class EncounterEffect(StrEnum):
    ATTACK = "attack"
    HAZARD = "hazard"
    DELAY = "delay"
    STRAYING = "straying"
    FIND = "find"
    TOLL = "toll"
    SICKNESS = "sickness"
    DESERTION = "desertion"


class ArrivalOutcome(StrEnum):
    SETTLERS = "settlers"
    REFUGEES = "refugees"
    INVADERS = "invaders"


class TravelMedium(StrEnum):
    SPACE = "space"
    DIMENSION = "dimension"
    DREAM = "dream"
    DEATH = "death"
    DIVINE = "divine"
    BODY = "body"


class TravelMechanism(StrEnum):
    GATE = "gate"
    FOLD = "fold"
    SAIL = "sail"
    MOUNT = "mount"
    BRIDGE = "bridge"
    CURRENT = "current"
    CARRIER_BEING = "carrier_being"
    ORBIT = "orbit"
