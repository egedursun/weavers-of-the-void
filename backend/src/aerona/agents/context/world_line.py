from sqlalchemy import func, select

from aerona.agents.context.scope import Scope
from aerona.catalog.cosmography import (
    BEING_AGENDA_LABELS,
    BEING_KINDS,
    BEING_PHASE_LABELS,
    BEING_SCALE_LABELS,
    DIMENSION_KINDS,
    GALACTIC_ZONES,
    GALAXY_TYPES,
    OMEN_LABELS,
    PHENOMENON_CAUSE_LABELS,
    PHENOMENON_KINDS,
    RIFT_CAUSE_LABELS,
    RIFT_STATE_LABELS,
    STAR_AGE_LABELS,
    WORLD_AGE_LABELS,
)
from aerona.catalog.kinds.terraform import TERRAFORM_AIMS
from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.catalog.worlds import ATMOSPHERE_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.cosmography import CelestialReadingRow, CosmicBeingProfileRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import CosmicFeatureRow, ImpactEventRow, TerraformingRow, WorldLifeRow, WorldPhysicsRow
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.physics import PERIODIC_BODIES, ImpactOutcome
from aerona.engine.cosmos.orbits import eclipse_period, next_epoch
from aerona.engine.cosmos.placement import Cosmography, cosmography_of
from aerona.engine.phases.world_age import golden_age_status
from aerona.engine.primitives.queries import canon
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import WorldLineContext


async def phenomenon_line(scope: Scope, entity: EntityRow) -> str:
    profile = await scope.session.get(PhenomenonProfileRow, entity.id)
    if profile is None:
        return entity.name
    kind = PHENOMENON_KINDS[profile.kind].label.lower()
    return f"{entity.name} ({kind}, intensity {profile.intensity}/100, from {PHENOMENON_CAUSE_LABELS[profile.cause].lower()})"


async def omen_lines(scope: Scope, world_id: int) -> list[str]:
    found: list[str] = []
    for body in await canon(scope.session, [EntityType.CELESTIAL], world_id):
        readings = list(await scope.session.scalars(select(CelestialReadingRow).where(CelestialReadingRow.celestial_entity_id == body.id)))
        for reading in readings:
            people = await scope.session.get(EntityRow, reading.people_entity_id)
            if people is not None:
                found.append(f"{people.name} read {body.name} as {OMEN_LABELS[reading.reading].lower()}")
    return found


async def heaven_lines(scope: Scope, ladder: Cosmography) -> list[str]:
    lines = [
        f"dimension#{row.id} {row.name} ({DIMENSION_KINDS[row.dimension_kind].label}; veil {row.veil}/100, stability {row.stability}/100"
        + (f"; ruled by #{row.ruler_node_id}" if row.ruler_node_id is not None else "")
        + ")"
        for row in ladder.dimensions.values()
    ]
    lines += [
        f"galaxy#{row.id} {row.name} ({GALAXY_TYPES[row.galaxy_type].label}; star formation {row.star_formation}/100"
        + (f"; patron #{row.patron_son_id}" if row.patron_son_id is not None else "")
        + ")"
        for row in ladder.galaxies.values()
    ]
    for rift in await scope.session.scalars(select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES))).order_by(RiftRow.id)):
        dimension = ladder.dimensions.get(rift.dimension_id)
        world = ladder.worlds.get(rift.world_id)
        state = f"{RIFT_STATE_LABELS[rift.state].lower()}, {RIFT_CAUSE_LABELS[rift.cause].lower()}"
        lines.append(
            f"rift#{rift.id} in {world.name if world else 'a world'} into {dimension.name if dimension else 'a dimension'} (size {rift.size}/100; {state})"
        )
    for being in await scope.session.scalars(select(CosmicBeingProfileRow).order_by(CosmicBeingProfileRow.entity_id)):
        entity = await scope.session.get(EntityRow, being.entity_id)
        if entity is None or entity.status is not EntityStatus.CANON:
            continue
        lines.append(
            f"being#{entity.id} {entity.name} ({BEING_KINDS[being.being_kind].label}; {BEING_SCALE_LABELS[being.scale].lower()} scale; "
            f"{BEING_PHASE_LABELS[being.phase].lower()}; aim: {BEING_AGENDA_LABELS[being.agenda].lower()}; might {being.might}/100)"
        )
    return lines


