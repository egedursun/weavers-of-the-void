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


class InjuryState(StrEnum):
    FRESH = "fresh"
    INFECTED = "infected"
    HEALING = "healing"
    HEALED_SCAR = "healed_scar"
    PERMANENT = "permanent"
    LETHAL = "lethal"


OPEN_INJURY_STATES = frozenset({InjuryState.FRESH, InjuryState.INFECTED, InjuryState.HEALING})
LASTING_INJURY_STATES = frozenset({InjuryState.PERMANENT, InjuryState.HEALED_SCAR})


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
    RITUAL = "ritual"


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


MADNESS_CONDITIONS = (ConditionKind.PARANOIA, ConditionKind.VISIONS, ConditionKind.RAGE, ConditionKind.MELANCHOLY)


class MedicineTier(StrEnum):
    NONE = "none"
    HERBS = "herbs"
    SURGERY = "surgery"
    PROSTHETICS = "prosthetics"
    REATTACHMENT = "reattachment"


MEDICINE_ORDER = (MedicineTier.NONE, MedicineTier.HERBS, MedicineTier.SURGERY, MedicineTier.PROSTHETICS, MedicineTier.REATTACHMENT)


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
