import math
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.kinds.tension import TENSION_PUSH
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.cycles import PolityStressRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.storyteller import StorytellerRow, TensionRecordRow
from aerona.db.write_guard import held
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.storyteller import RecoveryKind, SpontaneousKind, StorytellerProfile, TensionBand
from aerona.engine.context import TickContext
from aerona.engine.dominion.book import DominionBook
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.storyteller.palette import BY_KEY, keep_palette, weight_of
from aerona.engine.storyteller.regions import TENSE_KINDS, deeper_aim, measure_parts
from aerona.rules.registry import Rules

STRUCK_KEYS: dict[SpontaneousKind, tuple[str, ...]] = {kind: BY_KEY[kind.value].struck for kind in SpontaneousKind}


@dataclass
class StorytellerTally:
    worlds: int = 0
    quiet: int = 0
    heated: int = 0
    recoveries: int = 0
    spotlights: int = 0


async def storyteller_of(ctx: TickContext, world_id: int) -> StorytellerRow:
    row = await ctx.session.get(StorytellerRow, world_id)
    if row is None:
        settings = await ctx.session.scalar(select(CosmosRow.genesis_settings).limit(1))
        profile = settings.storyteller if settings is not None else StorytellerProfile.CYCLIC
        row = StorytellerRow(world_id=world_id, profile=profile, updated_epoch=ctx.epoch, recent_kinds={}, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


def aim(rules: Rules, row: StorytellerRow, epoch: int, chaos: int) -> int:
    table = rules.storyteller
    deeper = deeper_aim(rules, row, epoch)
    if deeper is not None:
        return deeper
    if row.profile is StorytellerProfile.STEADY:
        return table.steady_target
    if row.profile is StorytellerProfile.RISING:
        return min(table.rising_cap, table.rising_start + table.rising_step * epoch)
    if row.profile is StorytellerProfile.CHAOTIC:
        return clamp_int(table.chaotic_low + chaos * (table.chaotic_high - table.chaotic_low) / PERCENT, 0, PERCENT)
    wave = math.sin(2 * math.pi * (epoch + row.cycle_offset) / table.cyclic_period)
    return clamp_int(table.cyclic_middle + table.cyclic_amplitude * wave, 0, PERCENT)


def band_of(rules: Rules, tension: int, target: int) -> TensionBand:
    width = rules.storyteller.band
    if tension < target - width:
        return TensionBand.QUIET
    if tension > target + width:
        return TensionBand.HEATED
    return TensionBand.IN_BAND


def boost_of(rules: Rules, tension: int, target: int, band: TensionBand) -> int:
    table = rules.storyteller
    push = TENSION_PUSH[band]
    if not push:
        return 0
    off = abs(tension - target) - table.band
    return push * min(table.boost_max_pct, off * table.boost_per_point_pct)


async def drama(ctx: TickContext, world_id: int) -> int:
    weight = await ctx.session.scalar(
        select(func.coalesce(func.sum(IncidentRow.magnitude), 0))
        .join(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .where(IncidentRow.epoch == ctx.epoch, IncidentRow.world_id == world_id, ChronicleRow.kind.in_(sorted(TENSE_KINDS)))
    )
    return int(weight or 0) + await turmoil(ctx, world_id)


async def turmoil(ctx: TickContext, world_id: int) -> int:
    book = await DominionBook.load(ctx.session)
    steps = sum(max(0, -book.scale_at(ctx.rules, ruler.region_entity_id, DivineScale.ORDER)) for ruler in book.rulers.values() if ruler.world_id == world_id)
    return steps * ctx.rules.dominion.tension_per_step + await stress_tension(ctx, world_id)


async def stress_tension(ctx: TickContext, world_id: int) -> int:
    table = ctx.rules.structural_demography
    stresses = await ctx.session.scalars(
        select(PolityStressRow.psi)
        .join(EntityRow, EntityRow.id == PolityStressRow.polity_entity_id)
        .where(EntityRow.world_id == world_id, PolityStressRow.psi > table.crisis_at)
    )
    return sum(psi - table.crisis_at for psi in stresses) * table.crisis_weight // PERCENT


async def struck_counts(ctx: TickContext, world_id: int) -> Counter[str]:
    counts: Counter[str] = Counter()
    keys = await ctx.session.scalars(select(IncidentRow.kind).where(IncidentRow.epoch == ctx.epoch, IncidentRow.world_id == world_id))
    for key in keys:
        for kind, prefixes in STRUCK_KEYS.items():
            if key.startswith(prefixes):
                counts[kind.value] += 1
    return counts


def remember_kinds(rules: Rules, row: StorytellerRow, struck: Counter[str]) -> dict[str, int]:
    keep = PERCENT - rules.storyteller.variety_decay_pct
    faded = {kind: round_half_up(count * keep / PERCENT) for kind, count in (row.recent_kinds or {}).items()}
    for kind, count in struck.items():
        faded[kind] = faded.get(kind, 0) + count
    return {kind: min(count, rules.storyteller.variety_window) for kind, count in faded.items() if count > 0}


async def spotlight_for(ctx: TickContext, world_id: int) -> int | None:
    table = ctx.rules.storyteller
    since = ctx.epoch - table.variety_window
    mentions = (
        select(ChronicleEntityRow.entity_id, func.count().label("told"))
        .join(ChronicleRow, ChronicleRow.id == ChronicleEntityRow.chronicle_id)
        .where(ChronicleRow.epoch >= since)
        .group_by(ChronicleEntityRow.entity_id)
        .subquery()
    )
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .outerjoin(mentions, mentions.c.entity_id == EntityRow.id)
        .where(
            EntityRow.world_id == world_id,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_([EntityType.MORTAL, EntityType.SETTLEMENT, EntityType.PEOPLE]),
            EntityRow.importance >= table.spotlight_min_importance,
        )
        .order_by(func.coalesce(mentions.c.told, 0), EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def measure(ctx: TickContext, world: WorldRow, tally: StorytellerTally) -> StorytellerRow | None:
    if held(world.id):
        return None
    table = ctx.rules.storyteller
    row = await storyteller_of(ctx, world.id)
    fresh = clamp_int(await drama(ctx, world.id) * PERCENT / table.tension_scale, 0, PERCENT)
    if "tension" not in row.locked:
        row.tension = clamp_int(row.tension * table.tension_carry_pct / PERCENT + fresh, 0, PERCENT)
    chaos = ctx.rng(f"storyteller.chaos.{world.id}.{ctx.epoch}").die(PERCENT)
    row.target = aim(ctx.rules, row, ctx.epoch, chaos)
    felt = await lagged(ctx, BalanceLoop.STORYTELLER_PACING, world.id, row.tension)
    row.band = band_of(ctx.rules, felt, row.target)
    crises = await measure_parts(ctx, world.id)
    if "boost_pct" not in row.locked:
        row.boost_pct = 0 if crises and row.band is TensionBand.QUIET else boost_of(ctx.rules, felt, row.target, row.band)
    row.recent_kinds = remember_kinds(ctx.rules, row, await struck_counts(ctx, world.id))
    await keep_palette(ctx, row)
    if "spotlight_entity_id" not in row.locked:
        row.spotlight_entity_id = await spotlight_for(ctx, world.id)
        tally.spotlights += row.spotlight_entity_id is not None
    row.updated_epoch = ctx.epoch
    ctx.session.add(TensionRecordRow(world_id=world.id, epoch=ctx.epoch, tension=row.tension, target=row.target, boost_pct=row.boost_pct, band=row.band))
    tally.worlds += 1
    tally.quiet += row.band is TensionBand.QUIET
    tally.heated += row.band is TensionBand.HEATED
    return row


async def boosts(ctx: TickContext, world_id: int | None) -> list[StorytellerRow]:
    if world_id is not None:
        row = await ctx.session.get(StorytellerRow, world_id)
        return [row] if row is not None else []
    return list(await ctx.session.scalars(select(StorytellerRow).order_by(StorytellerRow.world_id)))


async def paced(ctx: TickContext, world_id: int | None, kind: SpontaneousKind, pct: float) -> float:
    rows = await boosts(ctx, world_id)
    if not rows:
        return pct
    table = ctx.rules.storyteller
    factor = 0.0
    for row in rows:
        recent = (row.recent_kinds or {}).get(kind.value, 0)
        variety = table.variety_pct * min(1.0, recent / table.variety_window) / PERCENT
        factor += (1 + row.boost_pct / PERCENT) * (1 - variety) * weight_of(row, kind.value)
    return pct * factor / len(rows)


async def paced_key(ctx: TickContext, world_id: int | None, key: str, pct: float) -> float:
    rows = await boosts(ctx, world_id)
    if not rows:
        return pct
    return pct * sum((1 + row.boost_pct / PERCENT) * weight_of(row, key) for row in rows) / len(rows)


async def recovered(ctx: TickContext, world_id: int | None, kind: RecoveryKind, value: float) -> float:
    rows = await boosts(ctx, world_id)
    if not rows:
        return value
    lift = sum(max(0, -row.boost_pct) for row in rows) / len(rows)
    return value * (1 + lift / PERCENT) * sum(weight_of(row, kind.value) for row in rows) / len(rows)


async def quiet_world(ctx: TickContext, world_id: int) -> bool:
    if not ctx.rules.storyteller.revival_band:
        return True
    row = await ctx.session.get(StorytellerRow, world_id)
    return row is None or row.band is TensionBand.QUIET
