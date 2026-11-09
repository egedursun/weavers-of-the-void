from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.cosmography import BEING_AGENDAS, BEING_KINDS, BEING_SCALES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, DimensionalEventRow, DimensionRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, BeingAgenda, BeingKind, BeingPhase, BeingScale, DimensionalEventKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.models.entity_stats import CosmicBeingStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.kinds import BEING_MECHANICS
from aerona.engine.cosmos.placement import Cosmography, Placement
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.interconnect.annotations import reads
from aerona.engine.intrigue.identities import assume
from aerona.engine.notes import note
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_bounded


async def create_being(
    ctx: TickContext,
    kind: BeingKind,
    world: WorldRow,
    *,
    region: EntityRow | None = None,
    home_dimension_id: int | None = None,
    name: str | None = None,
    mirrored: EntityRow | None = None,
    phase: BeingPhase = BeingPhase.ROAMING,
    agenda: BeingAgenda | None = None,
) -> EntityRow:
    spec = BEING_KINDS[kind]
    cosmography = await Cosmography.load(ctx.session)
    placement = cosmography.place_world(world)
    might = BEING_MECHANICS[kind].might(ctx.rules)
    label = name or (f"Echo of {mirrored.name}" if mirrored is not None else f"{spec.label} of {world.name}")
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.COSMIC_BEING,
            name=label,
            body=spec.description,
            stats=CosmicBeingStats(size=might, interest=PERCENT // 2, renown=might // 2),
            power=max(1, might // 10),
            world_id=world.id,
            location_id=region.id if region is not None else (mirrored.location_id if mirrored is not None else None),
        ),
    )
    ctx.session.add(
        CosmicBeingProfileRow(
            entity_id=entity.id,
            being_kind=kind,
            home_dimension_id=home_dimension_id if home_dimension_id is not None else placement.dimension_id,
            galaxy_id=placement.galaxy_id,
            scale=BEING_SCALES[kind],
            might=might,
            phase=phase,
            agenda=agenda or BEING_AGENDAS[kind],
            mirrored_entity_id=mirrored.id if mirrored is not None else None,
            manifest_epochs=0,
            locked=[],
        )
    )
    await ctx.session.flush()
    await note(
        ctx,
        f"{entity.name} came into {world.name}: {spec.description}",
        key=f"being.arrived.{kind.value}",
        ids=[entity.id],
        world_id=world.id,
        kind=ChronicleKind.COSMIC,
    )
    return entity


