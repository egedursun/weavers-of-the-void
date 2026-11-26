from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from aerona.catalog.providers import PROVIDERS, ROLE_LABELS, TEAM_SUBSCRIPTION_REASON, is_subscription, serves
from aerona.constants.providers import CONNECTION_LABEL_MAX_LENGTH
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.domain.enums.providers import ModelRole, ProviderFamily, ProviderKind
from aerona.llm.errors import LlmError
from aerona.services.providers.checks import check_model
from aerona.services.providers.directory import ProviderDirectory, Scope
from aerona.services.providers.login import LoginRun, LoginRunner, forget_login
from aerona.services.providers.pool import BackendPool
from aerona.services.providers.records import ChainEntry, Connection
from aerona.services.providers.secrets import SecretBox, hint_of
from aerona.services.providers.store import ChainLink, CheckResult, NewConnection, ProviderStore

NOT_HERE = "That connection does not belong to this workspace."
NOT_A_SUBSCRIPTION = "Only a subscription is logged in to."
CANNOT_SERVE = "{label} cannot serve {role}."
NAME_A_MODEL = "Name the model to use."
NAME_THE_CONNECTION = "Give the connection a name."
GIVE_A_KEY = "Paste the key of this provider."
GIVE_AN_ADDRESS = "Give the address of the server, starting with http:// or https://."
SAME_ENTRY = "The same model of the same connection is listed twice."
WEB_SCHEMES = frozenset({"http", "https"})


@dataclass(frozen=True)
class ProviderScope:
    workspace_id: int | None
    personal: bool

    @property
    def key(self) -> Scope:
        return self.workspace_id


