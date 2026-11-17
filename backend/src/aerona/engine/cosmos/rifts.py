from sqlalchemy import delete, select

from aerona.catalog.cosmography import RIFT_PHENOMENA
from aerona.catalog.travel import travel_method_profile
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import DimensionRow, PhenomenonFootprintRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, PhenomenonCause, PhenomenonKind, RiftCause, RiftState
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.enums.travel import RouteClosure, TravelMethod
from aerona.engine.context import TickContext
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.interconnect.annotations import reads
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.recording.record import StepDraft, record

WARDS = frozenset({EngineKind.TEMPLE, EngineKind.WALL})


async def open_rift(
    ctx: TickContext,
    world: WorldRow,
    region: EntityRow | None,
    dimension: DimensionRow,
    cause: RiftCause,
    *,
    by_node_id: int | None = None,
    target_world: WorldRow | None = None,
) -> RiftRow:
    cosmography = await Cosmography.load(ctx.session)
    if cosmography.place_world(world).dimension_id == dimension.id:
        raise ValidationFailedError(f"{world.name} already lies in {dimension.name}.")
    if target_world is not None and cosmography.place_world(target_world).dimension_id != dimension.id:
        raise ValidationFailedError(f"{target_world.name} does not lie in {dimension.name}.")
    if region is not None and (region.world_id != world.id or region.entity_type is not EntityType.REGION):
        raise ValidationFailedError("A rift opens in a region of its own world.")
    table = ctx.rules.rifts
    rift = RiftRow(
        world_id=world.id,
        region_entity_id=region.id if region is not None else None,
        dimension_id=dimension.id,
        target_world_id=target_world.id if target_world is not None else None,
        size=table.open_size,
        stability=table.open_stability,
        state=RiftState.OPENING,
        cause=cause,
        opened_by_node_id=by_node_id,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(rift)
    await ctx.session.flush()
    await open_passage(ctx, rift)
    where = region.id if region is not None else world.id
    await record(
        ctx,
        f"rift.opened.{cause.value}",
        roles={IncidentRole.PLACE: where, IncidentRole.DESTINATION: dimension.id, IncidentRole.ACTOR: by_node_id},
        facts={"cause": cause, "size": rift.size, "stability": rift.stability},
        steps=(StepDraft(StepAction.OPEN, actor=by_node_id, locus_kind=StepLocus.REGION if region is not None else StepLocus.REALM, locus_node=where),),
        place=region.id if region is not None else None,
        world_id=world.id,
    )
    return rift


async def open_passage(ctx: TickContext, rift: RiftRow) -> None:
    if rift.target_world_id is None or rift.route_id is not None or rift.state not in OPEN_RIFT_STATES:
        return
    profile = travel_method_profile(ctx.rules, TravelMethod.DIMENSIONAL_RIFT)
    route = RouteRow(
        world_a_id=rift.world_id,
        world_b_id=rift.target_world_id,
        method=TravelMethod.DIMENSIONAL_RIFT,
        duration_epochs=profile.duration_epochs,
        danger=profile.danger,
        known=True,
        created_epoch=ctx.epoch,
        active=True,
        locked=[],
    )
    ctx.session.add(route)
    await ctx.session.flush()
    rift.route_id = route.id


async def close_passage(ctx: TickContext, rift: RiftRow) -> None:
    route = await ctx.session.get(RouteRow, rift.route_id) if rift.route_id is not None else None
    if route is not None and "active" not in route.locked:
        route.active = False
        route.closure = RouteClosure.SEALED


async def seal_rift(ctx: TickContext, rift_id: int, by_id: int | None = None) -> RiftRow:
    rift = await ctx.session.get(RiftRow, rift_id)
    if rift is None:
        raise NotFoundError("No such rift.")
    if rift.state not in OPEN_RIFT_STATES:
        raise ValidationFailedError("That rift is already closed.")
    size = rift.size
    rift.state = RiftState.SEALED
    rift.size = 0
    rift.sealed_epoch = ctx.epoch
    await close_passage(ctx, rift)
    where = rift.region_entity_id or rift.world_id
    await record(
        ctx,
        "rift.sealed",
        roles={IncidentRole.PLACE: where, IncidentRole.DESTINATION: rift.dimension_id, IncidentRole.ACTOR: by_id},
        facts={"size": size},
        steps=(StepDraft(StepAction.CLOSE, actor=by_id, outcome=StepOutcome.SUCCESS),),
        place=rift.region_entity_id,
        world_id=rift.world_id,
    )
    await ctx.session.flush()
    return rift


async def tear_toward(
    ctx: TickContext, world: WorldRow, region: EntityRow | None, cause: RiftCause, *, by_node_id: int | None = None, home_id: int | None = None
) -> RiftRow | None:
    if held(world.id, region.id if region is not None else None):
        return None
    cosmography = await Cosmography.load(ctx.session)
    here = cosmography.place_world(world).dimension_id
    others = sorted(
        (row for row in cosmography.dimensions.values() if row.id != here and not held(row.id)), key=lambda row: (row.id != home_id, row.veil, row.id)
    )
    if not others:
        return None
    return await open_rift(ctx, world, region, others[0], cause, by_node_id=by_node_id)


async def seal_near(ctx: TickContext, region_id: int | None, by_id: int | None = None) -> RiftRow | None:
    if region_id is None:
        return None
    statement = (
        select(RiftRow).where(RiftRow.region_entity_id == region_id, RiftRow.state.in_(list(OPEN_RIFT_STATES))).order_by(RiftRow.size.desc(), RiftRow.id)
    )
    for rift in await ctx.session.scalars(statement):
        if held(rift.world_id, rift.region_entity_id, rift.dimension_id) or "state" in rift.locked:
            continue
        await seal_rift(ctx, rift.id, by_id)
        dimension = await ctx.session.get(DimensionRow, rift.dimension_id)
        if dimension is not None and "veil" not in dimension.locked:
            dimension.veil = clamp_percent(dimension.veil + ctx.rules.rifts.ward_veil)
        return rift
    return None


async def wards_near(ctx: TickContext, region_id: int | None) -> int:
    if region_id is None:
        return 0
    statement = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON, EntityRow.engine_kind.in_(list(WARDS)), EntityRow.location_id == region_id)
    return len(list(await ctx.session.scalars(statement)))


