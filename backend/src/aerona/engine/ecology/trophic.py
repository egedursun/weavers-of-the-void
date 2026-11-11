from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.catalog.evolution import TROPHIC_ORDER, trophic_level
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import TrophicLevelRow
from aerona.db.write_guard import held
from aerona.domain.enums.evolution import TrophicLevel
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up


@dataclass
class TrophicTally:
    levels: int = 0
    starved: int = 0


def ground_biomass(land: RegionEnvironmentRow | None) -> int:
    if land is None:
        return 0
    return land.forest_cover + land.soil_fertility + land.wetland


async def balance_food_chain(ctx: TickContext, tally: TrophicTally) -> None:
    table = ctx.rules.trophic
    profiles = {row.species_entity_id: row for row in await ctx.session.scalars(select(SpeciesProfileRow))}
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    members: dict[int, dict[TrophicLevel, list[SpeciesRangeRow]]] = defaultdict(lambda: defaultdict(list))
    for row in await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0).order_by(SpeciesRangeRow.region_entity_id, SpeciesRangeRow.species_entity_id)
    ):
        profile = profiles.get(row.species_entity_id)
        level = trophic_level(profile.diet, profile.size_class) if profile is not None else None
        if level is not None:
            members[row.region_entity_id][level].append(row)
    free = sorted(
        region_id
        for region_id in set(members) | {key for key, land in lands.items() if ground_biomass(land) > 0}
        if not held(region_id, lands[region_id].world_id if region_id in lands else None)
    )
    if free:
        await ctx.session.execute(delete(TrophicLevelRow).where(TrophicLevelRow.region_entity_id.in_(free)))
    for region_id in free:
        levels = members.get(region_id, {})
        below = ground_biomass(lands.get(region_id)) + sum(row.abundance for row in levels.get(TrophicLevel.PRODUCER, []))
        for level in TROPHIC_ORDER:
            rows = levels.get(level, [])
            biomass = below if level is TrophicLevel.PRODUCER else sum(row.abundance for row in rows)
            cap = below if level is TrophicLevel.PRODUCER else round_half_up(below * table.efficiency_pct / PERCENT)
            ctx.session.add(TrophicLevelRow(region_entity_id=region_id, level=level, biomass=biomass, cap=cap, epoch=ctx.epoch))
            tally.levels += 1
            if level is not TrophicLevel.PRODUCER and biomass > cap:
                for row in rows:
                    if held(row.species_entity_id) or "abundance" in row.locked:
                        continue
                    loss = round_half_up(table.collapse * row.abundance / max(1, biomass) * len(rows))
                    row.abundance = clamp_int(row.abundance - max(1, loss), 0, PERCENT)
                    row.updated_epoch = ctx.epoch
                    tally.starved += 1
            below = biomass
    await ctx.session.flush()
