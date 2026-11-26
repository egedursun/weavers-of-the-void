from fastapi import APIRouter, Path

from aerona.api import provider_views as views
from aerona.api.dependencies import ProvidersDep, SignedDep
from aerona.api.schemas.common import Done
from aerona.api.schemas.providers import (
    ChainPut,
    ConnectionCreate,
    ConnectionEdit,
    ModelRoleView,
    ProviderConnectionView,
    ProviderModels,
    ProvidersView,
)
from aerona.domain.enums.providers import ModelRole
from aerona.services.providers.service import ProviderScope

router = APIRouter(prefix="/server/providers", tags=["providers"])

ConnectionId = Path(ge=1)
SERVER = ProviderScope(None, personal=False)


@router.get("", response_model=ProvidersView)
async def read_server_providers(providers: ProvidersDep) -> ProvidersView:
    return views.providers_view(providers, SERVER, editable=True)


@router.post("/connections", response_model=ProviderConnectionView, status_code=201)
async def add_server_connection(body: ConnectionCreate, signed: SignedDep, providers: ProvidersDep) -> ProviderConnectionView:
    return await views.create(providers, SERVER, body, signed.account.id)


@router.patch("/connections/{connection_id}", response_model=ProviderConnectionView)
async def edit_server_connection(body: ConnectionEdit, providers: ProvidersDep, connection_id: int = ConnectionId) -> ProviderConnectionView:
    return await views.edit(providers, SERVER, connection_id, body)


@router.delete("/connections/{connection_id}", response_model=Done)
async def remove_server_connection(providers: ProvidersDep, connection_id: int = ConnectionId) -> Done:
    return await views.remove(providers, SERVER, connection_id)


@router.get("/connections/{connection_id}/models", response_model=ProviderModels)
async def server_connection_models(providers: ProvidersDep, connection_id: int = ConnectionId) -> ProviderModels:
    return ProviderModels(models=await providers.service.models(SERVER, connection_id))


@router.put("/roles/{role}", response_model=ModelRoleView)
async def set_server_chain(body: ChainPut, role: ModelRole, providers: ProvidersDep) -> ModelRoleView:
    return await views.set_chain(providers, SERVER, role, body)


@router.post("/roles/{role}/check", response_model=ModelRoleView)
async def check_server_chain(role: ModelRole, providers: ProvidersDep) -> ModelRoleView:
    return await views.check(providers, SERVER, role)