async def collapse(ctx: TickContext, rift: RiftRow) -> None:
    rift.state = RiftState.COLLAPSED
    rift.size = 0
    rift.sealed_epoch = ctx.epoch
    await close_passage(ctx, rift)
    region = await ctx.session.get(EntityRow, rift.region_entity_id) if rift.region_entity_id is not None else None
    if region is not None and not held(region.id):
        await apply_disaster(ctx, region, Disaster.EARTHQUAKE, ctx.rules.rifts.collapse_severity / PERCENT)
    where = rift.region_entity_id or rift.world_id
    await record(
        ctx,
        "rift.collapsed",
        roles={IncidentRole.PLACE: where, IncidentRole.DESTINATION: rift.dimension_id},
        facts={"severity": ctx.rules.rifts.collapse_severity},
        steps=(StepDraft(StepAction.COLLAPSE, outcome=StepOutcome.DESTROYED),),
        place=rift.region_entity_id,
        world_id=rift.world_id,
    )


async def tend_rift(ctx: TickContext, rift: RiftRow) -> None:
    table = ctx.rules.rifts
    if "stability" not in rift.locked:
        rift.stability = clamp_percent(rift.stability - table.stability_drift + await wards_near(ctx, rift.region_entity_id) * table.ward_stability)
    if rift.stability <= 0:
        await collapse(ctx, rift)
        return
    if "size" not in rift.locked:
        rift.size = clamp_percent(rift.size - table.shrink if rift.stability >= table.steady_at else rift.size + table.grow)
    if rift.size <= 0:
        rift.state = RiftState.SEALED
        rift.sealed_epoch = ctx.epoch
        await close_passage(ctx, rift)
        where = rift.region_entity_id or rift.world_id
        await record(
            ctx,
            "rift.closed",
            roles={IncidentRole.PLACE: where, IncidentRole.DESTINATION: rift.dimension_id},
            facts={"stability": rift.stability},
            steps=(StepDraft(StepAction.CLOSE, outcome=StepOutcome.SUCCESS),),
            place=rift.region_entity_id,
            world_id=rift.world_id,
        )
        return
    if "state" not in rift.locked:
        steady = rift.stability >= table.steady_at
        rift.state = RiftState.CLOSING if steady and rift.state is not RiftState.OPENING else RiftState.OPEN
    await open_passage(ctx, rift)
    if rift.size >= table.wound_size and rift.region_entity_id is not None:
        region = await ctx.session.get(EntityRow, rift.region_entity_id)
        if region is not None:
            await form_phenomenon(ctx, PhenomenonKind.OUTSIDE_OPENING, region, PhenomenonCause.RIFT, cause_node_id=rift.dimension_id)


