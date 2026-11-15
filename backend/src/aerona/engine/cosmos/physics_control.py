from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import (
    CosmicFeatureRow,
    ImpactEventRow,
    StarPhysicsRow,
    StarSystemRow,
    TerraformingRow,
    WorldLifeRow,
    WorldPhysicsRow,
    WorldSurveyRow,
)
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.physics import PERIODIC_BODIES, CosmicFeatureKind, LifeEnvironment, SurveyLevel, SystemRole, TerraformAim
from aerona.domain.enums.world import WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.catastrophe import scorch_world
from aerona.engine.cosmos.features import periodic_period
from aerona.engine.cosmos.impacts import call_impact, deflect_impact
from aerona.engine.cosmos.lifeforms import life_of
from aerona.engine.cosmos.stellar import luminosity_shifts, physics_of_stars, refresh
from aerona.engine.cosmos.survey import OBSERVER_TYPES
from aerona.engine.cosmos.systems import join_system, settle_systems, system_name
from aerona.engine.cosmos.terraform import begin
from aerona.engine.divine.control import apply
from aerona.engine.notes import note

Values = Mapping[str, Any]
SYSTEM_KEYS = frozenset({"system_id", "role"})
BROKEN_WORLDS = frozenset({WorldType.SHATTERED, WorldType.ASTEROID_BELT})
STAR_BOUND = frozenset({CosmicFeatureKind.ASTEROID_FIELD, CosmicFeatureKind.GRAVITY_WELL, *PERIODIC_BODIES})


async def found[Row](ctx: TickContext, kind: type[Row], key: object, label: str) -> Row:
    row = await ctx.session.get(kind, key)
    if row is None:
        raise NotFoundError(f"No such {label}.")
    return row


async def star_physics(ctx: TickContext, star_id: int) -> tuple[StarRow, StarPhysicsRow]:
    star = await found(ctx, StarRow, star_id, "star")
    return star, (await physics_of_stars(ctx.session, ctx.rules, [star]))[star.id]


async def edit_star_physics(ctx: TickContext, star_id: int, values: Values, release: list[str]) -> StarPhysicsRow:
    if SYSTEM_KEYS & set(values):
        raise ValidationFailedError("Move a star between systems with the system levers.")
    star, row = await star_physics(ctx, star_id)
    if "mass" in values and float(values["mass"]) <= 0:
        raise ValidationFailedError("A star's mass must be above nothing.")
    apply(row, values, release)
    refresh(ctx.rules, star, row, (await luminosity_shifts(ctx.session)).get(star.id, 0))
    await ctx.session.flush()
    return row


async def create_system(ctx: TickContext, name: str, star_ids: list[int], separation: float) -> StarSystemRow:
    if not star_ids:
        raise ValidationFailedError("A system holds at least one star.")
    stars = [await found(ctx, StarRow, star_id, "star") for star_id in star_ids]
    system = StarSystemRow(
        name=name.strip() or system_name(stars[0]),
        galaxy_id=stars[0].galaxy_id,
        x=stars[0].x,
        y=stars[0].y,
        separation=max(0.0, separation),
        created_epoch=max(1, ctx.epoch),
        locked=[],
    )
    ctx.session.add(system)
    await ctx.session.flush()
    for index, star in enumerate(stars):
        row = await join_system(ctx.session, ctx.rules, star, system.id)
        row.role = SystemRole.PRIMARY if index == 0 else SystemRole.COMPANION
    await settle_systems(ctx.session, ctx.rules)
    return system


async def edit_system(ctx: TickContext, system_id: int, values: Values, release: list[str]) -> StarSystemRow:
    row = apply(await found(ctx, StarSystemRow, system_id, "star system"), values, release)
    await settle_systems(ctx.session, ctx.rules)
    return row


async def delete_system(ctx: TickContext, system_id: int) -> None:
    system = await found(ctx, StarSystemRow, system_id, "star system")
    for row in await ctx.session.scalars(select(StarPhysicsRow).where(StarPhysicsRow.system_id == system.id)):
        row.system_id = None
        row.locked = [item for item in row.locked if item != "system_id"]
    await ctx.session.delete(system)
    await ctx.session.flush()


