from aerona.api.schemas.common import Done
from aerona.api.schemas.providers import (
    ChainEntryView,
    ChainPut,
    ConnectionCreate,
    ConnectionEdit,
    ModelRoleView,
    ProviderConnectionView,
    ProviderKindView,
    ProviderLoginView,
    ProvidersView,
)
from aerona.catalog.providers import PROVIDERS, ROLE_DESCRIPTIONS, ROLE_LABELS, SUBSCRIPTION_TERMS, is_subscription
from aerona.core.errors import NotFoundError
from aerona.domain.enums.providers import ModelRole, ProviderKind
from aerona.services.providers.hub import Providers
from aerona.services.providers.login import LoginRun
from aerona.services.providers.records import ChainEntry, Connection
from aerona.services.providers.service import ProviderScope, subscription_refusal
from aerona.services.providers.store import ChainLink

NO_LOGIN = "No login has been started for this connection."
REMOVED = "The connection is removed."
STOPPED = "The login is stopped."


def kind_view(scope: ProviderScope, kind: ProviderKind) -> ProviderKindView:
    spec = PROVIDERS[kind]
    return ProviderKindView(
        kind=kind,
        label=spec.label,
        family=spec.family,
        roles=sorted(spec.roles, key=list(ModelRole).index),
        asks_key=spec.asks_key,
        asks_address=spec.asks_address,
        key_page=spec.key_page,
        terms=SUBSCRIPTION_TERMS if is_subscription(kind) else None,
        refusal=subscription_refusal(scope, kind),
    )


def connection_view(providers: Providers, scope: ProviderScope, connection: Connection) -> ProviderConnectionView:
    return ProviderConnectionView(
        id=connection.id,
        kind=connection.kind,
        label=connection.label,
        secret_hint=connection.secret_hint,
        base_url=connection.base_url,
        logged_in_at=connection.logged_in_at,
        created_at=connection.created_at,
        unusable=providers.pool.unusable(connection),
        from_server=connection.workspace_id != scope.key,
    )


def entry_view(entry: ChainEntry) -> ChainEntryView:
    return ChainEntryView(
        id=entry.id,
        connection_id=entry.connection.id,
        model=entry.model,
        tools_work=entry.tools_work,
        sees_images=entry.sees_images,
        checked_at=entry.checked_at,
        check_note=entry.check_note,
    )


def role_view(providers: Providers, scope: ProviderScope, role: ModelRole) -> ModelRoleView:
    directory = providers.directory
    inherited = directory.own_chain(None, role) if scope.key is not None else ()
    return ModelRoleView(
        role=role,
        label=ROLE_LABELS[role],
        description=ROLE_DESCRIPTIONS[role],
        entries=[entry_view(entry) for entry in directory.own_chain(scope.key, role)],
        server_entries=[entry_view(entry) for entry in inherited],
    )


def providers_view(providers: Providers, scope: ProviderScope, *, editable: bool) -> ProvidersView:
    directory = providers.directory
    shown = directory.connections(scope.key) + (directory.connections(None) if scope.key is not None else ())
    return ProvidersView(
        workspace_id=scope.key,
        personal=scope.personal,
        editable=editable,
        gateway_ready=providers.pool.gateway_ready,
        kinds=[kind_view(scope, kind) for kind in ProviderKind],
        connections=[connection_view(providers, scope, connection) for connection in shown],
        roles=[role_view(providers, scope, role) for role in ModelRole],
    )


def login_view(run: LoginRun | None) -> ProviderLoginView:
    if run is None:
        raise NotFoundError(NO_LOGIN)
    return ProviderLoginView(
        state=run.state, output=run.output, links=run.links, code=run.code, note=run.note, started_at=run.started_at, ended_at=run.ended_at
    )


async def create(providers: Providers, scope: ProviderScope, body: ConnectionCreate, actor_id: int | None) -> ProviderConnectionView:
    connection = await providers.service.add(scope, body.kind, label=body.label, secret=body.secret, base_url=body.base_url, actor_id=actor_id)
    return connection_view(providers, scope, connection)


async def edit(providers: Providers, scope: ProviderScope, connection_id: int, body: ConnectionEdit) -> ProviderConnectionView:
    connection = await providers.service.edit(scope, connection_id, label=body.label, secret=body.secret, base_url=body.base_url)
    return connection_view(providers, scope, connection)


async def remove(providers: Providers, scope: ProviderScope, connection_id: int) -> Done:
    await providers.service.remove(scope, connection_id)
    return Done(message=REMOVED)


async def log_out(providers: Providers, scope: ProviderScope, connection_id: int) -> ProviderConnectionView:
    return connection_view(providers, scope, await providers.service.log_out(scope, connection_id))


async def stop_login(providers: Providers, scope: ProviderScope, connection_id: int) -> Done:
    await providers.service.stop_login(scope, connection_id)
    return Done(message=STOPPED)


async def set_chain(providers: Providers, scope: ProviderScope, role: ModelRole, body: ChainPut) -> ModelRoleView:
    await providers.service.set_chain(scope, role, [ChainLink(link.connection_id, link.model) for link in body.entries])
    return role_view(providers, scope, role)


async def check(providers: Providers, scope: ProviderScope, role: ModelRole) -> ModelRoleView:
    await providers.service.check(scope, role)
    return role_view(providers, scope, role)
