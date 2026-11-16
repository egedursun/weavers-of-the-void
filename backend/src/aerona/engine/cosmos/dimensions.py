from collections import Counter

from sqlalchemy import select

from aerona.catalog.cosmography import DIMENSIONAL_EVENT_LABELS, FRAGILE_DIMENSIONS, MIRROR_DIMENSIONS
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, DimensionalEventRow, DimensionRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, BeingKind, BeingPhase, DimensionalEventKind, DimensionKind, RiftCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.cosmos.aspects import keep_aspects
from aerona.engine.cosmos.beings import create_being, ruler_gains
from aerona.engine.cosmos.kinds import DIMENSION_KIND_MECHANICS
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import open_rift
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.stats import shift_bounded

THINNING_DOMAINS = frozenset({Domain.DREAM, Domain.SHADOW, Domain.MADNESS})
THICKENING_DOMAINS = frozenset({Domain.BORDER})
STEADYING_DOMAINS = frozenset({Domain.TIME})
STEADY_AT = PERCENT // 2


def is_active(event: DimensionalEventRow, epoch: int) -> bool:
    return event.until_epoch is None or event.until_epoch >= epoch


async def open_event(
    ctx: TickContext,
    dimension: DimensionRow,
    kind: DimensionalEventKind,
    intensity: int,
    *,
    other: DimensionRow | None = None,
    world: WorldRow | None = None,
    subject_id: int | None = None,
) -> DimensionalEventRow:
    label = DIMENSIONAL_EVENT_LABELS[kind]
    text = f"{label.label} of {dimension.name}: {label.description}"
    row = DimensionalEventRow(
        kind=kind,
        dimension_id=dimension.id,
        other_dimension_id=other.id if other is not None else None,
        world_id=world.id if world is not None else None,
        subject_entity_id=subject_id,
        epoch=ctx.epoch,
        until_epoch=ctx.epoch + ctx.rules.dimensions.event_epochs - 1,
        intensity=clamp_percent(intensity),
        text=text,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, text, key=f"dimension.{kind.value}", kind=ChronicleKind.COSMIC, world_id=world.id if world is not None else None)
    ctx.count(f"dimensional_{kind.value}")
    return row


def neighbour_of(cosmography: Cosmography, dimension: DimensionRow) -> DimensionRow | None:
    if dimension.parent_dimension_id is not None and dimension.parent_dimension_id in cosmography.dimensions:
        return cosmography.dimensions[dimension.parent_dimension_id]
    prime = cosmography.prime
    if prime is not None and prime.id != dimension.id:
        return prime
    others = sorted((row for row in cosmography.dimensions.values() if row.id != dimension.id), key=lambda row: row.id)
    return others[0] if others else None


def outside_worlds(cosmography: Cosmography, dimension: DimensionRow) -> list[WorldRow]:
    return sorted(
        (world for world in cosmography.worlds.values() if cosmography.place_world(world).dimension_id != dimension.id and not held(world.id)),
        key=lambda row: row.id,
    )


async def worship_counts(ctx: TickContext, ids: set[int]) -> Counter[int]:
    statement = select(BondRow.target_node_id).where(
        BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(ids))
    )
    return Counter(await ctx.session.scalars(statement))


async def ruler_shift(ctx: TickContext, dimension: DimensionRow) -> tuple[int, int]:
    son = await ctx.session.get(SonRow, dimension.ruler_node_id) if dimension.ruler_node_id is not None else None
    if son is None:
        return 0, 0
    shift = ctx.rules.dimensions.ruler_shift
    domains = {son.domain_primary, son.domain_secondary}
    veil = (-shift if domains & THINNING_DOMAINS else 0) + (shift if domains & THICKENING_DOMAINS else 0)
    return veil, shift if domains & STEADYING_DOMAINS else 0


