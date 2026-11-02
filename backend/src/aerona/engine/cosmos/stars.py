import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.worlds import STAR_TYPE_LABELS
from aerona.constants.cosmos import STAR_MAP_BASE_RADIUS, STAR_MAP_RADIUS_STEP
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.worlds import StarDraft, WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.world import DARK_STAR_TYPES, Discovery, StarType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import restore_sail_routes, snap_sail_routes
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import scale_stat, shift_bounded, stat_or

EXTINGUISHED_STAR_TYPES = frozenset({StarType.DEAD_STAR, StarType.BLACK_SUN, StarType.STAR_REMNANT})
BRIGHTNESS_KEY = "brightness"
FERTILITY_KEY = "fertility"
POPULATION_KEY = "population"
FOLLOWERS_KEY = "followers"


def star_label(star_type: StarType) -> str:
    return STAR_TYPE_LABELS[star_type]


async def star_position(session: AsyncSession, rng: SeededRandom) -> tuple[float, float]:
    count = int(await session.scalar(select(func.count()).select_from(StarRow)) or 0)
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


async def create_star(session: AsyncSession, rng: SeededRandom, epoch: int, spec: StarSpec) -> StarRow:
    name = await NameRepository(session).unique_name(spec.name)
    brightness = 0 if spec.star_type is StarType.BLACK_SUN else clamp_percent(spec.brightness_base + rng.die(spec.brightness_die))
    x, y = await star_position(session, rng)
    return await WorldRepository(session).create_star(StarDraft(name, spec.star_type, brightness, x, y, epoch, spec.description))


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


async def world_star_body(session: AsyncSession, world_id: int) -> EntityRow | None:
    world = await session.get(WorldRow, world_id)
    if world is None or world.epoch_star_entity_id is None:
        return None
    return await session.get(EntityRow, world.epoch_star_entity_id)


def _add_leak(world: WorldRow, amount: int) -> None:
    world.leakage = max(0, min(PERCENT_MAX, world.leakage + amount))


async def supernova(ctx: TickContext, star: StarRow) -> str:
    sky = ctx.rules.sky
    star.star_type = StarType.STAR_REMNANT
    star.brightness = sky.supernova_remnant_brightness
    for world in await worlds_of_star(ctx.session, star.id):
        for entity in await canon(ctx.session, None, world.id):
            scale_stat(ctx.rules, entity, POPULATION_KEY, 1 - sky.supernova_population_loss_pct / PERCENT)
            shift_bounded(ctx.rules, entity, FERTILITY_KEY, -sky.supernova_fertility_loss)
        _add_leak(world, sky.supernova_leak)
    await advance_doom(ctx.session, ctx.rules, sky.supernova_apocalypse)
    await snap_sail_routes(ctx, star.id)
    await ctx.session.flush()
    burned = "the supernova's light burned the worlds around it; most of their peoples became ash"
    return f"{star.name} exploded: {burned}, a new and terrible light remained in the sky."


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
    return f"{star.name} turned into a black sun: it gives no light, it swallows light."


async def extinguish_star(ctx: TickContext, star_id: int, by: str) -> str:
    pantheon = ctx.rules.pantheon
    star = await require_star(ctx.session, star_id)
    star.star_type = StarType.DEAD_STAR
    star.brightness = pantheon.dead_star_brightness
    worlds = await worlds_of_star(ctx.session, star.id)
    for world in worlds:
        _add_leak(world, pantheon.extinguish_leak)
        for region in await canon(ctx.session, [EntityType.REGION], world.id):
            shift_bounded(ctx.rules, region, FERTILITY_KEY, -pantheon.extinguish_fertility_loss, default=pantheon.default_fertility)
    await advance_doom(ctx.session, ctx.rules, pantheon.extinguish_star_apocalypse)
    await snap_sail_routes(ctx, star.id)
    names = ", ".join(world.name for world in worlds) or "The void around it"
    text = f"{by} extinguished {star.name}. {names} sank into darkness; the lands cooled, the things outside came closer."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="sky.star_extinguished", feed_category=FeedCategory.SKY)
    await ctx.session.flush()
    return text


async def rekindle_star(ctx: TickContext, star_id: int, by: str) -> str:
    hand = ctx.rules.god_hand
    star = await require_star(ctx.session, star_id)
    if star.star_type not in EXTINGUISHED_STAR_TYPES:
        raise ValidationFailedError(f"{star.name} is already burning.")
    star.star_type = StarType.REBORN_STAR
    star.brightness = hand.rekindle_brightness
    for world in await worlds_of_star(ctx.session, star.id):
        _add_leak(world, -hand.rekindle_leak_drain)
    await restore_sail_routes(ctx.session, star.id)
    text = f"{by} rekindled {star.name}; light returned to the worlds buried in darkness."
    await ctx.chronicle(ChronicleKind.SKY, text, template_key="sky.star_rekindled", feed_category=FeedCategory.SKY)
    await ctx.session.flush()
    return text


async def hang_star(ctx: TickContext, name: str, star_type: StarType, by: str, description: str | None = None) -> StarRow:
    pantheon = ctx.rules.pantheon
    star = await create_star(
        ctx.session,
        ctx.rng("hang_star"),
        ctx.epoch,
        StarSpec(name, star_type, pantheon.star_brightness_base, pantheon.star_brightness_die, description),
    )
    text = f"{by} hung a new star in the sky: {star.name} ({star_label(star_type)})."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="sky.star_hung", feed_category=FeedCategory.SKY)
    return star


def is_dark(star: StarRow | None) -> bool:
    return star is not None and star.star_type in DARK_STAR_TYPES
