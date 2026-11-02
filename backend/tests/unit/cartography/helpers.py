from functools import cache

from aerona.cartography.generator import GeneratedMap, generate_map
from aerona.cartography.model import MapRequest, MarkerInput, PlacementPreference, RegionInput
from aerona.domain.enums.world import WorldType
from aerona.rules.registry import Rules

RULES = Rules()

SAMPLE_REGIONS = (
    RegionInput(id=1),
    RegionInput(id=2, is_water=True),
    RegionInput(id=4),
    RegionInput(id=5, parent_id=1),
    RegionInput(id=6, parent_id=1),
    RegionInput(id=7, parent_id=5),
    RegionInput(id=9, parent_id=5),
)

SAMPLE_MARKERS = (
    MarkerInput(id=3, parent_id=1, preference=PlacementPreference.COASTAL_LOWLAND),
    MarkerInput(id=8, parent_id=3),
    MarkerInput(id=10, parent_id=4, preference=PlacementPreference.HIGHLAND),
    MarkerInput(id=11, parent_id=2),
)


def sample_request(world_type: WorldType = WorldType.ORDINARY, seed: str = "Aerona") -> MapRequest:
    return MapRequest(seed=seed, world_type=world_type, regions=SAMPLE_REGIONS, markers=SAMPLE_MARKERS)


@cache
def sample_map(world_type: WorldType = WorldType.ORDINARY) -> GeneratedMap:
    return generate_map(sample_request(world_type), RULES)
