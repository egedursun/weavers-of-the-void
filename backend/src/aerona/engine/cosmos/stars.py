import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stars import STAR_TYPE_LABELS, STAR_TYPES
from aerona.constants.cosmos import STAR_MAP_BASE_RADIUS, STAR_MAP_RADIUS_STEP
from aerona.constants.player import ORBIT_PLANET_BASE
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.worlds import StarDraft, WorldRepository
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.cosmography import GalaxyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery, SkyEventKind, StarType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.ladder import ensure_ladder, home_galaxy, settle_star
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.remnants import after_supernova
from aerona.engine.cosmos.routes import restore_sail_routes, scorch_sail_routes, snap_sail_routes
from aerona.engine.cosmos.star_types import fitted_brightness, kindled_brightness
from aerona.engine.cosmos.worlds import align_moons
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import scale_stat, shift_bounded, stat_or
from aerona.rules.registry import Rules

BRIGHTNESS_KEY = "brightness"
FERTILITY_KEY = "fertility"
POPULATION_KEY = "population"
FOLLOWERS_KEY = "followers"
PIETY_KEY = "piety"


def star_label(star_type: StarType) -> str:
    return STAR_TYPE_LABELS[star_type]


async def star_position(session: AsyncSession, rng: SeededRandom, galaxy_id: int | None = None) -> tuple[float, float]:
    statement = select(func.count()).select_from(StarRow)
    if galaxy_id is not None:
        statement = statement.where(StarRow.galaxy_id == galaxy_id)
    count = int(await session.scalar(statement) or 0)
    angle = rng.random() * math.tau
    radius = STAR_MAP_BASE_RADIUS + count * STAR_MAP_RADIUS_STEP
    return math.cos(angle) * radius, math.sin(angle) * radius


@dataclass(frozen=True)
class StarSpec:
    name: str
    star_type: StarType
    brightness_base: int
    brightness_die: int
    description: str | None = None
    galaxy_id: int | None = None
    position: tuple[float, float] | None = None


async def create_star(session: AsyncSession, rules: Rules, rng: SeededRandom, epoch: int, spec: StarSpec) -> StarRow:
    name = await NameRepository(session).unique_name(spec.name)
    brightness = kindled_brightness(rules, spec.star_type, spec.brightness_base + rng.die(spec.brightness_die))
    galaxy_id = spec.galaxy_id
    if galaxy_id is None:
        await ensure_ladder(session, rules)
        home = await home_galaxy(session)
        galaxy_id = home.id if home is not None else None
    x, y = spec.position if spec.position is not None else await star_position(session, rng, galaxy_id)
    star = await WorldRepository(session).create_star(StarDraft(name, spec.star_type, brightness, x, y, epoch, spec.description, galaxy_id))
    settle_star(rules, await Cosmography.load(session), star)
    return star


async def worlds_of_star(session: AsyncSession, star_id: int, *, include_forgotten: bool = False) -> list[WorldRow]:
    repository = WorldRepository(session)
    found: list[WorldRow] = []
    for world in await repository.all_worlds():
        if not include_forgotten and world.discovery is Discovery.FORGOTTEN:
            continue
        if await repository.root_star_id(world) == star_id:
            found.append(world)
    return found


async def require_star(session: AsyncSession, star_id: int | None) -> StarRow:
    if star_id is None:
        raise ValidationFailedError("A star is needed.")
    star = await session.get(StarRow, star_id)
    if star is None:
        raise NotFoundError("No such star.")
    return star


async def choose_epoch_stars(ctx: TickContext) -> dict[int, int | None]:
    chosen: dict[int, int | None] = {}
    rng = ctx.rng("epoch_star")
    base = ctx.rules.sky.star_pick_base_weight
    for world in await WorldRepository(ctx.session).reachable_worlds():
        bodies = await canon(ctx.session, [EntityType.CELESTIAL], world.id)
        if not bodies:
            world.epoch_star_entity_id = None
            chosen[world.id] = None
            continue
        pick = rng.weighted(bodies, [base + stat_or(body, BRIGHTNESS_KEY, 0) for body in bodies])
        world.epoch_star_entity_id = pick.id
        chosen[world.id] = pick.id
    await ctx.session.flush()
    return chosen