async def tend_veil(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow, rifts: Counter[int], worship: Counter[int]) -> None:
    table = ctx.rules.dimensions
    veil_shift, steady = await ruler_shift(ctx, dimension)
    if "veil" not in dimension.locked:
        leak = sum(world.leakage for world in cosmography.worlds_in_dimension(dimension.id))
        loss = (
            rifts[dimension.id] * table.veil_rift_loss
            + leak // table.veil_leak_per
            + min(table.veil_worship_cap, worship[dimension.id] * table.veil_worship_loss)
        )
        dimension.veil = clamp_percent(dimension.veil + table.veil_heal - loss + veil_shift)
    if "stability" not in dimension.locked:
        target = DIMENSION_KIND_MECHANICS[dimension.dimension_kind].stability(ctx.rules)
        step = table.stability_drift
        dimension.stability = clamp_percent(dimension.stability + max(-step, min(step, target - dimension.stability)) + steady)


async def converge(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow, events: list[DimensionalEventRow]) -> None:
    if dimension.veil > ctx.rules.dimensions.convergence_veil:
        return
    if any(
        event.kind is DimensionalEventKind.CONVERGENCE and dimension.id in (event.dimension_id, event.other_dimension_id) and is_active(event, ctx.epoch)
        for event in events
    ):
        return
    other = neighbour_of(cosmography, dimension)
    if other is None or held(other.id):
        return
    events.append(await open_event(ctx, dimension, DimensionalEventKind.CONVERGENCE, PERCENT - dimension.veil, other=other))


async def incursion(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow) -> None:
    table = ctx.rules.dimensions
    rng = ctx.rng(f"incursion.{dimension.id}")
    if not rng.chance(table.incursion_chance * (PERCENT - dimension.veil) / PERCENT):
        return
    targets = outside_worlds(cosmography, dimension)
    if not targets:
        return
    rifted = {
        rift.world_id
        for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.dimension_id == dimension.id, RiftRow.state.in_(list(OPEN_RIFT_STATES))))
    }
    world = next((row for row in targets if row.id in rifted), None) or rng.pick(targets)
    native = await ctx.session.scalar(
        select(CosmicBeingProfileRow)
        .where(CosmicBeingProfileRow.home_dimension_id == dimension.id, CosmicBeingProfileRow.phase.not_in([BeingPhase.BOUND, BeingPhase.BANISHED]))
        .limit(1)
    )
    if native is not None:
        native.phase = BeingPhase.MANIFEST
        native.target_world_id = world.id
        subject = native.entity_id
    else:
        being = await create_being(ctx, BeingKind.RIFT_SPAWN, world, home_dimension_id=dimension.id, phase=BeingPhase.MANIFEST)
        subject = being.id
    await open_event(ctx, dimension, DimensionalEventKind.INCURSION, PERCENT - dimension.veil, world=world, subject_id=subject)


async def bleed(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow) -> None:
    table = ctx.rules.dimensions
    rng = ctx.rng(f"bleed.{dimension.id}")
    targets = outside_worlds(cosmography, dimension)
    if not targets or not rng.chance(table.bleed_chance):
        return
    world = rng.pick(targets)
    if "time_factor" not in world.locked:
        world.time_factor = max(0.01, world.time_factor + (dimension.time_factor - world.time_factor) * table.bleed_step / PERCENT)
    if "leakage" not in world.locked:
        world.leakage = clamp_percent(world.leakage + round(dimension.leak * table.bleed_step / PERCENT))
    await open_event(ctx, dimension, DimensionalEventKind.BLEED, table.bleed_step, world=world)


async def schism(ctx: TickContext, dimension: DimensionRow) -> None:
    table = ctx.rules.dimensions
    if dimension.stability >= table.schism_stability or not ctx.rng(f"schism.{dimension.id}").chance(table.schism_chance):
        return
    branch = await create_dimension(
        ctx.session, ctx.rules, DimensionDraft(f"{dimension.name} Branch", DimensionKind.QUANTUM_BRANCH, ctx.epoch, parent_dimension_id=dimension.id)
    )
    await open_event(ctx, dimension, DimensionalEventKind.SCHISM, PERCENT - dimension.stability, other=branch)


