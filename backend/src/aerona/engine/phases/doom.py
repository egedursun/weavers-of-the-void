from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow, DimensionalEventRow, DimensionRow, GalacticEventRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import (
    OPEN_RIFT_STATES,
    ApocalypseVariant,
    BeingAgenda,
    BeingPhase,
    DimensionalEventKind,
    GalacticEventKind,
    PhenomenonKind,
)
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.kinds import BEING_MECHANICS
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.eras.progress import era_doom
from aerona.engine.gods.worship import cult_effect
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.research import mean_spread
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import apply_disaster, record_disaster_event
from aerona.engine.phases.horror import summon_outer_being
from aerona.engine.phases.world_age import WorldAge, age_of, read_world_age, world_age
from aerona.engine.primitives.doom import doom_threshold, step_doom
from aerona.engine.primitives.faith import son_faith
from aerona.engine.primitives.ledger import DoomItem, LedgerKey, read, record, record_doom
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity, living_sons
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import ongoing_war_count
from aerona.engine.storyteller.ages import turn_age
from aerona.engine.transition import cosmos_of, doom_calling, leakiest_world
from aerona.rules.registry import Rules

DOOM_FORECAST_ACTION = "doom.forecast"
APOCALYPSE_DISASTERS = (Disaster.EARTHQUAKE, Disaster.FLOOD, Disaster.DROUGHT, Disaster.STORM)
FIRST_OMEN = "Doom reached its first omen: the end of the world draws near."
FINAL_OMEN = "Doom reached its final omen: if the gods do nothing, the world will end."


@dataclass(frozen=True)
class DoomReading:
    items: dict[DoomItem, int]
    clock: int
    threshold: int


async def count_flagged(ctx: TickContext, flag: EntityFlag) -> int:
    flagged = await flags_by_entity(ctx.session, flag)
    if not flagged:
        return 0
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.id.in_(flagged), EntityRow.status == EntityStatus.CANON)
    return int(await ctx.session.scalar(statement) or 0)


async def count_structures(ctx: TickContext, kind: EngineKind, flag: EntityFlag | None = None) -> int:
    structures = await canon(ctx.session, [EntityType.STRUCTURE])
    flagged = await flags_by_entity(ctx.session, flag) if flag is not None else set()
    return sum(1 for structure in structures if structure.engine_kind is kind or structure.id in flagged)


