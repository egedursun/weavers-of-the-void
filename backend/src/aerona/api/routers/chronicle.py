from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.chronicle import ChronicleEpoch, ChroniclePage, PerspectiveLine
from aerona.api.schemas.records import ThreadRecord
from aerona.api.views.common import chronicle_lines, node_refs
from aerona.db.repositories.chronicle import in_world
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.lore import ChronicleRow, HistorianViewRow, ThreadLinkRow
from aerona.services.codex import CosmicEpoch, cosmic_chronicle
from aerona.services.threads import list_threads

router = APIRouter(tags=["chronicle"])

ALIASES = (
    Alias("POST", "/threads", "thread:open"),
    Alias("POST", "/threads/{thread_id}/close", "thread:close", path_fields={"thread_id": "thread_id"}),
)


async def primary_world(session: AsyncSession) -> int:
    cosmos = await CosmosRepository(session).require_cosmos()
    if cosmos.primary_world_id is not None:
        return cosmos.primary_world_id
    return int(await session.scalar(select(func.min(WorldRow.id))) or 0)


@router.get("/chronicle", response_model=ChroniclePage)
async def read_chronicle(
    services: ServicesDep,
    epoch: int | None = Query(default=None, ge=1),
    before: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    world_id: int | None = Query(default=None, ge=1),
) -> ChroniclePage:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        server = rules.server
        statement = select(ChronicleRow).where(ChronicleRow.visible.is_(True))
        if epoch is not None:
            statement = statement.where(ChronicleRow.epoch == epoch)
        if world_id is not None:
            statement = statement.where(in_world(world_id, await primary_world(session)))
        total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        if before is not None:
            statement = statement.where(ChronicleRow.id < before)
        size = min(limit, server.chronicle_page_max) if limit is not None else server.chronicle_page_size if before is not None else server.chronicle_latest
        if epoch is not None and limit is None and before is None:
            size = total
        rows = list(await session.scalars(statement.order_by(ChronicleRow.id.desc()).limit(size)))
        rows.reverse()
        return ChroniclePage(items=await chronicle_lines(session, rows), total=total)


@router.get("/chronicle/epochs", response_model=list[ChronicleEpoch])
async def chronicle_epochs(services: ServicesDep) -> list[ChronicleEpoch]:
    async with reader(services) as session:
        counts = await session.execute(
            select(ChronicleRow.epoch, func.count()).where(ChronicleRow.visible.is_(True)).group_by(ChronicleRow.epoch).order_by(ChronicleRow.epoch)
        )
        names = {row.epoch: row.name for row in await session.scalars(select(EpochRow))}
        return [ChronicleEpoch(epoch=epoch, name=names.get(epoch), lines=int(count)) for epoch, count in counts]


@router.get("/chronicle/perspectives", response_model=list[PerspectiveLine])
async def perspectives(services: ServicesDep, epoch: int | None = Query(default=None, ge=1)) -> list[PerspectiveLine]:
    async with reader(services) as session:
        statement = select(HistorianViewRow, EntityRow.name).join(EntityRow, EntityRow.id == HistorianViewRow.people_entity_id, isouter=True)
        if epoch is not None:
            statement = statement.where(HistorianViewRow.epoch == epoch)
        rows = await session.execute(statement.order_by(HistorianViewRow.epoch.desc(), HistorianViewRow.id))
        return [
            PerspectiveLine(id=row.id, epoch=row.epoch, people_id=row.people_entity_id, people_name=name, historian=row.historian, text=row.text)
            for row, name in rows
        ]


@router.get("/chronicle/cosmic", response_model=list[CosmicEpoch])
async def cosmic(services: ServicesDep, last: int | None = Query(default=None, ge=1)) -> list[CosmicEpoch]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        count = min(last or rules.server.cosmic_chronicle_default, rules.server.cosmic_chronicle_max)
        return await cosmic_chronicle(session, rules, count)


@router.get("/threads", response_model=list[ThreadRecord])
async def threads(services: ServicesDep) -> list[ThreadRecord]:
    async with reader(services) as session:
        rows = await list_threads(session)
        links = await session.execute(select(ThreadLinkRow.thread_id, ThreadLinkRow.entity_id).where(ThreadLinkRow.thread_id.in_([row.id for row in rows])))
        by_thread: dict[int, list[int]] = {}
        for thread_id, entity_id in links:
            by_thread.setdefault(thread_id, []).append(entity_id)
        refs = await node_refs(session, [entity for ids in by_thread.values() for entity in ids])
        return [
            ThreadRecord(
                **ThreadRecord.model_validate(row).model_dump(exclude={"related"}),
                related=[refs[entity] for entity in by_thread.get(row.id, []) if entity in refs],
            )
            for row in rows
        ]


mount_all(router, ALIASES, tag="chronicle")
