from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import DamageType, MaimedKind
from aerona.domain.enums.environment import TerrainKind, WeatherEffect
from aerona.domain.enums.region import DangerSource, HazardSeason, RegionMemoryKind, TerrainHazard


@dataclass(frozen=True)
class DangerSpec:
    label: str
    settlers_line: str
    maimed: MaimedKind | None


@dataclass(frozen=True)
class HazardSpec:
    label: str
    terrains: frozenset[TerrainKind]
    season: HazardSeason
    effect: WeatherEffect
    damage: DamageType
    words: str
    line: str


DANGERS = MappingProxyType(
    {
        DangerSource.BEASTS: DangerSpec("Beasts", "Wild beasts took {count} of {community} on the paths and pastures of {region}", MaimedKind.SCARRED),
        DangerSource.BANDITS: DangerSpec("Bandits", "Bandits preyed on {community} along the roads of {region}; {count} did not come home", MaimedKind.SCARRED),
        DangerSource.MONSTERS: DangerSpec("Monsters", "Monsters stalked {region} and {count} of {community} were taken", MaimedKind.ONE_ARMED),
        DangerSource.PHENOMENA: DangerSpec(
            "Strange phenomena", "Phenomena in {region} led {count} of {community} away, and they were not found", MaimedKind.BROKEN_MINDED
        ),
        DangerSource.DISEASE: DangerSpec("Disease", "Disease of the land of {region} killed {count} of {community}", None),
        DangerSource.AVALANCHE: DangerSpec("Avalanches", "Snow slid down the slopes of {region} and buried {count} of {community}", MaimedKind.ONE_LEGGED),
        DangerSource.QUICKSAND: DangerSpec("Quicksand", "Quicksand in {region} took {count} of {community}", None),
        DangerSource.VOLCANIC: DangerSpec(
            "Volcanic ground", "Fumes and fire from the volcanic ground of {region} killed {count} of {community}", MaimedKind.SCARRED
        ),
    }
)

HAZARDS = MappingProxyType(
    {
        TerrainHazard.AVALANCHE: HazardSpec(
            "Avalanche",
            frozenset({TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS, TerrainKind.ICE_SHEET}),
            HazardSeason.COLDEST,
            WeatherEffect.COLD,
            DamageType.BLUNT,
            "caught under an avalanche",
            "An avalanche came down on {region} in {season}: {deaths} died",
        ),
        TerrainHazard.SPRING_FLOOD: HazardSpec(
            "Spring flood",
            frozenset({TerrainKind.RIVER_VALLEY, TerrainKind.MARSH, TerrainKind.PLAIN, TerrainKind.COAST}),
            HazardSeason.WETTEST,
            WeatherEffect.WET,
            DamageType.BLUNT,
            "struck by flood debris",
            "The rivers of {region} burst their banks in {season}: {deaths} drowned",
        ),
        TerrainHazard.WILDFIRE: HazardSpec(
            "Wildfire",
            frozenset({TerrainKind.FOREST, TerrainKind.JUNGLE, TerrainKind.STEPPE, TerrainKind.HILLS}),
            HazardSeason.HOTTEST,
            WeatherEffect.HEAT,
            DamageType.FIRE,
            "burned in a wildfire",
            "Wildfire swept the dry woods of {region} in {season}: {deaths} died in the flames",
        ),
        TerrainHazard.WHITEOUT: HazardSpec(
            "Whiteout",
            frozenset({TerrainKind.TUNDRA, TerrainKind.ICE_SHEET, TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS}),
            HazardSeason.COLDEST,
            WeatherEffect.COLD,
            DamageType.COLD,
            "frostbitten in a whiteout",
            "A whiteout closed over {region} in {season}: {deaths} froze before they found shelter",
        ),
    }
)

MEMORY_LABELS = MappingProxyType(
    {
        RegionMemoryKind.BATTLE: "Battle",
        RegionMemoryKind.MASSACRE: "Massacre",
        RegionMemoryKind.SACK: "Sack",
        RegionMemoryKind.DISASTER: "Disaster",
        RegionMemoryKind.PLAGUE: "Plague",
        RegionMemoryKind.FAMINE: "Famine",
        RegionMemoryKind.GOD_DEATH: "A god fell here",
        RegionMemoryKind.SAINT_BURIAL: "Saint's grave",
        RegionMemoryKind.MIRACLE: "Miracle",
    }
)