async def collapse(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow) -> None:
    table = ctx.rules.dimensions
    if dimension.dimension_kind not in FRAGILE_DIMENSIONS or dimension.stability >= table.collapse_stability:
        return
    if not ctx.rng(f"collapse.{dimension.id}").chance(table.collapse_chance):
        return
    parent = cosmography.dimensions.get(dimension.parent_dimension_id) if dimension.parent_dimension_id is not None else None
    for world in cosmography.worlds_in_dimension(dimension.id):
        if held(world.id):
            continue
        if world.dimension_id == dimension.id:
            world.dimension_id = parent.id if parent is not None else None
        if parent is None and "discovery" not in world.locked:
            world.discovery = Discovery.FORGOTTEN
    for galaxy in cosmography.galaxies.values():
        if galaxy.dimension_id == dimension.id:
            galaxy.dimension_id = parent.id if parent is not None else None
    for cluster in cosmography.clusters.values():
        if cluster.dimension_id == dimension.id:
            cluster.dimension_id = parent.id if parent is not None else None
    dimension.stability = 0
    dimension.veil = 0
    await open_event(ctx, dimension, DimensionalEventKind.COLLAPSE, PERCENT, other=parent)


async def echo(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow) -> None:
    if dimension.dimension_kind not in MIRROR_DIMENSIONS or not ctx.rng(f"echo.{dimension.id}").chance(ctx.rules.dimensions.echo_chance):
        return
    targets = {world.id for world in outside_worlds(cosmography, dimension)}
    mortals = [row for row in await canon(ctx.session, [EntityType.MORTAL]) if row.world_id in targets and not held(row.id) and row.mortal_role is not None]
    if not mortals:
        return
    mortal = ctx.rng(f"echo_pick.{dimension.id}").pick(sorted(mortals, key=lambda row: row.id))
    world = cosmography.worlds[mortal.world_id]
    being = await create_being(ctx, BeingKind.ECHO, world, home_dimension_id=dimension.id, mirrored=mortal, phase=BeingPhase.MANIFEST)
    await open_event(ctx, dimension, DimensionalEventKind.ECHO, PERCENT // 2, world=world, subject_id=being.id)


async def spontaneous_rift(ctx: TickContext, cosmography: Cosmography, dimension: DimensionRow) -> None:
    if dimension.veil > 0 or not ctx.rng(f"veil_tear.{dimension.id}").chance(ctx.rules.dimensions.rift_chance):
        return
    targets = outside_worlds(cosmography, dimension)
    if not targets:
        return
    world = ctx.rng(f"veil_tear_world.{dimension.id}").pick(targets)
    regions = sorted(await canon(ctx.session, [EntityType.REGION], world.id), key=lambda row: row.id)
    inside = sorted(cosmography.worlds_in_dimension(dimension.id), key=lambda row: row.id)
    await open_rift(ctx, world, regions[0] if regions else None, dimension, RiftCause.CONVERGENCE, target_world=inside[0] if inside else None)


async def worship_plane(ctx: TickContext, dimension: DimensionRow, worship: Counter[int]) -> None:
    table = ctx.rules.dimensions
    if worship[dimension.id] and dimension.stability >= STEADY_AT:
        statement = select(BondRow.source_node_id).where(
            BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == dimension.id
        )
        for community_id in list(await ctx.session.scalars(statement)):
            row = await ctx.session.get(EntityRow, community_id)
            if row is not None and not held(row.id):
                shift_bounded(ctx.rules, row, "piety", table.worship_piety)


async def dimension_cults(ctx: TickContext, cosmography: Cosmography) -> int:
    touched: dict[int, set[int]] = {}
    for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES)))):
        touched.setdefault(rift.world_id, set()).add(rift.dimension_id)
    events = select(DimensionalEventRow).where(DimensionalEventRow.epoch == ctx.epoch, DimensionalEventRow.world_id.is_not(None))
    for event in await ctx.session.scalars(events):
        if event.world_id is not None:
            touched.setdefault(event.world_id, set()).add(event.dimension_id)
    if not touched:
        return 0
    rng = ctx.rng("dimension_cults")
    risen = 0
    for community in sorted(await canon(ctx.session, COMMUNITY_TYPES), key=lambda row: row.id):
        if held(community.id) or community.world_id not in touched:
            continue
        for dimension_id in sorted(touched[community.world_id]):
            dimension = cosmography.dimensions.get(dimension_id)
            if dimension is None or held(dimension.id) or not rng.chance(ctx.rules.dimensions.cult_chance):
                continue
            if await BondRepository(ctx.session).exists_between(community.id, dimension.id, BondKind.WORSHIPS):
                continue
            await connect(ctx.session, community.id, dimension.id, BondKind.WORSHIPS, ctx.epoch, description="came to worship it")
            await note(
                ctx,
                f"{community.name} came to worship {dimension.name}.",
                key="dimension.cult_risen",
                ids=[community.id],
                world_id=community.world_id,
                kind=ChronicleKind.WORSHIP,
            )
            risen += 1
    return risen


