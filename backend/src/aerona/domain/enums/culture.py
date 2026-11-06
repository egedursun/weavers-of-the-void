from enum import StrEnum


class SpeakerKind(StrEnum):
    NATIVE = "native"
    SECOND = "second"
    LITURGICAL = "liturgical"


class LegendArchetype(StrEnum):
    HERO_QUEST = "hero_quest"
    MONSTER = "monster"
    TRICKSTER = "trickster"
    CREATION = "creation"
    FLOOD = "flood"
    BETRAYAL = "betrayal"
    LOST_PARADISE = "lost_paradise"
    CHOSEN_ONE = "chosen_one"
    CURSED_LINE = "cursed_line"
    RETURN_OF_THE_KING = "return_of_the_king"
    HAUNTED_PLACE = "haunted_place"


class TraditionKind(StrEnum):
    FESTIVAL = "festival"
    FAST = "fast"
    FUNERAL_RITE = "funeral_rite"
    INITIATION = "initiation"
    MARRIAGE_RITE = "marriage_rite"
    COMING_OF_AGE = "coming_of_age"
    TABOO = "taboo"
    OFFERING = "offering"
    PILGRIMAGE = "pilgrimage"
    HOSPITALITY_LAW = "hospitality_law"
    DUEL_CUSTOM = "duel_custom"
    MOURNING = "mourning"
    HARVEST_RITE = "harvest_rite"
    WAR_DANCE = "war_dance"
    SCAR_RITE = "scar_rite"
    ANCESTOR_FEAST = "ancestor_feast"
    SIESTA = "siesta"
    NIGHT_VIGIL = "night_vigil"


class Technique(StrEnum):
    PHALANX_DRILL = "phalanx_drill"
    HORSE_ARCHERY = "horse_archery"
    SIEGECRAFT = "siegecraft"
    FORTIFICATION = "fortification"
    LOGISTICS = "logistics"
    HERBALISM = "herbalism"
    SURGERY = "surgery"
    AMPUTATION = "amputation"
    PROSTHETICS = "prosthetics"
    QUARANTINE = "quarantine"
    INOCULATION = "inoculation"
    IRRIGATION = "irrigation"
    CROP_ROTATION = "crop_rotation"
    TERRACING = "terracing"
    PLOUGH = "plough"
    SELECTIVE_BREEDING = "selective_breeding"
    BRONZE = "bronze"
    IRON = "iron"
    STEEL = "steel"
    SKYSTEEL = "skysteel"
    ARCH = "arch"
    DOME = "dome"
    AQUEDUCT = "aqueduct"
    FORTRESS = "fortress"
    ALPHABET = "alphabet"
    PAPER = "paper"
    PRINTING = "printing"
    CALENDAR = "calendar"
    NAVIGATION_STARS = "navigation_stars"
    ECLIPSE_PREDICTION = "eclipse_prediction"
    SAILING = "sailing"
    SHIPWRIGHTING = "shipwrighting"
    COINAGE = "coinage"
    BANKING = "banking"
    WARDING = "warding"
    SUMMONING = "summoning"
    SKY_SAILING = "sky_sailing"
    NECROMANCY = "necromancy"
    ALCHEMY = "alchemy"
    ASTRONOMY_INSTRUMENTS = "astronomy_instruments"


class IdeologyTenet(StrEnum):
    LEGALISM = "legalism"
    RESTRAINT = "restraint"
    EGALITARIANISM = "egalitarianism"
    DIVINE_RIGHT = "divine_right"
    MERCANTILISM = "mercantilism"
    MILITARISM = "militarism"
    ASCETICISM = "asceticism"
    RATIONALISM = "rationalism"
    NATURE_HARMONY = "nature_harmony"
    XENOPHOBIA = "xenophobia"
    COSMOPOLITANISM = "cosmopolitanism"
    ANTI_GOD = "anti_god"
    CREATORISM = "creatorism"


class MagicSchool(StrEnum):
    ELEMENTAL_FIRE = "elemental_fire"
    ELEMENTAL_WATER = "elemental_water"
    EARTH = "earth"
    STORM = "storm"
    LIFE = "life"
    DEATH = "death"
    MIND = "mind"
    ILLUSION = "illusion"
    DIVINATION = "divination"
    WARDING = "warding"
    BINDING = "binding"
    SUMMONING = "summoning"
    BLOOD = "blood"
    VOID = "void"


class MagicSource(StrEnum):
    LEY = "ley"
    DIVINE = "divine"
    BLOOD = "blood"
    SOUL = "soul"
    REAGENT = "reagent"
    VOID = "void"


class RiteEffectKind(StrEnum):
    DAMAGE = "damage"
    HEAL = "heal"
    WEATHER_CHANGE = "weather_change"
    CURSE = "curse"
    BLESS = "bless"
    WARD = "ward"
    SCRY = "scry"
    BIND = "bind"
    SUMMON = "summon"
    RAISE_DEAD = "raise_dead"
    FERTILITY = "fertility"
    HARVEST_BLESSING = "harvest_blessing"
    SEAL_SOUL = "seal_soul"
    UNSEAL_SOUL = "unseal_soul"
    EXORCISE = "exorcise"


