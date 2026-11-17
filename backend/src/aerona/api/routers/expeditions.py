from fastapi import APIRouter, Query
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.cosmos import EpochStarEntry, EpochStarView, EpochStarWorld, GreatExpedition
from aerona.api.schemas.records import EntitySummary
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, LegendaryQuestRow, ThreadRow
from aerona.engine.cosmos.quests import legendary_name

router = APIRouter(tags=["cosmos"])

EPOCH_BEGAN_KEY = "transition.epoch_began"
HISTORY_DEFAULT = 100
HISTORY_MAX = 1000


@router.get("/cosmos/epoch-star", response_model=EpochStarView)
async def read_epoch_star(
    services: ServicesDep, limit: int = Query(default=HISTORY_DEFAULT, ge=1, le=HISTORY_MAX), offset: int = Query(default=0, ge=0)
) -> EpochStarView:
    async with reader(services) as session:
        worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id)))
        current: list[EpochStarWorld] = []
        for world in worlds:
            body = await session.get(EntityRow, world.epoch_star_entity_id) if world.epoch_star_entity_id is not None else None
            current.append(EpochStarWorld(world_id=world.id, world_name=world.name, star=EntitySummary.model_validate(body) if body is not None else None))
        lines = list(
            await session.scalars(
                select(ChronicleRow).where(ChronicleRow.template_key == EPOCH_BEGAN_KEY).order_by(ChronicleRow.epoch.desc()).offset(offset).limit(limit)
            )
        )
        history: list[EpochStarEntry] = []
        for line in lines:
            link = await session.scalar(
                select(ChronicleEntityRow).where(ChronicleEntityRow.chronicle_id == line.id).order_by(ChronicleEntityRow.position).limit(1)
            )
            body = await session.get(EntityRow, link.entity_id) if link is not None else None
            history.append(
                EpochStarEntry(epoch=line.epoch, entity_id=body.id if body is not None else None, name=body.name if body is not None else None, text=line.text)
            )
        return EpochStarView(current=current, history=history)


@router.get("/expeditions", response_model=list[GreatExpedition])
async def list_expeditions(services: ServicesDep, open_only: bool = False) -> list[GreatExpedition]:
    async with reader(services) as session:
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        statement = (
            select(LegendaryQuestRow, ThreadRow).join(ThreadRow, ThreadRow.id == LegendaryQuestRow.thread_id).order_by(LegendaryQuestRow.thread_id.desc())
        )
        if open_only:
            statement = statement.where(LegendaryQuestRow.outcome.is_(None))
        return [
            GreatExpedition(
                thread_id=quest.thread_id,
                aim=quest.aim,
                target_kind=quest.target_kind,
                obstacle=quest.obstacle,
                reward=quest.reward,
                scale=quest.scale,
                locked=list(quest.locked),
                name=legendary_name(quest),
                text=thread.text,
                declared_by=quest.opened_by,
                opened_epoch=quest.opened_epoch,
                deadline_epoch=quest.deadline_epoch,
                epochs_remaining=max(0, quest.deadline_epoch - epoch) if quest.outcome is None else 0,
                thread_status=thread.status,
                outcome=quest.outcome,
                target_star_id=quest.target_star_id,
                target_route_id=quest.target_route_id,
                target_entity_id=quest.target_entity_id,
            )
            for quest, thread in (await session.execute(statement)).all()
        ]