def valid_address(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in WEB_SCHEMES and bool(parsed.netloc)


def subscription_refusal(scope: ProviderScope, kind: ProviderKind) -> str | None:
    return TEAM_SUBSCRIPTION_REASON if is_subscription(kind) and not scope.personal else None


class ProviderService:
    def __init__(self, store: ProviderStore, directory: ProviderDirectory, pool: BackendPool, box: SecretBox, logins: LoginRunner) -> None:
        self.store = store
        self.directory = directory
        self.pool = pool
        self.box = box
        self.logins = logins

    def connection_in(self, scope: ProviderScope, connection_id: int) -> Connection:
        connection = self.directory.connection(connection_id)
        if connection is None or connection.workspace_id != scope.key:
            raise NotFoundError(NOT_HERE)
        return connection

    def usable_in(self, scope: ProviderScope, connection_id: int) -> Connection:
        connection = self.directory.connection(connection_id)
        if connection is None or connection.workspace_id not in {scope.key, None}:
            raise NotFoundError(NOT_HERE)
        return connection

    async def add(self, scope: ProviderScope, kind: ProviderKind, *, label: str, secret: str, base_url: str, actor_id: int | None) -> Connection:
        refusal = subscription_refusal(scope, kind)
        if refusal is not None:
            raise ConflictError(refusal)
        spec = PROVIDERS[kind]
        name = self._label(label or spec.label)
        secret = secret.strip()
        base_url = base_url.strip()
        if spec.family is ProviderFamily.API and not secret:
            raise ValidationFailedError(GIVE_A_KEY)
        if spec.asks_address and not valid_address(base_url):
            raise ValidationFailedError(GIVE_AN_ADDRESS)
        connection_id = await self.store.add_connection(
            NewConnection(scope.key, kind, name, self.box.seal(secret), hint_of(secret), base_url, actor_id, datetime.now(UTC))
        )
        await self.directory.refresh()
        return self.connection_in(scope, connection_id)

    async def edit(self, scope: ProviderScope, connection_id: int, *, label: str | None, secret: str | None, base_url: str | None) -> Connection:
        connection = self.connection_in(scope, connection_id)
        spec = connection.spec
        if base_url is not None and spec.asks_address and not valid_address(base_url.strip()):
            raise ValidationFailedError(GIVE_AN_ADDRESS)
        sealed = (self.box.seal(secret.strip()), hint_of(secret.strip())) if secret is not None and spec.asks_key else None
        await self.store.edit_connection(
            connection_id,
            label=self._label(label) if label is not None else None,
            secret=sealed,
            base_url=base_url.strip() if base_url is not None and spec.asks_address else None,
        )
        await self._changed(connection_id)
        return self.connection_in(scope, connection_id)

    async def remove(self, scope: ProviderScope, connection_id: int) -> None:
        connection = self.connection_in(scope, connection_id)
        await self.logins.cancel(connection_id)
        await self.store.remove_connection(connection_id)
        forget_login(connection.home)
        await self._changed(connection_id)

    async def set_chain(self, scope: ProviderScope, role: ModelRole, links: Sequence[ChainLink]) -> tuple[ChainEntry, ...]:
        seen: set[tuple[int, str]] = set()
        cleaned: list[ChainLink] = []
        for link in links:
            connection = self.usable_in(scope, link.connection_id)
            refusal = subscription_refusal(scope, connection.kind)
            if refusal is not None:
                raise ConflictError(refusal)
            if not serves(connection.kind, role):
                raise ValidationFailedError(CANNOT_SERVE.format(label=connection.spec.label, role=ROLE_LABELS[role].lower()))
            model = link.model.strip()
            if not model and connection.kind is not ProviderKind.IMAGE_WORKER:
                raise ValidationFailedError(NAME_A_MODEL)
            if (connection.id, model) in seen:
                raise ValidationFailedError(SAME_ENTRY)
            seen.add((connection.id, model))
            cleaned.append(ChainLink(connection.id, model))
        await self.store.replace_chain(scope.key, role, cleaned)
        await self.directory.refresh()
        return self.directory.own_chain(scope.key, role)

    async def check(self, scope: ProviderScope, role: ModelRole) -> tuple[ChainEntry, ...]:
        for entry in self.directory.own_chain(scope.key, role):
            await self.store.record_check(entry.id, await self._check(entry))
        await self.directory.refresh()
        return self.directory.own_chain(scope.key, role)

    async def models(self, scope: ProviderScope, connection_id: int) -> list[str]:
        connection = self.usable_in(scope, connection_id)
        if connection.kind is ProviderKind.IMAGE_WORKER:
            return []
        try:
            return await (await self.pool.text(connection)).models()
        except LlmError as error:
            raise ConflictError(str(error)) from error

    async def log_in(self, scope: ProviderScope, connection_id: int) -> LoginRun:
        connection = self.connection_in(scope, connection_id)
        spec = connection.spec
        refusal = subscription_refusal(scope, connection.kind)
        if refusal is not None:
            raise ConflictError(refusal)
        if spec.agent is None:
            raise ConflictError(NOT_A_SUBSCRIPTION)
        return await self.logins.start(connection, spec.agent.login, spec.agent.files)

    def login_of(self, scope: ProviderScope, connection_id: int) -> LoginRun | None:
        self.connection_in(scope, connection_id)
        return self.logins.view(connection_id)

    async def answer_login(self, scope: ProviderScope, connection_id: int, text: str) -> LoginRun | None:
        self.connection_in(scope, connection_id)
        return await self.logins.send(connection_id, text)

    async def stop_login(self, scope: ProviderScope, connection_id: int) -> None:
        self.connection_in(scope, connection_id)
        await self.logins.cancel(connection_id)

    async def log_out(self, scope: ProviderScope, connection_id: int) -> Connection:
        connection = self.connection_in(scope, connection_id)
        await self.logins.cancel(connection_id)
        await self.store.mark_login(connection_id, None)
        if connection.spec.agent is not None and connection.spec.agent.secret_variable:
            await self.store.edit_connection(connection_id, secret=("", ""))
        forget_login(connection.home)
        await self._changed(connection_id)
        return self.connection_in(scope, connection_id)

    async def logged_in(self, connection_id: int, secret: str) -> None:
        if secret:
            await self.store.edit_connection(connection_id, secret=(self.box.seal(secret), hint_of(secret)))
        await self.store.mark_login(connection_id, datetime.now(UTC))
        await self._changed(connection_id)

    async def _check(self, entry: ChainEntry) -> CheckResult:
        now = datetime.now(UTC)
        if entry.role is ModelRole.IMAGES:
            return CheckResult(None, None, "", now)
        try:
            backend = await self.pool.text(entry.connection)
        except LlmError as error:
            return CheckResult(False, None, str(error), now)
        return await check_model(backend, entry.model, entry.role, now)

    async def _changed(self, connection_id: int) -> None:
        await self.pool.forget(connection_id)
        await self.directory.refresh()

    @staticmethod
    def _label(value: str) -> str:
        label = value.strip()[:CONNECTION_LABEL_MAX_LENGTH]
        if not label:
            raise ValidationFailedError(NAME_THE_CONNECTION)
        return label
