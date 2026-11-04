from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.gods.worship import cult_effect
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import apply_disaster, record_disaster_event
from aerona.engine.phases.world_age import world_age
from aerona.engine.primitives.doom import doom_threshold, step_doom
from aerona.engine.primitives.faith import son_faith
from aerona.engine.primitives.ledger import DoomItem, LedgerKey, read, record, record_doom
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity, living_sons
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import ongoing_war_count
from aerona.engine.transition import cosmos_of, doom_calling, leakiest_world
from aerona.rules.registry import Rules

DOOM_FORECAST_ACTION = "doom.forecast"
APOCALYPSE_DISASTERS = (Disaster.EARTHQUAKE, Disaster.FLOOD, Disaster.DROUGHT, Disaster.STORM)
FIRST_OMEN = "Omens fell from the sky: wells turned red, birds flew backwards. Seers whisper that the end of the world is near."
FINAL_OMEN = "The apocalypse is very near: the stars shifted from their places, the dead spoke in their sleep. If the gods do nothing the world will shatter."


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


async def doom_items(ctx: TickContext, new_epoch: int) -> dict[DoomItem, float]:
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
    age = await world_age(ctx, new_epoch)
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
    }


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
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "spirit.unrest",
    "table.bonds",
    "table.chronicle",
    "table.community_societies",
    "table.cosmos",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
    "table.war_sides",
    "table.wars",
)
@writes(
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
    items = await doom_items(ctx, ctx.epoch + 1)
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
        if await doom_calling(ctx):
            reset = round_half_up(threshold * doom.after_calling_pct / PERCENT)
        else:
            await destroy_leakiest_world(ctx)
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
    items = await doom_items(ctx, ctx.epoch + 1)
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
