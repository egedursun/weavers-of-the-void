from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.world import WorldType


@dataclass(frozen=True)
class WorldBody:
    radius: float
    iron: int
    rock: int
    ice: int
    gas: int
    exotic: int
    pressure_factor: float
    albedo: int
    tectonics: int
    volcanism: int
    cryosphere: int
    methane: int
    ammonia: int = 0
    hydrogen: int = 0


W = WorldType
WORLD_BODIES: Mapping[WorldType, WorldBody] = total(
    WorldType,
    {
        W.ORDINARY: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.OCEAN: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.SAND: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.ICE: WorldBody(1.0, 30, 60, 60, 0, 0, 1.0, 70, 50, 20, 80, 0),
        W.LAVA: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 90, 10, 0),
        W.CRYSTAL: WorldBody(1.0, 30, 60, 5, 0, 40, 1.0, 30, 50, 20, 10, 0),
        W.LIVING: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.DEAD: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 0, 0, 10, 0),
        W.DREAM: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.MIRROR: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.GAS: WorldBody(10.0, 5, 5, 5, 85, 0, 1.0, 30, 50, 20, 10, 0, hydrogen=80),
        W.RINGED: WorldBody(10.0, 5, 5, 5, 85, 0, 1.0, 30, 50, 20, 10, 0, hydrogen=80),
        W.ASTEROID_BELT: WorldBody(0.3, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.TIDALLY_LOCKED: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.VOID_POCKET: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.GODS_PALACE: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.GENERATION_SHIP: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.CORPSE_WORLD: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 0, 0, 10, 0),
        W.SUPER_EARTH: WorldBody(1.6, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.ICE_GIANT: WorldBody(10.0, 5, 5, 60, 85, 0, 1.0, 70, 50, 20, 80, 0, ammonia=10, hydrogen=70),
        W.HOT_GIANT: WorldBody(10.0, 5, 5, 5, 85, 0, 1.0, 30, 50, 20, 10, 0, hydrogen=80),
        W.IRON: WorldBody(1.0, 70, 20, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.CARBON: WorldBody(1.0, 30, 60, 5, 0, 40, 1.0, 30, 50, 20, 10, 0),
        W.GREENHOUSE: WorldBody(1.0, 30, 60, 5, 0, 0, 90.0, 30, 50, 20, 10, 0),
        W.DWARF_PLANET: WorldBody(0.3, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.CHTHONIAN: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 0, 90, 10, 0),
        W.HYCEAN: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0, hydrogen=40),
        W.JUNGLE: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.FORGE: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 90, 10, 0),
        W.FUNGAL: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.SHATTERED: WorldBody(0.3, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.HOLLOW: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 0),
        W.ICE_SHELL: WorldBody(1.0, 30, 60, 60, 0, 0, 1.0, 70, 50, 20, 80, 0),
        W.METHANE: WorldBody(1.0, 30, 60, 5, 0, 0, 1.0, 30, 50, 20, 10, 30),
    },
)
