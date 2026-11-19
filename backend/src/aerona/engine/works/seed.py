from sqlalchemy import select

from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.works import PublicWorksRow
from aerona.db.write_guard import held
from aerona.domain.enums.works import WorksKind, WorksStatus
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of

LEVEL_KINDS: tuple[tuple[str, WorksKind], ...] = (
    ("roads", WorksKind.ROAD),
    ("bridges", WorksKind.BRIDGE),
    ("walls_level", WorksKind.WALLS),
    ("irrigation", WorksKind.DRAINAGE),
)
CAPACITY_KINDS: tuple[tuple[str, WorksKind], ...] = (("harbour_capacity", WorksKind.HARBOUR_WORKS), ("granary_capacity", WorksKind.GRANARY_SYSTEM))
STAGES_MAX = 20


def legacy_kinds(row: SettlementInfrastructureRow) -> list[tuple[WorksKind, int]]:
    found = [(kind, getattr(row, column)) for column, kind in LEVEL_KINDS if getattr(row, column) > 0]
    found += [(kind, 1) for column, kind in CAPACITY_KINDS if getattr(row, column) > 0]
    if row.sewers:
        found.append((WorksKind.SEWER, 1))
    return found


async def seed_works(ctx: TickContext) -> int:
    worked = set(await ctx.session.scalars(select(PublicWorksRow.place_node_id)))
    made = 0
    for row in list(await ctx.session.scalars(select(SettlementInfrastructureRow).order_by(SettlementInfrastructureRow.settlement_entity_id))):
        town_id = row.settlement_entity_id
        if town_id in worked or held(town_id):
            continue
        builder = await realm_of(ctx.session, town_id) or town_id
        for kind, stages in legacy_kinds(row):
            ctx.session.add(
                PublicWorksRow(
                    polity_entity_id=builder,
                    place_node_id=town_id,
                    kind=kind,
                    stages=min(stages, STAGES_MAX),
                    stage=min(stages, STAGES_MAX),
                    status=WorksStatus.FINISHED,
                    begun_epoch=ctx.epoch,
                    finished_epoch=ctx.epoch,
                    locked=[],
                )
            )
            made += 1
    await ctx.session.flush()
    return made
