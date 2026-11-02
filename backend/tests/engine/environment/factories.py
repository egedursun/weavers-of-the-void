from typing import Any

from aerona.cartography.model import RegionGeography
from aerona.domain.enums.environment import CoastKind, RiverClass
from tests.engine.society.factories import region_record


def mapped_region(
    region_id: int,
    *,
    neighbours: list[int],
    mix: list[int] | None = None,
    latitude: int = 30,
    moisture: int = 50,
    roughness: int = 30,
    river: RiverClass = RiverClass.RIVER,
    coast: CoastKind = CoastKind.NONE,
) -> dict[str, Any]:
    record = region_record(region_id, neighbours=neighbours, coastal=coast is not CoastKind.NONE)
    record["geography"] = RegionGeography(
        biome_mix=mix or [0, 0, 0, 0, 100, 0, 0, 0, 0, 0],
        elevation_mean=20,
        roughness=roughness,
        moisture=moisture,
        latitude=latitude,
        forest=30,
        wetland=10,
        river_flow=50.0,
        river_class=river,
        coast_kind=coast,
        land_share=100,
    ).model_dump(mode="json")
    return record
