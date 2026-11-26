import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.access import Access, AccessKind, declared, open_route
from aerona.constants.accounts import SESSION_COOKIE, WORKSPACE_HEADER, WORKSPACE_QUERY
from aerona.constants.api import SAFE_METHODS
from aerona.constants.http import API_PREFIX, HEALTH_PATH, LIBRARY_PATH
from aerona.constants.library import UNIVERSE_HEADER, UNIVERSE_QUERY
from aerona.core.account_scope import CURRENT_ACCOUNT, AccountRef, enter_workspace
from aerona.core.errors import (
    ForbiddenError,
    NotFoundError,
    PasswordChangeRequiredError,
    SetupRequiredError,
    SignedOutError,
    UniverseRequiredError,
    ValidationFailedError,
)
from aerona.core.universe_scope import enter_universe
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.rules.registry import Rules
from aerona.services.accounts.guard import GrantedAccess, enter_grant
from aerona.services.accounts.permissions import lever_permission
from aerona.services.accounts.service import AccountService, Resolved, refuse, refuse_workspace, workspace_allows
from aerona.services.container import Services
from aerona.services.library.hub import CHOOSE_UNIVERSE, UniverseHub
from aerona.services.library.runtime import UniverseRuntime
from aerona.services.providers.hub import Providers

DISCOVERY_END_PATH = "/api/discovery/end"
HEALTH_PREFIX = f"{API_PREFIX}{HEALTH_PATH}"
LIBRARY_PREFIX = f"{API_PREFIX}{LIBRARY_PATH}"


UNDECLARED = "This route has no access declaration."
SETUP_FIRST = "Create the owner account first."
SIGN_IN = "Sign in to continue."
CHANGE_PASSWORD = "Set your own password before going on."
NO_UNIVERSE = "No such universe."
BAD_WORKSPACE = "Choose a workspace."
NOT_IN_WORKSPACE = "This account is not a member of that workspace."
SERVER_ADMINS_ONLY = "Only server administrators can do this."


def get_hub(request: Request) -> UniverseHub:
    hub: UniverseHub = request.app.state.hub
    return hub


HubDep = Annotated[UniverseHub, Depends(get_hub)]


def get_accounts(request: Request) -> AccountService:
    accounts: AccountService = request.app.state.accounts
    return accounts


AccountsDep = Annotated[AccountService, Depends(get_accounts)]


def get_providers(request: Request) -> Providers:
    providers: Providers = request.app.state.providers
    return providers


ProvidersDep = Annotated[Providers, Depends(get_providers)]


def route_access(request: Request) -> Access:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return open_route()
    found = declared(route, request.method, lever_permission)
    if found is None:
        raise ForbiddenError(UNDECLARED)
    return found


def workspace_named(request: Request) -> int | None:
    raw = request.path_params.get("workspace_id") or request.headers.get(WORKSPACE_HEADER) or request.query_params.get(WORKSPACE_QUERY)
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(str(raw).strip())
    except ValueError as error:
        raise ValidationFailedError(BAD_WORKSPACE) from error


async def chosen_workspace(request: Request, accounts: AccountService, signed: Resolved) -> int | None:
    named = workspace_named(request)
    if named is not None:
        return named
    personal = await accounts.store.personal_workspace(signed.account.id)
    return personal.id if personal is not None else None


async def check_workspace(request: Request, accounts: AccountService, signed: Resolved, access: Access) -> None:
    workspace_id = await chosen_workspace(request, accounts, signed)
    if workspace_id is None:
        raise ValidationFailedError(BAD_WORKSPACE)
    role = await accounts.role_in(workspace_id, signed.account.id)
    if role is None:
        raise ForbiddenError(NOT_IN_WORKSPACE)
    if access.workspace_role is not None and not workspace_allows(role, access.workspace_role):
        raise refuse_workspace(role)
    enter_workspace(workspace_id)


async def check_universe(request: Request, accounts: AccountService, hub: UniverseHub, signed: Resolved, access: Access) -> None:
    universe_id = str(request.path_params.get("universe_id") or "") if access.universe_from_path else universe_named(request)
    if not universe_id:
        raise UniverseRequiredError(CHOOSE_UNIVERSE)
    record = await hub.catalogue.get(universe_id)
    if record is None:
        if access.universe_from_path:
            raise NotFoundError(NO_UNIVERSE)
        raise UniverseRequiredError(CHOOSE_UNIVERSE)
    granted = await accounts.universe_access(signed.account.id, record)
    if not granted.visible or (access.universe_admin and not granted.admin):
        raise refuse(None, granted, record.name)
    if access.permission is not None and not granted.allows(access.permission):
        raise refuse(access.permission, granted, record.name)
    enter_workspace(record.workspace_id)
    enter_grant(GrantedAccess(granted, record.name, record.canon_approval))


