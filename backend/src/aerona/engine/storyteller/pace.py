import math
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.storyteller import StorytellerRow, TensionRecordRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.storyteller import RecoveryKind, SpontaneousKind, StorytellerProfile, TensionBand
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

STRUCK_KEYS: dict[SpontaneousKind, tuple[str, ...]] = {
    SpontaneousKind.BEAST_AWAKENING: ("monsters.emerged", "monsters.void_roamed", "pantheon.sleeper_woke"),
    SpontaneousKind.RAID: ("vendetta.raid", "faction.raid", "monsters.raid"),
    SpontaneousKind.COMET: ("sky.", "feature.comet_returned"),
    SpontaneousKind.PLAGUE: ("disasters.plague", "disasters.city_plague", "disasters.plague_spread"),
    SpontaneousKind.CLAIMANT: ("polity.usurper_accepted", "titles.usurped", "polity.coup"),
}


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
    if band is TensionBand.IN_BAND:
        return 0
    off = abs(tension - target) - table.band
    size = min(table.boost_max_pct, off * table.boost_per_point_pct)
    return size if band is TensionBand.QUIET else -size


async def drama(ctx: TickContext, world_id: int) -> int:
    weight = await ctx.session.scalar(
        select(func.coalesce(func.sum(IncidentRow.magnitude), 0)).where(IncidentRow.epoch == ctx.epoch, IncidentRow.world_id == world_id)
    )
    return int(weight or 0)


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
    row.band = band_of(ctx.rules, row.tension, row.target)
    if "boost_pct" not in row.locked:
        row.boost_pct = boost_of(ctx.rules, row.tension, row.target, row.band)
    row.recent_kinds = remember_kinds(ctx.rules, row, await struck_counts(ctx, world.id))
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
        factor += (1 + row.boost_pct / PERCENT) * (1 - variety)
    return pct * factor / len(rows)


async def recovered(ctx: TickContext, world_id: int | None, kind: RecoveryKind, value: float) -> float:
    rows = await boosts(ctx, world_id)
    if not rows:
        return value
    lift = sum(max(0, -row.boost_pct) for row in rows) / len(rows)
    return value * (1 + lift / PERCENT)


async def quiet_world(ctx: TickContext, world_id: int) -> bool:
    if not ctx.rules.storyteller.revival_band:
        return True
    row = await ctx.session.get(StorytellerRow, world_id)
    return row is None or row.band is TensionBand.QUIET