async def doom_items(ctx: TickContext, age: WorldAge) -> dict[DoomItem, float]:
    rules = ctx.rules
    doom = rules.apocalypse
    godless = await count_flagged(ctx, EntityFlag.GODLESS)
    cursed = await count_flagged(ctx, EntityFlag.CURSED)
    restless = sum(1 for spirit in await canon(ctx.session, [EntityType.SPIRIT]) if (stat(spirit, "unrest") or 0) >= doom.restless_threshold)
    wars = await ongoing_war_count(ctx.session)
    rebels = int(await ctx.session.scalar(select(func.count()).select_from(SonRow).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD)) or 0)
    miracles = int(
        await ctx.session.scalar(
            select(func.count()).select_from(ChronicleRow).where(ChronicleRow.epoch == ctx.epoch, ChronicleRow.kind == ChronicleKind.MIRACLE)
        )
        or 0
    )
    wonders = await count_structures(ctx, EngineKind.WONDER, EntityFlag.WONDER)
    temples = await count_structures(ctx, EngineKind.TEMPLE)
    cult = await cult_effect(ctx.session, rules)
    faith = read(ctx, LedgerKey.TOTAL_FAITH)
    return {
        DoomItem.GODLESS: godless * doom.godless,
        DoomItem.CURSED: cursed * doom.cursed,
        DoomItem.RESTLESS_SPIRITS: restless * doom.restless_spirit,
        DoomItem.WARS: wars / doom.hostility_divisor,
        DoomItem.REBEL_SONS: rebels * doom.rebel_son,
        DoomItem.MIRACLES: -miracles * doom.miracle,
        DoomItem.FAITH: -min(doom.faith_cap, faith // doom.faith_divisor),
        DoomItem.PEACE: -doom.peace if wars == 0 else 0,
        DoomItem.WONDERS: -min(doom.wonder_cap, wonders),
        DoomItem.TEMPLES: -min(doom.temple_cap, temples // rules.world_epoch_transition.temples_per_apocalypse_push),
        DoomItem.GOLDEN_AGE: -doom.golden_age * age.golden_worlds,
        DoomItem.WORLD_AGE: -age.relief,
        DoomItem.CREATOR_CULT: -cult.doom_pushback,
        DoomItem.ENLIGHTENMENT: -min(rules.research.enlightenment_cap, await mean_spread(ctx.session) * rules.research.enlightenment_relief_pct / PERCENT),
        DoomItem.DANGEROUS_TECH: await era_doom(ctx),
        **await cosmic_items(ctx),
    }


VARIANT_ITEMS: dict[ApocalypseVariant, frozenset[DoomItem]] = {
    ApocalypseVariant.WORLD_WAR: frozenset({DoomItem.WARS, DoomItem.DANGEROUS_TECH}),
    ApocalypseVariant.END_OF_THE_GODS: frozenset({DoomItem.GODLESS, DoomItem.REBEL_SONS}),
    ApocalypseVariant.OUTER_DESCENT: frozenset({DoomItem.CURSED, DoomItem.RESTLESS_SPIRITS, DoomItem.LEAK_WOUNDS, DoomItem.HOT_REGIONS}),
    ApocalypseVariant.DIMENSIONAL_COLLAPSE: frozenset({DoomItem.OPEN_RIFTS, DoomItem.INCURSIONS, DoomItem.CONVERGENCES, DoomItem.UNMAKERS}),
    ApocalypseVariant.GALACTIC_DEATH: frozenset({DoomItem.GAMMA_BURSTS, DoomItem.COLLAPSED_LIFE}),
}


async def cosmic_items(ctx: TickContext) -> dict[DoomItem, float]:
    doom = ctx.rules.apocalypse
    rifts = int(await ctx.session.scalar(select(func.count()).select_from(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES)))) or 0)
    incursions = int(
        await ctx.session.scalar(
            select(func.count())
            .select_from(DimensionalEventRow)
            .where(DimensionalEventRow.kind == DimensionalEventKind.INCURSION, DimensionalEventRow.epoch == ctx.epoch)
        )
        or 0
    )
    converging = int(
        await ctx.session.scalar(
            select(func.count())
            .select_from(DimensionalEventRow)
            .where(
                DimensionalEventRow.kind == DimensionalEventKind.CONVERGENCE,
                (DimensionalEventRow.until_epoch.is_(None)) | (DimensionalEventRow.until_epoch >= ctx.epoch),
            )
        )
        or 0
    )
    bursts = int(
        await ctx.session.scalar(
            select(func.count())
            .select_from(GalacticEventRow)
            .where(GalacticEventRow.kind == GalacticEventKind.GAMMA_RAY_BURST, GalacticEventRow.epoch == ctx.epoch)
        )
        or 0
    )
    wounds = sum(1 for profile in await ctx.session.scalars(select(PhenomenonProfileRow).where(PhenomenonProfileRow.kind == PhenomenonKind.OUTSIDE_OPENING)))
    hot = int(
        await ctx.session.scalar(select(func.count()).select_from(RegionEnvironmentRow).where(RegionEnvironmentRow.leak >= ctx.rules.world_life.leak_hot)) or 0
    )
    collapsed = int(
        await ctx.session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.biosphere_health < ctx.rules.world_life.biosphere_collapse)) or 0
    )
    unmaking = 0
    statement = select(CosmicBeingProfileRow).where(CosmicBeingProfileRow.phase.in_([BeingPhase.MANIFEST, BeingPhase.INCURSION]))
    for being in await ctx.session.scalars(statement):
        unmaking += BEING_MECHANICS[being.being_kind].doom(ctx.rules)
        unmaking += ctx.rules.cosmic_beings.unmake_doom if being.agenda is BeingAgenda.UNMAKE else 0
    return {
        DoomItem.UNMAKERS: unmaking,
        DoomItem.OPEN_RIFTS: rifts * doom.open_rift,
        DoomItem.INCURSIONS: incursions * doom.incursion,
        DoomItem.CONVERGENCES: converging * doom.convergence,
        DoomItem.GAMMA_BURSTS: bursts * doom.gamma_burst,
        DoomItem.LEAK_WOUNDS: wounds * doom.leak_wound,
        DoomItem.HOT_REGIONS: hot * ctx.rules.world_life.hot_doom,
        DoomItem.COLLAPSED_LIFE: collapsed * ctx.rules.world_life.collapse_doom,
    }


