from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.scope import Scope
from aerona.cartography.model import RegionRecord
from aerona.catalog.dangers import DANGERS, HAZARDS
from aerona.catalog.land_memory import LAND_MEMORIES
from aerona.catalog.named_years import NAMED_YEARS
from aerona.catalog.rocks import ROCKS
from aerona.catalog.scars import SCARS
from aerona.catalog.strata import STRATA
from aerona.catalog.weather import WEATHER
from aerona.constants.agents import LARGE_REGION_RATIO, SMALL_REGION_RATIO
from aerona.constants.units import PERCENT
from aerona.core.grammar import several, spoken
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.geology import RegionGeologyRow, RegionStratumRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.region import PolityMapKnowledgeRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import LandUse, MovementMode, RiverClass, ScarKind
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.columns import columns_by_region, deepest_reached
from aerona.engine.environment.dangers import dangers_by_region
from aerona.engine.environment.hazards import exposed
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
        "land": spoken(ground.dominant_terrain),
        "soil": f"{spoken(ground.soil)} (fertility {ground.soil_fertility})",
        "climate": f"{spoken(ground.temperature_band)}, rainfall {ground.rainfall}",
        "river": f"{spoken(ground.river_class)}" if ground.river_class is not RiverClass.NONE else None,
        "scars": [f"{SCARS[ScarKind(kind)].label.lower()} {depth}" for kind, depth in sorted(ground.scars.items()) if depth >= settings.scar_shown_depth],
        "growth": spoken(ground.succession),
        "hazards": [f"{spec.label.lower()} in the {spoken(spec.season)} season" for hazard, spec in HAZARDS.items() if exposed(rules, hazard, spec, ground)],
        "harvest": harvest,
        "use": land_words(ground),
        "passage": [f"{spoken(mode)} {passage}" for mode, passage in passages(ground)],
    }


def passages(ground: RegionEnvironmentRow) -> list[tuple[MovementMode, int]]:
    found = [(mode, ground.passability.get(mode.value, 0)) for mode in MovementMode]
    return sorted([item for item in found if item[1] > 0], key=lambda item: (-item[1], item[0].value))


NAMED_YEARS_SHOWN = 5


def named_year_words(row: NotableYearRow, kept: list[str]) -> str:
    kind = NAMED_YEARS[row.kind]
    source = WEATHER[row.weather].label.lower() if row.weather is not None else kind.sources
    remembered = f"; remembered by {', '.join(kept)}" if kept else ""
    return f"{row.name} (year {row.year}, {kind.label.lower()} from {source}, magnitude {row.magnitude}{remembered})"


async def named_years(scope: Scope, world_id: int) -> dict[int | None, list[str]]:
    rows = list(
        await scope.session.scalars(
            select(NotableYearRow).where(NotableYearRow.world_id == world_id).order_by(NotableYearRow.magnitude.desc(), NotableYearRow.year, NotableYearRow.id)
        )
    )
    kept: dict[int, list[str]] = {}
    statement = (
        select(TraditionProfileRow.notable_year_id, EntityRow.name)
        .join(EntityRow, EntityRow.id == TraditionProfileRow.tradition_entity_id)
        .where(TraditionProfileRow.notable_year_id.in_([row.id for row in rows]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.name)
    )
    for year_id, name in await scope.session.execute(statement):
        if year_id is not None:
            kept.setdefault(year_id, []).append(name)
    found: dict[int | None, list[str]] = {}
    for row in rows:
        shown = found.setdefault(row.region_entity_id, [])
        if len(shown) < NAMED_YEARS_SHOWN:
            shown.append(named_year_words(row, kept.get(row.id, [])))
    return found


BENEATH_TOP = 3
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
    parts = [spoken(profile.kind)]
    if profile.sacredness >= rules.places.pilgrimage_threshold:
        parts.append(f"sacred {profile.sacredness}")
    if profile.pilgrims:
        parts.append(f"{several(profile.pilgrims, 'pilgrim', 'pilgrims')}")
    for secret in known:
        state = ", still sealed" if secret.sealed else ""
        parts.append(f"found {spoken(secret.kind)}{state}")
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
    parts = [
        several(count, one, many)
        for count, one, many in (
            (works.bridges, "bridge", "bridges"),
            (works.irrigation, "irrigation work", "irrigation works"),
            (works.harbours, "harbour", "harbours"),
        )
        if count
    ]
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


def beneath_words(rows: list[RegionGeologyRow], depths: list[RegionStratumRow]) -> dict[str, Any] | None:
    if not rows:
        return None
    deepest = deepest_reached(rows)
    veins = sorted({material for row in rows if row.reached_epoch is not None for material in row.veins})
    return {
        "top": [ROCKS[row.rock].label.lower() for row in rows[:BENEATH_TOP]],
        "deepest_reached": ROCKS[deepest.rock].label.lower() if deepest is not None else None,
        "veins_reached": [words(vein) for vein in veins],
        "depths_reached": [STRATA[row.stratum].label.lower() for row in depths if row.reached_epoch is not None],
    }


async def depths_by_region(session: AsyncSession, region_ids: list[int]) -> dict[int, list[RegionStratumRow]]:
    found: dict[int, list[RegionStratumRow]] = {}
    for row in await session.scalars(select(RegionStratumRow).where(RegionStratumRow.region_entity_id.in_(region_ids)).order_by(RegionStratumRow.id)):
        found.setdefault(row.region_entity_id, []).append(row)
    return found


async def terrain_facts(scope: Scope, region_ids: set[int], grounds: dict[int, RegionEnvironmentRow]) -> dict[int, dict[str, Any]]:
    settings = scope.rules.context
    terrain = scope.rules.terrain
    dangers = await dangers_by_region(scope.session, region_ids)
    memories = await memories_by_region(scope.session)
    columns = await columns_by_region(scope.session, sorted(region_ids))
    depths = await depths_by_region(scope.session, sorted(region_ids))
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
                f"{DANGERS[row.source].label.lower()} {row.strength}" + (f" (harms {', '.join(words(harm) for harm in row.harmed)})" if row.harmed else "")
                for row in sorted(dangers.get(region_id, []), key=lambda item: -item.strength)
                if row.strength >= settings.scar_shown_depth
            ],
            "sacredness": sacred,
            "memories": [
                f"{row.title} ({LAND_MEMORIES[row.kind].label.lower()})"
                for row in sorted(memories.get(region_id, []), key=lambda item: -item.magnitude)
                if row.magnitude >= settings.scar_shown_depth
            ],
            "mapped_by": mapped.get(region_id, []),
            "beneath": beneath_words(columns.get(region_id, []), depths.get(region_id, [])),
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
    years = await named_years(scope, world_id)
    lines = [
        RegionGeography(
            id=record.id,
            name=regions[record.id].name,
            elevation_label=spoken(record.elevation_class),
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
            named_years=years.get(record.id, []),
            **terrain[record.id],
        )
        for record in known
    ]
    context = GeographyLinesContext(
        known_regions=len(lines),
        regions=lines,
        seasons=await season_words(scope, world_id),
        long_days=await long_day_words(scope, world_id),
        named_years=years.get(None, []),
    )
    return render(PromptId.GEOGRAPHY_LINES, context)