async def move_star(ctx: TickContext, star_id: int, system_id: int, role: SystemRole) -> StarPhysicsRow:
    star = await found(ctx, StarRow, star_id, "star")
    await found(ctx, StarSystemRow, system_id, "star system")
    row = await join_system(ctx.session, ctx.rules, star, system_id)
    if role is SystemRole.PRIMARY:
        for other in await ctx.session.scalars(select(StarPhysicsRow).where(StarPhysicsRow.system_id == system_id, StarPhysicsRow.star_id != star.id)):
            other.role = SystemRole.COMPANION
    row.role = role
    row.locked = sorted({*row.locked, "system_id"})
    await settle_systems(ctx.session, ctx.rules)
    return row


async def edit_world_physics(ctx: TickContext, world_id: int, values: Values, release: list[str]) -> WorldPhysicsRow:
    row = await found(ctx, WorldPhysicsRow, world_id, "world's physics")
    for key in ("mass", "radius", "rotation_hours"):
        if key in values and float(values[key]) <= 0:
            raise ValidationFailedError(f"A world's {key.replace('_', ' ')} must be above nothing.")
    if "eccentricity" in values and not 0 <= float(values["eccentricity"]) < 1:
        raise ValidationFailedError("An orbit's eccentricity runs from 0 up to, but not reaching, 1.")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def break_moon(ctx: TickContext, moon_id: int, by: str) -> WorldRow:
    moon = await found(ctx, WorldRow, moon_id, "world")
    parent = await ctx.session.get(WorldRow, moon.parent_world_id) if moon.parent_world_id is not None else None
    if parent is None:
        raise ValidationFailedError(f"{moon.name} circles no world; only a moon breaks into a ring.")
    if moon.world_type in BROKEN_WORLDS:
        raise ValidationFailedError(f"{moon.name} is already broken.")
    if "world_type" in moon.locked:
        raise ValidationFailedError(f"The nature of {moon.name} is held.")
    await scorch_world(ctx, moon, f"{by} broke")
    moon.world_type = WorldType.SHATTERED
    await note(ctx, f"{by} broke {moon.name} into a ring about {parent.name}.", key="world.ring_formed", world_id=parent.id, kind=ChronicleKind.SKY)
    await ctx.session.flush()
    return moon


async def edit_life(ctx: TickContext, world_id: int, values: Values, release: list[str]) -> WorldLifeRow:
    world = await found(ctx, WorldRow, world_id, "world")
    places = values.get("environments")
    if places is not None and (not isinstance(places, list) or any(item not in set(LifeEnvironment) for item in places)):
        raise ValidationFailedError(f"Life dwells in {', '.join(sorted(LifeEnvironment))}; name only those.")
    row = apply(await life_of(ctx.session, world), values, release)
    await ctx.session.flush()
    return row


async def create_feature(ctx: TickContext, kind: CosmicFeatureKind, name: str, values: Values) -> CosmicFeatureRow:
    star_id = values.get("star_id")
    star = await found(ctx, StarRow, star_id, "star") if star_id is not None else None
    if kind is CosmicFeatureKind.WORMHOLE and (
        values.get("world_id") is None or values.get("world_b_id") is None or values.get("world_id") == values.get("world_b_id")
    ):
        raise ValidationFailedError("A wormhole joins two different worlds.")
    if kind in STAR_BOUND and star is None:
        raise ValidationFailedError("This feature belongs to a star; choose one.")
    if kind is CosmicFeatureKind.ROGUE_WORLD and star is None and values.get("galaxy_id") is None:
        raise ValidationFailedError("A rogue world drifts among the stars of a galaxy; choose its star or its galaxy.")
    row = CosmicFeatureRow(
        kind=kind,
        name=name.strip() or kind.value.replace("_", " ").capitalize(),
        galaxy_id=star.galaxy_id if star is not None else values.get("galaxy_id"),
        x=star.x if star is not None else 0.0,
        y=star.y if star is not None else 0.0,
        created_epoch=max(1, ctx.epoch),
        locked=[],
    )
    ctx.session.add(row)
    apply(row, {key: value for key, value in values.items() if value is not None}, [])
    row.locked = []
    if kind is CosmicFeatureKind.ASTEROID_FIELD and values.get("density") is None:
        row.density = ctx.rules.cosmic_features.field_density
    if kind in PERIODIC_BODIES and values.get("omen_weight") is None:
        row.omen_weight = PERCENT // 2
    if kind in PERIODIC_BODIES and row.next_return_epoch is None:
        row.period_epochs = row.period_epochs or periodic_period(ctx, kind)
        row.next_return_epoch = ctx.epoch + row.period_epochs
    await ctx.session.flush()
    return row


