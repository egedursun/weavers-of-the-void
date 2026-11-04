from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.military import HullClass, VesselArmament
from aerona.domain.enums.society import KnowledgeBranch

H = HullClass
V = VesselArmament


@dataclass(frozen=True)
class HullSpec:
    hull: HullClass
    label: str
    speed: int
    range: int
    cargo: int
    crew: int
    seaworthiness: int
    slots: int
    armament: tuple[VesselArmament, ...]
    branch: KnowledgeBranch | None = None
    level: int = 0
    sky: bool = False
    living: bool = False
    strangeness: int = 0


HULLS: MappingProxyType[HullClass, HullSpec] = MappingProxyType(
    {
        spec.hull: spec
        for spec in (
            HullSpec(H.RAFT, "Raft", 15, 10, 20, 4, 10, 0, ()),
            HullSpec(H.BOAT, "Boat", 30, 20, 40, 8, 25, 0, ()),
            HullSpec(H.GALLEY, "Galley", 55, 35, 80, 120, 35, 2, (V.RAMS, V.MISSILES), KnowledgeBranch.SEAFARING, 1),
            HullSpec(H.LONGSHIP, "Longship", 65, 55, 60, 50, 45, 1, (V.RAMS,), KnowledgeBranch.SEAFARING, 1),
            HullSpec(H.COG, "Cog", 40, 60, 200, 25, 55, 1, (V.MISSILES,), KnowledgeBranch.SHIPBUILDING, 1),
            HullSpec(H.CARRACK, "Carrack", 50, 85, 320, 60, 70, 2, (V.MISSILES, V.SIEGE_ENGINES), KnowledgeBranch.SHIPBUILDING, 2),
            HullSpec(H.WARSHIP, "Warship", 50, 70, 120, 200, 65, 3, (V.RAMS, V.MISSILES, V.SIEGE_ENGINES), KnowledgeBranch.SHIPBUILDING, 2),
            HullSpec(H.LIGHT_SAILER, "Light-sailer", 90, 120, 60, 20, 50, 1, (V.MISSILES,), KnowledgeBranch.SKY_NAVIGATION, 2, strangeness=30),
            HullSpec(H.BONE_HULL, "Bone hull", 45, 50, 90, 40, 60, 2, (V.RAMS, V.RITES), KnowledgeBranch.FORBIDDEN, 1, strangeness=45),
            HullSpec(H.GENERATION_SHIP, "Generation ship", 25, 200, 800, 500, 80, 1, (V.RITES,), KnowledgeBranch.VOID_LIVING, 2, strangeness=35),
            HullSpec(H.SKYSHIP, "Skyship", 85, 80, 100, 40, 40, 2, (V.MISSILES, V.RITES), KnowledgeBranch.SKY_NAVIGATION, 1, sky=True, strangeness=20),
            HullSpec(H.LIVING_SHIP, "Living ship", 70, 90, 150, 30, 75, 2, (V.RAMS, V.RITES), KnowledgeBranch.MAGIC, 3, living=True, strangeness=55),
        )
    }
)
SEA_LADDER = (H.CARRACK, H.WARSHIP, H.COG, H.GALLEY, H.LONGSHIP, H.BOAT, H.RAFT)
