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
    LANDSLIDE = "landslide"
    EXPOSURE = "exposure"
    CURRENTS = "currents"
    TOXIC_GROUND = "toxic_ground"
    LIGHTNING = "lightning"
    SINKHOLE = "sinkhole"
    ROCKFALL = "rockfall"


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
    CROPS = "crops"
    VESSELS = "vessels"
    STRUCTURES = "structures"
    PILGRIMS = "pilgrims"
    WORKERS = "workers"


class TerrainHazard(StrEnum):
    AVALANCHE = "avalanche"
    SPRING_FLOOD = "spring_flood"
    WILDFIRE = "wildfire"
    WHITEOUT = "whiteout"
    MUDSLIDE = "mudslide"
    FLASH_FLOOD = "flash_flood"
    THIN_ICE = "thin_ice"
    ICE_JAM = "ice_jam"
    STORM_SURGE = "storm_surge"
    DUST_STORM = "dust_storm"


class HazardSeason(StrEnum):
    COLDEST = "coldest"
    WETTEST = "wettest"
    HOTTEST = "hottest"
    WARMING = "warming"
    DRIEST = "driest"


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
    FOUNDING = "founding"
    TREATY = "treaty"
    EXPULSION = "expulsion"
    DISCOVERY = "discovery"
    UPRISING = "uprising"
    UNION = "union"
    ACCESSION = "accession"


class MemoryOrigin(StrEnum):
    DERIVED = "derived"
    PLAYER = "player"
