from datetime import datetime

from fastapi import APIRouter, Query

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus
from aerona.services.metrics import EpochMetrics, ModelMetrics, StepMetrics, Totals

router = APIRouter(tags=["metrics"])


class LlmCall(ApiModel):
    id: int
    epoch: int | None
    job: str
    role: str | None
    model: str
    kind: LlmCallKind
    status: LlmCallStatus
    duration_ms: int
    attempts: int
    turns: int | None
    input_tokens: int
    output_tokens: int
    error: str | None
    created_at: datetime


class ModelMetricsView(ApiModel):
    totals: Totals
    epochs: list[EpochMetrics]
    models: list[ModelMetrics]
    steps: list[StepMetrics]
    slowest: list[LlmCall]
    latest_errors: list[LlmCall]
    slow_threshold_ms: int


@router.get("/metrics/models", response_model=ModelMetricsView)
async def model_metrics(services: ServicesDep, epochs: int | None = Query(default=None, ge=1)) -> ModelMetricsView:
    server = services.rules.current.server
    window = min(epochs or server.metrics_default_epochs, server.metrics_max_epochs)
    summary = await services.application.metrics.summary(window)
    return ModelMetricsView(
        totals=summary.totals,
        epochs=summary.epochs,
        models=summary.models,
        steps=summary.steps,
        slowest=[LlmCall.model_validate(row) for row in summary.slowest],
        latest_errors=[LlmCall.model_validate(row) for row in summary.latest_errors],
        slow_threshold_ms=summary.slow_threshold_ms,
    )
