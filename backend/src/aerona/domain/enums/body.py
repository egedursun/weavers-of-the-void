from enum import StrEnum


class BodyPlan(StrEnum):
    HUMANOID = "humanoid"
    QUADRUPED = "quadruped"
    AVIAN = "avian"
    SERPENTINE = "serpentine"
    INSECTOID = "insectoid"
    AQUATIC = "aquatic"
    AMORPHOUS = "amorphous"
    ARBOREAL = "arboreal"
    INCORPOREAL = "incorporeal"
    COLOSSAL = "colossal"
    CONSTRUCT = "construct"
    DIVINE_MANIFEST = "divine_manifest"


class HeightClass(StrEnum):
    SHORT = "short"
    AVERAGE = "average"
    TALL = "tall"
    GIANT = "giant"


class BodyBuild(StrEnum):
    SLIGHT = "slight"
    AVERAGE = "average"
    HEAVY = "heavy"
    GIANT = "giant"


class BodyFunction(StrEnum):
    GRASP = "grasp"
    FINE_MANIPULATION = "fine_manipulation"
    LOCOMOTION = "locomotion"
    SIGHT = "sight"
    HEARING = "hearing"
    SPEECH = "speech"
    BREATH = "breath"
    VITAL = "vital"
    COGNITION = "cognition"
    REPRODUCTION = "reproduction"
    FLIGHT = "flight"
    VENOM = "venom"
    HORN = "horn"
    TAIL = "tail"
    PRESENCE = "presence"


class BodyRegion(StrEnum):
    HEAD = "head"
    TORSO = "torso"
    ARMS = "arms"
    LEGS = "legs"
    WINGS = "wings"
    TAIL = "tail"


class DamageType(StrEnum):
    CUT = "cut"
    PIERCE = "pierce"
    BLUNT = "blunt"
    FIRE = "fire"
    COLD = "cold"
    VENOM = "venom"
    MAGIC = "magic"
    VOID = "void"
    HOLY = "holy"
    BALLISTIC = "ballistic"
    EXPLOSIVE = "explosive"
    ENERGY = "energy"
    ELECTRIC = "electric"
    RADIATION = "radiation"
    CHEMICAL = "chemical"
    SONIC = "sonic"
    PSYCHIC = "psychic"


class InjuryKind(StrEnum):
    BRUISE = "bruise"
    CUT = "cut"
    DEEP_CUT = "deep_cut"
    PUNCTURE = "puncture"
    FRACTURE = "fracture"
    CRUSH = "crush"
    BURN = "burn"
    FROSTBITE = "frostbite"
    BITE = "bite"
    VENOM = "venom"
    SEVERED = "severed"
    GOUGED = "gouged"
    DESTROYED = "destroyed"
    CURSE_WITHER = "curse_wither"
    VOID_TOUCH = "void_touch"
    DIVINE_BRAND = "divine_brand"
    SICKNESS = "sickness"
    GUNSHOT = "gunshot"
    SHRAPNEL = "shrapnel"
    CONCUSSION = "concussion"
    ELECTRICAL_BURN = "electrical_burn"
    CHEMICAL_BURN = "chemical_burn"
    RADIATION_SICKNESS = "radiation_sickness"
    MIND_SCAR = "mind_scar"


class InjuryState(StrEnum):
    FRESH = "fresh"
    INFECTED = "infected"
    HEALING = "healing"
    HEALED_SCAR = "healed_scar"
    PERMANENT = "permanent"
    LETHAL = "lethal"


OPEN_INJURY_STATES = frozenset({InjuryState.FRESH, InjuryState.INFECTED, InjuryState.HEALING})


class HarmCause(StrEnum):
    BATTLE = "battle"
    DUEL = "duel"
    PUNISHMENT = "punishment"
    TORTURE = "torture"
    ACCIDENT = "accident"
    MONSTER = "monster"
    DISASTER = "disaster"
    CURSE = "curse"
    MAGIC_BACKLASH = "magic_backlash"
    GOD = "god"
    POISON = "poison"
    QUEST = "quest"
    ESCAPE = "escape"
    SACRIFICE = "sacrifice"
    AGE = "age"
    PLAYER = "player"
    EXPOSURE = "exposure"
    RITUAL = "ritual"
    BOMBARDMENT = "bombardment"
    INDUSTRIAL = "industrial"
    CRASH = "crash"
    RADIATION = "radiation"
    DECOMPRESSION = "decompression"
    EXPERIMENT = "experiment"
    POWER = "power"
    BODY = "body"


class ConditionKind(StrEnum):
    CHRONIC_ILLNESS = "chronic_illness"
    PARANOIA = "paranoia"
    VISIONS = "visions"
    RAGE = "rage"
    MELANCHOLY = "melancholy"
    ADDICTION = "addiction"
    AGE_BLINDNESS = "age_blindness"
    AGE_DEAFNESS = "age_deafness"
    WITHERED_LIMB = "withered_limb"
    ENDLESS_HUNGER = "endless_hunger"
    POSSESSION = "possession"
    VOID_TAINT = "void_taint"
    CHOSEN_MARK = "chosen_mark"
    DIVINE_BRAND = "divine_brand"
    NIGHTMARES = "nightmares"
    COMATOSE = "comatose"
    COGNITIVE_DECLINE = "cognitive_decline"
    MALNUTRITION = "malnutrition"


MADNESS_CONDITIONS = (ConditionKind.PARANOIA, ConditionKind.VISIONS, ConditionKind.RAGE, ConditionKind.MELANCHOLY)


