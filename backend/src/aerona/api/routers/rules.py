from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.rules import RuleBatchRequest, RuleResponse, RuleUpdateRequest, RuleValuesResponse
from aerona.api.schemas.team import QueuedActView
from aerona.api.views.team import queued_view
from aerona.constants.http import RULES_PATH
from aerona.core.act_note import current_note
from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.team import QueuedActSource
from aerona.rules.model import RuleDescriptor
from aerona.services.container import Services
from aerona.services.rule_changes import rule_desk
from aerona.services.rules import RULE_KEY_SEPARATOR, rules_title
from aerona.services.team.execute import world_busy
from aerona.services.team.queue import QueueDraft, enqueue

KEY_SEPARATOR = RULE_KEY_SEPARATOR
RULES_ACTION = "rules:change"
QUEUED_RESPONSES: dict[int | str, dict[str, Any]] = {202: {"model": QueuedActView}}

router = APIRouter(prefix=RULES_PATH, tags=["rules"])


def to_response(descriptor: RuleDescriptor) -> RuleResponse:
    return RuleResponse(
        namespace=descriptor.namespace,
        key=descriptor.key,
        value=descriptor.value,
        default=descriptor.default,
        minimum=descriptor.minimum,
        maximum=descriptor.maximum,
        group=descriptor.group,
        label=descriptor.label,
        integer=isinstance(descriptor.default, int),
        warning=descriptor.warning,
    )


@router.get("", response_model=list[RuleResponse])
async def list_rules(services: ServicesDep) -> list[RuleResponse]:
    return [to_response(item) for item in services.rules.catalog()]


@router.get("/values", response_model=RuleValuesResponse)
async def rule_values(services: ServicesDep) -> RuleValuesResponse:
    return RuleValuesResponse(values={f"{item.namespace}{KEY_SEPARATOR}{item.key}": item.value for item in services.rules.catalog()})


async def queued_rules(services: Services, changes: dict[str, float | None], *, reset_all: bool = False) -> JSONResponse | None:
    if not world_busy(services):
        return None
    title = rules_title(services.rules.current, list(changes), reset_all=reset_all)
    payload: dict[str, Any] = {"changes": changes, "reset_all": reset_all}
    queued = await enqueue(services, QueueDraft(QueuedActSource.RULES, RULES_ACTION, title, payload, current_note().reason))
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=queued_view(queued).model_dump(mode="json"))


@router.put("/{namespace}/{key}", response_model=RuleResponse, responses=QUEUED_RESPONSES)
async def update_rule(namespace: str, key: str, request: RuleUpdateRequest, services: ServicesDep) -> RuleResponse | JSONResponse:
    waiting = await queued_rules(services, {f"{namespace}{KEY_SEPARATOR}{key}": request.value})
    if waiting is not None:
        return waiting
    return to_response(await rule_desk(services).change(namespace, key, request.value))


@router.delete("/{namespace}/{key}", response_model=RuleResponse, responses=QUEUED_RESPONSES)
async def reset_rule(namespace: str, key: str, services: ServicesDep) -> RuleResponse | JSONResponse:
    waiting = await queued_rules(services, {f"{namespace}{KEY_SEPARATOR}{key}": None})
    if waiting is not None:
        return waiting
    return to_response(await rule_desk(services).change(namespace, key, None))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_model=None, responses=QUEUED_RESPONSES)
async def reset_all_rules(services: ServicesDep) -> JSONResponse | None:
    waiting = await queued_rules(services, {}, reset_all=True)
    if waiting is not None:
        return waiting
    await services.rules.reset_all()
    await rule_desk(services).settle({})
    return None


@router.patch("", response_model=list[RuleResponse], responses=QUEUED_RESPONSES)
async def update_rules(request: RuleBatchRequest, services: ServicesDep) -> list[RuleResponse] | JSONResponse:
    parsed: list[tuple[str, str, float | None]] = []
    for path, value in request.changes.items():
        namespace, separator, key = path.partition(KEY_SEPARATOR)
        if not separator or not namespace or not key:
            raise ValidationFailedError(f"Unknown rule {path}.")
        parsed.append((namespace, key, value))
    waiting = await queued_rules(services, dict(request.changes), reset_all=request.reset_all)
    if waiting is not None:
        return waiting
    await services.rules.apply_batch(parsed, reset_all=request.reset_all)
    await rule_desk(services).settle({})
    return [to_response(item) for item in services.rules.catalog()]
