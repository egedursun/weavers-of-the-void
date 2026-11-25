from fastapi import APIRouter

from aerona.api.actions import Alias, mount_catalog
from aerona.api.dependencies import ServicesDep
from aerona.api.routers import chronicle, cosmos, creator, entities, foreign_gods, goals, languages, map, notes, player, prayers, relations, settings, sons
from aerona.api.schemas.actions import ActionCatalogueItem
from aerona.constants.http import API_PREFIX
from aerona.services.accounts.lever_holds import LEVER_HOLD_FIELDS
from aerona.services.accounts.permissions import lever_permission
from aerona.services.player.catalog import ACTIONS, describe

router = APIRouter(tags=["actions"])

ACTIONS_PATH = "/actions"
TYPED_ALIASES: tuple[Alias, ...] = (
    *chronicle.ALIASES,
    *cosmos.ALIASES,
    *creator.ALIASES,
    *entities.ALIASES,
    *foreign_gods.ALIASES,
    *goals.ALIASES,
    *languages.ALIASES,
    *map.ALIASES,
    *player.ALIASES,
    *prayers.ALIASES,
    *relations.ALIASES,
    *settings.ALIASES,
    *sons.ALIASES,
    *notes.ALIASES,
)
TYPED_ROUTES: dict[str, Alias] = {}
for alias in TYPED_ALIASES:
    TYPED_ROUTES.setdefault(alias.action_id, alias)
GENERIC_ACTIONS = tuple(spec for spec in ACTIONS if spec.id not in TYPED_ROUTES)


def action_path(action_id: str) -> str:
    alias = TYPED_ROUTES.get(action_id)
    return f"{API_PREFIX}{alias.path}" if alias is not None else f"{API_PREFIX}{ACTIONS_PATH}/{action_id}"


def action_method(action_id: str) -> str:
    alias = TYPED_ROUTES.get(action_id)
    return alias.method if alias is not None else "POST"


@router.get(ACTIONS_PATH, response_model=list[ActionCatalogueItem])
async def list_actions(services: ServicesDep) -> list[ActionCatalogueItem]:
    return [
        ActionCatalogueItem(
            **descriptor.model_dump(),
            path=action_path(descriptor.id),
            method=action_method(descriptor.id),
            permission=lever_permission(descriptor.id),
            hold_fields=list(LEVER_HOLD_FIELDS.get(descriptor.id, ())),
        )
        for descriptor in describe(services.rules.current)
    ]


mount_catalog(router, GENERIC_ACTIONS, ACTIONS_PATH)
