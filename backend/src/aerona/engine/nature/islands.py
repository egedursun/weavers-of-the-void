from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import SIZE_ORDER, SizeClass
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas


@dataclass
class IslandTally:
    drifted: int = 0
    endemic: int = 0
    relict: int = 0


def drifted_size(size: SizeClass) -> SizeClass:
    index, middle = SIZE_ORDER.index(size), SIZE_ORDER.index(SizeClass.MEDIUM)
    return SIZE_ORDER[index - 1] if index > middle else SIZE_ORDER[index + 1] if index < middle else size


async def keep_islands(ctx: TickContext, tally: IslandTally) -> None:
    table = ctx.rules.island_rule
    islands = set(await ctx.session.scalars(select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.dominant_terrain == TerrainKind.ISLAND)))
    ranges: dict[int, list[int]] = defaultdict(list)
    for kind_id, region in await ctx.session.execute(
        select(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.abundance > 0)
    ):
        ranges[kind_id].append(region)
    for profile in list(await ctx.session.scalars(select(SpeciesProfileRow).order_by(SpeciesProfileRow.species_entity_id))):
        species = await ctx.session.get(EntityRow, profile.species_entity_id)
        if species is None or species.status is not EntityStatus.CANON or held(species.id):
            continue
        lands = ranges.get(species.id, [])
        if "range_peak" not in profile.locked:
            profile.range_peak = max(profile.range_peak, len(lands))
        if "endemic" not in profile.locked:
            profile.endemic = 0 < len(lands) <= table.endemic_regions
        if "relict" not in profile.locked:
            profile.relict = profile.range_peak > table.endemic_regions and 0 < len(lands) <= profile.range_peak * table.relict_pct / PERCENT
        tally.endemic += profile.endemic
        tally.relict += profile.relict
        if lands and all(region in islands for region in lands):
            if "island_epochs" not in profile.locked:
                profile.island_epochs += 1
            smaller = drifted_size(profile.size_class)
            if profile.island_epochs % table.drift_epochs == 0 and "size_class" not in profile.locked and smaller is not profile.size_class:
                profile.size_class = smaller
                tally.drifted += 1
        elif "island_epochs" not in profile.locked:
            profile.island_epochs = 0
    await ctx.session.flush()


@memoized(SpeciesProfileRow, CultureValueRow, EntityRow)
async def spared_kinds(session: AsyncSession, revered_value: int) -> frozenset[tuple[int, int]]:
    rare = [
        row.species_entity_id
        for row in await session.scalars(select(SpeciesProfileRow).where((SpeciesProfileRow.endemic.is_(True)) | (SpeciesProfileRow.relict.is_(True))))
    ]
    if not rare:
        return frozenset()
    reverent = set(
        await session.scalars(select(CultureValueRow.entity_id).where(CultureValueRow.axis == ValueAxis.NATURE, CultureValueRow.value >= revered_value))
    )
    atlas = await RegionAtlas.load(session)
    found: set[tuple[int, int]] = set()
    for species, region in await session.execute(
        select(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id).where(
            SpeciesRangeRow.species_entity_id.in_(rare), SpeciesRangeRow.abundance > 0
        )
    ):
        for town in atlas.communities_in(region):
            row = await session.get(EntityRow, town)
            folk = await people_of(session, row) if row is not None else None
            if folk is not None and folk.id in reverent:
                found.add((species, region))
                break
    return frozenset(found)
