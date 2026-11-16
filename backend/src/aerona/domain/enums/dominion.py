from enum import StrEnum


class DivineScale(StrEnum):
    ORDER = "order"
    PRODUCTIVITY = "productivity"
    HEAT = "heat"
    GROWTH = "growth"
    FORTUNE = "fortune"
    MAGIC = "magic"


class PerceivedAlignment(StrEnum):
    BENEVOLENT = "benevolent"
    AMBIVALENT = "ambivalent"
    MALEVOLENT = "malevolent"


class WorshipMode(StrEnum):
    DEVOTION = "devotion"
    APPEASEMENT = "appeasement"


class PrayerTone(StrEnum):
    THANKS = "thanks"
    MERCY = "mercy"


class Manifestation(StrEnum):
    RADIANT = "radiant"
    SERENE = "serene"
    STERN = "stern"
    DREADFUL = "dreadful"


class BeliefStance(StrEnum):
    YIELD = "yield"
    RESIST = "resist"
    EMBRACE = "embrace"


class MagicSiteKind(StrEnum):
    SOURCE = "source"
    SCHOOL_SEAT = "school_seat"
    WARD = "ward"
    GATEWAY = "gateway"
    TIDE_POINT = "tide_point"
    DEPLETION_SCAR = "depletion_scar"


class CreatureDeed(StrEnum):
    HUNT_FOLK = "hunt_folk"
    TEND_FIELDS = "tend_fields"
    GUARD_HOLY_SITES = "guard_holy_sites"
    STRIKE_FOES = "strike_foes"
    HEAL_SICK = "heal_sick"
    WRECK_WORKS = "wreck_works"
    WANDER = "wander"
    REST = "rest"


class CreatureLesson(StrEnum):
    REWARD = "reward"
    PUNISH = "punish"
