from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Path, Query, Response, status

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import Done
from aerona.api.schemas.divine_will_library import (
    DivineWillArtifact,
    DivineWillArtifactDiff,
    DivineWillArtifactPage,
    DivineWillArtifactPatch,
    DivineWillArtifactQuery,
    DivineWillArtifactVersion,
    DivineWillForecast,
    DivineWillPlan,
    DivineWillPlanSteps,
)
from aerona.domain.enums.divine_will import ExportFormat
from aerona.services.divine_will.library import DivineWillLibrary, library_for
from aerona.services.divine_will.plans import PlanDesk
from aerona.tools.divine_will.library_ports import ArtifactPatch, LibraryQuery, PlanView, StepDraft

router = APIRouter(prefix="/divine-will", tags=["divine-will"])

ASCII_NAME = "artifact"


def library(services: ServicesDep) -> DivineWillLibrary:
    return library_for(services, services.application.lore_index)


LibraryDep = Annotated[DivineWillLibrary, Depends(library)]


def plan_of(view: PlanView) -> DivineWillPlan:
    return DivineWillPlan.model_validate(view)


def disposition(filename: str) -> str:
    fallback = "".join(character if character.isascii() and (character.isalnum() or character in "-_.") else "-" for character in filename)
    return f"attachment; filename=\"{fallback or ASCII_NAME}\"; filename*=UTF-8''{quote(filename)}"


@router.get("/artifacts", response_model=DivineWillArtifactPage)
async def list_artifacts(found: LibraryDep, query: Annotated[DivineWillArtifactQuery, Query()]) -> DivineWillArtifactPage:
    wanted = LibraryQuery(
        q=query.q,
        kind=query.kind,
        status=query.status,
        format=query.format,
        language=query.language or None,
        mode=query.mode,
        tag=query.tag or None,
        node_id=query.node_id,
        sort=query.sort,
        offset=query.offset,
        limit=query.limit,
    )
    return DivineWillArtifactPage.model_validate(await found.artifacts.library(wanted))


@router.get("/artifacts/{artifact_id}", response_model=DivineWillArtifact)
async def read_artifact(found: LibraryDep, artifact_id: int = Path(ge=1)) -> DivineWillArtifact:
    return DivineWillArtifact.model_validate(await found.artifacts.read(artifact_id))


@router.get("/artifacts/{artifact_id}/versions/{version}", response_model=DivineWillArtifactVersion)
async def read_artifact_version(found: LibraryDep, artifact_id: int = Path(ge=1), version: int = Path(ge=1)) -> DivineWillArtifactVersion:
    return DivineWillArtifactVersion.model_validate(await found.artifacts.version(artifact_id, version))


@router.get("/artifacts/{artifact_id}/diff", response_model=DivineWillArtifactDiff)
async def diff_artifact(found: LibraryDep, artifact_id: int = Path(ge=1), a: int = Query(ge=1), b: int = Query(ge=1)) -> DivineWillArtifactDiff:
    return DivineWillArtifactDiff.model_validate(await found.artifacts.versions_diff(artifact_id, a, b))


@router.patch("/artifacts/{artifact_id}", response_model=DivineWillArtifact)
async def patch_artifact(found: LibraryDep, body: DivineWillArtifactPatch, artifact_id: int = Path(ge=1)) -> DivineWillArtifact:
    patch = ArtifactPatch(title=body.title, status=body.status, tags=body.tags, kind=body.kind, node_ids=body.node_ids)
    return DivineWillArtifact.model_validate(await found.artifacts.patch(artifact_id, patch))


@router.delete("/artifacts/{artifact_id}", response_model=Done)
async def delete_artifact(found: LibraryDep, artifact_id: int = Path(ge=1)) -> Done:
    await found.artifacts.delete(artifact_id)
    return Done()


@router.get(
    "/artifacts/{artifact_id}/export",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def export_artifact(
    found: LibraryDep,
    export: Annotated[ExportFormat, Query(alias="format")],
    artifact_id: Annotated[int, Path(ge=1)],
    version: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    exported = await found.artifacts.export(artifact_id, export, version)
    headers = {"content-disposition": disposition(exported.filename), "x-content-type-options": "nosniff"}
    return Response(content=exported.content, media_type=exported.media_type, headers=headers)


def plans(found: LibraryDep) -> PlanDesk:
    return found.plans


PlansDep = Annotated[PlanDesk, Depends(plans)]


@router.get("/plans/{plan_id}", response_model=DivineWillPlan)
async def read_plan(desk: PlansDep, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.read(plan_id))


@router.put("/plans/{plan_id}/steps", response_model=DivineWillPlan)
async def revise_plan(desk: PlansDep, body: DivineWillPlanSteps, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    steps = [StepDraft.model_validate(step.model_dump()) for step in body.steps]
    return plan_of(await desk.revise(plan_id, steps, title=body.title))


@router.post("/plans/{plan_id}/approve", response_model=DivineWillPlan)
async def approve_plan(desk: PlansDep, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.approve(plan_id))


@router.post("/plans/{plan_id}/execute", response_model=DivineWillPlan, status_code=status.HTTP_202_ACCEPTED)
async def execute_plan(desk: PlansDep, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.execute(plan_id))


@router.post("/plans/{plan_id}/pause", response_model=DivineWillPlan)
async def pause_plan(desk: PlansDep, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.pause(plan_id))


@router.post("/plans/{plan_id}/resume", response_model=DivineWillPlan, status_code=status.HTTP_202_ACCEPTED)
async def resume_plan(desk: PlansDep, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.resume(plan_id))


@router.post("/plans/{plan_id}/abandon", response_model=DivineWillPlan)
async def abandon_plan(desk: PlansDep, plan_id: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.abandon(plan_id))


@router.post("/plans/{plan_id}/steps/{ordinal}/skip", response_model=DivineWillPlan)
async def skip_step(desk: PlansDep, plan_id: int = Path(ge=1), ordinal: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.skip(plan_id, ordinal))


@router.post("/plans/{plan_id}/steps/{ordinal}/undo", response_model=DivineWillPlan)
async def undo_step(desk: PlansDep, plan_id: int = Path(ge=1), ordinal: int = Path(ge=1)) -> DivineWillPlan:
    return plan_of(await desk.undo(plan_id, ordinal))


@router.get("/forecasts/{forecast_id}", response_model=DivineWillForecast)
async def read_forecast(found: LibraryDep, forecast_id: int = Path(ge=1)) -> DivineWillForecast:
    return DivineWillForecast.model_validate(await found.foresight.read(forecast_id))


@router.post("/forecasts/{forecast_id}/cancel", response_model=DivineWillForecast)
async def cancel_forecast(found: LibraryDep, forecast_id: int = Path(ge=1)) -> DivineWillForecast:
    return DivineWillForecast.model_validate(await found.foresight.cancel(forecast_id))
