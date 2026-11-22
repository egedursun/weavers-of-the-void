from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.body import DamageType, MaimedKind
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.region import DangerSource, HazardSeason, RegionMemoryKind, TerrainHazard


@dataclass(frozen=True)
class DangerSpec:
    label: str
    maimed: MaimedKind | None


@dataclass(frozen=True)
class HazardSpec:
    label: str
    season: HazardSeason
    effect: WeatherEffect
    damage: DamageType


DANGERS = MappingProxyType(
    {
        DangerSource.BEASTS: DangerSpec("Beasts", MaimedKind.SCARRED),
        DangerSource.BANDITS: DangerSpec("Bandits", MaimedKind.SCARRED),
        DangerSource.MONSTERS: DangerSpec("Monsters", MaimedKind.ONE_ARMED),
        DangerSource.PHENOMENA: DangerSpec("Phenomena", MaimedKind.BROKEN_MINDED),
        DangerSource.DISEASE: DangerSpec("Disease", None),
        DangerSource.AVALANCHE: DangerSpec("Avalanches", MaimedKind.ONE_LEGGED),
        DangerSource.QUICKSAND: DangerSpec("Quicksand", None),
        DangerSource.VOLCANIC: DangerSpec("Volcanic ground", MaimedKind.SCARRED),
    }
)

HAZARDS = MappingProxyType(
    {
        TerrainHazard.AVALANCHE: HazardSpec(
            "Avalanche",
            HazardSeason.COLDEST,
            WeatherEffect.COLD,
            DamageType.BLUNT,
        ),
        TerrainHazard.SPRING_FLOOD: HazardSpec(
            "Spring flood",
            HazardSeason.WETTEST,
            WeatherEffect.WET,
            DamageType.BLUNT,
        ),
        TerrainHazard.WILDFIRE: HazardSpec(
            "Wildfire",
            HazardSeason.HOTTEST,
            WeatherEffect.HEAT,
            DamageType.FIRE,
        ),
        TerrainHazard.WHITEOUT: HazardSpec(
            "Whiteout",
            HazardSeason.COLDEST,
            WeatherEffect.COLD,
            DamageType.COLD,
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
