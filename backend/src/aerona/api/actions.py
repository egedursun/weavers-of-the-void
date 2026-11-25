import inspect
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, cast

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, create_model

from aerona.api.access import LEVER_ENDPOINTS
from aerona.api.dependencies import get_services
from aerona.api.schemas.actions import ActionResponse
from aerona.api.views.team import proposal_view, queued_view
from aerona.constants.team import PROPOSED_TEXT, QUEUED_TEXT, REASON_COLUMN_MAX_LENGTH
from aerona.core.act_note import ActNote, noting
from aerona.core.errors import ValidationFailedError
from aerona.services.accounts.guard import ensure_lever_allowed
from aerona.services.container import Services
from aerona.services.player.catalog import ActionSpec, action
from aerona.services.player.scope import ActionOutcome
from aerona.services.team.gate import Admitted, admit

NON_WORD = re.compile(r"[^a-zA-Z0-9]+")
JOB_ID_KEY = "job_id"
REASON_TOO_LONG = "A reason can be at most {limit} characters."


@dataclass(frozen=True)
class Alias:
    method: str
    path: str
    action_id: str
    path_fields: Mapping[str, str] = field(default_factory=dict)
    fixed: Mapping[str, Any] = field(default_factory=dict)
    summary: str | None = None


def camel(text: str) -> str:
    return "".join(part.capitalize() for part in NON_WORD.split(text) if part)


def snake(text: str) -> str:
    return "_".join(part.lower() for part in NON_WORD.split(text) if part)


def body_model(spec: ActionSpec, excluded: set[str], name: str) -> type[BaseModel] | None:
    fields: dict[str, Any] = {}
    for key, info in spec.input_model.model_fields.items():
        if key in excluded:
            continue
        fields[key] = (info.annotation, info)
    if not fields:
        return None
    return create_model(name, __config__=ConfigDict(extra="forbid", str_strip_whitespace=True), **fields)


def optional_body(model: type[BaseModel]) -> bool:
    return all(not info.is_required() for info in model.model_fields.values())


def to_response(outcome: ActionOutcome) -> ActionResponse:
    job_id = outcome.values.get(JOB_ID_KEY)
    return ActionResponse(**outcome.model_dump(), job_id=str(job_id) if job_id is not None else None)


def waiting_response(spec: ActionSpec, admitted: Admitted) -> ActionResponse:
    if admitted.queued is not None:
        return ActionResponse(action=spec.id, message=QUEUED_TEXT, queued=queued_view(admitted.queued))
    if admitted.proposal is not None:
        return ActionResponse(action=spec.id, message=PROPOSED_TEXT, proposal=proposal_view(admitted.proposal))
    raise LookupError(spec.id)


async def run_action(services: Services, spec: ActionSpec, payload: dict[str, Any]) -> Admitted:
    ensure_lever_allowed(spec.id, spec.input_model.model_validate(payload))
    return await admit(services, spec, payload)


def act_note(services: Services, reason: str | None, expected_revision: int | None) -> ActNote:
    text = reason.strip() if reason else None
    if text and len(text) > services.settings.team_reason_max_length:
        raise ValidationFailedError(REASON_TOO_LONG.format(limit=services.settings.team_reason_max_length))
    return ActNote(reason=text or None, expected_revision=expected_revision)


def build_endpoint(
    spec: ActionSpec, model: type[BaseModel] | None, path_fields: Mapping[str, str], fixed: Mapping[str, Any]
) -> Callable[..., Awaitable[ActionResponse]]:
    async def endpoint(**kwargs: Any) -> ActionResponse:
        services: Services = kwargs["services"]
        body: BaseModel | None = kwargs.get("body")
        payload: dict[str, Any] = body.model_dump(exclude_unset=True) if body is not None else {}
        payload.update({target: kwargs[source] for source, target in path_fields.items()})
        payload.update(fixed)
        response: Response = kwargs["response"]
        with noting(act_note(services, kwargs.get("reason"), kwargs.get("expected_revision"))):
            admitted = await run_action(services, spec, payload)
        if admitted.outcome is None:
            response.status_code = status.HTTP_202_ACCEPTED
            return waiting_response(spec, admitted)
        if spec.job is not None:
            response.status_code = status.HTTP_202_ACCEPTED
        return to_response(admitted.outcome)

    parameters = [
        inspect.Parameter("services", inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[Services, Depends(get_services)]),
        inspect.Parameter("response", inspect.Parameter.KEYWORD_ONLY, annotation=Response),
        inspect.Parameter("reason", inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[str | None, Query(max_length=REASON_COLUMN_MAX_LENGTH)], default=None),
        inspect.Parameter("expected_revision", inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[int | None, Query(ge=0)], default=None),
    ]
    for source in path_fields:
        parameters.append(inspect.Parameter(source, inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[int, Path(ge=1)]))
    if model is not None:
        default = Body(default_factory=model) if optional_body(model) else Body()
        parameters.append(inspect.Parameter("body", inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[model, default]))
    cast(Any, endpoint).__signature__ = inspect.Signature(parameters, return_annotation=ActionResponse)
    LEVER_ENDPOINTS[endpoint] = spec.id
    return endpoint


def mount(router: APIRouter, alias: Alias, *, tag: str | None = None) -> None:
    spec = action(alias.action_id)
    excluded = set(alias.path_fields.values()) | set(alias.fixed)
    name = camel(f"{alias.method} {alias.path}") + "Body"
    model = body_model(spec, excluded, name)
    router.add_api_route(
        alias.path,
        build_endpoint(spec, model, alias.path_fields, alias.fixed),
        methods=[alias.method],
        response_model=ActionResponse,
        status_code=status.HTTP_202_ACCEPTED if spec.job is not None else status.HTTP_200_OK,
        name=snake(f"{alias.method} {alias.path}"),
        summary=alias.summary or spec.title,
        tags=[tag] if tag else None,
    )


def mount_all(router: APIRouter, aliases: tuple[Alias, ...], *, tag: str | None = None) -> None:
    for alias in aliases:
        mount(router, alias, tag=tag)


def mount_catalog(router: APIRouter, specs: tuple[ActionSpec, ...], prefix: str) -> None:
    for spec in specs:
        model = create_model(f"{camel(spec.id)}Input", __base__=spec.input_model)
        router.add_api_route(
            f"{prefix}/{spec.id}",
            build_endpoint(spec, model if model.model_fields else None, {}, {}),
            methods=["POST"],
            response_model=ActionResponse,
            status_code=status.HTTP_202_ACCEPTED if spec.job is not None else status.HTTP_200_OK,
            name=snake(f"action {spec.id}"),
            summary=spec.title,
            tags=["actions"],
        )
