from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.meta import HealthStatus
from aerona.services.metrics import HealthReport


class HealthResponse(ApiModel):
    status: HealthStatus
    version: str
    database_ok: bool
    llm_enabled: bool
    gateway_ready: bool
    running_jobs: int


class HealthReportResponse(ApiModel):
    report: HealthReport