async def set_epoch_star(session: AsyncSession, world_id: int, entity_id: int | None) -> WorldRow:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if entity_id is not None:
        body = await session.get(EntityRow, entity_id)
        if body is None or body.entity_type is not EntityType.CELESTIAL or body.world_id != world_id or body.status is not EntityStatus.CANON:
            raise ValidationFailedError("The star of the epoch must be a living sky body of that world.")
    world.epoch_star_entity_id = entity_id
    await session.flush()
    return world


def _add_leak(world: WorldRow, amount: int) -> None:
    world.leakage = max(0, min(PERCENT_MAX, world.leakage + amount))


async def supernova(ctx: TickContext, star: StarRow) -> str:
    sky = ctx.rules.sky
    star.star_type = STAR_TYPES[star.star_type].remnant
    star.brightness = fitted_brightness(ctx.rules, star.star_type, sky.supernova_remnant_brightness)
    for world in await worlds_of_star(ctx.session, star.id):
        for entity in await canon(ctx.session, None, world.id):
            scale_stat(ctx.rules, entity, POPULATION_KEY, 1 - sky.supernova_population_loss_pct / PERCENT)
            shift_bounded(ctx.rules, entity, FERTILITY_KEY, -sky.supernova_fertility_loss)
        _add_leak(world, sky.supernova_leak)
    await advance_doom(ctx.session, ctx.rules, sky.supernova_apocalypse)
    await snap_sail_routes(ctx, star.id)
    await after_supernova(ctx, star)
    await ctx.session.flush()
    return f"{star.name} exploded; the worlds around it lost most of their peoples and much of their soil, and a remnant was left in its place."


async def black_sun(ctx: TickContext, star: StarRow) -> str:
    sky = ctx.rules.sky
    star.star_type = StarType.BLACK_SUN
    star.brightness = 0
    cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    for world in await worlds_of_star(ctx.session, star.id):
        _add_leak(world, sky.black_sun_leak)
        for cult in await canon(ctx.session, [EntityType.CULT], world.id):
            if cult.id in cults:
                followers = stat_or(cult, FOLLOWERS_KEY, sky.cult_default_followers)
                scale_stat(ctx.rules, cult, FOLLOWERS_KEY, sky.black_sun_outer_cult_mult_pct / PERCENT, default=followers)
    await snap_sail_routes(ctx, star.id)
    await ctx.session.flush()
    return f"{star.name} turned into a black sun that gives no light."


async def flare(ctx: TickContext, star: StarRow) -> str:
    sky = ctx.rules.sky
    worlds = await worlds_of_star(ctx.session, star.id)
    for world in worlds:
        for region in await canon(ctx.session, [EntityType.REGION], world.id):
            shift_bounded(ctx.rules, region, FERTILITY_KEY, -sky.flare_fertility_loss)
        for community in await canon(ctx.session, COMMUNITY_TYPES, world.id):
            shift_bounded(ctx.rules, community, PIETY_KEY, sky.flare_piety_gain)
    scorched = await scorch_sail_routes(ctx, star.id)
    names = ", ".join(world.name for world in worlds) or "the empty void around it"
    text = f"{star.name} flared: the fields of {names} lost fertility and auroras filled their skies."
    if scorched:
        text += f" The flare scorched shut {scorched} light-sail route{'s' if scorched > 1 else ''} bound to it."
    await ctx.session.flush()
    return text