async def edit_feature(ctx: TickContext, feature_id: int, values: Values, release: list[str]) -> CosmicFeatureRow:
    row = apply(await found(ctx, CosmicFeatureRow, feature_id, "cosmic feature"), values, release)
    await ctx.session.flush()
    return row


async def delete_feature(ctx: TickContext, feature_id: int) -> None:
    await ctx.session.delete(await found(ctx, CosmicFeatureRow, feature_id, "cosmic feature"))
    await ctx.session.flush()


async def call(ctx: TickContext, world_id: int, region_id: int | None, by_node_id: int | None, *, by: str, size: int | None) -> ImpactEventRow:
    return await call_impact(ctx, world_id, region_id, by_node_id, by, size=size)


async def deflect(ctx: TickContext, impact_id: int, by_node_id: int | None, by: str) -> ImpactEventRow:
    return await deflect_impact(ctx, impact_id, by_node_id, by)


async def edit_impact(ctx: TickContext, impact_id: int, values: Values, release: list[str]) -> ImpactEventRow:
    row = apply(await found(ctx, ImpactEventRow, impact_id, "impact"), values, release)
    await ctx.session.flush()
    return row


async def delete_impact(ctx: TickContext, impact_id: int) -> None:
    await ctx.session.delete(await found(ctx, ImpactEventRow, impact_id, "impact"))
    await ctx.session.flush()


async def start_terraform(
    ctx: TickContext, world_id: int, aim: TerraformAim, by_node_id: int | None, *, by: str, step: int | None, epochs: int | None
) -> TerraformingRow:
    return await begin(ctx, world_id, aim, by_node_id, by, step=step, epochs=epochs)


async def edit_terraform(ctx: TickContext, project_id: int, values: Values, release: list[str]) -> TerraformingRow:
    row = apply(await found(ctx, TerraformingRow, project_id, "terraforming"), values, release)
    await ctx.session.flush()
    return row


async def stop_terraform(ctx: TickContext, project_id: int) -> None:
    await ctx.session.delete(await found(ctx, TerraformingRow, project_id, "terraforming"))
    await ctx.session.flush()


async def set_survey(ctx: TickContext, observer_id: int, world_id: int, level: SurveyLevel) -> WorldSurveyRow:
    observer = await found(ctx, EntityRow, observer_id, "people or realm")
    if observer.entity_type not in OBSERVER_TYPES:
        raise ValidationFailedError("Only a people or a realm keeps a survey of the worlds.")
    await found(ctx, WorldRow, world_id, "world")
    row = await ctx.session.scalar(select(WorldSurveyRow).where(WorldSurveyRow.observer_entity_id == observer.id, WorldSurveyRow.world_id == world_id))
    if row is None:
        row = WorldSurveyRow(observer_entity_id=observer.id, world_id=world_id, level=level, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.level = level
    row.epoch = ctx.epoch
    row.locked = ["level"]
    await ctx.session.flush()
    return row


async def forget_survey(ctx: TickContext, survey_id: int) -> None:
    await ctx.session.delete(await found(ctx, WorldSurveyRow, survey_id, "survey"))
    await ctx.session.flush()
