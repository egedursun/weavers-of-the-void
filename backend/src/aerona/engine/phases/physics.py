from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.physics import StarPhysicsRow, WorldLifeRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.world import WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.features import adopt_comets, devour, ensure_wells, harbour_pirates, keep_wormholes, mine_fields, pass_rogues, return_comets
from aerona.engine.cosmos.impacts import forecast, impact_winters, resolve
from aerona.engine.cosmos.lifeforms import inferred_life, quicken
from aerona.engine.cosmos.orbits import Moon, apply_to_world, calibrate, derive, infer, lose_air, rogue_worlds, root_of, sky_of
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.planetary import planetary_climate, sea_level_of
from aerona.engine.cosmos.stellar import hundredths, physics_of_stars
from aerona.engine.cosmos.survey import survey_cycle
from aerona.engine.cosmos.systems import ensure_systems, sync_system, systems_of, turn_galaxies
from aerona.engine.cosmos.terraform import powers_reshape, terraform_cycle
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.environment import write_seasons
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules

BROKEN = frozenset({WorldType.SHATTERED, WorldType.ASTEROID_BELT})


@reads("table.cosmos", "table.dimensional_events", "table.galactic_structures", "table.star_physics", "table.star_systems")
@writes("table.star_physics", "table.star_systems", "table.stars")
async def stellar_systems(ctx: TickContext) -> None:
    ctx.count("systems_made", await ensure_systems(ctx.session, ctx.rules, ctx.epoch))
    cosmography = await Cosmography.load(ctx.session)
    physics = await physics_of_stars(ctx.session, ctx.rules, list(cosmography.stars.values()))
    ctx.count("stars_turned", await turn_galaxies(ctx, cosmography, physics))
    for system in (await systems_of(ctx.session)).values():
        sync_system(ctx.rules, system, cosmography.stars, physics)
    await ctx.session.flush()


async def physics_rows(
    ctx: TickContext, worlds: dict[int, WorldRow], stars: dict[int, StarRow], star_physics: dict[int, StarPhysicsRow]
) -> dict[int, WorldPhysicsRow]:
    rows = {row.world_id: row for row in await ctx.session.scalars(select(WorldPhysicsRow))}
    systems = await systems_of(ctx.session)
    for world in sorted(worlds.values(), key=lambda row: row.id):
        if world.id in rows:
            continue
        root = root_of(worlds, world)
        star = stars.get(root.star_id) if root.star_id is not None else None
        row = infer(ctx.rules, world, star)
        parent = rows.get(world.parent_world_id) if world.parent_world_id is not None else None
        calibrate(ctx.rules, world, row, star=star, sky=sky_of(ctx.rules, root, row, stars=stars, star_physics=star_physics, systems=systems), parent=parent)
        row.sea_level = sea_level_of(ctx.rules, row)
        ctx.session.add(row)
        rows[world.id] = row
    for world in sorted(worlds.values(), key=lambda row: row.id):
        if await ctx.session.get(WorldLifeRow, world.id) is None:
            ctx.session.add(await inferred_life(ctx.session, world, rows.get(world.id)))
    await ctx.session.flush()
    return rows


def moons_of(worlds: dict[int, WorldRow], rows: dict[int, WorldPhysicsRow]) -> dict[int, list[Moon]]:
    found: dict[int, list[Moon]] = defaultdict(list)
    for world in worlds.values():
        row = rows.get(world.id)
        if world.parent_world_id is not None and row is not None and world.world_type not in BROKEN:
            found[world.parent_world_id].append(Moon(row.mass, world.orbit, row.inclination))
    return found


async def break_moons(ctx: TickContext, worlds: dict[int, WorldRow]) -> int:
    roche = hundredths(ctx.rules.orbits.roche_orbit_hundredths)
    broken = 0
    for world in sorted(worlds.values(), key=lambda row: row.id):
        if world.parent_world_id is None or world.orbit >= roche or world.world_type in BROKEN or held(world.id) or "world_type" in world.locked:
            continue
        world.world_type = WorldType.SHATTERED
        parent = worlds.get(world.parent_world_id)
        await note(
            ctx,
            f"{world.name} came too near {parent.name if parent is not None else 'its world'} and broke into a ring.",
            key="world.ring_formed",
            world_id=world.parent_world_id,
            kind=ChronicleKind.SKY,
        )
        broken += 1
    return broken


