from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import TradeRouteRegionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import DeepPassageRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.geology import DeepPassageState
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.deep import Cell, front_cells
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.recording.record import record

CUTTING = frozenset({DeepPassageState.DIGGING, DeepPassageState.FLOODED, DeepPassageState.COLLAPSED, DeepPassageState.SEALED})


async def passage_at(session: AsyncSession, first: Cell, second: Cell) -> DeepPassageRow | None:
    low, high = front_cells(first, second)
    return await session.scalar(
        select(DeepPassageRow).where(
            DeepPassageRow.first_region_entity_id == low[0],
            DeepPassageRow.first_stratum.is_(None) if low[1] is None else DeepPassageRow.first_stratum == low[1],
            DeepPassageRow.second_region_entity_id == high[0],
            DeepPassageRow.second_stratum.is_(None) if high[1] is None else DeepPassageRow.second_stratum == high[1],
        )
    )


def below(cells: list[Cell]) -> bool:
    return any(level is not None for _, level in cells)


def route_cells(atlas: RegionAtlas, first: EntityRow, second: EntityRow) -> list[Cell] | None:
    start, goal = atlas.cell_of(first.id), atlas.cell_of(second.id)
    if start is None or goal is None or (start[1] is None and goal[1] is None):
        return None
    found = atlas.cell_path(start, goal)
    return found if found is not None and below(found) else None


async def blocking_passage(ctx: TickContext, cells: list[Cell]) -> tuple[Cell, Cell, DeepPassageRow | None] | None:
    for first, second in pairwise(cells):
        if first[1] is None and second[1] is None:
            continue
        passage = await passage_at(ctx.session, first, second)
        if passage is None or passage.state in CUTTING:
            return first, second, passage
    return None


async def cut_below(ctx: TickContext, route_id: int, mode: TradeMode, cells: list[Cell]) -> bool:
    if mode is not TradeMode.UNDERGROUND or not below(cells) or held(route_id):
        return False
    return await blocking_passage(ctx, cells) is not None


async def tell_route_cut(ctx: TickContext, route_id: int, cells: list[Cell]) -> None:
    found = await blocking_passage(ctx, cells)
    if found is None:
        return
    first, second, passage = found
    await record(
        ctx,
        "route.passage_cut",
        roles={IncidentRole.SUBJECT: route_id, IncidentRole.PLACE: first[0], IncidentRole.DESTINATION: second[0]},
        facts={"state": passage.state if passage is not None else DeepPassageState.COLLAPSED},
        place=first[0],
    )


async def tell_route_reopened(ctx: TickContext, route_id: int, cells: list[Cell]) -> None:
    deepest = next((cell for cell in cells if cell[1] is not None), cells[0])
    await record(ctx, "route.passage_reopened", roles={IncidentRole.SUBJECT: route_id, IncidentRole.PLACE: deepest[0]}, place=deepest[0])


async def route_passages(session: AsyncSession, route_id: int) -> list[DeepPassageState | None]:
    steps = list(
        await session.execute(
            select(TradeRouteRegionRow.region_entity_id, TradeRouteRegionRow.stratum)
            .where(TradeRouteRegionRow.route_entity_id == route_id)
            .order_by(TradeRouteRegionRow.position)
        )
    )
    cells: list[Cell] = [(region, level) for region, level in steps]
    found: list[DeepPassageState | None] = []
    for first, second in pairwise(cells):
        if first[1] is None and second[1] is None:
            continue
        passage = await passage_at(session, first, second)
        found.append(passage.state if passage is not None else None)
    return found
