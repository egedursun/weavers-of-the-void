import inspect
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, cast

from fastapi import APIRouter, Body, Depends, Path, Response, status
from pydantic import BaseModel, ConfigDict, create_model

from aerona.api.dependencies import get_services, world_rules
from aerona.api.schemas.actions import ActionResponse
from aerona.services.container import Services
from aerona.services.player.catalog import ActionSpec, action
from aerona.services.player.scope import ActionOutcome

NON_WORD = re.compile(r"[^a-zA-Z0-9]+")
JOB_ID_KEY = "job_id"


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


async def run_action(services: Services, spec: ActionSpec, payload: dict[str, Any]) -> ActionOutcome:
    command = spec.input_model.model_validate(payload)
    if spec.sync is not None:
        async with services.database.write() as session:
            rules = await world_rules(services, session)
            return await spec.sync(services.player.scope(session, rules), command)
    if spec.job is None:
        raise LookupError(spec.id)
    async with services.database.read() as session:
        rules = await world_rules(services, session)
    return await spec.job(services.player, rules, command)


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
        if spec.job is not None:
            response.status_code = status.HTTP_202_ACCEPTED
        return to_response(await run_action(services, spec, payload))

    parameters = [
        inspect.Parameter("services", inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[Services, Depends(get_services)]),
        inspect.Parameter("response", inspect.Parameter.KEYWORD_ONLY, annotation=Response),
    ]
    for source in path_fields:
        parameters.append(inspect.Parameter(source, inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[int, Path(ge=1)]))
    if model is not None:
        default = Body(default_factory=model) if optional_body(model) else Body()
        parameters.append(inspect.Parameter("body", inspect.Parameter.KEYWORD_ONLY, annotation=Annotated[model, default]))
    cast(Any, endpoint).__signature__ = inspect.Signature(parameters, return_annotation=ActionResponse)
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
