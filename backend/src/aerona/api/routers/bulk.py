from fastapi import APIRouter, status

from aerona.api.background import require_llm
from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import JobAccepted
from aerona.services.bulk_deepen import BulkState, BulkStatus

router = APIRouter(tags=["bulk"])


@router.get("/batch-deepen", response_model=BulkStatus)
async def batch_status(services: ServicesDep) -> BulkStatus:
    return await services.application.bulk_deepen.status()


@router.post("/batch-deepen/start", response_model=BulkState)
async def start_batch(services: ServicesDep) -> BulkState:
    require_llm(services, "Batch deepening")
    return await services.application.bulk_deepen.start()


@router.post("/batch-deepen/stop", response_model=BulkState)
async def stop_batch(services: ServicesDep) -> BulkState:
    return services.application.bulk_deepen.stop()


@router.post("/names/assign-missing", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def assign_missing_names(services: ServicesDep) -> JobAccepted:
    require_llm(services, "Naming records")
    return JobAccepted(job_id=await services.orchestrator.submit_naming())
