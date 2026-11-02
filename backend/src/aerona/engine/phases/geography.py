from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.place_terrain import TERRAIN_NATURES
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat
from aerona.language.generator import NameKind


@dataclass(frozen=True)
class Nature:
    subtype: str
    suffix: str
    shifted: str | None


FERTILE = (
    Nature("forest", "Forest", "fertility"),
    Nature("lake", "Lake", "fertility"),
    Nature("valley", "Valley", "fertility"),
    Nature("river", "River", "fertility"),
)
DANGEROUS = (Nature("cave", "Cave", "danger"), Nature("marsh", "Marsh", "danger"), Nature("pass", "Pass", "danger"), Nature("chasm", "Chasm", "danger"))
MAGICAL = (Nature("well", "Well", "mystery"), Nature("stone circle", "Stone Circle", "mystery"), Nature("misty grove", "Misty Grove", "mystery"))
COMMON = (Nature("hill", "Hill", None), Nature("plain", "Plain", None), Nature("cove", "Cove", None), Nature("upland", "Upland", None))
WORLD_NATURES: dict[WorldType, tuple[Nature, ...]] = {
    WorldType.OCEAN: (Nature("island", "Island", "fertility"), Nature("reef", "Reef", "danger")),
    WorldType.SAND: (Nature("oasis", "Oasis", "fertility"), Nature("dune", "Dune", "danger")),
    WorldType.ICE: (Nature("glacier", "Glacier", "danger"), Nature("hot spring", "Hot Spring", "fertility")),
    WorldType.LAVA: (Nature("lava lake", "Lava Lake", "danger"), Nature("ash plain", "Ash Plain", "mystery")),
}


@dataclass(frozen=True)
class SeededPlace:
    place: EntityRow
    moved: EntityRow | None
    text: str


NATURES_BY_SUBTYPE: dict[str, Nature] = {nature.subtype: nature for group in (FERTILE, DANGEROUS, MAGICAL, COMMON, *WORLD_NATURES.values()) for nature in group}


async def nature_of(ctx: TickContext, region: EntityRow) -> Nature:
    settings = ctx.rules.geography
    world = await ctx.session.get(WorldRow, region.world_id)
    pool = list(WORLD_NATURES.get(world.world_type, ())) if world is not None else []
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    if ground is not None:
        shaped = [NATURES_BY_SUBTYPE[subtype] for subtype in TERRAIN_NATURES.get(ground.dominant_terrain, ()) if subtype in NATURES_BY_SUBTYPE]
        pool.extend(shaped * settings.terrain_nature_weight)
    if (stat(region, "fertility") or 0) >= settings.fertile_threshold:
        pool.extend(FERTILE)
    if (stat(region, "danger") or 0) >= settings.dangerous_threshold:
        pool.extend(DANGEROUS)
    if (stat(region, "magic") or 0) >= settings.magical_threshold:
        pool.extend(MAGICAL)
    return ctx.rng(seed_of("nature", region.id)).pick(pool or COMMON)


async def direct_settlements(ctx: TickContext, region_id: int) -> list[EntityRow]:
    settlements = [item for item in await EntityRepository(ctx.session).contents(region_id) if item.entity_type is EntityType.SETTLEMENT]
    return sorted(settlements, key=lambda item: (-(stat(item, "population") or 0), item.id))


async def seed_place(ctx: TickContext, region: EntityRow, *, move: bool | None = None, by: str | None = None) -> SeededPlace:
    settings = ctx.rules.geography
    nature = await nature_of(ctx, region)
    rng = ctx.rng(seed_of("seed_place", region.id))
    settlements = await direct_settlements(ctx, region.id)
    neighbours = settlements or [item for item in await EntityRepository(ctx.session).contents(region.id) if item.entity_type in COMMUNITY_TYPES]
    derived = (
        await Namer(ctx.session, ctx.rules).from_speaker(neighbours[0].id, seed_of(region.id, ctx.epoch, "geography"), NameKind.PLACE) if neighbours else None
    )
    half = settings.place_stat_die // 2
    values = {key: clamp_int(settings.place_stat + rng.integer(-half, half), 0, 100) for key in ("danger", "fertility", "mystery")}
    if nature.shifted is not None:
        values[nature.shifted] = clamp_int(values[nature.shifted] + settings.stat_shift, 0, 100)
    hand = f" by the hand of {by}" if by is not None else ""
    place = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PLACE,
            name=derived or f"{region.name} {nature.suffix}",
            body=f"A {nature.subtype} of {region.name} that entered the map{hand}; until then it was a nameless corner of the region.",
            stats=PlaceStats(**values),
            power=settings.place_power,
            location_id=region.id,
            world_id=region.world_id,
            subtype=nature.subtype,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if derived else (),
        ),
    )
    moved: EntityRow | None = None
    if settlements and (move if move is not None else rng.chance(settings.move_chance)):
        moved = settlements[0]
        await EntityRepository(ctx.session).move(moved, place.id, ctx.epoch)
    edge = f"; {moved.name} stands at its edge" if moved is not None else ""
    text = f"A {nature.subtype} of {region.name} entered the map: {place.name}{edge}."
    await note(ctx, text, key="geography.place_seeded", ids=[place.id, region.id, *([moved.id] if moved is not None else [])])
    return SeededPlace(place, moved, text)


async def geography(ctx: TickContext) -> None:
    settings = ctx.rules.geography
    if not settings.seed_cap:
        return
    places = set(
        await ctx.session.scalars(select(EntityRow.location_id).where(EntityRow.entity_type == EntityType.PLACE, EntityRow.status == EntityStatus.CANON))
    )
    inhabited = {community.location_id for community in await canon(ctx.session, COMMUNITY_TYPES)}
    empty = [region for region in await canon(ctx.session, [EntityType.REGION]) if region.id not in places]
    empty.sort(key=lambda region: (region.id not in inhabited, region.id))
    rng = ctx.rng("seed")
    seeded = 0
    for region in empty:
        if seeded >= settings.seed_cap:
            break
        if not rng.chance(min(100, settings.seed_chance * (2 if region.id in inhabited else 1))):
            continue
        await seed_place(ctx, region)
        seeded += 1
    ctx.count("seeded", seeded)
    await ctx.session.flush()


async def seed_place_by_hand(ctx: TickContext, region_id: int, by: str) -> SeededPlace:
    region = await living_entity(ctx.session, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise ValidationFailedError("Choose a living region.")
    return await seed_place(ctx, region, move=True, by=by)


PHASES = (Phase("geography", geography),)
