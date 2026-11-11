from enum import StrEnum


class HousingLevel(StrEnum):
    HUT = "hut"
    COTTAGE = "cottage"
    HOUSE = "house"
    TOWNHOUSE = "townhouse"
    MANOR = "manor"


class UrbanService(StrEnum):
    WATER = "water"
    FAITH = "faith"
    WATCH = "watch"
    HEALING = "healing"
    MARKET = "market"
    SCHOOL = "school"
    BATH = "bath"
    FIRE = "fire"


class Morphology(StrEnum):
    ORGANIC = "organic"
    PLANNED = "planned"
    CONCENTRIC = "concentric"


class RacketKind(StrEnum):
    PROTECTION = "protection"
    SMUGGLING = "smuggling"
    GAMBLING = "gambling"
    FENCING = "fencing"
    KIDNAPPING = "kidnapping"
    COUNTERFEITING = "counterfeiting"


class OrderLaw(StrEnum):
    SPARE_MEMBERS = "spare_members"
    NO_OUTER_DEALINGS = "no_outer_dealings"
    SHARE_DISCOVERIES = "share_discoveries"
    KEEP_SECRECY = "keep_secrecy"


class TribunalVerdict(StrEnum):
    ACQUITTED = "acquitted"
    FINED = "fined"
    EXPELLED = "expelled"
    STRIPPED = "stripped"


class ConvoyStatus(StrEnum):
    LOADING = "loading"
    TRAVELLING = "travelling"
    DELAYED = "delayed"
    ARRIVED = "arrived"
    RAIDED = "raided"
    LOST = "lost"


class TransportKind(StrEnum):
    PACK_ANIMALS = "pack_animals"
    WAGONS = "wagons"
    RIVER_BOATS = "river_boats"
    SHIPS = "ships"


class CargoClass(StrEnum):
    PERISHABLE = "perishable"
    LIVESTOCK = "livestock"
    BULK = "bulk"
    FINE = "fine"


class Preservation(StrEnum):
    NONE = "none"
    SALTED = "salted"
    ICED = "iced"
    MAGIC = "magic"


class MarketPlay(StrEnum):
    CORNER = "corner"
    DUMP = "dump"


class CrimeStance(StrEnum):
    SUPPRESS = "suppress"
    CO_OPT = "co_opt"
