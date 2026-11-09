from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import (
    CelestialReadingRow,
    ClusterRow,
    CosmicBeingProfileRow,
    DimensionalEventRow,
    DimensionRow,
    GalacticEventRow,
    GalacticStructureRow,
    GalaxyRow,
    PhenomenonFootprintRow,
    PhenomenonProfileRow,
    RiftRow,
)
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import (
    ApocalypseVariant,
    BeingKind,
    ClusterKind,
    DimensionalEventKind,
    DimensionElement,
    DimensionKind,
    GalacticEventKind,
    GalacticStructureKind,
    GalaxyType,
    OmenReading,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    SkyObject,
)
from aerona.domain.enums.divine import LawScope
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.world import Discovery
from aerona.domain.models.records import CargoLine, PassengerLine
from aerona.engine.context import TickContext
from aerona.engine.cosmos import dimensions as planes
from aerona.engine.cosmos import galaxies as heavens
from aerona.engine.cosmos.beings import banish_being, bind_being, create_being
from aerona.engine.cosmos.climate import ClimateTurn, turn_region
from aerona.engine.cosmos.ladder import ClusterDraft, DimensionDraft, GalaxyDraft, create_cluster, create_dimension, create_galaxy, settle_star
from aerona.engine.cosmos.phenomena import contain, form_phenomenon
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import open_rift, seal_rift
from aerona.engine.divine.control import apply
from aerona.engine.divine.laws import profile_for
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import connect, living_entity

Values = Mapping[str, Any]
NAME = "name"


async def found[Row](ctx: TickContext, kind: type[Row], key: object, label: str) -> Row:
    row = await ctx.session.get(kind, key)
    if row is None:
        raise NotFoundError(f"No such {label}.")
    return row


async def rename(ctx: TickContext, node_id: int, values: Values) -> dict[str, Any]:
    rest = dict(values)
    name = rest.pop(NAME, None)
    if name is not None:
        if not str(name).strip():
            raise ValidationFailedError("A name cannot be empty.")
        names = NameRepository(ctx.session)
        if await names.is_taken(str(name), ignore_node_id=node_id):
            raise ValidationFailedError(f'"{name}" is already used in the cosmos; choose another name.')
        await names.rename(node_id, str(name))
    return rest


def parent_chain(rows: Mapping[int, Any], start: int | None, attribute: str) -> set[int]:
    seen: set[int] = set()
    while start is not None and start not in seen:
        seen.add(start)
        row = rows.get(start)
        start = getattr(row, attribute) if row is not None else None
    return seen


async def resettle(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    for star in cosmography.stars.values():
        settle_star(ctx.rules, cosmography, star)
    await ctx.session.flush()


async def new_dimension(
    ctx: TickContext, name: str, kind: DimensionKind, *, parent_id: int | None, element: DimensionElement | None, description: str | None
) -> DimensionRow:
    if parent_id is not None:
        await found(ctx, DimensionRow, parent_id, "dimension")
    return await create_dimension(ctx.session, ctx.rules, DimensionDraft(name, kind, ctx.epoch, parent_id, element, description))


async def edit_dimension(ctx: TickContext, dimension_id: int, values: Values, release: list[str]) -> DimensionRow:
    row = await found(ctx, DimensionRow, dimension_id, "dimension")
    rest = await rename(ctx, row.id, values)
    parent = rest.get("parent_dimension_id")
    if parent is not None:
        rows = {item.id: item for item in await ctx.session.scalars(select(DimensionRow))}
        if row.id in parent_chain(rows, int(parent), "parent_dimension_id"):
            raise ValidationFailedError("A dimension cannot lie inside itself.")
    ruler = rest.get("ruler_node_id")
    if ruler is not None and await ctx.session.get(NodeRow, int(ruler)) is None:
        raise NotFoundError("No such ruler.")
    apply(row, rest, release)
    if row.dimension_kind is not DimensionKind.ELEMENTAL:
        row.element = None
    await ctx.session.flush()
    return row


async def remove_dimension(ctx: TickContext, dimension_id: int) -> None:
    row = await found(ctx, DimensionRow, dimension_id, "dimension")
    for cluster in await ctx.session.scalars(select(ClusterRow).where(ClusterRow.dimension_id == row.id)):
        cluster.dimension_id = row.parent_dimension_id
    for galaxy in await ctx.session.scalars(select(GalaxyRow).where(GalaxyRow.dimension_id == row.id)):
        galaxy.dimension_id = row.parent_dimension_id
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.dimension_id == row.id)):
        world.dimension_id = row.parent_dimension_id
    for child in await ctx.session.scalars(select(DimensionRow).where(DimensionRow.parent_dimension_id == row.id)):
        child.parent_dimension_id = row.parent_dimension_id
    await ctx.session.delete(row)
    await ctx.session.flush()