async def enforce_access(request: Request, accounts: AccountsDep, hub: HubDep) -> Access:
    access = route_access(request)
    token = request.cookies.get(SESSION_COOKIE)
    signed = await accounts.resolve(token) if token and await accounts.ready() else None
    if signed is not None:
        CURRENT_ACCOUNT.set(AccountRef(signed.account.id, signed.account.display_name))
        request.state.signed = signed
    if access.kind is AccessKind.OPEN:
        return access
    if not await accounts.ready():
        raise SetupRequiredError(SETUP_FIRST)
    if signed is None:
        raise SignedOutError(SIGN_IN)
    if signed.account.must_change_password and not access.during_password_change:
        raise PasswordChangeRequiredError(CHANGE_PASSWORD)
    if access.kind is AccessKind.SERVER_ADMIN and not signed.account.server_admin:
        raise ForbiddenError(SERVER_ADMINS_ONLY)
    if access.kind is AccessKind.WORKSPACE:
        await check_workspace(request, accounts, signed, access)
    if access.kind is AccessKind.UNIVERSE:
        await check_universe(request, accounts, hub, signed, access)
    if access.kind in (AccessKind.SIGNED_IN, AccessKind.SERVER_ADMIN):
        workspace_id = await chosen_workspace(request, accounts, signed)
        if workspace_id is not None and await accounts.role_in(workspace_id, signed.account.id) is not None:
            enter_workspace(workspace_id)
    return access


AccessDep = Annotated[Access, Depends(enforce_access)]


def signed_account(request: Request) -> Resolved:
    signed: Resolved | None = getattr(request.state, "signed", None)
    if signed is None:
        raise SignedOutError(SIGN_IN)
    return signed


SignedDep = Annotated[Resolved, Depends(signed_account)]


def universe_named(request: Request) -> str | None:
    named = request.headers.get(UNIVERSE_HEADER) or request.query_params.get(UNIVERSE_QUERY)
    return named.strip() if named and named.strip() else None


def universe_free(path: str) -> bool:
    return path == LIBRARY_PREFIX or path.startswith(f"{LIBRARY_PREFIX}/")


async def bound_runtime(request: Request, hub: HubDep, access: AccessDep) -> AsyncIterator[UniverseRuntime | None]:
    universe_id = universe_named(request)
    if universe_id is None or universe_free(request.url.path) or access.kind is not AccessKind.UNIVERSE or access.universe_from_path:
        yield None
        return
    runtime = await hub.acquire(universe_id)
    enter_universe(universe_id)
    try:
        yield runtime
    finally:
        hub.release(runtime)


RuntimeDep = Annotated[UniverseRuntime | None, Depends(bound_runtime)]


async def get_services(runtime: RuntimeDep) -> Services:
    if runtime is None:
        raise UniverseRequiredError(CHOOSE_UNIVERSE)
    return runtime.services


ServicesDep = Annotated[Services, Depends(get_services)]


async def guard_writes(request: Request, runtime: RuntimeDep) -> None:
    if runtime is None:
        return
    services = runtime.services
    await repairs_finished(request, services)
    if request.method.upper() in SAFE_METHODS or request.url.path == DISCOVERY_END_PATH:
        return
    services.application.discovery.ensure_writable()


async def repairs_finished(request: Request, services: Services) -> None:
    ready = services.application.repairs_ready
    if ready.is_set() or request.url.path.startswith(HEALTH_PREFIX):
        return
    wait = services.rules.current.server.repair_wait_seconds
    if wait:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(ready.wait(), timeout=wait)


@asynccontextmanager
async def reader(services: Services) -> AsyncIterator[AsyncSession]:
    discovery = services.application.discovery
    if discovery.active:
        async with discovery.guest_session() as session:
            yield session
        return
    async with services.database.read() as session:
        yield session


async def world_rules(services: Services, session: AsyncSession) -> Rules:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None or not cosmos.rules_snapshot:
        return services.rules.current
    return rules_from_snapshot(cosmos.rules_snapshot)