async def body_lines(scope: Scope, world_id: int) -> list[str]:
    lines: list[str] = []
    physics = await scope.session.get(WorldPhysicsRow, world_id)
    if physics is not None:
        lines.append(
            f"surface {round(physics.surface_temperature)} K, gravity {physics.gravity_g:g} g, air pressure {physics.pressure:g}, "
            f"water {physics.hydrosphere}/100, ice {physics.cryosphere}/100"
        )
        world = scope.worlds.get(world_id)
        star = await scope.session.get(StarRow, world.star_id) if world is not None and world.star_id is not None else None
        period = eclipse_period(scope.rules, physics, star)
        if world is not None and period is not None:
            lines.append(f"the next great eclipse darkens its sky at age {next_epoch(scope.epoch, period, world.id)}")
    life = await scope.session.get(WorldLifeRow, world_id)
    if life is not None:
        lines.append(f"life: {spoken(life.complexity)}")
    pending = select(ImpactEventRow).where(ImpactEventRow.world_id == world_id, ImpactEventRow.outcome == ImpactOutcome.PENDING)
    for impact in await scope.session.scalars(pending.order_by(ImpactEventRow.due_epoch, ImpactEventRow.id)):
        region = await scope.session.get(EntityRow, impact.region_entity_id) if impact.region_entity_id is not None else None
        lines.append(
            f"impact#{impact.id}: {an(impact.body.value.replace('_', ' '))} of size {impact.size}/100 strikes"
            + (f" {region.name}" if region is not None else "")
            + f" at age {impact.due_epoch}"
        )
    for project in await scope.session.scalars(select(TerraformingRow).where(TerraformingRow.world_id == world_id).order_by(TerraformingRow.id)):
        lines.append(f"a work to {TERRAFORM_AIMS[project.aim].words}, {several(project.epochs_left, 'age', 'ages')} left")
    root = scope.worlds.get(world_id)
    star_id = root.star_id if root is not None else None
    returning = select(CosmicFeatureRow).where(
        CosmicFeatureRow.star_id == star_id, CosmicFeatureRow.kind.in_(sorted(PERIODIC_BODIES)), CosmicFeatureRow.ended_epoch.is_(None)
    )
    for body in await scope.session.scalars(returning.order_by(CosmicFeatureRow.next_return_epoch, CosmicFeatureRow.id)) if star_id is not None else []:
        if body.next_return_epoch is not None:
            lines.append(f"{body.name} returns to its sky at age {body.next_return_epoch}")
    return lines


async def world_line_context(scope: Scope, world_id: int) -> WorldLineContext | None:
    world = scope.worlds.get(world_id)
    if world is None:
        return None
    star = await scope.session.get(StarRow, world.star_id) if world.star_id is not None else None
    golden = await golden_age_status(scope.session, scope.rules, world.id, scope.epoch)
    ladder = await cosmography_of(scope.session)
    place = ladder.place_world(world)
    rifts = int(
        await scope.session.scalar(select(func.count()).select_from(RiftRow).where(RiftRow.world_id == world.id, RiftRow.state.in_(list(OPEN_RIFT_STATES))))
        or 0
    )
    phenomena = [await phenomenon_line(scope, row) for row in await canon(scope.session, [EntityType.PHENOMENON], world.id)]
    phenomena += await omen_lines(scope, world.id)
    return WorldLineContext(
        galaxy_name=place.galaxy.name if place.galaxy is not None else None,
        galaxy_type=GALAXY_TYPES[place.galaxy.galaxy_type].label if place.galaxy is not None else None,
        zone_label=GALACTIC_ZONES[place.zone].label if place.galaxy is not None else None,
        structure_name=place.structure.name if place.structure is not None else None,
        cluster_name=place.cluster.name if place.cluster is not None else None,
        dimension_name=place.dimension.name if place.dimension is not None and len(ladder.dimensions) > 1 else None,
        dimension_kind=DIMENSION_KINDS[place.dimension.dimension_kind].label if place.dimension is not None and len(ladder.dimensions) > 1 else None,
        star_age=STAR_AGE_LABELS[place.star.age_stage].lower() if place.star is not None else None,
        world_age=WORLD_AGE_LABELS[world.age_stage].lower(),
        biosphere=world.biosphere_health,
        radiation=world.radiation,
        open_rifts=rifts,
        phenomena=phenomena,
        heavens=await heaven_lines(scope, ladder),
        body=await body_lines(scope, world.id),
        golden_age_epochs=golden.epochs if golden.active else None,
        golden_age_since=golden.since_epoch,
        golden_age_gain=golden.prosperity_gain,
        golden_age_soft=golden.decadence > 0,
        id=world.id,
        name=world.name,
        type_label=WORLD_TYPES[world.world_type].label,
        star_name=star.name if star else None,
        star_type=STAR_TYPE_LABELS[star.star_type] if star else None,
        gravity=GRAVITY_LABELS[world.gravity],
        atmosphere=ATMOSPHERE_LABELS[world.atmosphere],
        time_factor=world.time_factor,
        leak=world.leakage,
        cosmology=world.cosmology if world.id != scope.primary_world_id else None,
    )


async def world_line(scope: Scope, world_id: int | None) -> str:
    context = await world_line_context(scope, world_id) if world_id is not None else None
    return render(PromptId.WORLD_LINE, context) if context is not None else ""
