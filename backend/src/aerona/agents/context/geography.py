from typing import Any

from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.cartography.model import RegionRecord
from aerona.constants.agents import LARGE_REGION_RATIO, REGION_TERRAIN_SHOWN, SMALL_REGION_RATIO
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import LandUse, RiverClass
from aerona.engine.environment.ley import LeyWeb
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import GeographyLinesContext, RegionGeography
from aerona.prompts.contexts.common import NamedRecord
from aerona.rules.registry import Rules

SIZE_LABELS = ("small", "medium", "large")


def words(value: str) -> str:
    return value.replace("_", " ")


def land_words(ground: RegionEnvironmentRow) -> str | None:
    worked = [(use.value, getattr(ground, use.value)) for use in LandUse if getattr(ground, use.value)]
    return ", ".join(f"{value}% {name}" for name, value in worked) if worked else None


def environment_facts(rules: Rules, ground: RegionEnvironmentRow | None) -> dict[str, Any]:
    if ground is None:
        return {}
    settings = rules.context
    harvest = None
    if ground.harvest_pct < settings.harvest_poor_below_pct:
        harvest = "poor harvests lately"
    elif ground.harvest_pct > settings.harvest_rich_above_pct:
        harvest = "rich harvests lately"
    return {
        "land": words(ground.dominant_terrain.value),
        "soil": words(ground.soil.value),
        "climate": f"{ground.temperature_band.value}, rainfall {ground.rainfall}",
        "river": f"{words(ground.river_class.value)}" if ground.river_class is not RiverClass.NONE else None,
        "scars": [words(kind) for kind, depth in sorted(ground.scars.items()) if depth >= settings.scar_shown_depth],
        "harvest": harvest,
        "use": land_words(ground),
    }


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


async def nexus_names(scope: Scope, region_ids: set[int]) -> dict[int, str]:
    rows = await scope.session.execute(
        select(PlaceEnvironmentRow.region_entity_id, EntityRow.name)
        .join(EntityRow, EntityRow.id == PlaceEnvironmentRow.entity_id)
        .where(PlaceEnvironmentRow.nexus.is_(True), PlaceEnvironmentRow.region_entity_id.in_(list(region_ids)))
    )
    return {region_id: name for region_id, name in rows if region_id is not None}


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
    grounds = {row.entity_id: row for row in await scope.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world_id))}
    web = await LeyWeb.load(scope.session)
    nexus = await nexus_names(scope, set(regions))
    lines = [
        RegionGeography(
            id=record.id,
            name=regions[record.id].name,
            elevation_label=record.elevation_class.value.replace("_", " "),
            coastal=record.coastal,
            size_label=size_label(record.size, mean),
            terrain=[share.name for share in sorted(record.climate, key=lambda share: -share.share_pct)[:REGION_TERRAIN_SHOWN]],
            neighbours=[NamedRecord(id=item, name=regions[item].name) for item in record.neighbours if item in regions],
            **environment_facts(scope.rules, grounds.get(record.id)),
            ley=[NamedRecord(id=other, name=regions[other].name) for other in web.partners(record.id) if other in regions],
            nexus=nexus.get(record.id),
        )
        for record in known
    ]
    return render(PromptId.GEOGRAPHY_LINES, GeographyLinesContext(known_regions=len(lines), regions=lines))
