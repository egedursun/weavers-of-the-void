from fastapi import APIRouter, Path

from aerona.api import provider_views as views
from aerona.api.dependencies import AccountsDep, ProvidersDep, SignedDep
from aerona.api.schemas.common import Done
from aerona.api.schemas.providers import (
    ChainPut,
    ConnectionCreate,
    ConnectionEdit,
    LoginInput,
    ModelRoleView,
    ProviderConnectionView,
    ProviderLoginView,
    ProviderModels,
    ProvidersView,
)
from aerona.core.errors import NotFoundError
from aerona.domain.enums.accounts import WorkspaceKind, WorkspaceRole
from aerona.domain.enums.providers import ModelRole
from aerona.services.accounts.service import AccountService
from aerona.services.providers.service import ProviderScope

router = APIRouter(prefix="/workspaces/{workspace_id}/providers", tags=["providers"])

WorkspaceId = Path(ge=1)
ConnectionId = Path(ge=1)
NO_WORKSPACE = "No such workspace."


async def scope_of(accounts: AccountService, workspace_id: int) -> ProviderScope:
    workspace = await accounts.store.workspace(workspace_id)
    if workspace is None:
        raise NotFoundError(NO_WORKSPACE)
    return ProviderScope(workspace.id, workspace.kind is WorkspaceKind.PERSONAL)


@router.get("", response_model=ProvidersView)
async def read_providers(signed: SignedDep, accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId) -> ProvidersView:
    role = await accounts.role_in(workspace_id, signed.account.id)
    return views.providers_view(providers, await scope_of(accounts, workspace_id), editable=role is WorkspaceRole.ADMIN)


@router.post("/connections", response_model=ProviderConnectionView, status_code=201)
async def add_connection(
    body: ConnectionCreate, signed: SignedDep, accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId
) -> ProviderConnectionView:
    return await views.create(providers, await scope_of(accounts, workspace_id), body, signed.account.id)


@router.patch("/connections/{connection_id}", response_model=ProviderConnectionView)
async def edit_connection(
    body: ConnectionEdit, accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId
) -> ProviderConnectionView:
    return await views.edit(providers, await scope_of(accounts, workspace_id), connection_id, body)


@router.delete("/connections/{connection_id}", response_model=Done)
async def remove_connection(accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId) -> Done:
    return await views.remove(providers, await scope_of(accounts, workspace_id), connection_id)


@router.get("/connections/{connection_id}/models", response_model=ProviderModels)
async def connection_models(
    accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId, role: ModelRole | None = None
) -> ProviderModels:
    return ProviderModels(models=await providers.service.models(await scope_of(accounts, workspace_id), connection_id, role))


@router.post("/connections/{connection_id}/login", response_model=ProviderLoginView)
async def start_login(accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId) -> ProviderLoginView:
    return views.login_view(await providers.service.log_in(await scope_of(accounts, workspace_id), connection_id))


@router.get("/connections/{connection_id}/login", response_model=ProviderLoginView)
async def read_login(accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId) -> ProviderLoginView:
    return views.login_view(providers.service.login_of(await scope_of(accounts, workspace_id), connection_id))


@router.post("/connections/{connection_id}/login/input", response_model=ProviderLoginView)
async def answer_login(
    body: LoginInput, accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId
) -> ProviderLoginView:
    return views.login_view(await providers.service.answer_login(await scope_of(accounts, workspace_id), connection_id, body.text))


@router.delete("/connections/{connection_id}/login", response_model=Done)
async def stop_login(accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId) -> Done:
    return await views.stop_login(providers, await scope_of(accounts, workspace_id), connection_id)


@router.post("/connections/{connection_id}/logout", response_model=ProviderConnectionView)
async def log_out(accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId, connection_id: int = ConnectionId) -> ProviderConnectionView:
    return await views.log_out(providers, await scope_of(accounts, workspace_id), connection_id)


@router.put("/roles/{role}", response_model=ModelRoleView)
async def set_chain(body: ChainPut, role: ModelRole, accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId) -> ModelRoleView:
    return await views.set_chain(providers, await scope_of(accounts, workspace_id), role, body)


@router.post("/roles/{role}/check", response_model=ModelRoleView)
async def check_chain(role: ModelRole, accounts: AccountsDep, providers: ProvidersDep, workspace_id: int = WorkspaceId) -> ModelRoleView:
    return await views.check(providers, await scope_of(accounts, workspace_id), role)
