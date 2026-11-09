from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.climate import ClimateProfile, climate_profile, climate_weights
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.climate import ClimateOrderRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import ClimateEra
from aerona.engine.context import TickContext
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_economy import population_bounds
from aerona.engine.primitives.derivation import Origin, replace_derived, shaped_draft
from aerona.engine.primitives.modifiers import ModifierDraft
from aerona.engine.primitives.numbers import clamp_int, fraction
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

LAND_TYPES = (EntityType.REGION, EntityType.PLACE)


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


async def apply_climate_effect(ctx: TickContext, world: WorldRow, era: ClimateEra) -> int:
    loss = population_loss_pct(ctx.rules, era)
    changed = 0
    if loss:
        for community in await canon(ctx.session, SOCIETY_TYPES, world.id):
            population = stat(community, "population")
            if population is not None:
                floor, ceiling = population_bounds(ctx.rules, community)
                set_stats(community, population=clamp_int(population * (1 - fraction(loss)), floor, ceiling))
                changed += 1
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


async def star_instability(ctx: TickContext, world: WorldRow) -> int:
    star = await ctx.session.get(StarRow, world.star_id) if world.star_id is not None else None
    return star_mechanics(star.star_type).instability(ctx.rules) if star is not None else 0


async def advance_world(ctx: TickContext, world: WorldRow, many_worlds: bool) -> None:
    era = ensure_climate(ctx, world)
    order = await ctx.session.get(ClimateOrderRow, world.id)
    if order is not None:
        await apply_climate_effect(ctx, world, order.era)
        await ctx.session.delete(order)
    left = (world.climate_epochs_left or 0) - 1
    if left <= 0:
        settings = ctx.rules.climate_effects
        era = pick_next_era(ctx, world, era)
        world.climate_era = era
        world.climate_since_epoch = ctx.epoch
        world.climate_imposed_by_son_id = None
        left = settings.duration + ctx.rng(f"era_length.{world.id}").die(settings.duration_die)
        left = max(1, left - await star_instability(ctx, world))
        await announce_era(ctx, world, era, many_worlds)
    world.climate_epochs_left = left
    await apply_climate_effect(ctx, world, era)


@reads("table.climate_orders", "table.epoch_year_cursors")
@writes("table.chronicle", "table.epoch_year_cursors", "table.incidents", "table.worlds")
async def climate_transition(ctx: TickContext) -> None:
    worlds = await WorldRepository(ctx.session).reachable_worlds()
    for world in worlds:
        await advance_world(ctx, world, len(worlds) > 1)
    await ctx.session.flush()
    ctx.count("worlds", len(worlds))


@reads("place.fertility", "region.fertility", "table.modifiers", "table.natural_law_profiles")
@writes("table.modifiers")
async def law_fertility(ctx: TickContext) -> None:
    laws = await ctx.laws()
    settings = ctx.rules.climate_effects
    drafts: list[ModifierDraft] = []
    for land in await canon(ctx.session, LAND_TYPES):
        bounty = laws.has(NaturalLaw.BOUNTY, land.world_id)
        drought = laws.has(NaturalLaw.DROUGHT, land.world_id)
        if stat(land, "fertility") is None or not (bounty or drought):
            continue
        factor = (1 + settings.bounty_law_fertility / PERCENT if bounty else 1.0) * (1 - settings.drought_law_fertility / PERCENT if drought else 1.0)
        reason = (
            "modifier.natural_law.bounty"
            if bounty and not drought
            else "modifier.natural_law.drought"
            if drought and not bounty
            else "modifier.natural_law.bounty_and_drought"
        )
        draft = shaped_draft(land, "fertility", ModifierOp.MULTIPLY, factor, Origin(ModifierSource.NATURAL_LAW, reason, ctx.epoch, group="natural_law"))
        if draft is not None:
            drafts.append(draft)
    ctx.count("lands", await replace_derived(ctx.session, {ModifierSource.NATURAL_LAW}, drafts))


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


PHASES = (
    Phase("law_fertility", law_fertility),
    Phase("climate_transition", climate_transition),
)
