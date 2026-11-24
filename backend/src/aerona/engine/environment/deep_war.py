from dataclasses import dataclass

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import DeepPassageRow
from aerona.db.write_guard import held
from aerona.domain.enums.geology import DeepPassageState
from aerona.domain.enums.military import SiegeAction
from aerona.engine.context import TickContext
from aerona.engine.environment.cells import dig_toward, passage_between, tell
from aerona.engine.military.logistics import March
from aerona.engine.primitives.deep import Cell
from aerona.engine.primitives.distance import RegionAtlas

COLLAPSIBLE = frozenset({DeepPassageState.OPEN, DeepPassageState.FLOODED, DeepPassageState.DIGGING})


@dataclass
class DeepWarTally:
    cut: int = 0
    reopened: int = 0
    collapsed: int = 0
    mined: int = 0


def cells_into(atlas: RegionAtlas, cell: Cell) -> list[Cell]:
    region, level = cell
    if level is None:
        return []
    return [(region, None), *[(other, level) for other in atlas.neighbours(region)]]


async def collapse_ways(ctx: TickContext, besieged: EntityRow, march: March, atlas: RegionAtlas, tally: DeepWarTally) -> int:
    town = atlas.cell_of(besieged.id)
    camp = (march.profile.region_entity_id, march.profile.stratum) if march.profile.region_entity_id is not None else None
    if town is None or town[1] is None or held(besieged.id):
        return 0
    collapsed = 0
    for other in cells_into(atlas, town):
        if other == camp:
            continue
        passage = await passage_between(ctx, town, other)
        if passage is None or passage.state not in COLLAPSIBLE or "state" in passage.locked or held(other[0]):
            continue
        passage.state = DeepPassageState.COLLAPSED
        await tell(ctx, "deep.passage_collapsed", passage, march.owner.id)
        collapsed += 1
    tally.collapsed += collapsed
    return collapsed


async def mine_below(ctx: TickContext, besieged: EntityRow, march: March, atlas: RegionAtlas, tally: DeepWarTally) -> DeepPassageRow | None:
    town = atlas.cell_of(besieged.id)
    region = march.profile.region_entity_id
    if town is None or town[1] is None or region is None or held(besieged.id):
        return None
    start: Cell = (region, town[1]) if region != town[0] else (region, None)
    if region != town[0] and region not in atlas.neighbours(town[0]):
        return None
    found = await passage_between(ctx, start, town)
    if found is not None:
        return None
    passage = await dig_toward(ctx, march.army, start, town)
    tally.mined += 1
    await tell(ctx, "deep.passage_dug", passage, march.owner.id)
    return passage


async def press_below(ctx: TickContext, besieged: EntityRow, march: March, action: SiegeAction, atlas: RegionAtlas) -> None:
    tally = DeepWarTally()
    if action is SiegeAction.BLOCKADE:
        await collapse_ways(ctx, besieged, march, atlas, tally)
    elif action is SiegeAction.MINE:
        await mine_below(ctx, besieged, march, atlas, tally)
    ctx.count("passages_collapsed_in_siege", tally.collapsed)
    ctx.count("passages_mined_in_siege", tally.mined)
