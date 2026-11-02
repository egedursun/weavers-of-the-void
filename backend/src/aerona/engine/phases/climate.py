from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import ElevationClass
from aerona.catalog.climate import ClimateProfile, climate_profile, climate_weights
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climate import ClimateOrderRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import ClimateEra
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_economy import population_bounds
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

LAND_TYPES = (EntityType.REGION, EntityType.PLACE)
HIGHLANDS = frozenset({ElevationClass.MOUNTAINOUS, ElevationClass.HILLY})


@dataclass(frozen=True)
class ClimateState:
    world_id: int
    era: ClimateEra
    epochs_left: int
    since_epoch: int
    profile: ClimateProfile
    plague_pct: int
    population_loss_pct: int
    imposed_by_son_id: int | None


def plague_pct(rules: Rules, era: ClimateEra) -> int:
    return rules.climate_effects.scorching_age_plague_freq if era is ClimateEra.SCORCHING else PERCENT


def population_loss_pct(rules: Rules, era: ClimateEra) -> int:
    return rules.climate_effects.ice_age_population_loss if era is ClimateEra.ICE_AGE else 0


def regional_change(rules: Rules, era: ClimateEra, coastal: bool, elevation: ElevationClass | None) -> int:
    settings = rules.climate_effects
    change = climate_profile(rules, era).fertility_change
    if era is ClimateEra.DROUGHT and coastal:
        change = round_half_up(change / settings.coast_drought_divisor)
    if era is ClimateEra.RAIN and coastal:
        change += settings.coast_rain_bonus
    if era is ClimateEra.ICE_AGE and elevation in HIGHLANDS:
        change -= settings.mountain_ice_loss
    return change


def drifted_fertility(rules: Rules, fertility: int, change: int) -> int:
    settings = rules.climate_effects
    equilibrium = settings.fertility_equilibrium
    divisor = settings.fertility_recovery_divisor if fertility < equilibrium else settings.fertility_decline_divisor
    return clamp_int(fertility + change + (equilibrium - fertility) / divisor, 0, PERCENT)


async def apply_climate_effect(ctx: TickContext, world: WorldRow, era: ClimateEra, atlas: RegionAtlas) -> int:
    changed = 0
    for land in await canon(ctx.session, LAND_TYPES, world.id):
        fertility = stat(land, "fertility")
        if fertility is None:
            continue
        region_id = atlas.top_region(land.id) or land.id
        record = atlas.record(region_id)
        change = regional_change(ctx.rules, era, record.coastal if record else False, record.elevation_class if record else None)
        set_stats(land, fertility=drifted_fertility(ctx.rules, fertility, change))
        changed += 1
    loss = population_loss_pct(ctx.rules, era)
    if loss:
        for community in await canon(ctx.session, SOCIETY_TYPES, world.id):
            population = stat(community, "population")
            if population is not None:
                floor, ceiling = population_bounds(ctx.rules, community)
                set_stats(community, population=clamp_int(population * (1 - fraction(loss)), floor, ceiling))
    return changed


def pick_next_era(ctx: TickContext, world: WorldRow, current: ClimateEra) -> ClimateEra:
    weights = climate_weights(ctx.rules, world.world_type)
    eras = [era for era in ClimateEra if era is not current and weights[era] > 0]
    if not eras:
        return current
    return ctx.rng(f"era.{world.id}").weighted(eras, [weights[era] for era in eras])


def ensure_climate(ctx: TickContext, world: WorldRow) -> ClimateEra:
    if world.climate_era is None or world.climate_epochs_left is None:
        settings = ctx.rules.climate_effects
        world.climate_era = ClimateEra.TEMPERATE
        world.climate_epochs_left = settings.first_duration + ctx.rng(f"first_era.{world.id}").die(settings.first_die)
        world.climate_since_epoch = ctx.epoch
    return world.climate_era


async def announce_era(ctx: TickContext, world: WorldRow, era: ClimateEra, many_worlds: bool) -> None:
    profile = climate_profile(ctx.rules, era)
    prefix = f"{world.name}: " if many_worlds else ""
    await note(
        ctx,
        f"{prefix}the {profile.label.lower()} began. {profile.description}",
        key="climate.era",
        world_id=world.id,
        feed=FeedCategory.WORLD,
        kind=ChronicleKind.CLIMATE,
    )


