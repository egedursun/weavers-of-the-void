import math
from collections import defaultdict
from html import escape

from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.catalog.seasons import ONSET_LABELS, WARMTH_LABELS, WATER_LABELS
from aerona.constants.calendar import SHARE_TOTAL
from aerona.core.grammar import several
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import SeasonOnsetRow, WorldSeasonRow
from aerona.domain.enums.environment import SeasonWarmth
from aerona.engine.environment.season_shape import season_phase
from aerona.engine.lore.calendar_slots import festivals_of
from aerona.services.books.citysvg import Plan
from aerona.services.books.typed import TypedFact, TypedIndex, TypedSection

SIZE = 240
CENTER = SIZE / 2
OUTER = 108
INNER = 62
START = -math.pi / 2
INK = "#2b2118"
EDGE = "#f6efe3"
WARMTH_INK: dict[SeasonWarmth, str] = {
    SeasonWarmth.COLDEST: "#5b7fb3",
    SeasonWarmth.COLD: "#86a3cc",
    SeasonWarmth.COOLING: "#8fb5a8",
    SeasonWarmth.EVEN: "#c9bfae",
    SeasonWarmth.WARMING: "#a9c98b",
    SeasonWarmth.WARM: "#e3b56b",
    SeasonWarmth.WARMEST: "#d98a3d",
}


def _at(angle: float, radius: float) -> str:
    return f"{CENTER + math.cos(angle) * radius:.2f},{CENTER + math.sin(angle) * radius:.2f}"


def _segment(start: float, end: float) -> str:
    large = 1 if end - start > math.pi else 0
    return f"M{_at(start, OUTER)} A{OUTER},{OUTER} 0 {large} 1 {_at(end, OUTER)} L{_at(end, INNER)} A{INNER},{INNER} 0 {large} 0 {_at(start, INNER)} Z"


def season_wheel(seasons: list[WorldSeasonRow]) -> Markup | None:
    if not seasons:
        return None
    phases = season_phase(seasons)
    total = sum(season.share_pct for season in seasons) or SHARE_TOTAL
    parts: list[str] = []
    start = START
    for season in sorted(seasons, key=lambda row: row.position):
        end = start + (2 * math.pi - 1e-4 if len(seasons) == 1 else 2 * math.pi * season.share_pct / total)
        middle = (start + end) / 2
        x, y = (float(value) for value in _at(middle, (OUTER + INNER) / 2).split(","))
        title = escape(f"{season.name}: {season.share_pct}% of the year")
        ink = WARMTH_INK[phases[season.position].warmth]
        parts.append(f'<path d="{_segment(start, end)}" fill="{ink}" stroke="{EDGE}" stroke-width="2"><title>{title}</title></path>')
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="13" fill="{INK}">{season.position + 1}</text>')
        start = end
    return Markup(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" role="img">{"".join(parts)}</svg>')


def season_row(season: WorldSeasonRow, warmth: SeasonWarmth, water_label: str) -> str:
    held = " · held" if season.edited else ""
    return (
        f"{season.position + 1}. {season.name} · {WARMTH_LABELS[warmth]} · {water_label} · {season.share_pct}% of the year · "
        f"warmth {season.temperature_shift:+d} · rain {season.rain_shift:+d} · growth {season.growth} · travel {season.travel} · war {season.campaign}{held}"
    )


def onset_row(row: SeasonOnsetRow, names: dict[int, str]) -> str:
    season = names.get(row.season_position, f"season {row.season_position + 1}")
    held = " · held" if row.locked else ""
    return f"Year {row.year} · {season} · {ONSET_LABELS[row.onset]}{held}"


async def add_season_sections(session: AsyncSession, index: TypedIndex) -> dict[int, Markup]:
    grouped: dict[int, list[WorldSeasonRow]] = defaultdict(list)
    for season in await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)):
        grouped[season.world_id].append(season)
    onsets: dict[int, list[SeasonOnsetRow]] = defaultdict(list)
    for onset in await session.scalars(select(SeasonOnsetRow).order_by(SeasonOnsetRow.world_id, SeasonOnsetRow.year, SeasonOnsetRow.season_position)):
        onsets[onset.world_id].append(onset)
    wheels: dict[int, Markup] = {}
    for world_id, seasons in grouped.items():
        phases = season_phase(seasons)
        section = TypedSection("Seasons", facts=[TypedFact("Seasons in the year", str(len(seasons)))])
        section.rows = [season_row(season, phases[season.position].warmth, WATER_LABELS[phases[season.position].water]) for season in seasons]
        index.sections[world_id].append(section)
        wheel = season_wheel(seasons)
        if wheel is not None:
            wheels[world_id] = wheel
    for world_id, rows in onsets.items():
        names = {season.position: season.name for season in grouped.get(world_id, [])}
        lines = [onset_row(row, names) for row in rows]
        index.sections[world_id].append(TypedSection("Season onsets", rows=lines))
    return wheels


