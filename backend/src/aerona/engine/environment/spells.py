from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.long_seasons import CAUSES, REACHES, northern
from aerona.constants.units import PERCENT
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.celestial import WorldRow
from aerona.domain.enums.ages import LongSeasonReach, SeasonCause, SeasonSpell, SeasonSpellShape
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SpellSources:
    impact_id: int | None = None
    region_id: int | None = None
    star_id: int | None = None
    incident_id: int | None = None


@dataclass(frozen=True)
class SpellPull:
    winter: int
    summer: int


async def spells_of(ctx: TickContext, world_id: int) -> list[IrregularSeasonRow]:
    return list(await ctx.session.scalars(select(IrregularSeasonRow).where(IrregularSeasonRow.world_id == world_id).order_by(IrregularSeasonRow.id)))


def covers(row: IrregularSeasonRow, latitude: int, map_y: float | None) -> bool:
    return REACHES[row.reach].covers(latitude, northern(map_y))


def felt(rules: Rules, row: IrregularSeasonRow, latitude: int, map_y: float | None) -> int:
    if covers(row, latitude, map_y):
        return row.severity
    return row.severity * rules.long_seasons.far_share_pct // PERCENT if row.cause is SeasonCause.ERUPTION else 0


def stacked(rules: Rules, severities: Sequence[int]) -> int:
    ordered = sorted(severities, reverse=True)
    if not ordered:
        return 0
    return clamp_int(ordered[0] + sum(value * rules.long_seasons.stacking_share_pct // PERCENT for value in ordered[1:]), 0, PERCENT)


def pull_of(rules: Rules, rows: Sequence[IrregularSeasonRow], latitude: int, map_y: float | None) -> SpellPull:
    winters = [felt(rules, row, latitude, map_y) for row in rows if row.spell is SeasonSpell.WINTER]
    summers = [felt(rules, row, latitude, map_y) for row in rows if row.spell is SeasonSpell.SUMMER]
    winter, summer = stacked(rules, [value for value in winters if value]), stacked(rules, [value for value in summers if value])
    offset = min(winter, summer)
    return SpellPull(winter - offset, summer - offset)


def shifts(rules: Rules, pull: SpellPull) -> tuple[int, int]:
    table = rules.long_seasons
    temperature = round_half_up((pull.summer * table.summer_heat_shift - pull.winter * table.winter_cold_shift) / PERCENT)
    rain = -round_half_up(pull.summer * table.summer_rain_shift / PERCENT)
    return temperature, rain


async def begin_spell(
    ctx: TickContext,
    world: WorldRow,
    cause: SeasonCause,
    *,
    shape: SeasonSpellShape,
    spell: SeasonSpell,
    length: int,
    severity: int,
    reach: LongSeasonReach = LongSeasonReach.WORLD,
    sources: SpellSources | None = None,
    by_node_id: int | None = None,
) -> IrregularSeasonRow:
    allowed = CAUSES[cause].shapes
    sources = sources or SpellSources()
    row = IrregularSeasonRow(
        world_id=world.id,
        cause=cause,
        shape=shape if shape in allowed else min(allowed),
        spell=spell,
        spell_started_epoch=ctx.epoch,
        spell_length=max(1, length),
        severity=clamp_int(severity, 0, PERCENT),
        reach=reach,
        source_impact_id=sources.impact_id,
        source_region_id=sources.region_id,
        source_star_id=sources.star_id,
        source_incident_id=sources.incident_id,
        by_node_id=by_node_id,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        "seasons.spell_began",
        roles={IncidentRole.SUBJECT: world.id, **({IncidentRole.ACTOR: by_node_id} if by_node_id is not None else {})},
        facts={"cause": cause, "shape": row.shape, "spell": spell, "severity": row.severity, "length": row.spell_length, "reach": reach},
        world_id=world.id,
    )
    return row
