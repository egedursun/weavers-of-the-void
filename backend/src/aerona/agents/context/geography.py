from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.cartography.model import RegionRecord
from aerona.constants.agents import LARGE_REGION_RATIO, REGION_TERRAIN_SHOWN, SMALL_REGION_RATIO
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import GeographyLinesContext, RegionGeography
from aerona.prompts.contexts.common import NamedRecord

SIZE_LABELS = ("small", "medium", "large")


def size_label(size: int, mean: float) -> str:
    if mean <= 0:
        return SIZE_LABELS[1]
    ratio = size / mean
    if ratio < SMALL_REGION_RATIO:
        return SIZE_LABELS[0]
    return SIZE_LABELS[2] if ratio > LARGE_REGION_RATIO else SIZE_LABELS[1]


async def region_records(scope: Scope, world_id: int) -> list[RegionRecord]:
    world_map = await scope.session.get(WorldMapRow, world_id)
    if world_map is None or not isinstance(world_map.geometry, dict):
        return []
    return [RegionRecord.model_validate(item) for item in world_map.geometry.get("regions", [])]


async def geography_lines(scope: Scope, world_id: int | None) -> str:
    if world_id is None:
        return ""
    records = await region_records(scope, world_id)
    regions = {
        region.id: region
        for region in await scope.session.scalars(
            select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        )
    }
    known = [record for record in records if record.id in regions]
    if not known:
        return ""
    mean = sum(record.size for record in known) / len(known)
    lines = [
        RegionGeography(
            id=record.id,
            name=regions[record.id].name,
            elevation_label=record.elevation_class.value.replace("_", " "),
            coastal=record.coastal,
            size_label=size_label(record.size, mean),
            terrain=[share.name for share in sorted(record.climate, key=lambda share: -share.share_pct)[:REGION_TERRAIN_SHOWN]],
            neighbours=[NamedRecord(id=item, name=regions[item].name) for item in record.neighbours if item in regions],
        )
        for record in known
    ]
    return render(PromptId.GEOGRAPHY_LINES, GeographyLinesContext(known_regions=len(lines), regions=lines))