FESTIVAL_DOT = 4
FESTIVAL_RING = OUTER + 7
FESTIVAL_STEP = 0.09
FESTIVAL_INK = "#7a3e1d"


def festival_wheel(seasons: list[WorldSeasonRow], counts: dict[int, int]) -> Markup:
    phases = season_phase(seasons)
    total = sum(season.share_pct for season in seasons) or SHARE_TOTAL
    parts: list[str] = []
    start = START
    for season in sorted(seasons, key=lambda row: row.position):
        end = start + (2 * math.pi - 1e-4 if len(seasons) == 1 else 2 * math.pi * season.share_pct / total)
        middle = (start + end) / 2
        x, y = (float(value) for value in _at(middle, (OUTER + INNER) / 2).split(","))
        kept = counts.get(season.position, 0)
        title = escape(f"{season.name}: {several(kept, 'festival', 'festivals')}")
        ink = WARMTH_INK[phases[season.position].warmth]
        parts.append(f'<path d="{_segment(start, end)}" fill="{ink}" stroke="{EDGE}" stroke-width="2"><title>{title}</title></path>')
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="13" fill="{INK}">{season.position + 1}</text>')
        for index in range(kept):
            angle = middle + (index - (kept - 1) / 2) * FESTIVAL_STEP
            dot_x, dot_y = (float(value) for value in _at(angle, FESTIVAL_RING).split(","))
            parts.append(f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="{FESTIVAL_DOT}" fill="{FESTIVAL_INK}" stroke="{EDGE}" stroke-width="1"/>')
        start = end
    return Markup(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" role="img">{"".join(parts)}</svg>')


def festival_words(entity: EntityRow, profile: TraditionProfileRow) -> str:
    if profile.calendar_slot is None:
        return f"{entity.name} (whenever it falls)"
    comes = {True: ", comes this epoch", False: ", does not come this epoch", None: ""}[profile.in_season]
    return f"{entity.name} (at {SLOTS[profile.calendar_slot].label.lower()}{comes})"


async def festival_plan(session: AsyncSession, people: EntityRow) -> Plan | None:
    festivals = await festivals_of(session, people.id)
    if not festivals:
        return None
    seasons = list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == people.world_id).order_by(WorldSeasonRow.position)))
    placed: dict[int | None, list[str]] = defaultdict(list)
    positions = {season.position for season in seasons}
    for entity, profile in festivals:
        position = profile.season_position if profile.season_position in positions else None
        placed[position].append(festival_words(entity, profile))
    facts = [(f"{season.position + 1}. {season.name}", "; ".join(placed[season.position]) or "none") for season in seasons]
    if placed.get(None):
        facts.append(("Whenever its time comes", "; ".join(placed[None])))
    counts = {position: len(names) for position, names in placed.items() if position is not None}
    figure = festival_wheel(seasons, counts) if seasons else Markup("")
    return Plan(figure=figure, caption=f"The year of festivals of {people.name}", facts=facts)