async def new_cluster(
    ctx: TickContext, name: str, kind: ClusterKind, *, dimension_id: int | None, parent_id: int | None, position: tuple[float, float, float]
) -> ClusterRow:
    if parent_id is not None:
        await found(ctx, ClusterRow, parent_id, "cluster")
    if dimension_id is not None:
        await found(ctx, DimensionRow, dimension_id, "dimension")
    x, y, radius = position
    return await create_cluster(ctx.session, ctx.rules, ClusterDraft(name, kind, ctx.epoch, dimension_id, parent_id, x, y, radius))


async def edit_cluster(ctx: TickContext, cluster_id: int, values: Values, release: list[str]) -> ClusterRow:
    row = await found(ctx, ClusterRow, cluster_id, "cluster")
    rest = await rename(ctx, row.id, values)
    parent = rest.get("parent_cluster_id")
    if parent is not None:
        rows = {item.id: item for item in await ctx.session.scalars(select(ClusterRow))}
        if row.id in parent_chain(rows, int(parent), "parent_cluster_id"):
            raise ValidationFailedError("A cluster cannot lie inside itself.")
        rest["dimension_id"] = None
    elif rest.get("dimension_id") is not None:
        rest["parent_cluster_id"] = None
    apply(row, rest, release)
    await ctx.session.flush()
    return row


async def remove_cluster(ctx: TickContext, cluster_id: int) -> None:
    row = await found(ctx, ClusterRow, cluster_id, "cluster")
    cosmography = await Cosmography.load(ctx.session)
    home = cosmography.dimension_of_cluster(row)
    for galaxy in await ctx.session.scalars(select(GalaxyRow).where(GalaxyRow.cluster_id == row.id)):
        galaxy.cluster_id = row.parent_cluster_id
        galaxy.dimension_id = None if row.parent_cluster_id is not None else (home.id if home is not None else None)
    for child in await ctx.session.scalars(select(ClusterRow).where(ClusterRow.parent_cluster_id == row.id)):
        child.parent_cluster_id = row.parent_cluster_id
        child.dimension_id = None if row.parent_cluster_id is not None else (home.id if home is not None else None)
    await ctx.session.delete(row)
    await ctx.session.flush()


async def new_galaxy(
    ctx: TickContext, name: str, galaxy_type: GalaxyType, *, cluster_id: int | None, dimension_id: int | None, position: tuple[float, float, float]
) -> GalaxyRow:
    if cluster_id is not None:
        await found(ctx, ClusterRow, cluster_id, "cluster")
    if dimension_id is not None:
        await found(ctx, DimensionRow, dimension_id, "dimension")
    x, y, radius = position
    return await create_galaxy(ctx.session, ctx.rules, GalaxyDraft(name, galaxy_type, ctx.epoch, cluster_id, dimension_id, x, y, radius))


async def edit_galaxy(ctx: TickContext, galaxy_id: int, values: Values, release: list[str]) -> GalaxyRow:
    row = await found(ctx, GalaxyRow, galaxy_id, "galaxy")
    rest = await rename(ctx, row.id, values)
    if rest.get("cluster_id") is not None:
        rest["dimension_id"] = None
    elif rest.get("dimension_id") is not None:
        rest["cluster_id"] = None
    if rest.get("merging_with_galaxy_id") == row.id:
        raise ValidationFailedError("A galaxy cannot merge with itself.")
    apply(row, rest, release)
    await ctx.session.flush()
    await resettle(ctx)
    return row


async def remove_galaxy(ctx: TickContext, galaxy_id: int) -> None:
    row = await found(ctx, GalaxyRow, galaxy_id, "galaxy")
    for star in await ctx.session.scalars(select(StarRow).where(StarRow.galaxy_id == row.id)):
        star.galaxy_id = None
        star.structure_id = None
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.galaxy_id == row.id)):
        world.galaxy_id = None
    for other in await ctx.session.scalars(select(GalaxyRow).where(GalaxyRow.merging_with_galaxy_id == row.id)):
        other.merging_with_galaxy_id = None
        other.merge_progress = 0
    await ctx.session.delete(row)
    await ctx.session.flush()
    await resettle(ctx)