@reads("table.bonds", "table.cosmos", "table.dimension_aspects", "table.dimensional_events", "table.galactic_structures", "table.rifts")
@writes("table.bonds", "table.dimension_aspects", "table.dimensions")
async def dimension_cycles(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    rifts: Counter[int] = Counter(await ctx.session.scalars(select(RiftRow.dimension_id).where(RiftRow.state.in_(list(OPEN_RIFT_STATES)))))
    worship = await worship_counts(ctx, set(cosmography.dimensions))
    events = list(
        await ctx.session.scalars(
            select(DimensionalEventRow).where((DimensionalEventRow.until_epoch.is_(None)) | (DimensionalEventRow.until_epoch >= ctx.epoch))
        )
    )
    table = ctx.rules.dimensions
    if ctx.rng("planar_alignment").chance(table.alignment_chance) and cosmography.dimensions:
        for dimension in cosmography.dimensions.values():
            if not held(dimension.id) and "veil" not in dimension.locked:
                dimension.veil = clamp_percent(dimension.veil - table.alignment_loss)
        first = min(cosmography.dimensions.values(), key=lambda row: row.id)
        await open_event(ctx, first, DimensionalEventKind.PLANAR_ALIGNMENT, table.alignment_loss)
    for dimension in sorted(cosmography.dimensions.values(), key=lambda row: row.id):
        if held(dimension.id):
            continue
        await tend_veil(ctx, cosmography, dimension, rifts, worship)
        ctx.count("aspects", await keep_aspects(ctx, dimension))
        ctx.count("ruler_gains", await ruler_gains(ctx, dimension))
        if ctx.rng(f"thinning.{dimension.id}").chance(table.thinning_chance) and "veil" not in dimension.locked:
            dimension.veil = clamp_percent(dimension.veil - table.thinning_loss)
            await open_event(ctx, dimension, DimensionalEventKind.VEIL_THINNING, table.thinning_loss)
        if dimension.dimension_kind is DimensionKind.PRIME:
            await worship_plane(ctx, dimension, worship)
            continue
        await converge(ctx, cosmography, dimension, events)
        await incursion(ctx, cosmography, dimension)
        await bleed(ctx, cosmography, dimension)
        await schism(ctx, dimension)
        await collapse(ctx, cosmography, dimension)
        await echo(ctx, cosmography, dimension)
        await spontaneous_rift(ctx, cosmography, dimension)
        await worship_plane(ctx, dimension, worship)
    ctx.count("dimension_cults", await dimension_cults(ctx, cosmography))
    await ctx.session.flush()
