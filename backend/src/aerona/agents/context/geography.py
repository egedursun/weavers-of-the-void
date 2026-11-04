from typing import Any

from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.cartography.model import RegionRecord
from aerona.constants.agents import LARGE_REGION_RATIO, SMALL_REGION_RATIO
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import LandUse, RiverClass
from aerona.engine.environment.book import EnvironmentBook
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


CONTEXT_WEATHER_SLOT = "context"


def weather_words(scope: Scope, book: EnvironmentBook, ground: RegionEnvironmentRow | None) -> str | None:
    if ground is None:
        return None
    season = book.season_at(ground.world_id, scope.epoch)
    weather = book.weather(scope.cosmos.rng_seed, scope.epoch, ground, season, CONTEXT_WEATHER_SLOT)
    return f"{season.name.lower()}, {weather.label.lower()}" if season is not None else weather.label.lower()


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


def place_words(place: EntityRow, profile: PlaceProfileRow, known: list[PlaceSecretRow], rules: Rules) -> str:
    parts = [words(profile.kind.value)]
    if profile.sacredness >= rules.places.pilgrimage_threshold:
        parts.append(f"sacred {profile.sacredness}")
    if profile.pilgrims:
        parts.append(f"{profile.pilgrims} pilgrims")
    for secret in known:
        state = ", still sealed" if secret.sealed else ""
        parts.append(f"found {words(secret.kind.value)}{state}")
    return f"#{place.id} {place.name} ({', '.join(parts)})"


async def place_lines(scope: Scope, region_ids: set[int]) -> dict[int, list[str]]:
    rows = list(
        await scope.session.execute(
            select(EntityRow, PlaceProfileRow, PlaceEnvironmentRow.region_entity_id)
            .join(PlaceProfileRow, PlaceProfileRow.entity_id == EntityRow.id)
            .join(PlaceEnvironmentRow, PlaceEnvironmentRow.entity_id == EntityRow.id)
            .where(EntityRow.status == EntityStatus.CANON, PlaceEnvironmentRow.region_entity_id.in_(list(region_ids)))
            .order_by(EntityRow.id)
        )
    )
    place_ids = [place.id for place, _, _ in rows]
    known: dict[int, list[PlaceSecretRow]] = {}
    for secret in await scope.session.scalars(
        select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id.in_(place_ids), PlaceSecretRow.revealed_epoch.is_not(None)).order_by(PlaceSecretRow.id)
    ):
        known.setdefault(secret.place_entity_id, []).append(secret)
    found: dict[int, list[str]] = {}
    for place, profile, region_id in rows:
        if region_id is not None:
            found.setdefault(region_id, []).append(place_words(place, profile, known.get(place.id, []), scope.rules))
    return found


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
    book = await EnvironmentBook.load(scope.session, scope.rules, scope.epoch)
    places = await place_lines(scope, set(regions))
    lines = [
        RegionGeography(
            id=record.id,
            name=regions[record.id].name,
            elevation_label=record.elevation_class.value.replace("_", " "),
            coastal=record.coastal,
            size_label=size_label(record.size, mean),
            terrain=[f"{share.share_pct}% {share.name}" for share in sorted(record.climate, key=lambda share: (-share.share_pct, share.name))],
            neighbours=[NamedRecord(id=item, name=regions[item].name) for item in record.neighbours if item in regions],
            **environment_facts(scope.rules, grounds.get(record.id)),
            ley=[NamedRecord(id=other, name=regions[other].name) for other in web.partners(record.id) if other in regions],
            nexus=nexus.get(record.id),
            weather=weather_words(scope, book, grounds.get(record.id)),
            places=places.get(record.id, []),
        )
        for record in known
    ]
    return render(PromptId.GEOGRAPHY_LINES, GeographyLinesContext(known_regions=len(lines), regions=lines))