async def new_structure(
    ctx: TickContext, galaxy_id: int, kind: GalacticStructureKind, *, name: str, position: tuple[float, float, float], intensity: int
) -> GalacticStructureRow:
    await found(ctx, GalaxyRow, galaxy_id, "galaxy")
    x, y, radius = position
    if radius <= 0:
        raise ValidationFailedError("A structure needs a radius above zero.")
    row = GalacticStructureRow(
        galaxy_id=galaxy_id,
        kind=kind,
        name=name.strip() or kind.value,
        x=x,
        y=y,
        radius=radius,
        intensity=clamp_percent(intensity),
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await resettle(ctx)
    return row


async def edit_structure(ctx: TickContext, structure_id: int, values: Values, release: list[str]) -> GalacticStructureRow:
    row = apply(await found(ctx, GalacticStructureRow, structure_id, "galactic structure"), values, release)
    await ctx.session.flush()
    await resettle(ctx)
    return row


async def remove_structure(ctx: TickContext, structure_id: int) -> None:
    row = await found(ctx, GalacticStructureRow, structure_id, "galactic structure")
    for star in await ctx.session.scalars(select(StarRow).where(StarRow.structure_id == row.id)):
        star.structure_id = None
    await ctx.session.delete(row)
    await ctx.session.flush()
    await resettle(ctx)


async def galactic_event(
    ctx: TickContext, galaxy_id: int, kind: GalacticEventKind, *, intensity: int, other_id: int | None, star_id: int | None
) -> GalacticEventRow:
    galaxy = await found(ctx, GalaxyRow, galaxy_id, "galaxy")
    other = await found(ctx, GalaxyRow, other_id, "galaxy") if other_id is not None else None
    star = await found(ctx, StarRow, star_id, "star") if star_id is not None else None
    cosmography = await Cosmography.load(ctx.session)
    stars = sorted(cosmography.stars_in_galaxy(galaxy.id), key=lambda row: row.id)
    rng = ctx.rng(f"ordered_galactic.{galaxy.id}.{kind.value}")
    if kind is GalacticEventKind.STARBURST:
        galaxy.star_formation = clamp_percent(galaxy.star_formation + intensity)
    elif kind is GalacticEventKind.GAMMA_RAY_BURST:
        await heavens.gamma_burst(ctx, cosmography, galaxy)
    elif kind is GalacticEventKind.NEBULA_COLLAPSE:
        await heavens.collapse_cloud(ctx, cosmography, galaxy, rng)
    elif kind is GalacticEventKind.SEVERING and len(stars) > 1:
        await heavens.sever(ctx, cosmography, galaxy, stars)
    elif kind is GalacticEventKind.MERGER_BEGUN and other is not None:
        galaxy.merging_with_galaxy_id = other.id
        galaxy.merge_progress = 0
        await heavens.shorten_routes(ctx, cosmography, galaxy, other)
    elif kind is GalacticEventKind.MERGER_COMPLETED and other is not None:
        await heavens.absorb(ctx, cosmography, other, galaxy)
    elif kind is GalacticEventKind.HYPERVELOCITY_STAR and (star or stars):
        flung = star or rng.pick(stars)
        flung.galaxy_id = None
        settle_star(ctx.rules, cosmography, flung)
    elif kind in (GalacticEventKind.GALACTIC_DIMMING, GalacticEventKind.AWAKENING):
        sign = -1 if kind is GalacticEventKind.GALACTIC_DIMMING else 1
        for item in stars:
            item.brightness = clamp_percent(item.brightness + sign * intensity // 10)
    elif kind is GalacticEventKind.SHROUDING:
        galaxy.discovery = Discovery.LEGEND
    return await heavens.open_event(ctx, galaxy, kind, intensity, other=other, star=star)


async def edit_galactic_event(ctx: TickContext, event_id: int, values: Values) -> GalacticEventRow:
    row = apply(await found(ctx, GalacticEventRow, event_id, "galactic event"), values, [])
    await ctx.session.flush()
    return row


async def remove_galactic_event(ctx: TickContext, event_id: int) -> None:
    await ctx.session.delete(await found(ctx, GalacticEventRow, event_id, "galactic event"))
    await ctx.session.flush()


async def dimensional_event(
    ctx: TickContext, dimension_id: int, kind: DimensionalEventKind, *, intensity: int, other_id: int | None, world_id: int | None
) -> DimensionalEventRow:
    dimension = await found(ctx, DimensionRow, dimension_id, "dimension")
    other = await found(ctx, DimensionRow, other_id, "dimension") if other_id is not None else None
    world = await found(ctx, WorldRow, world_id, "world") if world_id is not None else None
    cosmography = await Cosmography.load(ctx.session)
    if kind is DimensionalEventKind.VEIL_THINNING:
        dimension.veil = clamp_percent(dimension.veil - intensity)
    elif kind is DimensionalEventKind.PLANAR_ALIGNMENT:
        for item in cosmography.dimensions.values():
            item.veil = clamp_percent(item.veil - intensity)
    elif kind is DimensionalEventKind.CONVERGENCE:
        other = other or planes.neighbour_of(cosmography, dimension)
    elif kind is DimensionalEventKind.SCHISM:
        other = await create_dimension(
            ctx.session, ctx.rules, DimensionDraft(f"{dimension.name} Branch", DimensionKind.QUANTUM_BRANCH, ctx.epoch, parent_dimension_id=dimension.id)
        )
    elif kind is DimensionalEventKind.INCURSION and world is not None:
        being = await create_being(ctx, BeingKind.RIFT_SPAWN, world, home_dimension_id=dimension.id)
        return await planes.open_event(ctx, dimension, kind, intensity, other=other, world=world, subject_id=being.id)
    elif kind is DimensionalEventKind.BLEED and world is not None:
        world.time_factor = max(0.01, world.time_factor + (dimension.time_factor - world.time_factor) * intensity / 100)
    elif kind is DimensionalEventKind.COLLAPSE:
        dimension.stability = 0
    return await planes.open_event(ctx, dimension, kind, intensity, other=other, world=world)


async def edit_dimensional_event(ctx: TickContext, event_id: int, values: Values) -> DimensionalEventRow:
    row = apply(await found(ctx, DimensionalEventRow, event_id, "dimensional event"), values, [])
    await ctx.session.flush()
    return row


async def remove_dimensional_event(ctx: TickContext, event_id: int) -> None:
    await ctx.session.delete(await found(ctx, DimensionalEventRow, event_id, "dimensional event"))
    await ctx.session.flush()


async def tear_rift(
    ctx: TickContext, world_id: int, region_id: int | None, *, dimension_id: int, target_world_id: int | None, by_node_id: int | None, cause: RiftCause
) -> RiftRow:
    world = await found(ctx, WorldRow, world_id, "world")
    region = await living_entity(ctx.session, region_id) if region_id is not None else None
    dimension = await found(ctx, DimensionRow, dimension_id, "dimension")
    target = await found(ctx, WorldRow, target_world_id, "world") if target_world_id is not None else None
    return await open_rift(ctx, world, region, dimension, cause, by_node_id=by_node_id, target_world=target)


async def edit_rift(ctx: TickContext, rift_id: int, values: Values, release: list[str]) -> RiftRow:
    row = apply(await found(ctx, RiftRow, rift_id, "rift"), values, release)
    await ctx.session.flush()
    return row


async def close_rift(ctx: TickContext, rift_id: int, by: str) -> RiftRow:
    return await seal_rift(ctx, rift_id, by)


async def remove_rift(ctx: TickContext, rift_id: int) -> None:
    row = await found(ctx, RiftRow, rift_id, "rift")
    route = await ctx.session.get(RouteRow, row.route_id) if row.route_id is not None else None
    if route is not None:
        route.active = False
    await ctx.session.delete(row)
    await ctx.session.flush()


async def call_being(ctx: TickContext, kind: BeingKind, world_id: int, *, region_id: int | None, home_dimension_id: int | None, name: str | None) -> EntityRow:
    world = await found(ctx, WorldRow, world_id, "world")
    region = await living_entity(ctx.session, region_id) if region_id is not None else None
    if home_dimension_id is not None:
        await found(ctx, DimensionRow, home_dimension_id, "dimension")
    return await create_being(ctx, kind, world, region=region, home_dimension_id=home_dimension_id, name=name)


async def edit_being(ctx: TickContext, entity_id: int, values: Values, release: list[str]) -> CosmicBeingProfileRow:
    row = apply(await found(ctx, CosmicBeingProfileRow, entity_id, "cosmic being"), values, release)
    await ctx.session.flush()
    return row


async def bind(ctx: TickContext, entity_id: int, binder_id: int, by: str) -> CosmicBeingProfileRow:
    if await ctx.session.get(NodeRow, binder_id) is None:
        raise NotFoundError("No such binder.")
    return await bind_being(ctx, entity_id, binder_id, by)


async def banish(ctx: TickContext, entity_id: int, by: str) -> CosmicBeingProfileRow:
    return await banish_being(ctx, entity_id, by)


async def new_phenomenon(ctx: TickContext, kind: PhenomenonKind, region_id: int, intensity: int, cause: PhenomenonCause) -> EntityRow:
    region = await living_entity(ctx.session, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise ValidationFailedError("A phenomenon forms in a region.")
    made = await form_phenomenon(ctx, kind, region, cause, intensity=intensity)
    if made is None:
        raise ValidationFailedError(f"{region.name} is held; nothing forms there.")
    return made


async def edit_phenomenon(ctx: TickContext, entity_id: int, values: Values, release: list[str]) -> PhenomenonProfileRow:
    row = apply(await found(ctx, PhenomenonProfileRow, entity_id, "phenomenon"), values, release)
    await ctx.session.flush()
    return row


async def set_footprint(ctx: TickContext, entity_id: int, region_id: int, intensity: int | None) -> PhenomenonFootprintRow | None:
    await found(ctx, PhenomenonProfileRow, entity_id, "phenomenon")
    region = await living_entity(ctx.session, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise ValidationFailedError("A phenomenon covers regions.")
    row = await ctx.session.get(PhenomenonFootprintRow, (entity_id, region_id))
    if intensity is None:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = PhenomenonFootprintRow(phenomenon_entity_id=entity_id, region_entity_id=region_id, intensity=clamp_percent(intensity))
        ctx.session.add(row)
    row.intensity = clamp_percent(intensity)
    await ctx.session.flush()
    return row


async def ward_phenomenon(ctx: TickContext, entity_id: int, amount: int, by: str) -> PhenomenonProfileRow:
    return await contain(ctx, entity_id, amount, by)


async def edit_star_life(ctx: TickContext, star_id: int, values: Values, release: list[str]) -> StarRow:
    row = apply(await found(ctx, StarRow, star_id, "star"), values, release)
    await ctx.session.flush()
    if "galactic_zone" not in values and "structure_id" not in values:
        settle_star(ctx.rules, await Cosmography.load(ctx.session), row)
    return row


async def edit_world_life(ctx: TickContext, world_id: int, values: Values, release: list[str]) -> WorldRow:
    row = await found(ctx, WorldRow, world_id, "world")
    placed = {key for key in ("galaxy_id", "dimension_id") if values.get(key) is not None}
    if placed and (row.star_id is not None or row.parent_world_id is not None):
        raise ValidationFailedError(f"{row.name} lies where its star lies; move its star, or free it from its star first.")
    rest = dict(values)
    if "galaxy_id" in placed:
        rest["dimension_id"] = None
    elif "dimension_id" in placed:
        rest["galaxy_id"] = None
    apply(row, rest, release)
    await ctx.session.flush()
    return row


async def edit_route_flow(ctx: TickContext, route_id: int, values: Values, release: list[str]) -> RouteRow:
    row = await found(ctx, RouteRow, route_id, "route")
    controller = values.get("toll_controller_entity_id")
    if controller is not None and await living_entity(ctx.session, int(controller)) is None:
        raise NotFoundError("No such toll keeper.")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def load_journey(
    ctx: TickContext, journey_id: int, *, convoy: int | None, escorts: int | None, cargo: list[CargoLine] | None, passengers: list[PassengerLine] | None
) -> JourneyRow:
    row = await found(ctx, JourneyRow, journey_id, "journey")
    locked = set(row.locked)
    for key, value in (("convoy", convoy), ("escorts", escorts)):
        if value is not None:
            if value < (1 if key == "convoy" else 0):
                raise ValidationFailedError(f"{key.capitalize()} cannot go that low.")
            setattr(row, key, value)
            locked.add(key)
    if cargo is not None:
        row.cargo = cargo
        locked.add("cargo")
    if passengers is not None:
        row.passengers = passengers
        locked.add("passengers")
    row.locked = sorted(locked)
    await ctx.session.flush()
    return row


async def release_journey(ctx: TickContext, journey_id: int, fields: list[str]) -> JourneyRow:
    row = await found(ctx, JourneyRow, journey_id, "journey")
    row.locked = [item for item in row.locked if item not in fields]
    await ctx.session.flush()
    return row


async def set_reading(ctx: TickContext, celestial_id: int, people_id: int, reading: OmenReading | None) -> CelestialReadingRow | None:
    body = await living_entity(ctx.session, celestial_id)
    people = await living_entity(ctx.session, people_id)
    if body is None or body.entity_type is not EntityType.CELESTIAL or people is None or people.entity_type is not EntityType.PEOPLE:
        raise ValidationFailedError("A reading joins a celestial body and a people.")
    row = await ctx.session.get(CelestialReadingRow, (celestial_id, people_id))
    if reading is None:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = CelestialReadingRow(celestial_entity_id=celestial_id, people_entity_id=people_id, reading=reading, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.reading = reading
    row.locked = ["reading"]
    await ctx.session.flush()
    return row


async def set_variant(ctx: TickContext, variant: ApocalypseVariant | None) -> CosmosRow:
    cosmos: CosmosRow | None = await ctx.session.scalar(select(CosmosRow))
    if cosmos is None:
        raise NotFoundError("No cosmos.")
    cosmos.apocalypse_variant = variant
    await ctx.session.flush()
    return cosmos


async def turn_climate(ctx: TickContext, region_id: int, turn: ClimateTurn, by: str) -> None:
    await turn_region(ctx, region_id, turn, by)


async def bind_law(ctx: TickContext, dimension_id: int, law_id: int) -> NaturalLawProfileRow:
    dimension = await found(ctx, DimensionRow, dimension_id, "dimension")
    law = await ctx.session.get(EntityRow, law_id)
    if law is None or law.entity_type is not EntityType.NATURAL_LAW:
        raise NotFoundError("No such natural law.")
    profile = await profile_for(ctx, law)
    if profile is None:
        raise ValidationFailedError(f"{law.name} has no effect to hold across a dimension.")
    ladder = await Cosmography.load(ctx.session)
    homes = sorted(world.id for world in ladder.worlds.values() if ladder.place_world(world).dimension_id == dimension.id)
    if not homes:
        raise ValidationFailedError(f"No world lies in {dimension.name} yet, so no law can hold across it.")
    profile.scope = LawScope.DIMENSION
    profile.world_id = profile.world_id if profile.world_id in homes else homes[0]
    profile.region_entity_id = None
    await ctx.session.flush()
    return profile


async def release_law(ctx: TickContext, law_id: int) -> NaturalLawProfileRow:
    profile = await ctx.session.get(NaturalLawProfileRow, law_id)
    if profile is None or profile.scope is not LawScope.DIMENSION:
        raise ValidationFailedError("This law holds across no dimension.")
    profile.scope = LawScope.WORLD
    await ctx.session.flush()
    return profile


async def set_sky_worship(ctx: TickContext, community_id: int, sky: SkyObject, worships: bool, dimension_id: int | None = None) -> str:
    community = await ctx.session.get(EntityRow, community_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES or community.status is not EntityStatus.CANON:
        raise NotFoundError("No such people or settlement.")
    ladder = await Cosmography.load(ctx.session)
    place = ladder.place_world_id(community.world_id)
    if sky is SkyObject.DIMENSION:
        dimension = await found(ctx, DimensionRow, dimension_id, "dimension") if dimension_id is not None else place.dimension
        if dimension is None:
            raise ValidationFailedError(f"{community.name} lies in no dimension.")
        if worships:
            await connect(ctx.session, community.id, dimension.id, BondKind.WORSHIPS, ctx.epoch, description="worships it")
        else:
            await BondRepository(ctx.session).close_between(community.id, dimension.id, [BondKind.WORSHIPS], ctx.epoch)
        await ctx.session.flush()
        return dimension.name
    target = place.star if sky is SkyObject.STAR else place.galaxy
    if target is None:
        raise ValidationFailedError(f"No {sky.value} shines over {community.name}.")
    flag = EntityFlag.WORSHIPS_STAR if sky is SkyObject.STAR else EntityFlag.WORSHIPS_GALAXY
    entities = EntityRepository(ctx.session)
    if worships:
        await entities.add_flag(community.id, flag, ctx.epoch)
    else:
        await entities.remove_flag(community.id, flag)
    await ctx.session.flush()
    return target.name
