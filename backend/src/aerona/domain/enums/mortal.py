from enum import IntEnum, StrEnum


class MortalSex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class Ability(StrEnum):
    ENDURANCE = "endurance"
    WILLPOWER = "willpower"
    PERCEPTION = "perception"
    WISDOM = "wisdom"
    CREATIVITY = "creativity"
    BEAUTY = "beauty"


class LifeStage(StrEnum):
    INFANT = "infant"
    CHILD = "child"
    YOUTH = "youth"
    ADULT = "adult"
    ELDER = "elder"
    ANCIENT = "ancient"


class DeathCause(StrEnum):
    OLD_AGE = "old_age"
    WOUNDS = "wounds"
    BATTLE = "battle"
    DUEL = "duel"
    EXECUTION = "execution"
    MURDER = "murder"
    MONSTER = "monster"
    DISEASE = "disease"
    CHILDBIRTH = "childbirth"
    FAMINE = "famine"
    ACCIDENT = "accident"
    DISASTER = "disaster"
    EXPOSURE = "exposure"
    CURSE = "curse"
    MAGIC = "magic"
    DIVINE = "divine"
    POISON = "poison"
    SACRIFICE = "sacrifice"
    HARDSHIP = "hardship"
    DESPAIR = "despair"
    UNKNOWN = "unknown"


class MarriageKind(StrEnum):
    MONOGAMOUS = "monogamous"
    PLURAL = "plural"
    POLITICAL = "political"


class MarriageEnd(StrEnum):
    DEATH = "death"
    DIVORCE = "divorce"
    ANNULMENT = "annulment"
    WAR = "war"


class CareerPath(StrEnum):
    STAY = "stay"
    ARMY = "army"
    OFFICE = "office"
    APPRENTICE = "apprentice"
    VOWS = "vows"
    TRADE = "trade"
    WANDER = "wander"
    BANDIT = "bandit"


class StressBreak(StrEnum):
    RAGE = "rage"
    FLIGHT = "flight"
    DESPAIR = "despair"
    ZEAL = "zeal"
    VICE = "vice"
    REVELATION = "revelation"


class CrimeKind(StrEnum):
    THEFT = "theft"
    BLASPHEMY = "blasphemy"
    TREASON = "treason"
    MURDER = "murder"
    DESERTION = "desertion"


class PunishmentKind(StrEnum):
    FINE = "fine"
    FLOGGING = "flogging"
    EXILE = "exile"
    BRANDING = "branding"
    HAND = "hand"
    TONGUE = "tongue"
    EYES = "eyes"
    DEATH = "death"


class EquipmentSlot(StrEnum):
    WIELDED_MAIN = "wielded_main"
    WIELDED_OFF = "wielded_off"
    ARMOUR_BODY = "armour_body"
    ARMOUR_HEAD = "armour_head"
    MOUNT = "mount"
    FOCUS = "focus"


class LoyaltyTarget(StrEnum):
    LIEGE = "liege"
    COMMUNITY = "community"
    GOD = "god"


class HarshnessProfile(IntEnum):
    HEROIC = 0
    REALISTIC = 1
    BRUTAL = 2


class HarshnessScale(StrEnum):
    WOUND_LETHALITY = "wound_lethality"
    INFECTION = "infection"
    PERMANENT_INJURY = "permanent_injury"
    DISEASE_DEATH = "disease_death"
    FAMINE_DEATH = "famine_death"
    CHILDBIRTH_DEATH = "childbirth_death"
    BATTLE_LOSS = "battle_loss"
    NOTABLE_SURVIVAL = "notable_survival"