class MedicineTier(StrEnum):
    NONE = "none"
    HERBS = "herbs"
    SURGERY = "surgery"
    PROSTHETICS = "prosthetics"
    REATTACHMENT = "reattachment"
    ANTISEPSIS = "antisepsis"
    ANAESTHESIA = "anaesthesia"
    IMMUNISATION = "immunisation"
    ANTIMICROBIALS = "antimicrobials"
    TRANSPLANTATION = "transplantation"
    REGENERATION = "regeneration"
    GENOME_REPAIR = "genome_repair"
    CELLULAR_MACHINES = "cellular_machines"
    MIND_MEDICINE = "mind_medicine"


MEDICINE_ORDER = (
    MedicineTier.NONE,
    MedicineTier.HERBS,
    MedicineTier.SURGERY,
    MedicineTier.ANTISEPSIS,
    MedicineTier.ANAESTHESIA,
    MedicineTier.PROSTHETICS,
    MedicineTier.IMMUNISATION,
    MedicineTier.ANTIMICROBIALS,
    MedicineTier.REATTACHMENT,
    MedicineTier.TRANSPLANTATION,
    MedicineTier.MIND_MEDICINE,
    MedicineTier.REGENERATION,
    MedicineTier.GENOME_REPAIR,
    MedicineTier.CELLULAR_MACHINES,
)


class Capacity(StrEnum):
    MELEE = "melee"
    MISSILE = "missile"
    COMMAND = "command"
    CRAFT = "craft"
    SCHOLARSHIP = "scholarship"
    PRESENCE = "presence"
    MOBILITY = "mobility"
    FERTILITY = "fertility"


class BodyReading(StrEnum):
    NEUTRAL = "neutral"
    MARTIAL_HONOUR = "martial_honour"
    PURITY = "purity"
    SANCTIFIED_SUFFERING = "sanctified_suffering"


class MaimedKind(StrEnum):
    ONE_ARMED = "one_armed"
    ONE_LEGGED = "one_legged"
    ONE_EYED = "one_eyed"
    BLIND = "blind"
    DEAF = "deaf"
    MUTE = "mute"
    LAME = "lame"
    SCARRED = "scarred"
    BROKEN_MINDED = "broken_minded"


class StrikeStyle(StrEnum):
    NORMAL = "normal"
    TRAMPLE = "trample"
    AERIAL = "aerial"
    LOW = "low"
    WHOLE = "whole"
    RANGED = "ranged"
    BURROWING = "burrowing"
    ENGULFING = "engulfing"
    FROM_HIDING = "from_hiding"


class BodyPart(StrEnum):
    AURA = "aura"
    CORE = "core"
    EYE = "eye"
    FACE = "face"
    FINGERS = "fingers"
    GILLS = "gills"
    GROIN = "groin"
    GUT = "gut"
    HEAD = "head"
    HEART = "heart"
    HORN = "horn"
    JAW = "jaw"
    LEFT_ANTENNA = "left_antenna"
    LEFT_ARM = "left_arm"
    LEFT_BRANCH = "left_branch"
    LEFT_EAR = "left_ear"
    LEFT_EYE = "left_eye"
    LEFT_FIN = "left_fin"
    LEFT_FOOT = "left_foot"
    LEFT_FORELEG = "left_foreleg"
    LEFT_HAND = "left_hand"
    LEFT_HINDLEG = "left_hindleg"
    LEFT_LEG = "left_leg"
    LEFT_MIDLEG = "left_midleg"
    LEFT_WING = "left_wing"
    LUNGS = "lungs"
    NECK = "neck"
    NOSE = "nose"
    PSEUDOPODS = "pseudopods"
    RIGHT_ANTENNA = "right_antenna"
    RIGHT_ARM = "right_arm"
    RIGHT_BRANCH = "right_branch"
    RIGHT_EAR = "right_ear"
    RIGHT_EYE = "right_eye"
    RIGHT_FIN = "right_fin"
    RIGHT_FOOT = "right_foot"
    RIGHT_FORELEG = "right_foreleg"
    RIGHT_HAND = "right_hand"
    RIGHT_HINDLEG = "right_hindleg"
    RIGHT_LEG = "right_leg"
    RIGHT_MIDLEG = "right_midleg"
    RIGHT_WING = "right_wing"
    ROOTS = "roots"
    TAIL = "tail"
    TEETH = "teeth"
    TOES = "toes"
    TONGUE = "tongue"
    TORSO = "torso"
    VENOM_GLAND = "venom_gland"
    WINGS = "wings"


class TissueKind(StrEnum):
    SKIN = "skin"
    SCALE = "scale"
    CHITIN = "chitin"
    BARK = "bark"
    FAT = "fat"
    MUSCLE = "muscle"
    TENDON = "tendon"
    BONE = "bone"
    ARTERY = "artery"
    MOTOR_NERVE = "motor_nerve"
    SENSORY_NERVE = "sensory_nerve"
    ORGAN = "organ"


class NerveDamage(StrEnum):
    NONE = "none"
    MOTOR = "motor"
    SENSORY = "sensory"


class Handedness(StrEnum):
    RIGHT = "right"
    LEFT = "left"
    BOTH = "both"


class Consciousness(StrEnum):
    AWAKE = "awake"
    NAUSEOUS = "nauseous"
    DIZZY = "dizzy"
    UNCONSCIOUS = "unconscious"


class TreatmentStep(StrEnum):
    DIAGNOSE = "diagnose"
    CLEAN = "clean"
    SUTURE = "suture"
    SET_BONE = "set_bone"
    SPLINT = "splint"
    DRESS = "dress"
    AMPUTATE = "amputate"
    CAUTERISE = "cauterise"
    CRUTCH = "crutch"
    TRACTION = "traction"
