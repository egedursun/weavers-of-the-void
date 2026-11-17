from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.catalog.art_modes import HEARD_MODES
from aerona.catalog.preferences import FOODS
from aerona.catalog.thoughts import EMOTIONS, MEMORY_THOUGHTS, NEEDS, THOUGHTS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow, ItemProfileRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mind import MemoryRow, ThoughtRow
from aerona.db.tables.mortal import MarriageRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind, Emotion, MemoryKind, PreferenceKind, ThoughtKind, ValueHolder
from aerona.domain.models.entity_stats import ArtworkStats
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holding
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.gods.queries import community_of
from aerona.engine.mind.book import needs_of, stored_values
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.preferences import fit, home_region, home_terrain, prefs_of
from aerona.engine.mind.split import facets_of
from aerona.engine.mind.thoughts import need_importance, think
from aerona.engine.mortal.kin import close_kin_of, spouses_of
from aerona.engine.primitives.naming import seed_of

FEASTS = frozenset({TraditionFunction.FESTIVAL, TraditionFunction.ANCESTRAL_RITE, TraditionFunction.SEASONAL_RITE})
MUSIC = HEARD_MODES


@dataclass
class FeelingTally:
    thoughts: int = 0
    relived: int = 0


async def memory_thoughts(ctx: TickContext, mortal: EntityRow) -> int:
    rows = await ctx.session.scalars(
        select(MemoryRow).where(
            MemoryRow.holder_node_id == mortal.id,
            MemoryRow.epoch >= ctx.epoch - 1,
            MemoryRow.kind.in_(list(MEMORY_THOUGHTS)),
            MemoryRow.inherited_from_node_id.is_(None),
        )
    )
    made = 0
    for row in list(rows):
        kind = MEMORY_THOUGHTS[row.kind]
        size = (THOUGHTS[kind].intensity + abs(row.magnitude)) / 2
        made += 1 if await think(ctx.session, ctx.rules, mortal.id, kind, row.epoch, subject_id=row.subject_node_id, intensity=size) else 0
    return made


async def life_events(ctx: TickContext, mortal: EntityRow) -> int:
    made = 0
    weddings = await ctx.session.scalars(
        select(MarriageRow).where(or_(MarriageRow.first_id == mortal.id, MarriageRow.second_id == mortal.id), MarriageRow.start_epoch >= ctx.epoch - 1)
    )
    for wedding in list(weddings):
        other = wedding.second_id if wedding.first_id == mortal.id else wedding.first_id
        if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.MARRIED, wedding.start_epoch, subject_id=other) is None:
            continue
        made += 1
        if wedding.first_id == mortal.id and other in await close_kin_of(ctx.session, mortal.id):
            await judged(ctx, mortal.id, other, ActKind.INCEST)
        if wedding.first_id == mortal.id and len(await spouses_of(ctx.session, mortal.id)) > 1:
            await judged(ctx, mortal.id, other, ActKind.POLYGAMY)
    births = await ctx.session.scalars(
        select(BondRow).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.PARENT_OF, BondRow.epoch >= ctx.epoch - 1)
    )
    for bond in list(births):
        made += 1 if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.CHILD_BORN, bond.epoch, subject_id=bond.target_node_id) else 0
    return made


async def need_thoughts(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.thoughts
    facets = await facets_of(ctx.session, mortal.id)
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    made = 0
    for need, value in (await needs_of(ctx.session, mortal.id)).items():
        weight = need_importance(ctx.rules, need, facets, values)
        if weight < table.need_felt_above_pct:
            continue
        spec = NEEDS[need]
        if value >= table.need_met_above:
            size = THOUGHTS[spec.met].intensity * weight / PERCENT
            made += 1 if await think(ctx.session, ctx.rules, mortal.id, spec.met, ctx.epoch, intensity=size) else 0
        elif value < table.need_unmet_below:
            depth = (table.need_unmet_below - value) / max(1, table.need_unmet_below)
            size = THOUGHTS[spec.unmet].intensity * weight / PERCENT * (1 + depth)
            made += 1 if await think(ctx.session, ctx.rules, mortal.id, spec.unmet, ctx.epoch, intensity=size) else 0
    return made


async def ambient(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.thoughts
    community = await community_of(ctx.session, mortal)
    if community is None:
        return 0
    made = 0
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == community.id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    feast = await ctx.session.scalar(
        select(TraditionProfileRow).where(TraditionProfileRow.tradition_entity_id.in_(kept), TraditionProfileRow.kind.in_(FEASTS)).limit(1)
    )
    if feast is not None and ctx.rng(seed_of("feast", mortal.id, ctx.epoch)).chance(table.feast_pct):
        season = fit(await prefs_of(ctx.session, mortal.id), PreferenceKind.SEASON, feast.calendar_slot.value if feast.calendar_slot is not None else None)
        size = THOUGHTS[ThoughtKind.ATTENDED_FEAST].intensity * (1 + season / PERCENT)
        made += (
            1
            if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.ATTENDED_FEAST, ctx.epoch, subject_id=feast.tradition_entity_id, intensity=size)
            else 0
        )
    home = [community.id, *([community.location_id] if community.location_id is not None else [])]
    works = list(
        await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.location_id.in_(home), EntityRow.entity_type.in_((EntityType.ARTWORK, EntityType.ITEM)), EntityRow.status == EntityStatus.CANON
            )
        )
    )
    renowned: list[int] = []
    songs: list[int] = []
    for work in works:
        if work.entity_type is EntityType.ARTWORK:
            profile = await ctx.session.get(ArtworkProfileRow, work.id)
            fame = work.stats.renown if isinstance(work.stats, ArtworkStats) else None
            if profile is not None and profile.medium in MUSIC:
                songs.append(work.id)
            if (fame or 0) >= table.great_work_renown or (profile is not None and profile.quality >= table.great_work_renown * 2):
                renowned.append(work.id)
        else:
            item = await ctx.session.get(ItemProfileRow, work.id)
            if item is not None and item.renown >= table.great_work_renown:
                renowned.append(work.id)
    rng = ctx.rng(seed_of("ambient", mortal.id, ctx.epoch))
    if renowned and rng.chance(table.great_work_pct):
        made += 1 if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.ADMIRED_GREAT_WORK, ctx.epoch, subject_id=rng.pick(renowned)) else 0
    if songs and rng.chance(table.music_pct):
        made += 1 if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.HEARD_GREAT_MUSIC, ctx.epoch, subject_id=rng.pick(songs)) else 0
    return made


