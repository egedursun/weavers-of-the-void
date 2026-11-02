from aerona.api.schemas.common import ApiModel
from aerona.constants.llm import ClaudeAuth
from aerona.services.metrics import HealthReport


class HealthResponse(ApiModel):
    status: str
    version: str
    database_ok: bool
    llm_enabled: bool
    claude_auth: ClaudeAuth
    image_worker_configured: bool
    running_jobs: int


class HealthReportResponse(ApiModel):
    report: HealthReport
