import numpy as np
from numpy.typing import NDArray

from aerona.cartography.biomes import Biome
from aerona.cartography.context import MapContext
from aerona.cartography.model import RegionGeography
from aerona.constants.cartography import BIOME_COUNT
from aerona.constants.units import PERCENT
from aerona.domain.enums.environment import CoastKind, RiverClass

WET_BIOMES = (Biome.WET_LOWLAND, Biome.WET_HILLS)
HALF = 0.5


def flow_accumulation(context: MapContext) -> NDArray[np.float64]:
    elevation = context.normalized
    land = ~context.water
    flow = np.where(land, 1.0 + np.clip(context.moisture, 0.0, None), 0.0)
    for cell in np.argsort(-elevation, kind="stable").tolist():
        if not land[cell]:
            continue
        neighbours = context.mesh.neighbours[cell]
        if not neighbours:
            continue
        lowest = min(neighbours, key=lambda other: (elevation[other], other))
        if elevation[lowest] < elevation[cell]:
            flow[lowest] += flow[cell] if land[lowest] else 0.0
    return flow


def latitudes(context: MapContext) -> NDArray[np.float64]:
    window = context.mesh.window
    span = max(1.0, window.height * context.rules.cartography.latitude_span_pct / PERCENT)
    centre = window.top + window.height / 2
    return np.clip(np.abs(context.mesh.points[:, 1] - centre) / (span / 2), 0.0, 1.0)


def _percent(value: float) -> int:
    return round(min(1.0, max(0.0, value)) * PERCENT)


def _river_class(context: MapContext, flow: float) -> RiverClass:
    settings = context.rules.cartography
    if flow >= settings.great_river_flow:
        return RiverClass.GREAT_RIVER
    if flow >= settings.river_flow:
        return RiverClass.RIVER
    if flow >= settings.stream_flow:
        return RiverClass.STREAM
    return RiverClass.NONE


def _coast(context: MapContext, cells: NDArray[np.int64], coastal: NDArray[np.bool_], biomes: NDArray[np.int64], river: RiverClass) -> CoastKind:
    settings = context.rules.cartography
    shore_cells = cells[coastal[cells]]
    if not len(shore_cells):
        return CoastKind.NONE
    if river in (RiverClass.RIVER, RiverClass.GREAT_RIVER):
        return CoastKind.HARBOUR_SITE
    shallow = sum(1 for cell in shore_cells.tolist() for other in context.mesh.neighbours[cell] if biomes[other] == Biome.SHALLOW_WATER) / max(
        1, sum(len(context.mesh.neighbours[cell]) for cell in shore_cells.tolist())
    )
    if shallow * PERCENT >= settings.reef_shallow_share_pct:
        return CoastKind.REEF
    beach = float(np.mean(biomes[shore_cells] == Biome.SHORE))
    if float(context.normalized[shore_cells].mean()) * PERCENT >= settings.cliff_elevation_pct and beach < HALF:
        return CoastKind.CLIFF
    return CoastKind.BEACH


def region_geography(
    context: MapContext,
    cells: NDArray[np.int64],
    *,
    biomes: NDArray[np.int64],
    coastal: NDArray[np.bool_],
    flow: NDArray[np.float64],
    latitude: NDArray[np.float64],
) -> RegionGeography | None:
    if not len(cells):
        return None
    settings = context.rules.cartography
    counts = np.bincount(biomes[cells], minlength=BIOME_COUNT)
    shares = [round(int(count) * PERCENT / len(cells)) for count in counts.tolist()]
    land = cells[~context.water[cells]]
    measured = land if len(land) else cells
    elevation = context.normalized[measured]
    moisture = context.moisture[measured]
    wet_share = sum(int(counts[biome]) for biome in WET_BIOMES) / len(cells)
    mid_share = int(counts[Biome.MID_LOWLAND]) / len(cells)
    river_flow = float(flow[measured].max()) if len(land) else 0.0
    river = _river_class(context, river_flow)
    delta = float(np.mean(coastal[measured] & (flow[measured] >= settings.stream_flow))) if len(land) else 0.0
    lowland_wet = int(counts[Biome.WET_LOWLAND]) / len(cells)
    return RegionGeography(
        biome_mix=shares,
        elevation_mean=_percent(float(np.clip(elevation, 0.0, None).mean())),
        roughness=_percent(float(elevation.std()) * settings.roughness_scale_pct / PERCENT),
        moisture=_percent(float(moisture.mean())),
        latitude=_percent(float(latitude[measured].mean())),
        forest=_percent((wet_share + mid_share * settings.mid_lowland_forest_pct / PERCENT) * float(np.clip(moisture.mean() * 2, 0.0, 1.0))),
        wetland=_percent(lowland_wet * settings.wet_lowland_wetland_pct / PERCENT + delta * settings.delta_wetland_pct / PERCENT),
        river_flow=round(river_flow, 1),
        river_class=river,
        coast_kind=_coast(context, cells, coastal, biomes, river),
        land_share=_percent(len(land) / len(cells)),
    )