async def surroundings(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.preferences
    rng = ctx.rng(seed_of("surroundings", mortal.id, ctx.epoch))
    if not rng.chance(table.surroundings_pct):
        return 0
    prefs = await prefs_of(ctx.session, mortal.id)
    if not prefs:
        return 0
    seen: list[tuple[PreferenceKind, str]] = []
    terrain = await home_terrain(ctx.session, mortal)
    if terrain is not None:
        seen.append((PreferenceKind.TERRAIN, terrain))
    region = await home_region(ctx.session, mortal)
    if region is not None:
        book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
        weather = book.weather(ctx.environment.world_seed, ctx.epoch, region, book.growing_season(region.world_id), f"mood.{mortal.id}")
        seen.append((PreferenceKind.WEATHER, weather.kind.value))
    community = await community_of(ctx.session, mortal)
    if community is not None:
        for good in FOODS:
            if await holding(ctx.session, community.id, good) > 0:
                seen.append((PreferenceKind.FOOD, good.value))
    made = 0
    for kind, target in seen:
        value = fit(prefs, kind, target)
        if abs(value) < table.noted_above:
            continue
        food = kind is PreferenceKind.FOOD
        thought = (
            (ThoughtKind.ENJOYED_FAVOURITE if food else ThoughtKind.LIKED_SURROUNDINGS)
            if value > 0
            else (ThoughtKind.ENDURED_A_DISLIKE if food else ThoughtKind.DISLIKED_SURROUNDINGS)
        )
        made += 1 if await think(ctx.session, ctx.rules, mortal.id, thought, ctx.epoch, intensity=THOUGHTS[thought].intensity * abs(value) / PERCENT * 2) else 0
    return made


async def prayers(ctx: TickContext, mortal: EntityRow) -> int:
    wait = ctx.rules.thoughts.prayer_wait_epochs
    rows = await ctx.session.scalars(
        select(MessageRow).where(MessageRow.sender_node_id == mortal.id, MessageRow.intent == MessageIntent.PRAYER, MessageRow.epoch >= ctx.epoch - wait - 1)
    )
    made = 0
    for row in list(rows):
        if row.answered and row.answered_epoch is not None and row.answered_epoch >= ctx.epoch - 1:
            found = await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.PRAYED_ANSWERED, row.answered_epoch, subject_id=row.recipient_node_id)
            made += 1 if found else 0
        elif not row.answered and row.epoch == ctx.epoch - wait:
            made += 1 if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.PRAYER_IGNORED, ctx.epoch, subject_id=row.recipient_node_id) else 0
    return made


async def relive(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.thoughts
    rows = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind == MemoryKind.FORMATIVE))
    made = 0
    for memory in list(rows):
        age = ctx.epoch - memory.epoch
        if age <= 0:
            continue
        subject = await ctx.session.get(EntityRow, memory.subject_node_id)
        near = subject is not None and subject.status is EntityStatus.CANON and subject.location_id == mortal.location_id and subject.id != mortal.location_id
        if not (age % table.anniversary_epochs == 0 or near):
            continue
        if not ctx.rng(seed_of("relive", mortal.id, memory.id, ctx.epoch)).chance(table.relive_pct):
            continue
        source = await ctx.session.scalar(select(ThoughtRow.emotion).where(ThoughtRow.memory_id == memory.id).limit(1))
        feeling = source or (Emotion.JOY if memory.magnitude > 0 else Emotion.SADNESS)
        size = abs(memory.magnitude) * table.relive_pct_of_original / PERCENT
        if EMOTIONS[feeling].valence * memory.magnitude < 0:
            feeling = Emotion.JOY if memory.magnitude > 0 else Emotion.SADNESS
        found = await think(
            ctx.session, ctx.rules, mortal.id, ThoughtKind.RELIVED_MEMORY, ctx.epoch, subject_id=memory.subject_node_id, intensity=size, emotion=feeling
        )
        made += 1 if found else 0
    return made


async def feel(ctx: TickContext, mortal: EntityRow) -> FeelingTally:
    tally = FeelingTally()
    tally.thoughts += await memory_thoughts(ctx, mortal)
    tally.thoughts += await life_events(ctx, mortal)
    tally.thoughts += await need_thoughts(ctx, mortal)
    tally.thoughts += await ambient(ctx, mortal)
    tally.thoughts += await prayers(ctx, mortal)
    tally.thoughts += await surroundings(ctx, mortal)
    tally.relived += await relive(ctx, mortal)
    return tally
