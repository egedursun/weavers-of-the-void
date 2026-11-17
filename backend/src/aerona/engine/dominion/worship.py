from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.dominion import ALIGNMENT_LOOKS
from aerona.catalog.peoples import STYLE_AXES, Style
from aerona.constants.units import PERCENT
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.dominion import PerceivedAlignment, PrayerTone, WorshipMode
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import god_of
from aerona.engine.lore.style import axis_of
from aerona.engine.primitives.numbers import round_half_up
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


def mode_of(rules: Rules, love: int, fear: int) -> WorshipMode:
    return WorshipMode.APPEASEMENT if fear >= rules.worship_views.appease_fear and fear > love else WorshipMode.DEVOTION


async def prayer_tone(session: AsyncSession, mortal: EntityRow, god_id: int) -> PrayerTone:
    community = mortal.location_id if mortal.location_id is not None else mortal.id
    standing = await session.get(DivineStandingRow, (community, god_id))
    if standing is None or standing.mode is None:
        return PrayerTone.THANKS
    return PrayerTone.MERCY if standing.mode is WorshipMode.APPEASEMENT else PrayerTone.THANKS


async def reshape_temples(ctx: TickContext, community: EntityRow, god_id: int, perceived: PerceivedAlignment, tally: WorshipTally) -> None:
    table = ctx.rules.worship_views
    temples = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(
            StructureProfileRow.kind == StructureKind.TEMPLE,
            StructureProfileRow.dedicated_son_id == god_id,
            StructureProfileRow.host_entity_id == community.id,
            EntityRow.status == EntityStatus.CANON,
        )
    )
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
    for row in list(await ctx.session.scalars(select(DivineStandingRow).order_by(DivineStandingRow.community_entity_id, DivineStandingRow.god_node_id))):
        if held(row.community_entity_id, row.god_node_id):
            continue
        community = await ctx.session.get(EntityRow, row.community_entity_id)
        if community is None or community.status is not EntityStatus.CANON or community.entity_type not in COMMUNITY_TYPES:
            continue
        perceived = perceived_of(ctx.rules, row.love, row.fear)
        mode = mode_of(ctx.rules, row.love, row.fear)
        if "perceived" not in row.locked:
            row.perceived = perceived
        if "mode" not in row.locked:
            row.mode = mode
        tally.views += 1
        if row.mode is WorshipMode.APPEASEMENT:
            tally.appeasing += 1
            offering = round_half_up(table.appeasement_offering_pct * row.fear / PERCENT / OFFERING_DIVISOR)
            tally.offerings += await give_faith(ctx, row.god_node_id, offering)
        else:
            tally.devoted += 1
            if has_stat(community, "piety"):
                shift_stat(community, "piety", table.devotion_morale if stat_or(community, "piety", 0) < PERCENT else 0)
        await reshape_temples(ctx, community, row.god_node_id, row.perceived or perceived, tally)
    await ctx.session.flush()


async def give_faith(ctx: TickContext, god_id: int, amount: int) -> int:
    if amount <= 0 or held(god_id):
        return 0
    god = await god_of(ctx.session, god_id)
    if god is None or "faith" in getattr(god, "locked", []):
        return 0
    god.faith = god.faith + amount
    return amount
