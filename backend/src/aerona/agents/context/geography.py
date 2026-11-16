from typing import Any

from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.cartography.model import RegionRecord
from aerona.catalog.dangers import DANGERS, MEMORY_LABELS
from aerona.constants.agents import LARGE_REGION_RATIO, SMALL_REGION_RATIO
from aerona.constants.units import PERCENT
from aerona.core.grammar import several, spoken
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.region import PolityMapKnowledgeRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import LandUse, RiverClass
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.dangers import dangers_by_region
from aerona.engine.environment.ley import LeyWeb
from aerona.engine.environment.memory import memories_by_region
from aerona.engine.environment.profile import Works
from aerona.engine.environment.works import region_works
from aerona.engine.lore.calendar_rites import long_days
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
        "climate": f"{spoken(ground.temperature_band)}, rainfall {ground.rainfall}",
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
        parts.append(f"{several(profile.pilgrims, 'pilgrim', 'pilgrims')}")
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


def works_words(works: Works | None) -> str | None:
    if works is None:
        return None
    parts = [f"{count} {label}" for count, label in ((works.bridges, "bridges"), (works.irrigation, "irrigation works"), (works.harbours, "harbours")) if count]
    return ", ".join(parts) or None


def drying_words(rules: Rules, ground: RegionEnvironmentRow | None) -> str | None:
    if ground is None:
        return None
    lost = round(ground.base_forest * ground.cleared / PERCENT * rules.environment.forest_rain_pct / PERCENT)
    return f"rains down {lost} since the forests were cleared" if lost >= rules.context.scar_shown_depth else None


async def season_words(scope: Scope, world_id: int) -> list[str]:
    seasons = list(await scope.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))
    if not seasons:
        return []
    statement = (
        select(EntityRow.name, TraditionProfileRow.season_position)
        .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, TraditionProfileRow.season_position.is_not(None))
        .order_by(EntityRow.name)
    )
    kept: dict[int, list[str]] = {}
    for name, position in await scope.session.execute(statement):
        kept.setdefault(position or 0, []).append(name)
    return [f"{season.name}" + (f" (kept: {', '.join(kept[season.position])})" if season.position in kept else "") for season in seasons]


async def long_day_words(scope: Scope, world_id: int) -> str | None:
    world = await scope.session.get(WorldRow, world_id)
    if not long_days(scope.rules.seasonal.long_day_hours, world) or world is None:
        return None
    return f"A day lasts {several(world.day_length_hours, 'hour', 'hours')}."


async def terrain_facts(scope: Scope, region_ids: set[int], grounds: dict[int, RegionEnvironmentRow]) -> dict[int, dict[str, Any]]:
    settings = scope.rules.context
    terrain = scope.rules.terrain
    dangers = await dangers_by_region(scope.session, region_ids)
    memories = await memories_by_region(scope.session)
    names = {
        row.id: row.name
        for row in await scope.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON))
    }
    mapped: dict[int, list[str]] = {}
    for row in await scope.session.scalars(
        select(PolityMapKnowledgeRow).where(PolityMapKnowledgeRow.region_entity_id.in_(list(region_ids))).order_by(PolityMapKnowledgeRow.level.desc())
    ):
        if row.level >= terrain.unmapped_below and row.polity_entity_id in names:
            mapped.setdefault(row.region_entity_id, []).append(names[row.polity_entity_id])
    found: dict[int, dict[str, Any]] = {}
    for region_id in region_ids:
        ground = grounds.get(region_id)
        sacred = ground.sacredness if ground is not None and ground.sacredness >= terrain.pilgrim_sacred_min else None
        found[region_id] = {
            "dangers": [
                f"{DANGERS[row.source].label.lower()} {row.strength}"
                for row in sorted(dangers.get(region_id, []), key=lambda item: -item.strength)
                if row.strength >= settings.scar_shown_depth
            ],
            "sacredness": sacred,
            "memories": [
                f"{row.title} ({MEMORY_LABELS[row.kind].lower()})"
                for row in sorted(memories.get(region_id, []), key=lambda item: -item.magnitude)
                if row.magnitude >= settings.scar_shown_depth
            ],
            "mapped_by": mapped.get(region_id, []),
        }
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
    works = await region_works(scope.session, book.atlas, scope.rules)
    terrain = await terrain_facts(scope, set(regions), grounds)
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
            works=works_words(works.get(record.id)),
            drying=drying_words(scope.rules, grounds.get(record.id)),
            **terrain[record.id],
        )
        for record in known
    ]
    context = GeographyLinesContext(
        known_regions=len(lines), regions=lines, seasons=await season_words(scope, world_id), long_days=await long_day_words(scope, world_id)
    )
    return render(PromptId.GEOGRAPHY_LINES, context)
