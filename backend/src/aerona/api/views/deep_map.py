from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.maps import (
    MapDeepCell,
    MapDeepLevel,
    MapDeepOpening,
    MapDeepPassage,
    MapDeepRegion,
    MapDeepStratum,
    MapDeepSummary,
    MapRelation,
    RelationLineKind,
)
from aerona.cartography.model import WorldMap
from aerona.catalog.strata import STRATA
from aerona.core.grammar import an, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.geology import DeepPassageKind, UndergroundStratum
from aerona.engine.primitives.deep import passage_kind
from aerona.engine.primitives.distance import RegionAtlas

DWELLING_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})


async def world_cells(session: AsyncSession, world_id: int) -> list[RegionStratumRow]:
    regions = select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.world_id == world_id)
    return list(await session.scalars(select(RegionStratumRow).where(RegionStratumRow.region_entity_id.in_(regions)).order_by(RegionStratumRow.id)))


async def world_passages(session: AsyncSession, world_id: int) -> list[DeepPassageRow]:
    return list(await session.scalars(select(DeepPassageRow).where(DeepPassageRow.world_id == world_id).order_by(DeepPassageRow.id)))


def centres(shape: WorldMap) -> dict[int, tuple[float, float]]:
    sums: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    cells = shape.cells
    for index, region in enumerate(cells.top_region):
        if region is not None:
            total = sums[region]
            total[0] += cells.x[index]
            total[1] += cells.y[index]
            total[2] += 1
    return {region: (total[0] / total[2], total[1] / total[2]) for region, total in sums.items() if total[2]}


def level_counts(entities: list[EntityRow], atlas: RegionAtlas) -> tuple[Counter[tuple[int, UndergroundStratum]], Counter[int]]:
    dwellings: Counter[tuple[int, UndergroundStratum]] = Counter()
    below: Counter[int] = Counter()
    for entity in entities:
        level = atlas.level_of(entity.id)
        region = atlas.top_region(entity.id)
        if level is None or region is None:
            continue
        below[region] += 1
        if entity.entity_type in DWELLING_TYPES:
            dwellings[(region, level)] += 1
    return dwellings, below


async def deep_summary(session: AsyncSession, world_id: int, entities: list[EntityRow], atlas: RegionAtlas) -> MapDeepSummary:
    cells = await world_cells(session, world_id)
    if not cells:
        return MapDeepSummary()
    passages = await world_passages(session, world_id)
    counts = Counter(cell.stratum for cell in cells)
    per_region = Counter(cell.region_entity_id for cell in cells)
    armies = Counter(
        row.region_entity_id
        for row in await session.scalars(select(ArmyProfileRow).where(ArmyProfileRow.stratum.is_not(None)).order_by(ArmyProfileRow.army_entity_id))
        if row.region_entity_id is not None
    )
    settlements: Counter[int] = Counter()
    peoples: Counter[int] = Counter()
    for entity in entities:
        region, level = atlas.top_region(entity.id), atlas.level_of(entity.id)
        if region is None or level is None:
            continue
        if entity.entity_type is EntityType.SETTLEMENT:
            settlements[region] += 1
        elif entity.entity_type is EntityType.PEOPLE:
            peoples[region] += 1
    openings = [
        MapDeepOpening(
            passage_id=row.id,
            region_id=row.first_region_entity_id,
            stratum=row.second_stratum or row.first_stratum or UndergroundStratum.CAVERN_UPPER,
            place_id=row.place_entity_id,
            state=row.state,
        )
        for row in passages
        if passage_kind((row.first_region_entity_id, row.first_stratum), (row.second_region_entity_id, row.second_stratum)) is DeepPassageKind.OPENING
    ]
    return MapDeepSummary(
        strata=[
            MapDeepStratum(stratum=stratum, cells=counts[stratum], depth=STRATA[stratum].depth)
            for stratum in sorted(STRATA, key=lambda kind: (STRATA[kind].depth, kind.value))
            if counts[stratum]
        ],
        openings=openings,
        below=[
            MapDeepRegion(region_id=region, strata=per_region[region], settlements=settlements[region], armies=armies[region], peoples=peoples[region])
            for region in sorted(per_region)
        ],
    )


async def deep_level(session: AsyncSession, world_id: int, stratum: UndergroundStratum, entities: list[EntityRow], atlas: RegionAtlas) -> MapDeepLevel:
    cells = [cell for cell in await world_cells(session, world_id) if cell.stratum is stratum]
    dwellings, _ = level_counts(entities, atlas)
    peoples: dict[int, list[int]] = defaultdict(list)
    for entity in entities:
        if entity.entity_type is EntityType.PEOPLE and atlas.level_of(entity.id) is stratum:
            region = atlas.top_region(entity.id)
            if region is not None:
                peoples[region].append(entity.id)
    passages = [row for row in await world_passages(session, world_id) if stratum in (row.first_stratum, row.second_stratum)]
    return MapDeepLevel(
        stratum=stratum,
        cells=[
            MapDeepCell(
                cell_id=cell.id,
                region_id=cell.region_entity_id,
                name=cell.name,
                terrain=cell.terrain,
                extent=cell.extent,
                light=cell.light,
                holder_id=cell.realm_entity_id,
                held=bool(cell.locked),
                dwellable=STRATA[stratum].dwellable,
                settlements=dwellings[(cell.region_entity_id, stratum)],
                peoples=peoples[cell.region_entity_id],
            )
            for cell in cells
        ],
        passages=[
            MapDeepPassage(
                passage_id=row.id,
                kind=passage_kind((row.first_region_entity_id, row.first_stratum), (row.second_region_entity_id, row.second_stratum)),
                state=row.state,
                width=row.width,
                progress=row.progress,
                first_region_id=row.first_region_entity_id,
                first_stratum=row.first_stratum,
                second_region_id=row.second_region_entity_id,
                second_stratum=row.second_stratum,
            )
            for row in passages
        ],
    )


def passage_lines(level: MapDeepLevel, shape: WorldMap) -> list[MapRelation]:
    middle = centres(shape)
    lines: list[MapRelation] = []
    for passage in level.passages:
        first, second = middle.get(passage.first_region_id), middle.get(passage.second_region_id)
        if passage.kind is not DeepPassageKind.LEVEL or first is None or second is None:
            continue
        lines.append(
            MapRelation(
                source=passage.first_region_id,
                target=passage.second_region_id,
                kind=RelationLineKind.PASSAGE,
                description=f"{an(spoken(passage.state), capital=True)} passage, {passage.width} wide",
                path=[first[0], first[1], second[0], second[1]],
            )
        )
    return lines


def at_level(entities: list[EntityRow], atlas: RegionAtlas, level: UndergroundStratum | None) -> list[EntityRow]:
    return [entity for entity in entities if entity.entity_type is EntityType.REGION or atlas.level_of(entity.id) is level]