def dominant_variant(rules: Rules, items: dict[DoomItem, float]) -> ApocalypseVariant:
    total = sum(value for value in items.values() if value > 0)
    if total <= 0:
        return ApocalypseVariant.RUIN
    shares = {variant: sum(max(0.0, items.get(item, 0.0)) for item in members) / total for variant, members in VARIANT_ITEMS.items()}
    variant, share = max(shares.items(), key=lambda pair: (pair[1], pair[0].value))
    return variant if share * PERCENT >= rules.apocalypse.variant_share_pct else ApocalypseVariant.RUIN


async def end_by(ctx: TickContext, variant: ApocalypseVariant) -> None:
    doom = ctx.rules.apocalypse
    if variant is ApocalypseVariant.END_OF_THE_GODS:
        for son in await living_sons(ctx.session):
            if not held(son.id):
                son.existence = son.existence // doom.twilight_fade_mult
        await note(ctx, "The twilight of the gods came: every son faded.", key="doom.twilight", kind=ChronicleKind.APOCALYPSE)
    elif variant is ApocalypseVariant.OUTER_DESCENT:
        target = await leakiest_world(ctx.session)
        if target is not None and not held(target.id):
            for _ in range(doom.descent_beings):
                await summon_outer_being(ctx, target)
            await note(ctx, f"Outer beings descended on {target.name}.", key="doom.outer_descent", kind=ChronicleKind.APOCALYPSE, world_id=target.id)
    elif variant is ApocalypseVariant.DIMENSIONAL_COLLAPSE:
        for dimension in await ctx.session.scalars(select(DimensionRow).order_by(DimensionRow.id)):
            if not held(dimension.id) and "veil" not in dimension.locked:
                dimension.veil = max(0, dimension.veil - doom.collapse_veil)
        await note(ctx, "The veils between the dimensions gave way.", key="doom.dimensional_collapse", kind=ChronicleKind.APOCALYPSE)
    elif variant is ApocalypseVariant.GALACTIC_DEATH:
        await galactic_death(ctx)
    await destroy_leakiest_world(ctx)