async def derive_all(ctx: TickContext, *, quiet: bool) -> int:
    cosmography = await Cosmography.load(ctx.session)
    worlds, stars = cosmography.worlds, cosmography.stars
    star_physics = await physics_of_stars(ctx.session, ctx.rules, list(stars.values()))
    known = set(await ctx.session.scalars(select(WorldPhysicsRow.world_id)))
    rows = await physics_rows(ctx, worlds, stars, star_physics)
    if not quiet:
        ctx.count("rings_formed", await break_moons(ctx, worlds))
        ctx.count("life_quickened", await quicken(ctx, worlds, rows))
    moons = moons_of(worlds, rows)
    rogue = await rogue_worlds(ctx.session)
    systems = await systems_of(ctx.session)
    derived = 0
    for world_id, row in sorted(rows.items()):
        world = worlds.get(world_id)
        if world is None or held(world_id):
            continue
        root = root_of(worlds, world)
        sky = sky_of(ctx.rules, root, rows.get(root.id, row), stars=stars, star_physics=star_physics, systems=systems)
        parent = rows.get(world.parent_world_id) if world.parent_world_id is not None else None
        was_locked = row.tidally_locked
        derive(ctx.rules, world, row, sky=sky, moons=moons.get(world.id, []), parent=parent, rogue=rogue, orbit=root.orbit)
        if not quiet and lose_air(ctx.rules, row):
            ctx.count("air_lost")
        changed = apply_to_world(ctx.rules, world, row, sky, moons.get(world.id, []))
        if "season_count" in changed:
            await write_seasons(ctx, world)
        if not quiet and world_id in known and row.tidally_locked and not was_locked:
            await note(ctx, f"{world.name} came to turn one face forever to its star.", key="world.tidally_locked", world_id=world.id, kind=ChronicleKind.SKY)
        derived += 1
    await ctx.session.flush()
    return derived


@reads("table.cosmic_features", "table.cosmos", "table.star_physics", "table.star_systems", "table.world_physics", "table.worlds")
@writes("table.chronicle", "table.epoch_year_cursors", "table.incidents", "table.world_life", "table.world_physics", "table.world_seasons", "table.worlds")
async def world_physics(ctx: TickContext) -> None:
    ctx.count("worlds_derived", await derive_all(ctx, quiet=False))


async def settle_heavens(session: AsyncSession, rules: Rules) -> int:
    ctx = await manual_context(session, "heavens_physics", rules)
    made = await ensure_systems(session, rules, ctx.epoch)
    made += await derive_all(ctx, quiet=True)
    return made + await survey_cycle(ctx, await Cosmography.load(session))


@reads("table.cosmos", "table.region_environment", "table.world_physics")
@writes("table.chronicle", "table.epoch_year_cursors", "table.incidents", "table.region_environment", "table.world_physics")
async def planetary(ctx: TickContext) -> None:
    worlds = {row.id: row for row in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))}
    rows = {row.world_id: row for row in await ctx.session.scalars(select(WorldPhysicsRow))}
    ctx.count("climate_moves", await planetary_climate(ctx, worlds, rows))
    await ctx.session.flush()


@reads("table.cosmic_features", "table.cosmos", "table.routes", "table.star_physics")
@writes("table.chronicle", "table.community_stocks", "table.cosmic_features", "table.epoch_year_cursors", "table.incidents", "table.routes", "table.sky_events")
async def cosmic_features(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    ctx.count("wells_made", await ensure_wells(ctx, cosmography))
    ctx.count("comets_adopted", await adopt_comets(ctx))
    ctx.count("fields_mined", await mine_fields(ctx, cosmography))
    ctx.count("routes_raided", await harbour_pirates(ctx, cosmography))
    ctx.count("wormholes_kept", await keep_wormholes(ctx))
    ctx.count("worlds_devoured", await devour(ctx, cosmography))
    ctx.count("orbits_perturbed", await pass_rogues(ctx, cosmography))
    ctx.count("comets_returned", await return_comets(ctx, cosmography))
    await ctx.session.flush()


@reads("table.cosmic_features", "table.cosmos", "table.impact_events")
@writes("table.chronicle", "table.epoch_year_cursors", "table.impact_events", "table.incidents", "table.region_environment")
async def impacts(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    ctx.count("impacts_foreseen", await forecast(ctx, cosmography))
    ctx.count("impacts_struck", await resolve(ctx))
    ctx.count("impact_winters", await impact_winters(ctx))
    await ctx.session.flush()


@reads("table.terraforming", "table.world_physics")
@writes(
    "table.chronicle", "table.epoch_year_cursors", "table.incidents", "table.terraforming", "table.world_biochemistries", "table.world_physics", "table.worlds"
)
async def terraforming(ctx: TickContext) -> None:
    ctx.count("terraform_steps", await terraform_cycle(ctx))
    ctx.count("terraform_begun", await powers_reshape(ctx))
    await ctx.session.flush()


@reads("table.journeys", "table.routes", "table.world_surveys")
@writes("table.world_surveys")
async def surveys(ctx: TickContext) -> None:
    ctx.count("surveys_raised", await survey_cycle(ctx, await Cosmography.load(ctx.session)))


EARLY = (Phase("stellar_systems", stellar_systems),)
LATE = (
    Phase("world_physics", world_physics),
    Phase("planetary_climate", planetary),
    Phase("cosmic_features", cosmic_features),
    Phase("impacts", impacts),
    Phase("terraforming", terraforming),
    Phase("surveys", surveys),
)
