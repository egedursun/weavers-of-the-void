from enum import StrEnum


class TravelMethod(StrEnum):
    ANCIENT_GATE = "ancient_gate"
    SPACE_FOLD = "space_fold"
    LIGHT_SAIL = "light_sail"
    COSMIC_MOUNT = "cosmic_mount"
    DREAM_JOURNEY = "dream_journey"
    RIVER_OF_DEAD = "river_of_dead"
    DIVINE_BRIDGE = "divine_bridge"
    SLINGSHOT_ORBIT = "slingshot_orbit"
    SWALLOWED = "swallowed"
    WORMHOLE = "wormhole"


class VehicleKind(StrEnum):
    GATE = "gate"
    SHIP = "ship"
    MOUNT = "mount"
    BRIDGE = "bridge"


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
    SWALLOWED = "swallowed"
    STOWAWAY = "stowaway"
    OTHER = "other"


class HorizonStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    BORN = "born"
    WASTED = "wasted"


class RouteClosure(StrEnum):
    SEALED = "sealed"
    SEVERED = "severed"
    FORGOTTEN = "forgotten"
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
