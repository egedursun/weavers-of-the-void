from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.place_terrain import DEFAULT_KIND, HEIGHT_BONUS, height_of, kind_spec
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.faith import RelicRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.place import PlaceKind, SacredClass
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import flags_by_entity
from aerona.rules.registry import Rules

PROFILE_FIELDS = ("terrain", "cover", "water_source", "height_advantage", "chokepoint")
KIND_LOCK = "kind"
SACREDNESS_LOCK = "sacredness"
NEXUS_FIELD = "nexus"
MYSTERY_KEY = "mystery"


def sacred_base(rules: Rules, sacred: SacredClass) -> int:
    table = rules.places
    if sacred is SacredClass.HOLY:
        return table.sacred_holy_base
    if sacred is SacredClass.NOTABLE:
        return table.sacred_notable_base
    return table.sacred_profane_base


def apply_kind(rules: Rules, ground: PlaceEnvironmentRow, kind: PlaceKind) -> list[str]:
    spec = kind_spec(kind)
    values = {
        "terrain": spec.terrain,
        "cover": spec.cover,
        "water_source": spec.water,
        "height_advantage": clamp_int(height_of(rules, spec.height) + (HEIGHT_BONUS[kind](rules) if kind in HEIGHT_BONUS else 0), 0, PERCENT),
        "chokepoint": spec.chokepoint,
    }
    changed = []
    for key in PROFILE_FIELDS:
        if key in ground.locked or getattr(ground, key) == values[key]:
            continue
        setattr(ground, key, values[key])
        changed.append(key)
    if kind is PlaceKind.NEXUS and NEXUS_FIELD not in ground.locked and not ground.nexus:
        ground.nexus = True
        changed.append(NEXUS_FIELD)
    return changed


async def write_kind(session: AsyncSession, rules: Rules, place_id: int, kind: PlaceKind) -> PlaceProfileRow:
    profile = await session.get(PlaceProfileRow, place_id)
    if profile is None:
        profile = PlaceProfileRow(
            entity_id=place_id, kind=kind, sacredness=sacred_base(rules, kind_spec(kind).sacred), pilgrims=0, secrets_seeded=False, locked=[]
        )
        session.add(profile)
    else:
        profile.kind = kind
    ground = await session.get(PlaceEnvironmentRow, place_id)
    if ground is not None:
        apply_kind(rules, ground, kind)
    await session.flush()
    return profile


@dataclass(frozen=True)
class KindClues:
    lairs: frozenset[int]
    ruins: frozenset[int]
    pilgrimage: frozenset[int]

    @classmethod
    async def load(cls, session: AsyncSession) -> "KindClues":
        lairs = await session.scalars(select(BeastProfileRow.lair_place_id).where(BeastProfileRow.lair_place_id.is_not(None)))
        return cls(
            frozenset(item for item in lairs if item is not None),
            frozenset(await flags_by_entity(session, EntityFlag.RUIN)),
            frozenset(await flags_by_entity(session, EntityFlag.PILGRIMAGE_SITE)),
        )


def typed_kind(place: EntityRow, ground: PlaceEnvironmentRow | None, region: RegionEnvironmentRow | None, clues: KindClues) -> PlaceKind:
    signs = (
        (place.engine_kind is EngineKind.DEAD_GOD, PlaceKind.DEAD_GOD_SITE),
        (place.id in clues.lairs, PlaceKind.LAIR),
        (place.id in clues.ruins, PlaceKind.RUIN),
        (ground is not None and ground.nexus, PlaceKind.NEXUS),
        (place.id in clues.pilgrimage, PlaceKind.SHRINE_SITE),
    )
    found = next((kind for sign, kind in signs if sign), None)
    if found is not None:
        return found
    return TERRAIN[region.dominant_terrain].place_kind if region is not None else DEFAULT_KIND


async def temples_at(session: AsyncSession, place_ids: list[int]) -> dict[int, int]:
    if not place_ids:
        return {}
    rows = await session.execute(
        select(EntityRow.location_id, func.count())
        .where(
            EntityRow.engine_kind == EngineKind.TEMPLE,
            EntityRow.entity_type == EntityType.STRUCTURE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id.in_(place_ids),
        )
        .group_by(EntityRow.location_id)
    )
    return {place_id: count for place_id, count in rows if place_id is not None}


async def relics_at(session: AsyncSession, place_ids: list[int]) -> dict[int, int]:
    if not place_ids:
        return {}
    rows = await session.execute(
        select(RelicRow.shrine_entity_id, func.count()).where(RelicRow.shrine_entity_id.in_(place_ids)).group_by(RelicRow.shrine_entity_id)
    )
    return {place_id: count for place_id, count in rows if place_id is not None}


@dataclass(frozen=True)
class SacredInputs:
    temples: int
    relics: int
    pilgrimage_site: bool
    nexus: bool


def sacred_target(rules: Rules, kind: PlaceKind, inputs: SacredInputs) -> int:
    table = rules.places
    total = (
        sacred_base(rules, kind_spec(kind).sacred)
        + inputs.temples * table.sacred_per_temple
        + inputs.relics * table.sacred_per_relic
        + (table.sacred_pilgrimage_site if inputs.pilgrimage_site else 0)
        + (table.sacred_nexus if inputs.nexus else 0)
    )
    return clamp_int(total, 0, PERCENT)


def drift_toward(current: int, target: int, step: int) -> int:
    if current < target:
        return min(target, current + step)
    return max(target, current - step)


def pilgrims_drawn(rules: Rules, sacredness: int, region_people: int) -> int:
    table = rules.places
    if sacredness < table.pilgrimage_threshold:
        return 0
    return round(region_people * sacredness / PERCENT * table.pilgrim_share_permille / 1000)


async def holy_place_ids(session: AsyncSession, rules: Rules, world_id: int) -> list[int]:
    statement = (
        select(PlaceProfileRow.entity_id, PlaceProfileRow.sacredness, PlaceEnvironmentRow.nexus)
        .join(EntityRow, EntityRow.id == PlaceProfileRow.entity_id)
        .outerjoin(PlaceEnvironmentRow, PlaceEnvironmentRow.entity_id == PlaceProfileRow.entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    )
    rows = [(place_id, sacredness, bool(nexus)) for place_id, sacredness, nexus in await session.execute(statement)]
    holy = [row for row in rows if row[2] or row[1] >= rules.places.holy_site_threshold]
    return [place_id for place_id, _, _ in sorted(holy, key=lambda row: (-row[1], not row[2], row[0]))]


async def place_kind_of(session: AsyncSession, place_id: int) -> PlaceKind:
    profile = await session.get(PlaceProfileRow, place_id)
    return profile.kind if profile is not None else DEFAULT_KIND


async def mystery_held(session: AsyncSession, place_id: int) -> bool:
    found = await session.scalar(
        select(ModifierRow.id).where(
            ModifierRow.target_node_id == place_id, ModifierRow.target_key == MYSTERY_KEY, ModifierRow.source_kind == ModifierSource.PIN
        )
    )
    return found is not None