async def advance_world(ctx: TickContext, world: WorldRow, atlas: RegionAtlas, many_worlds: bool) -> None:
    era = ensure_climate(ctx, world)
    order = await ctx.session.get(ClimateOrderRow, world.id)
    if order is not None:
        await apply_climate_effect(ctx, world, order.era, atlas)
        await ctx.session.delete(order)
    left = (world.climate_epochs_left or 0) - 1
    if left <= 0:
        settings = ctx.rules.climate_effects
        era = pick_next_era(ctx, world, era)
        world.climate_era = era
        world.climate_since_epoch = ctx.epoch
        world.climate_imposed_by_son_id = None
        left = settings.duration + ctx.rng(f"era_length.{world.id}").die(settings.duration_die)
        await announce_era(ctx, world, era, many_worlds)
    world.climate_epochs_left = left
    await apply_climate_effect(ctx, world, era, atlas)


async def climate_transition(ctx: TickContext) -> None:
    worlds = await WorldRepository(ctx.session).reachable_worlds()
    atlas = await RegionAtlas.load(ctx.session)
    for world in worlds:
        await advance_world(ctx, world, atlas, len(worlds) > 1)
    await ctx.session.flush()
    ctx.count("worlds", len(worlds))


async def law_fertility(ctx: TickContext) -> None:
    laws = await ctx.laws()
    if not (laws.anywhere(NaturalLaw.BOUNTY) or laws.anywhere(NaturalLaw.DROUGHT)):
        return
    settings = ctx.rules.climate_effects
    changed = 0
    for land in await canon(ctx.session, LAND_TYPES):
        fertility = stat(land, "fertility")
        bounty = laws.has(NaturalLaw.BOUNTY, land.world_id)
        drought = laws.has(NaturalLaw.DROUGHT, land.world_id)
        if fertility is None or not (bounty or drought):
            continue
        change = (settings.bounty_law_fertility if bounty else 0) - (settings.drought_law_fertility if drought else 0)
        set_stats(land, fertility=clamp_int(fertility + change, 0, PERCENT))
        changed += 1
    ctx.count("lands", changed)


async def climate_of(session: AsyncSession, rules: Rules, world_id: int) -> ClimateState | None:
    world = await session.get(WorldRow, world_id)
    if world is None:
        return None
    source = world
    if world.climate_era is None:
        cosmos = await CosmosRepository(session).get()
        primary = await session.get(WorldRow, cosmos.primary_world_id) if cosmos is not None and cosmos.primary_world_id is not None else None
        if primary is None or primary.climate_era is None:
            return None
        source = primary
    era = source.climate_era
    if era is None:
        return None
    return ClimateState(
        world_id=world.id,
        era=era,
        epochs_left=source.climate_epochs_left or 0,
        since_epoch=source.climate_since_epoch or 0,
        profile=climate_profile(rules, era),
        plague_pct=plague_pct(rules, era),
        population_loss_pct=population_loss_pct(rules, era),
        imposed_by_son_id=source.climate_imposed_by_son_id,
    )


async def impose_climate(ctx: TickContext, world_id: int, era: ClimateEra, epochs: int, son_id: int | None = None) -> ClimateState:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if epochs < 1:
        raise ValidationFailedError("A climate age lasts at least one epoch.")
    world.climate_era = era
    world.climate_epochs_left = epochs
    world.climate_since_epoch = ctx.epoch
    world.climate_imposed_by_son_id = son_id
    order = await ctx.session.get(ClimateOrderRow, world.id)
    if order is None:
        ctx.session.add(ClimateOrderRow(world_id=world.id, era=era, ordered_epoch=max(1, ctx.epoch), son_id=son_id))
    else:
        order.era = era
        order.ordered_epoch = max(1, ctx.epoch)
        order.son_id = son_id
    await ctx.session.flush()
    profile = climate_profile(ctx.rules, era)
    await note(
        ctx,
        f"By divine order the {profile.label.lower()} fell upon {world.name} for {epochs} epochs. {profile.description}",
        key="climate.imposed",
        world_id=world.id,
        son_id=son_id,
        kind=ChronicleKind.CLIMATE,
    )
    state = await climate_of(ctx.session, ctx.rules, world.id)
    if state is None:
        raise NotFoundError("The world has no climate.")
    return state


async def pending_orders(session: AsyncSession) -> list[ClimateOrderRow]:
    return list(await session.scalars(select(ClimateOrderRow).order_by(ClimateOrderRow.world_id)))


PHASES = (
    Phase("law_fertility", law_fertility),
    Phase("climate_transition", climate_transition),
)
