from enum import StrEnum


class DangerSource(StrEnum):
    BEASTS = "beasts"
    BANDITS = "bandits"
    MONSTERS = "monsters"
    PHENOMENA = "phenomena"
    DISEASE = "disease"
    AVALANCHE = "avalanche"
    QUICKSAND = "quicksand"
    VOLCANIC = "volcanic"


class DangerOrigin(StrEnum):
    DERIVED = "derived"
    PLAYER = "player"
    DIVINE = "divine"


class DangerHarm(StrEnum):
    SETTLERS = "settlers"
    LIVESTOCK = "livestock"
    TRAVELLERS = "travellers"
    ARMIES = "armies"
    AMBUSH = "ambush"
    MERCHANTS = "merchants"


class TerrainHazard(StrEnum):
    AVALANCHE = "avalanche"
    SPRING_FLOOD = "spring_flood"
    WILDFIRE = "wildfire"
    WHITEOUT = "whiteout"


class HazardSeason(StrEnum):
    COLDEST = "coldest"
    WETTEST = "wettest"
    HOTTEST = "hottest"


class RegionMemoryKind(StrEnum):
    BATTLE = "battle"
    MASSACRE = "massacre"
    SACK = "sack"
    DISASTER = "disaster"
    PLAGUE = "plague"
    FAMINE = "famine"
    GOD_DEATH = "god_death"
    SAINT_BURIAL = "saint_burial"
    MIRACLE = "miracle"


class MemoryOrigin(StrEnum):
    DERIVED = "derived"
    PLAYER = "player"
