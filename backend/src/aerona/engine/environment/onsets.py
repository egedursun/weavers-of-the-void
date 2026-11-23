from collections.abc import Sequence

from sqlalchemy import select

from aerona.catalog.seasons import ONSET_SHIFT
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import SeasonOnsetRow, WorldSeasonRow
from aerona.domain.enums.environment import SeasonOnset
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.environment.season_shape import onset_draw
from aerona.engine.environment.years import SampledYear
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules


def onset_growth(rules: Rules, growth: int, onset: SeasonOnset) -> int:
    return clamp_int(growth * (PERCENT + ONSET_SHIFT[onset] * rules.seasons.onset_yield_shift_pct) / PERCENT, 0, PERCENT)


def onset_of_year(rules: Rules, world_seed: int, world_id: int, year: int, position: int) -> SeasonOnset:
    settings = rules.seasons
    rng = SeededRandom.for_epoch(world_seed, 0, f"season_onset.{world_id}.{year}.{position}")
    return onset_draw(rng, settings.early_pct, settings.late_pct, settings.failed_pct)


async def stored_onsets(ctx: TickContext, world_id: int, years: Sequence[int]) -> dict[tuple[int, int], SeasonOnsetRow]:
    rows = await ctx.session.scalars(select(SeasonOnsetRow).where(SeasonOnsetRow.world_id == world_id, SeasonOnsetRow.year.in_(list(years))))
    return {(row.year, row.season_position): row for row in rows}


async def draw_onsets(ctx: TickContext, world: WorldRow, seasons: Sequence[WorldSeasonRow], years: Sequence[SampledYear]) -> dict[tuple[int, int], SeasonOnset]:
    stored = await stored_onsets(ctx, world.id, [sampled.year for sampled in years])
    found: dict[tuple[int, int], SeasonOnset] = {}
    if len(seasons) <= 1:
        return {key: row.onset for key, row in stored.items()}
    for sampled in years:
        for season in seasons:
            key = (sampled.year, season.position)
            row = stored.get(key)
            if row is not None and row.locked:
                found[key] = row.onset
                continue
            onset = onset_of_year(ctx.rules, ctx.environment.world_seed, world.id, sampled.year, season.position)
            found[key] = onset
            if onset is SeasonOnset.ON_TIME:
                if row is not None:
                    await ctx.session.delete(row)
                continue
            if row is None:
                row = SeasonOnsetRow(world_id=world.id, year=sampled.year, season_position=season.position, onset=onset)
                ctx.session.add(row)
            row.onset = onset
            await record(
                ctx,
                "season.onset",
                roles={IncidentRole.SUBJECT: world.id},
                facts={"season": season.name, "onset": onset, "year": sampled.year},
                world_id=world.id,
            )
    await ctx.session.flush()
    return found


def failed_wet(onsets: dict[tuple[int, int], SeasonOnset], seasons: Sequence[WorldSeasonRow], year: int) -> bool:
    return any(onsets.get((year, season.position)) is SeasonOnset.FAILED and season.rain_shift > 0 for season in seasons)
