from enum import StrEnum


class EchelonLevel(StrEnum):
    ARMY_GROUP = "army_group"
    ARMY = "army"
    CORPS = "corps"
    DIVISION = "division"
    BRIGADE = "brigade"


class EchelonOrder(StrEnum):
    ATTACK = "attack"
    MANOEUVRE = "manoeuvre"
    RESUPPLY = "resupply"
    HOLD = "hold"
    STANDING = "standing"


class CarrierKind(StrEnum):
    PORTERS = "porters"
    PACK_ANIMALS = "pack_animals"
    ANIMAL_CARTS = "animal_carts"
    RAIL = "rail"
    ROAD_MOTOR = "road_motor"
    RIVER_AND_CANAL = "river_and_canal"
    SEA = "sea"
    AIR = "air"
    PIPELINE = "pipeline"
    ORBITAL_LIFT = "orbital_lift"
    SPACE = "space"
    TELEPORT = "teleport"
    LIVING = "living"
    RITE = "rite"
    NETWORK = "network"


class ShotKind(StrEnum):
    ROUND = "round"
    CHAIN = "chain"
    GRAPE = "grape"
    FIRE = "fire"
    SOLID = "solid"
    SPREAD = "spread"
    INCENDIARY = "incendiary"
    EXPLOSIVE = "explosive"
    PIERCING = "piercing"
    GUIDED = "guided"
    ENERGY = "energy"


class PointOfSail(StrEnum):
    IN_IRONS = "in_irons"
    CLOSE_HAULED = "close_hauled"
    REACHING = "reaching"
    RUNNING = "running"
    UNDER_OARS = "under_oars"


class CrewStation(StrEnum):
    GUNNERS = "gunners"
    RIGGERS = "riggers"
    MARINES = "marines"
    OFFICERS = "officers"
    ROWERS = "rowers"
    PILOTS = "pilots"
    ENGINEERS = "engineers"
    SENSOR_OPERATORS = "sensor_operators"
    MEDICS = "medics"
    HANDLERS = "handlers"
    LINK_OPERATORS = "link_operators"
    CASTERS = "casters"
    NAVIGATORS = "navigators"


class ExpeditionRole(StrEnum):
    SCOUT = "scout"
    GUIDE = "guide"
    HEALER = "healer"
    FIGHTER = "fighter"
    SCHOLAR = "scholar"
    PORTER = "porter"


class ExpeditionGround(StrEnum):
    SITE = "site"
    WILDS = "wilds"
    UNDERWORLD = "underworld"
    REALM = "realm"


class ExpeditionStatus(StrEnum):
    UNDERWAY = "underway"
    CAMPED = "camped"
    RETURNED = "returned"
    LOST = "lost"


class ResolveKind(StrEnum):
    STEADY = "steady"
    PARANOID = "paranoid"
    HOPELESS = "hopeless"
    SELFISH = "selfish"
    ABUSIVE = "abusive"
    COURAGEOUS = "courageous"
    FOCUSED = "focused"
    STALWART = "stalwart"


class ExpeditionEvent(StrEnum):
    SETOUT = "setout"
    LEG = "leg"
    ROOM = "room"
    CAMP = "camp"
    AMBUSH = "ambush"
    EXPOSURE = "exposure"
    AFFLICTION = "affliction"
    VIRTUE = "virtue"
    QUIRK = "quirk"
    FALLEN = "fallen"
    RETURN = "return"
    LOSS = "loss"


class QuirkKind(StrEnum):
    FEARS_DARK = "fears_dark"
    DARK_SIGHTED = "dark_sighted"
    KNOWS_WAYS = "knows_ways"
    EATS_ANYTHING = "eats_anything"
    HARDY = "hardy"
    FRAIL = "frail"
    JUMPY = "jumpy"
    STEADY_NERVES = "steady_nerves"
    KEEN_EYED = "keen_eyed"
    HOMESICK = "homesick"
    RESTLESS = "restless"
    LIGHT_FINGERED = "light_fingered"
