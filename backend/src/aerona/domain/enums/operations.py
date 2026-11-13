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
    WAGONS = "wagons"
    PACK_ANIMALS = "pack_animals"
    PORTERS = "porters"
    BARGES = "barges"
    SHIPS = "ships"
    SKY_BARGES = "sky_barges"


class ShotKind(StrEnum):
    ROUND = "round"
    CHAIN = "chain"
    GRAPE = "grape"
    FIRE = "fire"


class PointOfSail(StrEnum):
    IN_IRONS = "in_irons"
    CLOSE_HAULED = "close_hauled"
    REACHING = "reaching"
    RUNNING = "running"
    UNDER_OARS = "under_oars"


class CrewStation(StrEnum):
    GUNNERS = "gunners"
    TOPMEN = "topmen"
    MARINES = "marines"
    OFFICERS = "officers"
    ROWERS = "rowers"


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
