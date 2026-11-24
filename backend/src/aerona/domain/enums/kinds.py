from enum import StrEnum


class KindConcept(StrEnum):
    GOOD = "good"
    DISH = "dish"
    DRINK = "drink"
    CUISINE = "cuisine"
    GARMENT = "garment"
    COLOUR_TERM = "colour_term"
    SCENT = "scent"
    EMBLEM_SYSTEM = "emblem_system"
    FURNISHING = "furnishing"
    TOOL = "tool"
    INSTRUMENT = "instrument"
    MUSIC_TRADITION = "music_tradition"
    GAME = "game"
    SUBSTANCE = "substance"
    PROFESSION = "profession"
    RANK = "rank"
    ORGANISATION = "organisation"
    DWELLING = "dwelling"
    PRODUCTION_METHOD = "production_method"
    DIVINE_OFFICE = "divine_office"
    REALM = "realm"
    TRAIT = "trait"
    TENET = "tenet"
    FEAR = "fear"
    DREAM_READING = "dream_reading"
    AIM = "aim"


class KindStance(StrEnum):
    MAKES = "makes"
    USES = "uses"
    FAVOURS = "favours"
    FORBIDS = "forbids"
    BLESSES = "blesses"


CARRIED_STANCES = frozenset({KindStance.MAKES, KindStance.USES, KindStance.FAVOURS})


class KindSpread(StrEnum):
    INVENTED = "invented"
    TRADE = "trade"
    CONTACT = "contact"
    CONQUEST = "conquest"
    MIGRATION = "migration"
    DECREE = "decree"
    DIVINE = "divine"
    GENESIS = "genesis"


class GoodCategory(StrEnum):
    GRAIN = "grain"
    ROOT_AND_TUBER = "root_and_tuber"
    VEGETABLE = "vegetable"
    LEGUME = "legume"
    FRUIT = "fruit"
    NUT_AND_SEED = "nut_and_seed"
    OIL_AND_FAT = "oil_and_fat"
    SWEETENER = "sweetener"
    SEASONING = "seasoning"
    MINERAL_SEASONING = "mineral_seasoning"
    MEAT = "meat"
    FISH_AND_SEAFOOD = "fish_and_seafood"
    DAIRY = "dairy"
    EGGS = "eggs"
    INSECTS = "insects"
    FUNGI = "fungi"
    ALGAE = "algae"
    OFFAL_AND_BLOOD = "offal_and_blood"
    FODDER = "fodder"
    DRINK_BASE = "drink_base"
    STIMULANT = "stimulant"
    INTOXICANT = "intoxicant"
    MEDICINE = "medicine"
    FIBRE = "fibre"
    TEXTILE = "textile"
    HIDE_AND_LEATHER = "hide_and_leather"
    TIMBER = "timber"
    FUEL = "fuel"
    ORE = "ore"
    METAL = "metal"
    STONE = "stone"
    CLAY_AND_CERAMIC = "clay_and_ceramic"
    GLASS = "glass"
    CHEMICAL = "chemical"
    DYE_AND_PIGMENT = "dye_and_pigment"
    SCENT_MATERIAL = "scent_material"
    REAGENT = "reagent"
    TOOLS = "tools"
    WEAPONS = "weapons"
    ARMOUR = "armour"
    GARMENTS = "garments"
    FURNISHINGS = "furnishings"
    CONTAINERS = "containers"
    INSTRUMENTS = "instruments"
    ORNAMENTS = "ornaments"
    BOOKS_AND_RECORDS = "books_and_records"
    MACHINES = "machines"
    PARTS = "parts"
    ENERGY_STORE = "energy_store"
    DATA = "data"
    LIVING_GOODS = "living_goods"
    SACRED_GOODS = "sacred_goods"
    LUXURIES = "luxuries"
    LIVESTOCK = "livestock"
    MOUNTS = "mounts"
    VEHICLES = "vehicles"
    PREPARED_FOOD = "prepared_food"
    SEED_AND_STOCK = "seed_and_stock"
    FERTILISER = "fertiliser"
    RESIN_AND_GUM = "resin_and_gum"
    RELICS_AND_ANTIQUITIES = "relics_and_antiquities"


class KindAct(StrEnum):
    MAKE = "make"
    BLESS = "bless"
    FORBID = "forbid"


class GoodSource(StrEnum):
    SPECIES = "species"
    MATERIAL = "material"
    DEPOSIT = "deposit"
    METHOD = "method"
    MAKING = "making"


class GoodTaxClass(StrEnum):
    EXEMPT = "exempt"
    STAPLE = "staple"
    ORDINARY = "ordinary"
    LUXURY = "luxury"
    STRATEGIC = "strategic"


class GoodLegality(StrEnum):
    FREE = "free"
    LICENSED = "licensed"
    RESTRICTED = "restricted"
    FORBIDDEN = "forbidden"


class IngredientRole(StrEnum):
    BASE = "base"
    PROTEIN = "protein"
    FAT = "fat"
    SEASONING = "seasoning"
    GARNISH = "garnish"
    BINDER = "binder"
    LIQUID = "liquid"
    LEAVENING = "leavening"
    PRESERVATIVE = "preservative"
    COLOURING = "colouring"
    ACID = "acid"
    AROMA = "aroma"


class MealSlot(StrEnum):
    DAILY_MEAL = "daily_meal"
    SNACK = "snack"
    FEAST = "feast"
    RITE = "rite"
    RATION = "ration"
    REMEDY = "remedy"
    TRAVEL_FOOD = "travel_food"
    FAMINE_FOOD = "famine_food"
    STREET = "street"


class DrinkCategory(StrEnum):
    WATER = "water"
    INFUSION = "infusion"
    FERMENTED = "fermented"
    DISTILLED = "distilled"
    PRESSED = "pressed"
    MILK_BASED = "milk_based"
    BROTH = "broth"
    STIMULANT_BREW = "stimulant_brew"
    INTOXICANT = "intoxicant"
    MEDICINAL = "medicinal"
    RITUAL = "ritual"
    SYNTHESISED = "synthesised"
    SPARKLING = "sparkling"
    SAP_DRINK = "sap_drink"


class DrinkRole(StrEnum):
    DAILY = "daily"
    HOSPITALITY = "hospitality"
    FEAST = "feast"
    RITE = "rite"
    MEDICINE = "medicine"
    TRADE = "trade"
    BOND_MAKING = "bond_making"
