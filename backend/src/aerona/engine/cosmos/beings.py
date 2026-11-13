from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.cosmography import BEING_AGENDAS, BEING_KINDS, BEING_SCALES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, DimensionalEventRow, DimensionRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, BeingAgenda, BeingKind, BeingPhase, BeingScale, DimensionalEventKind, RiftCause
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.models.entity_stats import CosmicBeingStats, CultStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.being_wounds import can_roam, can_see, effective_might, wound_being
from aerona.engine.cosmos.commerce import carry, market_of
from aerona.engine.cosmos.kinds import BEING_MECHANICS
from aerona.engine.cosmos.placement import Cosmography, Placement
from aerona.engine.cosmos.rifts import tear_toward
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.interconnect.annotations import reads
from aerona.engine.intrigue.identities import assume
from aerona.engine.notes import note
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import POPULATION_KEY, scale_stat, shift_bounded, stat_or


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
    if not await can_see(ctx.session, ctx.rules.cosmic_wounds.sight_floor, being):
        return []
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
    if not await can_roam(ctx.session, ctx.rules.cosmic_wounds.roam_floor, being):
        return False
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
            intensity=await effective_might(ctx.session, being, profile.might),
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
    await answer_incursion(scene, region)


async def answer_incursion(scene: Scene, region: EntityRow) -> bool:
    ctx, profile, table = scene.ctx, scene.profile, scene.ctx.rules.cosmic_beings
    armies = [army for army in await canon(ctx.session, [EntityType.ARMY], scene.world.id) if not held(army.id) and stat_or(army, "size", 0) > 0]
    if not armies:
        return False
    soldiers = sum(stat_or(army, "size", 0) for army in armies)
    for army in armies:
        scale_stat(ctx.rules, army, "size", (PERCENT - table.army_answer_pct) / PERCENT)
    if "might" not in profile.locked:
        profile.might = clamp_percent(profile.might - soldiers // table.army_drive_size)
    await wound_being(ctx, scene.being, soldiers / 1000 * ctx.rules.cosmic_wounds.army_wound, HarmCause.BATTLE, f"the armies of {scene.world.name}")
    driven = soldiers >= max(1, await effective_might(ctx.session, scene.being, profile.might)) * table.army_drive_size
    if driven:
        profile.phase = BeingPhase.ROAMING
        profile.manifest_epochs = 0
    text = (
        f"The armies of {scene.world.name} answered {scene.being.name} in {region.name} and drove it back."
        if driven
        else f"The armies of {scene.world.name} answered {scene.being.name} in {region.name} but could not drive it back."
    )
    await note(ctx, text, key="being.incursion_answered", ids=[scene.being.id, region.id, *[army.id for army in armies]], world_id=scene.world.id)
    return driven


async def guard(scene: Scene) -> None:
    dimension = scene.placement.dimension
    if dimension is not None and not held(dimension.id) and "veil" not in dimension.locked:
        dimension.veil = clamp_percent(dimension.veil + scene.ctx.rules.cosmic_beings.guard_veil)


async def trade(scene: Scene) -> None:
    ctx, world = scene.ctx, scene.world
    route = await ctx.session.scalar(
        select(RouteRow).where(RouteRow.active.is_(True), (RouteRow.world_a_id == world.id) | (RouteRow.world_b_id == world.id)).order_by(RouteRow.id).limit(1)
    )
    if route is None or held(route.world_a_id, route.world_b_id):
        return
    markets: dict[int, EntityRow | None] = {}
    first, second = await market_of(ctx, route.world_a_id, markets), await market_of(ctx, route.world_b_id, markets)
    moved = 0
    if first is not None and second is not None:
        moved, _ = await carry(ctx, route, scene.cosmography.scope_by_id(route.world_a_id, route.world_b_id), first, second)
    if "traffic" not in route.locked:
        route.traffic += moved + ctx.rules.cosmic_beings.trade_traffic
    if moved:
        await note(ctx, f"{scene.being.name} carried goods along the route from {world.name}.", key="being.traded", ids=[scene.being.id], world_id=world.id)


async def seek_worship(scene: Scene) -> None:
    ctx = scene.ctx
    if not scene.rng.chance(ctx.rules.cosmic_beings.worship_chance):
        return
    communities = [row for row in await canon(ctx.session, COMMUNITY_TYPES, scene.world.id) if not held(row.id)]
    if communities:
        community = scene.rng.pick(sorted(communities, key=lambda row: row.id))
        await connect(ctx.session, community.id, scene.being.id, BondKind.WORSHIPS, ctx.epoch, description="came to worship it")
        await found_cult(ctx, scene.being, community)


async def found_cult(ctx: TickContext, being: EntityRow, community: EntityRow) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.CULT,
            EntityRow.status == EntityStatus.CANON,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            BondRow.target_node_id == being.id,
            EntityRow.world_id == community.world_id,
        )
        .limit(1)
    )
    if await ctx.session.scalar(statement) is not None:
        return None
    share = ctx.rules.cosmic_beings.cult_share_pct
    cult = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"The cult of {being.name}",
            body=f"A cult among {community.name} that worships {being.name}.",
            stats=CultStats(followers=max(1, stat_or(community, POPULATION_KEY, 0) * share // PERCENT), zeal=PERCENT // 2, influence=share),
            power=max(1, being.power_level // 2),
            world_id=community.world_id,
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            subtype="cult of a cosmic being",
        ),
    )
    await connect(ctx.session, cult.id, being.id, BondKind.WORSHIPS, ctx.epoch, description="its object of worship")
    await connect(ctx.session, cult.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch, description="born from within")
    await note(ctx, f"{cult.name} arose among {community.name}.", key="being.cult_founded", ids=[cult.id, community.id, being.id], world_id=community.world_id)
    return cult


async def unmake(scene: Scene) -> None:
    dimension = scene.placement.dimension
    if dimension is not None and not held(dimension.id) and "stability" not in dimension.locked:
        dimension.stability = clamp_percent(dimension.stability - scene.ctx.rules.cosmic_beings.unmake_stability)


async def restore(scene: Scene) -> None:
    await mend(scene.ctx, scene.placement.star, scene.world)


async def wander(scene: Scene) -> None:
    return None


TEARING_KINDS = frozenset({BeingKind.DIMENSION_WALKER, BeingKind.RIFT_SPAWN})
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
    if profile.being_kind is not BeingKind.ECHO or profile.mirrored_entity_id is None:
        return
    mortal = await ctx.session.get(EntityRow, profile.mirrored_entity_id)
    if mortal is None or mortal.status is not EntityStatus.CANON or held(mortal.id):
        return
    if scene.rng.chance(ctx.rules.cosmic_beings.echo_replace_chance):
        if await assume(ctx, mortal, IdentityReason.IMPOSTOR, mortal.name, cover_role="its own echo") is not None:
            await note(
                ctx,
                f"{scene.being.name} took the place of {mortal.name}.",
                key="being.echo_replaced",
                ids=[scene.being.id, mortal.id],
                world_id=mortal.world_id,
            )
        return
    if scene.rng.chance(ctx.rules.cosmic_beings.befriend_chance) and not await BondRepository(ctx.session).exists_between(
        mortal.id, scene.being.id, BondKind.COMPANION
    ):
        await connect(ctx.session, mortal.id, scene.being.id, BondKind.COMPANION, ctx.epoch, description="befriended its own echo")
        await note(ctx, f"{mortal.name} befriended {scene.being.name}.", key="being.echo_befriended", ids=[scene.being.id, mortal.id], world_id=mortal.world_id)


async def act(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> None:
    world = cosmography.worlds.get(being.world_id)
    if world is None:
        return
    placement = cosmography.place_world(world)
    regions = [region for region in sorted(await canon(ctx.session, [EntityType.REGION], world.id), key=lambda row: row.id) if not held(region.id)]
    scene = Scene(ctx, cosmography, being, profile, world, placement, regions, ctx.rng(f"being_act.{being.id}"))
    await AGENDA_ACTS[profile.agenda](scene)
    await mirror(scene)
    await tear(scene)
    kind = BEING_MECHANICS[profile.being_kind]
    dimension = placement.dimension
    if dimension is not None and kind.veil(ctx.rules) and not held(dimension.id) and "veil" not in dimension.locked:
        dimension.veil = clamp_percent(dimension.veil + kind.veil(ctx.rules))


async def tear(scene: Scene) -> None:
    ctx, profile = scene.ctx, scene.profile
    if profile.being_kind not in TEARING_KINDS or not scene.rng.chance(ctx.rules.cosmic_beings.tear_chance):
        return
    region = scene.rng.pick(scene.regions) if scene.regions else None
    rift = await tear_toward(ctx, scene.world, region, RiftCause.BEING, by_node_id=scene.being.id, home_id=profile.home_dimension_id)
    if rift is not None and "rift_id" not in profile.locked:
        profile.rift_id = rift.id


async def serve(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> int:
    binder_id = profile.bound_by_node_id
    if binder_id is None or held(binder_id):
        return 0
    gain = await effective_might(ctx.session, being, profile.might) * ctx.rules.cosmic_beings.serve_pct // PERCENT
    son = await ctx.session.get(SonRow, binder_id)
    god = await ctx.session.get(ForeignGodRow, binder_id) if son is None else None
    if son is not None:
        son.essence += gain
    elif god is not None:
        god.power = clamp_percent(god.power + gain)
    world = cosmography.worlds.get(being.world_id)
    if world is not None and not held(world.id):
        placement = cosmography.place_world(world)
        await guard(Scene(ctx, cosmography, being, profile, world, placement, [], ctx.rng(f"being_serve.{being.id}")))
        await mend(ctx, placement.star, world)
    return gain


async def take_rule(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> bool:
    if profile.being_kind is not BeingKind.PLANE_SOVEREIGN or profile.home_dimension_id is None:
        return False
    home = cosmography.dimensions.get(profile.home_dimension_id)
    if home is None or home.ruler_node_id is not None or held(home.id) or "ruler_node_id" in home.locked:
        return False
    if not ctx.rng(f"being_rule.{being.id}").chance(ctx.rules.cosmic_beings.rule_chance):
        return False
    home.ruler_node_id = being.id
    await note(ctx, f"{being.name} took rule of {home.name}.", key="being.took_rule", ids=[being.id], world_id=being.world_id, kind=ChronicleKind.COSMIC)
    return True


async def foreign_binding(ctx: TickContext, being: EntityRow, profile: CosmicBeingProfileRow) -> bool:
    if profile.phase not in (BeingPhase.MANIFEST, BeingPhase.INCURSION) or being.world_id is None:
        return False
    statement = select(ForeignGodRow).where(ForeignGodRow.world_id == being.world_id, ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)
    for god in await ctx.session.scalars(statement):
        if held(god.id) or not ctx.rng(f"foreign_bind.{being.id}.{god.id}").chance(ctx.rules.cosmic_beings.foreign_bind_chance):
            continue
        name = await ctx.session.scalar(select(NodeRow.name).where(NodeRow.id == god.id)) or "A foreign god"
        await bind_being(ctx, being.id, god.id, name)
        return True
    return False


async def mend(ctx: TickContext, star: StarRow | None, world: WorldRow) -> None:
    table = ctx.rules.cosmic_beings
    if star is not None and not held(star.id) and "brightness" not in star.locked:
        star.brightness = min(star_mechanics(star.star_type).brightness_max(ctx.rules), star.brightness + table.mend_brightness)
    for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.world_id == world.id, RiftRow.state.in_(list(OPEN_RIFT_STATES)))):
        if "stability" not in rift.locked:
            rift.stability = clamp_percent(rift.stability + table.mend_stability)


async def roam(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow, rng: SeededRandom) -> None:
    table = ctx.rules.cosmic_beings
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


async def manifest(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> None:
    table = ctx.rules.cosmic_beings
    profile.manifest_epochs += 1
    if "might" not in profile.locked:
        profile.might = clamp_percent(profile.might + table.might_growth)
    await act(ctx, cosmography, being, profile)
    if await foreign_binding(ctx, being, profile):
        return
    if profile.manifest_epochs >= table.retreat_epochs:
        profile.phase = BeingPhase.ROAMING
        profile.manifest_epochs = 0


async def live(ctx: TickContext, cosmography: Cosmography, being: EntityRow, profile: CosmicBeingProfileRow) -> None:
    rng = ctx.rng(f"being.{being.id}")
    if profile.phase is BeingPhase.BOUND:
        ctx.count("bound_service", await serve(ctx, cosmography, being, profile))
        return
    if profile.phase is BeingPhase.BANISHED:
        return
    if await take_rule(ctx, cosmography, being, profile):
        ctx.count("beings_took_rule")
    if profile.phase is BeingPhase.DORMANT:
        if rng.chance(ctx.rules.cosmic_beings.manifest_chance // 2):
            profile.phase = BeingPhase.ROAMING
        return
    if profile.phase is BeingPhase.ROAMING:
        await roam(ctx, cosmography, being, profile, rng)
        return
    await manifest(ctx, cosmography, being, profile)


@reads("table.cosmos", "table.dimensional_events", "table.galactic_structures")
async def being_cycles(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    for being in await canon(ctx.session, [EntityType.COSMIC_BEING]):
        profile = await ctx.session.get(CosmicBeingProfileRow, being.id)
        if profile is None or held(being.id) or "phase" in profile.locked:
            continue
        await live(ctx, cosmography, being, profile)
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
    await wound_being(ctx, being, ctx.rules.cosmic_wounds.bind_wound, HarmCause.RITUAL, f"bound by {by}", killer_id=binder_id)
    await connect(ctx.session, binder_id, being.id, BondKind.COMMANDS, ctx.epoch, description="bound to serve")
    await note(ctx, f"{by} bound {being.name}.", key="being.bound", ids=[being.id], world_id=being.world_id, kind=ChronicleKind.MIRACLE)
    await ctx.session.flush()
    return profile


async def bind_near(ctx: TickContext, region_id: int | None, binder_id: int, by: str) -> str | None:
    if region_id is None:
        return None
    statement = (
        select(EntityRow)
        .join(CosmicBeingProfileRow, CosmicBeingProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.location_id == region_id, CosmicBeingProfileRow.phase.in_([BeingPhase.MANIFEST, BeingPhase.INCURSION]))
        .order_by(CosmicBeingProfileRow.might, EntityRow.id)
    )
    for being in await ctx.session.scalars(statement):
        if held(being.id, being.world_id):
            continue
        await bind_being(ctx, being.id, binder_id, by)
        return being.name
    return None


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
    profile.target_world_id = None
    profile.rift_id = None
    await send_home(ctx, being, profile)
    profile.might = clamp_percent(profile.might - ctx.rules.cosmic_beings.banish_might)
    await wound_being(ctx, being, ctx.rules.cosmic_wounds.banish_wound, HarmCause.RITUAL, f"banished by {by}")
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


async def send_home(ctx: TickContext, being: EntityRow, profile: CosmicBeingProfileRow) -> None:
    if profile.home_dimension_id is None or "world_id" in profile.locked:
        return
    cosmography = await Cosmography.load(ctx.session)
    if cosmography.place_world_id(being.world_id).dimension_id == profile.home_dimension_id:
        return
    homes = sorted((world for world in cosmography.worlds_in_dimension(profile.home_dimension_id) if not held(world.id)), key=lambda row: row.id)
    if homes:
        await move_to(ctx, cosmography, being, profile, homes[0])


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
