from enum import StrEnum


class DivineScale(StrEnum):
    ORDER = "order"
    PRODUCTIVITY = "productivity"
    HEAT = "heat"
    GROWTH = "growth"
    FORTUNE = "fortune"
    MAGIC = "magic"
    HEALTH = "health"
    PEACE = "peace"


class PerceivedAlignment(StrEnum):
    BENEVOLENT = "benevolent"
    AMBIVALENT = "ambivalent"
    MALEVOLENT = "malevolent"


class WorshipMode(StrEnum):
    DEVOTION = "devotion"
    APPEASEMENT = "appeasement"
    BARGAIN = "bargain"
    UNION = "union"
    KINSHIP = "kinship"


class PrayerTone(StrEnum):
    THANKS = "thanks"
    MERCY = "mercy"
    REQUEST = "request"
    PRAISE = "praise"
    LAMENT = "lament"
    CONFESSION = "confession"


class Manifestation(StrEnum):
    RADIANT = "radiant"
    SERENE = "serene"
    STERN = "stern"
    DREADFUL = "dreadful"
    VEILED = "veiled"
    PLAYFUL = "playful"
    SORROWFUL = "sorrowful"


class BeliefStance(StrEnum):
    YIELD = "yield"
    RESIST = "resist"
    EMBRACE = "embrace"
    BARGAIN = "bargain"


class MagicSiteKind(StrEnum):
    SOURCE = "source"
    SCHOOL_SEAT = "school_seat"
    WARD = "ward"
    GATEWAY = "gateway"
    TIDE_POINT = "tide_point"
    DEPLETION_SCAR = "depletion_scar"
    CONFLUENCE = "confluence"
    NULL_ZONE = "null_zone"


class CreatureDeed(StrEnum):
    HUNT_FOLK = "hunt_folk"
    TEND_FIELDS = "tend_fields"
    GUARD_HOLY_SITES = "guard_holy_sites"
    STRIKE_FOES = "strike_foes"
    HEAL_SICK = "heal_sick"
    WRECK_WORKS = "wreck_works"
    WANDER = "wander"
    REST = "rest"
    CARRY_MESSAGES = "carry_messages"
    TEACH = "teach"
    TRADE = "trade"


class CreatureLesson(StrEnum):
    REWARD = "reward"
    PUNISH = "punish"
    WARN = "warn"
