from enum import StrEnum


class HousingLevel(StrEnum):
    HUT = "hut"
    COTTAGE = "cottage"
    HOUSE = "house"
    TOWNHOUSE = "townhouse"
    MANOR = "manor"
    APARTMENT = "apartment"
    TENEMENT = "tenement"
    TOWER_BLOCK = "tower_block"
    ARCOLOGY_UNIT = "arcology_unit"
    HABITAT_MODULE = "habitat_module"
    SHIP_BERTH = "ship_berth"


class UrbanService(StrEnum):
    WATER = "water"
    FAITH = "faith"
    WATCH = "watch"
    HEALING = "healing"
    MARKET = "market"
    SCHOOL = "school"
    BATH = "bath"
    FIRE = "fire"
    SANITATION = "sanitation"
    TRANSPORT = "transport"
    COMMUNICATION = "communication"
    POWER = "power"
    COURTS = "courts"
    WELFARE = "welfare"
    GRANARY = "granary"
    PARKS = "parks"
    LIBRARY = "library"
    BURIAL = "burial"
    DEPOT = "depot"
    ADMINISTRATION = "administration"
    ENTERTAINMENT = "entertainment"


class Morphology(StrEnum):
    ORGANIC = "organic"
    PLANNED = "planned"
    CONCENTRIC = "concentric"
    GRID = "grid"
    VERTICAL = "vertical"
    SPRAWL = "sprawl"


class RacketKind(StrEnum):
    PROTECTION = "protection"
    SMUGGLING = "smuggling"
    GAMBLING = "gambling"
    FENCING = "fencing"
    KIDNAPPING = "kidnapping"
    COUNTERFEITING = "counterfeiting"
    FRAUD = "fraud"
    EXTORTION = "extortion"
    TRAFFICKING = "trafficking"
    INTOXICANTS = "intoxicants"
    DATA_THEFT = "data_theft"
    LOAN_SHARKING = "loan_sharking"
    ARMS = "arms"


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


class CargoClass(StrEnum):
    PERISHABLE = "perishable"
    LIVESTOCK = "livestock"
    BULK = "bulk"
    FINE = "fine"
    LIQUID = "liquid"
    GAS = "gas"
    HAZARDOUS = "hazardous"
    PASSENGERS = "passengers"
    LIVING = "living"
    SAVED_MINDS = "saved_minds"
    RELICS = "relics"


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


class ZoneKind(StrEnum):
    GOVERNANCE = "governance"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"
    CIVIC = "civic"
    GREEN = "green"
    TRANSPORT = "transport"
    MILITARY = "military"
    RESEARCH = "research"


class CivicService(StrEnum):
    EDUCATION = "education"
    HEALTH = "health"
    SPORTS = "sports"
    CULTURE = "culture"
    SOCIAL = "social"
    ADMINISTRATION = "administration"
    SAFETY = "safety"
    SANITATION = "sanitation"
    TRANSPORT = "transport"
    COMMUNICATION = "communication"
    RECREATION = "recreation"
    JUSTICE = "justice"
    WORSHIP = "worship"
    RESEARCH = "research"
    COMMERCE = "commerce"
    ENERGY = "energy"
    WATER = "water"
    RECORDS = "records"
    HOUSING = "housing"
    FUNERARY = "funerary"
    EMERGENCY = "emergency"
    FOOD_SUPPLY = "food_supply"
    CARE = "care"
    DEFENCE = "defence"


class LandGround(StrEnum):
    WATER = "water"
    SHORE = "shore"
    LOWLAND = "lowland"
    WETLAND = "wetland"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    PEAKS = "peaks"


class LandCover(StrEnum):
    OPEN = "open"
    FOREST = "forest"
    FIELDS = "fields"
    PASTURE = "pasture"
    MARSH = "marsh"
    CLEARED = "cleared"
    BUILT = "built"
    MINED = "mined"