async def galactic_death(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    galaxies = [galaxy for galaxy in cosmography.galaxies.values() if cosmography.stars_in_galaxy(galaxy.id) and not held(galaxy.id)]
    if not galaxies:
        return
    dimmest = min(
        galaxies,
        key=lambda galaxy: (sum(star.brightness for star in cosmography.stars_in_galaxy(galaxy.id)) / len(cosmography.stars_in_galaxy(galaxy.id)), galaxy.id),
    )
    for star in cosmography.stars_in_galaxy(dimmest.id):
        if not held(star.id) and "brightness" not in star.locked:
            star.brightness = max(0, star.brightness - ctx.rules.apocalypse.galactic_death_dimming)
    await note(ctx, f"The stars of {dimmest.name} went dark.", key="doom.galactic_death", kind=ChronicleKind.APOCALYPSE)


def threshold_of(ctx: TickContext) -> int:
    return doom_threshold(ctx.rules)


async def destroy_leakiest_world(ctx: TickContext) -> None:
    transition = ctx.rules.world_epoch_transition
    rng = ctx.rng("apocalypse")
    target = await leakiest_world(ctx.session)
    if target is None:
        return
    regions = await canon(ctx.session, [EntityType.REGION], target.id)
    for region in regions:
        await apply_disaster(ctx, region, rng.pick(APOCALYPSE_DISASTERS), transition.apocalypse_disaster_severity / PERCENT)
    if regions:
        await record_disaster_event(ctx, regions[0], Disaster.EARTHQUAKE, transition.apocalypse_event_severity)
    await note(
        ctx,
        f"APOCALYPSE: {target.name} was shaken. All its regions were destroyed by disasters; the survivors awoke to a new age.",
        key="doom.apocalypse",
        ids=[region.id for region in regions[: transition.apocalypse_chronicle_regions]],
        kind=ChronicleKind.APOCALYPSE,
        world_id=target.id,
    )


@reads(
    "knowledge.spread",
    "people.martiality",
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "spirit.unrest",
    "table.bonds",
    "table.chronicle",
    "table.community_societies",
    "table.cosmic_being_profiles",
    "table.cosmos",
    "table.dimensional_events",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.galactic_events",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.modifiers",
    "table.nodes",
    "table.phenomenon_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.region_environment",
    "table.rifts",
    "table.sons",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes(
    "people.martiality",
    "people.prosperity",
    "settlement.defense",
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.cosmos",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def doom_clock(ctx: TickContext) -> None:
    rules = ctx.rules
    doom = rules.apocalypse
    cosmos = await cosmos_of(ctx.session)
    items = await doom_items(ctx, await world_age(ctx, ctx.epoch + 1))
    for item, amount in items.items():
        record_doom(ctx, item, round_half_up(amount))
    threshold = threshold_of(ctx)
    raw = sum(items.values())
    step = step_doom(rules, cosmos, raw)
    record_doom(ctx, DoomItem.SPEED, round_half_up(step.scaled - raw))
    before = step.before
    clock = step.after
    for warning, text in ((doom.warning_1_pct, FIRST_OMEN), (doom.warning_2_pct, FINAL_OMEN)):
        point = threshold * warning / PERCENT
        if before < point <= clock:
            await note(ctx, text, key=f"doom.omen_{warning}", kind=ChronicleKind.APOCALYPSE)
    if clock >= threshold:
        variant = cosmos.apocalypse_variant or dominant_variant(rules, items)
        if variant is ApocalypseVariant.WORLD_WAR and await doom_calling(ctx):
            reset = round_half_up(threshold * doom.after_calling_pct / PERCENT)
        else:
            await end_by(ctx, variant)
            if cosmos.age_cycle is AgeCycle.CYCLIC:
                await turn_age(ctx, variant)
            reset = round_half_up(threshold * doom.after_ruin_pct / PERCENT)
        record_doom(ctx, DoomItem.RESET, reset - clock)
        clock = reset
        cosmos.doom_fraction = 0.0
    cosmos.doom_clock = clock
    record(ctx, LedgerKey.DOOM_CLOCK, clock)


async def trigger_apocalypse(ctx: TickContext, calling: bool = False) -> int:
    cosmos = await cosmos_of(ctx.session)
    threshold = threshold_of(ctx)
    doom = ctx.rules.apocalypse
    if calling:
        if not await doom_calling(ctx):
            raise ValidationFailedError("The worlds do not leak enough for the apocalypse to become a calling.")
        cosmos.doom_clock = round_half_up(threshold * doom.after_calling_pct / PERCENT)
    else:
        if await leakiest_world(ctx.session) is None:
            raise NotFoundError("No world remains to be shaken.")
        await destroy_leakiest_world(ctx)
        cosmos.doom_clock = round_half_up(threshold * doom.after_ruin_pct / PERCENT)
    return cosmos.doom_clock


async def set_doom_clock(ctx: TickContext, value: int) -> int:
    threshold = threshold_of(ctx)
    if not 0 <= value <= threshold:
        raise ValidationFailedError(f"The doom clock runs from 0 to {threshold}.")
    cosmos = await cosmos_of(ctx.session)
    cosmos.doom_clock = value
    return value


PHASES = (Phase("doom_clock", doom_clock),)


@dataclass(frozen=True)
class DoomForecast:
    clock: int
    threshold: int
    speed_pct: int
    raw: float
    step: float
    items: list[tuple[DoomItem, float]]


async def doom_forecast(session: AsyncSession, rules: Rules) -> DoomForecast:
    ctx = await manual_context(session, DOOM_FORECAST_ACTION, rules)
    total = 0
    for son in await living_sons(session):
        total += await son_faith(session, rules, son)
    record(ctx, LedgerKey.TOTAL_FAITH, total)
    items = await doom_items(ctx, age_of(await read_world_age(ctx, ctx.epoch + 1)))
    cosmos = await cosmos_of(session)
    raw = sum(items.values())
    return DoomForecast(
        clock=cosmos.doom_clock,
        threshold=threshold_of(ctx),
        speed_pct=rules.balance.apocalypse_speed,
        raw=raw,
        step=raw * rules.balance.apocalypse_speed / PERCENT,
        items=list(items.items()),
    )
