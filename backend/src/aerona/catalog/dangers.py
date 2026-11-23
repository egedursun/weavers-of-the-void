from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body import DamageType, MaimedKind
from aerona.domain.enums.environment import TerrainTrait, WeatherEffect
from aerona.domain.enums.region import DangerSource, HazardSeason, TerrainHazard


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
    traits: frozenset[TerrainTrait] = frozenset()


DANGERS = total(
    DangerSource,
    {
        DangerSource.BEASTS: DangerSpec("Beasts", MaimedKind.SCARRED),
        DangerSource.BANDITS: DangerSpec("Bandits", MaimedKind.SCARRED),
        DangerSource.MONSTERS: DangerSpec("Monsters", MaimedKind.ONE_ARMED),
        DangerSource.PHENOMENA: DangerSpec("Phenomena", MaimedKind.BROKEN_MINDED),
        DangerSource.DISEASE: DangerSpec("Disease", None),
        DangerSource.AVALANCHE: DangerSpec("Avalanches", MaimedKind.ONE_LEGGED),
        DangerSource.QUICKSAND: DangerSpec("Quicksand", None),
        DangerSource.VOLCANIC: DangerSpec("Volcanic ground", MaimedKind.SCARRED),
        DangerSource.LANDSLIDE: DangerSpec("Landslides", MaimedKind.ONE_LEGGED),
        DangerSource.EXPOSURE: DangerSpec("Exposure", MaimedKind.SCARRED),
        DangerSource.CURRENTS: DangerSpec("Currents", None),
        DangerSource.TOXIC_GROUND: DangerSpec("Toxic ground", MaimedKind.BROKEN_MINDED),
        DangerSource.LIGHTNING: DangerSpec("Lightning", MaimedKind.SCARRED),
        DangerSource.SINKHOLE: DangerSpec("Sinkholes", MaimedKind.ONE_LEGGED),
        DangerSource.ROCKFALL: DangerSpec("Rockfall", MaimedKind.ONE_ARMED),
    },
)

HAZARDS = total(
    TerrainHazard,
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
            DamageType.ASPHYXIA,
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
        TerrainHazard.MUDSLIDE: HazardSpec(
            "Mudslide",
            HazardSeason.WETTEST,
            WeatherEffect.WET,
            DamageType.ASPHYXIA,
            frozenset({TerrainTrait.ROUGH}),
        ),
        TerrainHazard.FLASH_FLOOD: HazardSpec(
            "Flash flood",
            HazardSeason.WETTEST,
            WeatherEffect.FLOOD,
            DamageType.ASPHYXIA,
            frozenset({TerrainTrait.ARID}),
        ),
        TerrainHazard.THIN_ICE: HazardSpec(
            "Thin ice",
            HazardSeason.WARMING,
            WeatherEffect.HEAT,
            DamageType.ASPHYXIA,
            frozenset({TerrainTrait.COLD}),
        ),
        TerrainHazard.ICE_JAM: HazardSpec(
            "Ice jam",
            HazardSeason.WARMING,
            WeatherEffect.WET,
            DamageType.BLUNT,
            frozenset({TerrainTrait.COLD}),
        ),
        TerrainHazard.STORM_SURGE: HazardSpec(
            "Storm surge",
            HazardSeason.WETTEST,
            WeatherEffect.WIND,
            DamageType.ASPHYXIA,
            frozenset({TerrainTrait.COASTAL}),
        ),
        TerrainHazard.DUST_STORM: HazardSpec(
            "Dust storm",
            HazardSeason.DRIEST,
            WeatherEffect.WIND,
            DamageType.ASPHYXIA,
            frozenset({TerrainTrait.ARID}),
        ),
    },
)