class BacklashKind(StrEnum):
    INJURY = "injury"
    MADNESS = "madness"
    LEAK = "leak"
    ESCAPE = "escape"
    PHENOMENON = "phenomenon"


class ProphecyPredicate(StrEnum):
    DIES = "dies"
    FALLS = "falls"
    BORN_IN = "born_in"
    SKY_EVENT = "sky_event"
    WAR_BETWEEN = "war_between"
    RULER_OF = "ruler_of"
    WITHIN_EPOCHS = "within_epochs"


class ProphecyState(StrEnum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    FAILED = "failed"


class ItemClass(StrEnum):
    BLADE = "blade"
    LONGBLADE = "longblade"
    AXE = "axe"
    SPEAR = "spear"
    POLEARM = "polearm"
    MACE = "mace"
    BOW = "bow"
    CROSSBOW = "crossbow"
    SLING = "sling"
    THROWING = "throwing"
    STAFF = "staff"
    ARMOUR = "armour"
    PADDING = "padding"
    CLOAK = "cloak"
    SHIELD = "shield"
    HELMET = "helmet"
    CROWN = "crown"
    SCEPTRE = "sceptre"
    SEAL = "seal"
    RING = "ring"
    STANDARD = "standard"
    HOLY_RELIC = "holy_relic"
    IDOL = "idol"
    PRAYER_BOOK = "prayer_book"
    BOOK = "book"
    SCROLL = "scroll"
    MAP = "map"
    ASTROLABE = "astrolabe"
    TOOL = "tool"
    INSTRUMENT = "instrument"
    MIRROR = "mirror"
    VESSEL_OBJECT = "vessel_object"
    PROSTHESIS = "prosthesis"
    KEY = "key"
    JEWEL = "jewel"
    CURRENCY = "currency"


class CurseKind(StrEnum):
    NONE = "none"
    BLOODTHIRST = "bloodthirst"
    MISFORTUNE = "misfortune"
    WASTING = "wasting"
    MADNESS = "madness"
    BETRAYAL = "betrayal"


class ItemDeed(StrEnum):
    MADE = "made"
    OWNED = "owned"
    KILL = "kill"
    BATTLE = "battle"
    CORONATION = "coronation"
    LOST = "lost"
    THEFT = "theft"
    BURIAL = "burial"
    BROKEN = "broken"
    REPAIRED = "repaired"
    ENCHANTED = "enchanted"
    GIVEN = "given"
    CAPTURED = "captured"


class ArtMedium(StrEnum):
    SONG = "song"
    EPIC_POEM = "epic_poem"
    PLAY = "play"
    STATUE = "statue"
    FRESCO = "fresco"
    TAPESTRY = "tapestry"
    MOSAIC = "mosaic"
    BOOK = "book"
    DANCE = "dance"
    MUSIC = "music"
    CARVING = "carving"
    ARCHITECTURE_ORNAMENT = "architecture_ornament"


class LanguageRegister(StrEnum):
    COURT = "court"
    COMMON = "common"
    LITURGICAL = "liturgical"
    TRADE = "trade"


class CalendarSlot(StrEnum):
    SOWING = "sowing"
    HARVEST = "harvest"
    MIDWINTER = "midwinter"
    CAMPAIGN = "campaign"
    HOLY_DAY = "holy_day"


class TraditionEffectKind(StrEnum):
    COHESION = "cohesion"
    SATISFACTION = "satisfaction"
    PIETY = "piety"
    VALUE = "value"
    FERTILITY = "fertility"
    MARTIAL = "martial"
    PLACATION = "placation"
    HARVEST = "harvest"
    SAFETY = "safety"
    FOOD_SAVED = "food_saved"
    REST = "rest"
    VIGIL = "vigil"


class RumourChannel(StrEnum):
    WITNESS = "witness"
    ROUTE = "route"
    PILGRIMAGE = "pilgrimage"
    JOURNEY = "journey"
    SPY = "spy"
    PLANTED = "planted"


class ProphecyConsequence(StrEnum):
    RULE = "rule"
    FALL = "fall"
    DEATH = "death"
    WAR = "war"
    BIRTH = "birth"
    OMEN = "omen"


class SummonForm(StrEnum):
    SPIRIT = "spirit"
    BEAST = "beast"
    UNDEAD = "undead"


class CustomCatalog(StrEnum):
    TECHNIQUE = "technique"
    TENET = "tenet"
    TRADITION_KIND = "tradition_kind"
    ARCHETYPE = "archetype"
    ITEM_CLASS = "item_class"
    RITE_EFFECT = "rite_effect"


PERFORMED_MEDIA = frozenset({ArtMedium.SONG, ArtMedium.EPIC_POEM, ArtMedium.PLAY, ArtMedium.DANCE, ArtMedium.MUSIC})
VERBAL_MEDIA = frozenset({ArtMedium.SONG, ArtMedium.EPIC_POEM, ArtMedium.PLAY, ArtMedium.BOOK})
