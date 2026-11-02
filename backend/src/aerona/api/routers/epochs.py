from fastapi import APIRouter, Path, status
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import Done, JobAccepted
from aerona.api.schemas.epochs import EpochListItem, WorldNarrative
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.epoch.eta import EpochEstimate, estimate
from aerona.services.lore_totals import LoreTotals, lore_totals
from aerona.services.statistics import EpochBreakdown, EpochStatistics, breakdown, series

router = APIRouter(tags=["epochs"])

NO_EPOCH_RUNNING = "No epoch is running."
NO_STATISTICS = "No statistics for this epoch."


@router.post("/epochs/current/complete", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def complete_epoch(services: ServicesDep) -> JobAccepted:
    return JobAccepted(job_id=await services.orchestrator.submit())


@router.post("/epochs/current/stop", response_model=Done)
async def stop_epoch(services: ServicesDep) -> Done:
    if services.jobs.busy_group(WORLD_GROUP) is None:
        raise ConflictError(NO_EPOCH_RUNNING)
    services.orchestrator.request_stop()
    return Done(message="The epoch stops at the next safe point.")


@router.get("/epochs/current/estimate", response_model=EpochEstimate)
async def epoch_estimate(services: ServicesDep) -> EpochEstimate:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        cosmos = await CosmosRepository(session).get()
        return await estimate(session, rules, cosmos.epoch if cosmos else None)


@router.get("/epochs", response_model=list[EpochListItem])
async def list_epochs(services: ServicesDep) -> list[EpochListItem]:
    async with reader(services) as session:
        epochs = list(await session.scalars(select(EpochRow).where(EpochRow.closed_at.is_not(None)).order_by(EpochRow.epoch.desc())))
        narratives = await session.execute(
            select(EpochWorldNarrativeRow, WorldRow.name)
            .join(WorldRow, WorldRow.id == EpochWorldNarrativeRow.world_id)
            .order_by(EpochWorldNarrativeRow.world_id)
        )
        by_epoch: dict[int, list[WorldNarrative]] = {}
        for row, world_name in narratives:
            by_epoch.setdefault(row.epoch, []).append(
                WorldNarrative(world_id=row.world_id, world_name=world_name, narrative=row.narrative, summary=row.summary)
            )
    return [EpochListItem(**EpochListItem.model_validate(row).model_dump(exclude={"worlds"}), worlds=by_epoch.get(row.epoch, [])) for row in epochs]


@router.get("/epochs/{epoch}/breakdown", response_model=EpochBreakdown)
async def epoch_breakdown(services: ServicesDep, epoch: int = Path(ge=1)) -> EpochBreakdown:
    async with reader(services) as session:
        found = await breakdown(session, epoch)
    if found.current is None:
        raise NotFoundError(NO_STATISTICS)
    return found


@router.get("/stats/epochs", response_model=list[EpochStatistics])
async def epoch_statistics(services: ServicesDep) -> list[EpochStatistics]:
    async with reader(services) as session:
        if await CosmosRepository(session).get() is None:
            return []
        return await series(session)


@router.get("/stats/lore", response_model=LoreTotals)
async def lore_statistics(services: ServicesDep) -> LoreTotals:
    async with reader(services) as session:
        return await lore_totals(session)
