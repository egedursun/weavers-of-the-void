from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.dominion import ALIGNMENT_LOOKS, BARGAINING_MODES, PRAYER_TONES
from aerona.catalog.peoples import STYLE_AXES, Style
from aerona.constants.units import PERCENT
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.dominion import PerceivedAlignment, PrayerTone, WorshipMode
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import god_of
from aerona.engine.lore.style import axis_of
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import has_stat, shift_stat, stat_or
from aerona.engine.structures.profiles import style_column
from aerona.rules.registry import Rules

OFFERING_DIVISOR = 10


@dataclass
class WorshipTally:
    views: int = 0
    devoted: int = 0
    appeasing: int = 0
    temples: int = 0
    offerings: int = 0
    bargaining: int = 0
    essence: int = 0


def lean_style(profile: StructureProfileRow, look: Style, pull: int) -> None:
    for axis in STYLE_AXES:
        column = style_column(axis)
        if column in profile.locked:
            continue
        current = getattr(profile, column)
        target = axis_of(look, axis)
        setattr(profile, column, target if current is None else current + round_half_up((target - current) * pull / PERCENT))


def perceived_of(rules: Rules, love: int, fear: int) -> PerceivedAlignment:
    table = rules.worship_views
    if love - fear >= table.benevolent_margin:
        return PerceivedAlignment.BENEVOLENT
    if fear - love >= table.malevolent_margin:
        return PerceivedAlignment.MALEVOLENT
    return PerceivedAlignment.AMBIVALENT


def mode_of(rules: Rules, love: int, fear: int, trading: int = 0) -> WorshipMode:
    table = rules.worship_views
    if fear >= table.appease_fear and fear > love:
        return WorshipMode.APPEASEMENT
    if trading > 0 and love < table.appease_fear and fear < table.appease_fear:
        return WorshipMode.BARGAIN
    return WorshipMode.DEVOTION


async def prayer_tone(session: AsyncSession, mortal: EntityRow, god_id: int, rules: Rules | None = None) -> PrayerTone:
    community = mortal.location_id if mortal.location_id is not None else mortal.id
    standing = await session.get(DivineStandingRow, (community, god_id))
    if standing is None or standing.mode is None:
        return PrayerTone.THANKS
    if standing.mode is WorshipMode.APPEASEMENT:
        return PrayerTone.MERCY
    if standing.mode in BARGAINING_MODES:
        return PrayerTone.REQUEST
    praising = rules is not None and standing.love - standing.fear >= rules.worship_views.benevolent_margin
    return PrayerTone.PRAISE if praising else PrayerTone.THANKS


async def prayer_essence(ctx: TickContext, tally: WorshipTally) -> None:
    prayers = await ctx.session.execute(
        select(MessageRow.recipient_node_id, MessageRow.sender_node_id, MessageRow.tone)
        .where(MessageRow.epoch == ctx.epoch, MessageRow.intent == MessageIntent.PRAYER, MessageRow.tone.is_not(None))
        .order_by(MessageRow.id)
    )
    for god_id, sender_id, tone in list(prayers):
        if tone is None or held(god_id):
            continue
        spec = PRAYER_TONES[tone]
        son = await ctx.session.get(SonRow, god_id)
        if son is not None:
            son.essence = son.essence + spec.essence(ctx.rules)
            tally.essence += spec.essence(ctx.rules)
        sender = await ctx.session.get(EntityRow, sender_id)
        community = sender.location_id if sender is not None else None
        standing = await ctx.session.get(DivineStandingRow, (community, god_id)) if community is not None and spec.praises else None
        if standing is not None and not held(community) and "awe" not in standing.locked:
            standing.awe = clamp_int(standing.awe + ctx.rules.worship.praise_renown, 0, PERCENT)


Altars = dict[tuple[int, int], list[tuple[EntityRow, StructureProfileRow]]]


async def altars(ctx: TickContext) -> Altars:
    found: Altars = {}
    temples = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind == StructureKind.TEMPLE, StructureProfileRow.dedicated_son_id.is_not(None), EntityRow.status == EntityStatus.CANON)
    )
    for temple, profile in temples:
        if profile.host_entity_id is not None and profile.dedicated_son_id is not None:
            found.setdefault((profile.host_entity_id, profile.dedicated_son_id), []).append((temple, profile))
    return found


async def reshape_temples(ctx: TickContext, temples: list[tuple[EntityRow, StructureProfileRow]], perceived: PerceivedAlignment, tally: WorshipTally) -> None:
    table = ctx.rules.worship_views
    look = ALIGNMENT_LOOKS.get(perceived)
    for temple, profile in temples:
        if held(temple.id):
            continue
        if look is not None:
            lean_style(profile, look, table.temple_style_pull)
        if has_stat(temple, "splendor") and perceived is not PerceivedAlignment.AMBIVALENT:
            step = table.temple_shift if perceived is PerceivedAlignment.BENEVOLENT else -table.temple_shift
            shift_stat(temple, "splendor", step)
        tally.temples += 1


async def view_worship(ctx: TickContext, tally: WorshipTally) -> None:
    table = ctx.rules.worship_views
    standings = list(await ctx.session.scalars(select(DivineStandingRow).order_by(DivineStandingRow.community_entity_id, DivineStandingRow.god_node_id)))
    temples = await altars(ctx)
    for row in standings:
        if held(row.community_entity_id, row.god_node_id):
            continue
        community = await ctx.session.get(EntityRow, row.community_entity_id)
        if community is None or community.status is not EntityStatus.CANON or community.entity_type not in COMMUNITY_TYPES:
            continue
        perceived = perceived_of(ctx.rules, row.love, row.fear)
        trading = (await stored_values(ctx.session, ValueHolder.CULTURE, community.id)).get(ValueAxis.WEALTH, 0)
        mode = mode_of(ctx.rules, row.love, row.fear, trading)
        if "perceived" not in row.locked:
            row.perceived = perceived
        if "mode" not in row.locked:
            row.mode = mode
        tally.views += 1
        if row.mode is WorshipMode.APPEASEMENT:
            tally.appeasing += 1
            offering = round_half_up(table.appeasement_offering_pct * row.fear / PERCENT / OFFERING_DIVISOR)
            tally.offerings += await give_faith(ctx, row.god_node_id, offering)
        elif row.mode in BARGAINING_MODES:
            tally.bargaining += 1
            share = ctx.rules.worship.bargain_offering_pct * table.appeasement_offering_pct / PERCENT
            offering = round_half_up(share * max(row.awe, 1) / PERCENT / OFFERING_DIVISOR)
            tally.offerings += await give_faith(ctx, row.god_node_id, offering)
        else:
            tally.devoted += 1
            if has_stat(community, "piety"):
                shift_stat(community, "piety", table.devotion_morale if stat_or(community, "piety", 0) < PERCENT else 0)
        await reshape_temples(ctx, temples.get((community.id, row.god_node_id), []), row.perceived or perceived, tally)
    await prayer_essence(ctx, tally)
    await ctx.session.flush()


async def give_faith(ctx: TickContext, god_id: int, amount: int) -> int:
    if amount <= 0 or held(god_id):
        return 0
    god = await god_of(ctx.session, god_id)
    if god is None or "faith" in getattr(god, "locked", []):
        return 0
    god.faith = god.faith + amount
    return amount