async def worlds_in_reach(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> list[WorldRow]:
    here = cosmography.place_world_id(being.world_id)
    found: list[WorldRow] = []
    for world in sorted(cosmography.worlds.values(), key=lambda row: row.id):
        place = cosmography.place_world(world)
        reach = {
            BeingScale.WORLD: world.id == being.world_id,
            BeingScale.SYSTEM: place.star is not None and here.star is not None and place.star.id == here.star.id,
            BeingScale.GALAXY: place.galaxy_id == here.galaxy_id,
            BeingScale.CLUSTER: place.top_cluster is not None and here.top_cluster is not None and place.top_cluster.id == here.top_cluster.id,
            BeingScale.DIMENSION: place.dimension_id == here.dimension_id,
        }[profile.scale]
        if reach and not held(world.id):
            found.append(world)
    return found


async def move_to(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow, world: WorldRow) -> None:
    if "world_id" in profile.locked or world.id == being.world_id:
        return
    being.world_id = world.id
    being.location_id = None
    profile.galaxy_id = cosmography.place_world(world).galaxy_id


async def cross(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> bool:
    table = ctx.rules.cosmic_beings
    here = cosmography.place_world_id(being.world_id).dimension
    through = await ctx.session.scalar(
        select(RiftRow)
        .where(RiftRow.state.in_(list(OPEN_RIFT_STATES)), RiftRow.size >= ctx.rules.rifts.crossing_size, RiftRow.target_world_id.is_not(None))
        .where((RiftRow.world_id == being.world_id) | (RiftRow.target_world_id == being.world_id))
        .order_by(RiftRow.id)
        .limit(1)
    )
    if through is not None:
        other = through.target_world_id if through.world_id == being.world_id else through.world_id
        world = cosmography.worlds.get(other or 0)
        if world is not None and not held(world.id):
            await move_to(ctx, cosmography, being, profile, world)
            profile.rift_id = through.id
            return True
    if here is None or here.veil >= table.cross_veil:
        return False
    others = [row for row in cosmography.worlds.values() if cosmography.place_world(row).dimension_id not in (None, here.id) and not held(row.id)]
    if not others:
        return False
    await move_to(ctx, cosmography, being, profile, ctx.rng(f"being_cross.{being.id}").pick(sorted(others, key=lambda row: row.id)))
    return True


async def record_incursion(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow, region: EntityRow) -> None:
    dimension = profile.home_dimension_id or cosmography.place_world_id(being.world_id).dimension_id
    if dimension is None:
        return
    ctx.session.add(
        DimensionalEventRow(
            kind=DimensionalEventKind.INCURSION,
            dimension_id=dimension,
            world_id=being.world_id,
            region_entity_id=region.id,
            subject_entity_id=being.id,
            epoch=ctx.epoch,
            until_epoch=ctx.epoch,
            intensity=profile.might,
            text=f"{being.name} broke into {region.name}.",
        )
    )


@dataclass
class Scene:
    ctx: TickContext
    cosmography: Cosmography
    being: EntityRow
    profile: CosmicBeingProfileRow
    world: WorldRow
    placement: Placement
    regions: list[EntityRow]
    rng: SeededRandom


async def feed(scene: Scene) -> None:
    table = scene.ctx.rules.cosmic_beings
    star = scene.placement.star
    if scene.profile.being_kind is BeingKind.STAR_EATER and star is not None and not held(star.id) and "brightness" not in star.locked:
        star.brightness = clamp_percent(star.brightness - table.feed_brightness)
        return
    for region in scene.regions:
        shift_bounded(scene.ctx.rules, region, "magic", -table.feed_magic)


async def conquer(scene: Scene) -> None:
    table = scene.ctx.rules.cosmic_beings
    if not scene.regions or not scene.rng.chance(table.incursion_chance):
        return
    region = scene.rng.pick(scene.regions)
    scene.profile.phase = BeingPhase.INCURSION
    await apply_disaster(scene.ctx, region, Disaster.EARTHQUAKE, table.incursion_severity / PERCENT)
    await record_incursion(scene.ctx, scene.cosmography, scene.being, scene.profile, region)
    await note(
        scene.ctx,
        f"{scene.being.name} broke into {region.name}.",
        key="being.incursion",
        ids=[scene.being.id, region.id],
        world_id=scene.world.id,
        kind=ChronicleKind.COSMIC,
    )


async def guard(scene: Scene) -> None:
    dimension = scene.placement.dimension
    if dimension is not None and not held(dimension.id) and "veil" not in dimension.locked:
        dimension.veil = clamp_percent(dimension.veil + scene.ctx.rules.cosmic_beings.guard_veil)


async def trade(scene: Scene) -> None:
    world = scene.world
    route = await scene.ctx.session.scalar(
        select(RouteRow).where(RouteRow.active.is_(True), (RouteRow.world_a_id == world.id) | (RouteRow.world_b_id == world.id)).order_by(RouteRow.id).limit(1)
    )
    if route is not None and "traffic" not in route.locked:
        route.traffic += scene.ctx.rules.cosmic_beings.trade_traffic


async def seek_worship(scene: Scene) -> None:
    ctx = scene.ctx
    if not scene.rng.chance(ctx.rules.cosmic_beings.worship_chance):
        return
    communities = [row for row in await canon(ctx.session, COMMUNITY_TYPES, scene.world.id) if not held(row.id)]
    if communities:
        community = scene.rng.pick(sorted(communities, key=lambda row: row.id))
        await connect(ctx.session, community.id, scene.being.id, BondKind.WORSHIPS, ctx.epoch, description="came to worship it")


async def unmake(scene: Scene) -> None:
    await advance_doom(scene.ctx.session, scene.ctx.rules, scene.ctx.rules.cosmic_beings.unmake_doom)


async def restore(scene: Scene) -> None:
    await mend(scene.ctx, scene.placement.star, scene.world)


async def wander(scene: Scene) -> None:
    return None


AGENDA_ACTS: dict[BeingAgenda, Callable[[Scene], Awaitable[None]]] = {
    BeingAgenda.FEED: feed,
    BeingAgenda.EXPLORE: wander,
    BeingAgenda.CONQUER: conquer,
    BeingAgenda.GUARD: guard,
    BeingAgenda.TRADE: trade,
    BeingAgenda.FLEE: wander,
    BeingAgenda.SEEK_WORSHIP: seek_worship,
    BeingAgenda.UNMAKE: unmake,
    BeingAgenda.MEND: restore,
}


async def mirror(scene: Scene) -> None:
    ctx, profile = scene.ctx, scene.profile
    if profile.being_kind is not BeingKind.ECHO or profile.mirrored_entity_id is None or not scene.rng.chance(ctx.rules.cosmic_beings.echo_replace_chance):
        return
    mortal = await ctx.session.get(EntityRow, profile.mirrored_entity_id)
    if mortal is not None and await assume(ctx, mortal, IdentityReason.IMPOSTOR, mortal.name, cover_role="its own echo") is not None:
        await note(
            ctx, f"{scene.being.name} took the place of {mortal.name}.", key="being.echo_replaced", ids=[scene.being.id, mortal.id], world_id=mortal.world_id
        )


async def act(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> None:
    world = cosmography.worlds.get(being.world_id)
    if world is None:
        return
    placement = cosmography.place_world(world)
    regions = [region for region in sorted(await canon(ctx.session, [EntityType.REGION], world.id), key=lambda row: row.id) if not held(region.id)]
    scene = Scene(ctx, cosmography, being, profile, world, placement, regions, ctx.rng(f"being_act.{being.id}"))
    await AGENDA_ACTS[profile.agenda](scene)
    await mirror(scene)
    kind = BEING_MECHANICS[profile.being_kind]
    dimension = placement.dimension
    if dimension is not None and kind.veil(ctx.rules) and not held(dimension.id) and "veil" not in dimension.locked:
        dimension.veil = clamp_percent(dimension.veil + kind.veil(ctx.rules))
    if kind.doom(ctx.rules):
        await advance_doom(ctx.session, ctx.rules, kind.doom(ctx.rules))


async def mend(ctx: TickContext, star: StarRow | None, world: WorldRow) -> None:
    table = ctx.rules.cosmic_beings
    if star is not None and not held(star.id) and "brightness" not in star.locked:
        star.brightness = min(star_mechanics(star.star_type).brightness_max(ctx.rules), star.brightness + table.mend_brightness)
    for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.world_id == world.id, RiftRow.state.in_(list(OPEN_RIFT_STATES)))):
        if "stability" not in rift.locked:
            rift.stability = clamp_percent(rift.stability + table.mend_stability)


@reads("table.cosmos", "table.dimensional_events", "table.galactic_structures")
async def being_cycles(ctx: TickContext) -> None:
    table = ctx.rules.cosmic_beings
    cosmography = await Cosmography.load(ctx.session)
    for being in await canon(ctx.session, [EntityType.COSMIC_BEING]):
        profile = await ctx.session.get(CosmicBeingProfileRow, being.id)
        if profile is None or held(being.id) or "phase" in profile.locked:
            continue
        rng = ctx.rng(f"being.{being.id}")
        if profile.phase in (BeingPhase.BOUND, BeingPhase.BANISHED):
            continue
        if profile.phase is BeingPhase.DORMANT:
            if rng.chance(table.manifest_chance // 2):
                profile.phase = BeingPhase.ROAMING
            continue
        if profile.phase is BeingPhase.ROAMING:
            if rng.chance(table.cross_chance) and await cross(ctx, cosmography, being, profile):
                ctx.count("beings_crossed")
            elif rng.chance(table.roam_chance):
                reach = await worlds_in_reach(ctx, cosmography, being, profile)
                if reach:
                    await move_to(ctx, cosmography, being, profile, rng.pick(reach))
            if rng.chance(table.manifest_chance):
                profile.phase = BeingPhase.MANIFEST
                profile.target_world_id = being.world_id
                await note(ctx, f"{being.name} showed itself.", key="being.manifest", ids=[being.id], world_id=being.world_id, kind=ChronicleKind.COSMIC)
            continue
        profile.manifest_epochs += 1
        if "might" not in profile.locked:
            profile.might = clamp_percent(profile.might + table.might_growth)
        await act(ctx, cosmography, being, profile)
        if profile.manifest_epochs >= table.retreat_epochs:
            profile.phase = BeingPhase.ROAMING
            profile.manifest_epochs = 0
    await ctx.session.flush()


async def require_being(ctx: TickContext, entity_id: int) -> tuple[EntityRow, CosmicBeingProfileRow]:
    being = await ctx.session.get(EntityRow, entity_id)
    profile = await ctx.session.get(CosmicBeingProfileRow, entity_id)
    if being is None or profile is None:
        raise NotFoundError("No such cosmic being.")
    return being, profile


async def bind_being(ctx: TickContext, entity_id: int, binder_id: int, by: str) -> CosmicBeingProfileRow:
    being, profile = await require_being(ctx, entity_id)
    if profile.phase is BeingPhase.BANISHED:
        raise ValidationFailedError(f"{being.name} is banished and cannot be bound.")
    profile.phase = BeingPhase.BOUND
    profile.bound_by_node_id = binder_id
    await connect(ctx.session, binder_id, being.id, BondKind.COMMANDS, ctx.epoch, description="bound to serve")
    await note(ctx, f"{by} bound {being.name}.", key="being.bound", ids=[being.id], world_id=being.world_id, kind=ChronicleKind.MIRACLE)
    await ctx.session.flush()
    return profile


async def banish_near(ctx: TickContext, region_id: int | None, by: str) -> str | None:
    if region_id is None:
        return None
    statement = (
        select(EntityRow)
        .join(CosmicBeingProfileRow, CosmicBeingProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.location_id == region_id, CosmicBeingProfileRow.phase.in_([BeingPhase.MANIFEST, BeingPhase.INCURSION]))
        .order_by(CosmicBeingProfileRow.might.desc(), EntityRow.id)
    )
    for being in await ctx.session.scalars(statement):
        if held(being.id, being.world_id):
            continue
        await banish_being(ctx, being.id, by)
        return being.name
    return None


async def banish_being(ctx: TickContext, entity_id: int, by: str) -> CosmicBeingProfileRow:
    being, profile = await require_being(ctx, entity_id)
    profile.phase = BeingPhase.BANISHED
    profile.bound_by_node_id = None
    profile.might = clamp_percent(profile.might - ctx.rules.cosmic_beings.banish_might)
    await note(
        ctx,
        f"{by} banished {being.name} to the dimension it came from.",
        key="being.banished",
        ids=[being.id],
        world_id=being.world_id,
        kind=ChronicleKind.MIRACLE,
    )
    await ctx.session.flush()
    return profile


async def ruler_gains(ctx: TickContext, dimension: DimensionRow) -> int:
    if dimension.ruler_node_id is None or held(dimension.ruler_node_id):
        return 0
    gain = ctx.rules.dimensions.ruler_essence
    son = await ctx.session.get(SonRow, dimension.ruler_node_id)
    if son is not None:
        son.essence += gain
        return gain
    god = await ctx.session.get(ForeignGodRow, dimension.ruler_node_id)
    if god is not None:
        god.power = clamp_percent(god.power + gain)
        return gain
    profile = await ctx.session.get(CosmicBeingProfileRow, dimension.ruler_node_id)
    if profile is not None and "might" not in profile.locked:
        profile.might = clamp_percent(profile.might + gain)
        return gain
    return 0
