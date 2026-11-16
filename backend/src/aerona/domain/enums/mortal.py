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
    INDUSTRIAL = "industrial"
    CRASH = "crash"
    RADIATION = "radiation"
    DECOMPRESSION = "decompression"
    EXPERIMENT = "experiment"
    BOMBARDMENT = "bombardment"


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
    STUDY = "study"


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
    WITCHCRAFT = "witchcraft"
    MIND_THEFT = "mind_theft"
    UNLICENSED_COPYING = "unlicensed_copying"
    FORCED_EDIT = "forced_edit"
    ERASURE = "erasure"
    MACHINE_SEIZURE = "machine_seizure"
    IMPERSONATION = "impersonation"


class PunishmentKind(StrEnum):
    FINE = "fine"
    FLOGGING = "flogging"
    EXILE = "exile"
    BRANDING = "branding"
    HAND = "hand"
    TONGUE = "tongue"
    EYES = "eyes"
    DEATH = "death"
    PUBLIC_SHAMING = "public_shaming"
    IMPRISONMENT = "imprisonment"
    REMAKING = "remaking"
    FORCED_DORMANCY = "forced_dormancy"
    FORCED_EDIT = "forced_edit"
    SEAT_CONFINEMENT = "seat_confinement"
    STATE_SEIZURE = "state_seizure"
    ERASURE = "erasure"


class EquipmentSlot(StrEnum):
    WIELDED_MAIN = "wielded_main"
    WIELDED_OFF = "wielded_off"
    ARMOUR_BODY = "armour_body"
    ARMOUR_HEAD = "armour_head"
    ARMOUR_UNDER = "armour_under"
    ARMOUR_COVER = "armour_cover"
    MOUNT = "mount"
    FOCUS = "focus"


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