async def extinguish_star(ctx: TickContext, star_id: int, by: str) -> str:
    pantheon = ctx.rules.pantheon
    star = await require_star(ctx.session, star_id)
    star.star_type = StarType.DEAD_STAR
    star.brightness = fitted_brightness(ctx.rules, StarType.DEAD_STAR, pantheon.dead_star_brightness)
    worlds = await worlds_of_star(ctx.session, star.id)
    for world in worlds:
        _add_leak(world, pantheon.extinguish_leak)
        for region in await canon(ctx.session, [EntityType.REGION], world.id):
            shift_bounded(ctx.rules, region, FERTILITY_KEY, -pantheon.extinguish_fertility_loss, default=pantheon.default_fertility)
    await advance_doom(ctx.session, ctx.rules, pantheon.extinguish_star_apocalypse)
    await snap_sail_routes(ctx, star.id)
    names = ", ".join(world.name for world in worlds) or "The void around it"
    text = f"{by} extinguished {star.name}. {names} lost their light; their lands cooled and the leak grew."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="sky.star_extinguished", feed_category=FeedCategory.SKY)
    await ctx.session.flush()
    return text


async def rekindle_star(ctx: TickContext, star_id: int, by: str) -> str:
    hand = ctx.rules.god_hand
    star = await require_star(ctx.session, star_id)
    if star.star_type not in EXTINGUISHED_STAR_TYPES:
        raise ValidationFailedError(f"{star.name} is already burning.")
    star.star_type = StarType.REBORN_STAR
    star.brightness = fitted_brightness(ctx.rules, StarType.REBORN_STAR, hand.rekindle_brightness)
    for world in await worlds_of_star(ctx.session, star.id):
        _add_leak(world, -hand.rekindle_leak_drain)
    await restore_sail_routes(ctx.session, star.id)
    await end_black_sun(ctx.session, star.id, ctx.epoch)
    text = f"{by} rekindled {star.name}; its worlds have light again."
    await ctx.chronicle(ChronicleKind.SKY, text, template_key="sky.star_rekindled", feed_category=FeedCategory.SKY)
    await ctx.session.flush()
    return text


async def hang_star(
    ctx: TickContext,
    name: str,
    star_type: StarType,
    by: str,
    description: str | None = None,
    *,
    galaxy_id: int | None = None,
    world_id: int | None = None,
) -> StarRow:
    pantheon = ctx.rules.pantheon
    if galaxy_id is not None and await ctx.session.get(GalaxyRow, galaxy_id) is None:
        raise NotFoundError("No such galaxy.")
    world = await ctx.session.get(WorldRow, world_id) if world_id is not None else None
    if world_id is not None and world is None:
        raise NotFoundError("No such world.")
    rng = ctx.rng("hang_star")
    position: tuple[float, float] | None = None
    root: WorldRow | None = None
    if world is not None:
        cosmography = await Cosmography.load(ctx.session)
        root = cosmography.root_world(world)
        place = cosmography.place_world(root)
        galaxy_id = place.galaxy_id if place.galaxy_id is not None else galaxy_id
        if place.star is not None:
            position = beside(place.star, rng)
    star = await create_star(
        ctx.session,
        ctx.rules,
        rng,
        ctx.epoch,
        StarSpec(name, star_type, pantheon.star_brightness_base, pantheon.star_brightness_die, description, galaxy_id=galaxy_id, position=position),
    )
    text = f"{by} hung a new star in the sky: {star.name} ({star_label(star_type)})."
    if world is not None and root is not None:
        text = f"{by} hung a new star in the sky of {world.name}: {star.name} ({star_label(star_type)})."
        if root.star_id is None and not held(root.id):
            root.star_id = star.id
            root.orbit = ORBIT_PLANET_BASE
            await align_moons(ctx.session)
            text += f" {root.name} now circles it."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="sky.star_hung", feed_category=FeedCategory.SKY)
    await ctx.session.flush()
    return star


def beside(star: StarRow, rng: SeededRandom) -> tuple[float, float]:
    angle = rng.random() * math.tau
    return star.x + math.cos(angle) * STAR_MAP_RADIUS_STEP, star.y + math.sin(angle) * STAR_MAP_RADIUS_STEP


async def end_black_sun(session: AsyncSession, star_id: int, epoch: int) -> None:
    statement = select(SkyEventRow).where(SkyEventRow.star_id == star_id, SkyEventRow.kind == SkyEventKind.BLACK_SUN, SkyEventRow.until_epoch.is_(None))
    for row in await session.scalars(statement):
        row.until_epoch = max(row.epoch, epoch)
