from fastapi import APIRouter, status

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.rules import RuleBatchRequest, RuleResponse, RuleUpdateRequest
from aerona.constants.http import RULES_PATH
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.events.kinds import EventKind
from aerona.rules.model import RuleDescriptor
from aerona.services.container import Services

KEY_SEPARATOR = "."

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


async def sync_world(services: Services) -> None:
    if services.application.discovery.active:
        return
    async with services.database.write() as session:
        repository = CosmosRepository(session)
        if await repository.get() is not None:
            await repository.store_rules(services.rules.current)


@router.get("", response_model=list[RuleResponse])
async def list_rules(services: ServicesDep) -> list[RuleResponse]:
    return [to_response(item) for item in services.rules.catalog()]


@router.put("/{namespace}/{key}", response_model=RuleResponse)
async def update_rule(namespace: str, key: str, request: RuleUpdateRequest, services: ServicesDep) -> RuleResponse:
    descriptor = await services.rules.set_value(namespace, key, request.value)
    await sync_world(services)
    services.bus.publish(EventKind.RULES_CHANGED, {"namespace": namespace, "key": key})
    return to_response(descriptor)


@router.delete("/{namespace}/{key}", response_model=RuleResponse)
async def reset_rule(namespace: str, key: str, services: ServicesDep) -> RuleResponse:
    descriptor = await services.rules.reset_value(namespace, key)
    await sync_world(services)
    services.bus.publish(EventKind.RULES_CHANGED, {"namespace": namespace, "key": key})
    return to_response(descriptor)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def reset_all_rules(services: ServicesDep) -> None:
    await services.rules.reset_all()
    await sync_world(services)
    services.bus.publish(EventKind.RULES_CHANGED, {})


@router.patch("", response_model=list[RuleResponse])
async def update_rules(request: RuleBatchRequest, services: ServicesDep) -> list[RuleResponse]:
    parsed: list[tuple[str, str, float | None]] = []
    for path, value in request.changes.items():
        namespace, separator, key = path.partition(KEY_SEPARATOR)
        if not separator or not namespace or not key:
            raise ValidationFailedError(f"Unknown rule {path}.")
        parsed.append((namespace, key, value))
    await services.rules.apply_batch(parsed, reset_all=request.reset_all)
    await sync_world(services)
    services.bus.publish(EventKind.RULES_CHANGED, {})
    return [to_response(item) for item in services.rules.catalog()]