async def leak_peaks(ctx: TickContext, cosmography: Cosmography) -> int:
    table = ctx.rules.rifts
    torn = 0
    gates = select(PhenomenonFootprintRow.region_entity_id).join(
        PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id
    )
    gated = set(await ctx.session.scalars(gates.where(PhenomenonProfileRow.kind.in_(list(RIFT_PHENOMENA)))))
    statement = (
        select(RegionEnvironmentRow)
        .where((RegionEnvironmentRow.leak >= table.leak_peak) | RegionEnvironmentRow.entity_id.in_(list(gated)))
        .order_by(RegionEnvironmentRow.entity_id)
    )
    for ground in await ctx.session.scalars(statement):
        world = cosmography.worlds.get(ground.world_id)
        region = await ctx.session.get(EntityRow, ground.entity_id)
        if world is None or region is None or held(ground.entity_id, ground.world_id):
            continue
        if ground.entity_id not in gated and ctx.rng(f"leak_wound.{ground.entity_id}").chance(ctx.rules.phenomena.leak_peak_chance):
            await form_phenomenon(ctx, PhenomenonKind.OUTSIDE_OPENING, region, PhenomenonCause.LEAK_PEAK)
        if not ctx.rng(f"leak_peak.{ground.entity_id}").chance(table.peak_chance):
            continue
        home = cosmography.place_world(world).dimension_id
        others = sorted((row for row in cosmography.dimensions.values() if row.id != home and not held(row.id)), key=lambda row: (row.veil, row.id))
        if not others:
            continue
        await open_rift(ctx, world, region, others[0], RiftCause.PHENOMENON if ground.entity_id in gated else RiftCause.LEAK_PEAK)
        torn += 1
    return torn


@reads("table.cosmos", "table.dimensional_events", "table.galactic_structures", "table.region_environment", "table.rifts")
async def rift_cycles(ctx: TickContext) -> None:
    table = ctx.rules.rifts
    cosmography = await Cosmography.load(ctx.session)
    statement = select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES))).order_by(RiftRow.id)
    for rift in list(await ctx.session.scalars(statement)):
        if held(rift.world_id, rift.region_entity_id, rift.dimension_id):
            continue
        await tend_rift(ctx, rift)
    ctx.count("rifts_torn", await leak_peaks(ctx, cosmography))
    gone = select(RiftRow.id).where(RiftRow.state.not_in(list(OPEN_RIFT_STATES)), RiftRow.sealed_epoch < ctx.epoch - table.sealed_epochs)
    stale = [rift_id for rift_id in await ctx.session.scalars(gone)]
    held_worlds = {rift.id for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.id.in_(stale))) if held(rift.world_id, rift.dimension_id)}
    removable = [rift_id for rift_id in stale if rift_id not in held_worlds]
    if removable:
        await ctx.session.execute(delete(RiftRow).where(RiftRow.id.in_(removable)))
    await ctx.session.flush()
