import os
from pathlib import Path

from openai import AsyncOpenAI

from aerona.catalog.providers import HOME, PROVIDERS, AgentSpec
from aerona.constants.llm import TOOL_SERVER_NAME
from aerona.constants.providers import AGENT_PACKAGE_BIN, GATEWAY_DIRECT_KEY_HEADER
from aerona.domain.enums.providers import ProviderFamily, ProviderKind
from aerona.imaging.client import ImageWorkerClient
from aerona.imaging.gateway import GatewayImages
from aerona.imaging.provider import ImageProvider
from aerona.llm.backends.acp import AcpBackend, AgentLaunch
from aerona.llm.backends.base import ModelBackend
from aerona.llm.backends.openai import OpenAIBackend
from aerona.llm.errors import LlmUnavailableError
from aerona.llm.tool_gate import ToolGate
from aerona.services.providers.records import Connection

KEPT_VARIABLES = ("PATH", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "TEMP", "TMP")
QUIET_VARIABLES = {"TERM": "dumb", "NO_BROWSER": "true", "BROWSER": "none", "CI": "true", "NO_COLOR": "1"}
LOCAL_KEY = "local"
NO_GATEWAY = "No gateway is configured for API keys (AERONA_GATEWAY_URL)."
NOT_LOGGED_IN = "This subscription is not logged in yet."
NO_KEY = "This connection has no key."
NO_ADDRESS = "This connection has no address."


def with_version(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    return stripped if stripped.endswith("/v1") else f"{stripped}/v1"


def base_environment(home: Path) -> dict[str, str]:
    environment = {name: os.environ[name] for name in KEPT_VARIABLES if name in os.environ}
    environment.update(QUIET_VARIABLES)
    environment["HOME"] = str(home)
    return environment


def agent_environment(spec: AgentSpec, home: Path, secret: str) -> dict[str, str]:
    environment = base_environment(home)
    environment.update({name: value.replace(HOME, str(home)) for name, value in spec.environment.items()})
    if spec.secret_variable and secret:
        environment[spec.secret_variable] = secret
    return environment


def agent_launch(spec: AgentSpec, connection: Connection, agents_dir: Path) -> AgentLaunch:
    return AgentLaunch(
        program=agents_dir / AGENT_PACKAGE_BIN / spec.program,
        arguments=tuple(argument.replace("{tool_server}", TOOL_SERVER_NAME) for argument in spec.arguments),
        environment=agent_environment(spec, connection.home, connection.secret),
        home=connection.home,
        files=dict(spec.files),
        auth_method=spec.auth_method,
        session_meta=dict(spec.session_meta),
        session_mode=spec.session_mode,
        marks_messages=spec.marks_messages,
    )


class BackendPool:
    def __init__(self, gateway_url: str, agents_dir: Path, gate: ToolGate) -> None:
        self._gateway_url = gateway_url
        self._agents_dir = agents_dir
        self._gate = gate
        self._text: dict[int, tuple[tuple[object, ...], ModelBackend]] = {}
        self._images: dict[tuple[int, str], tuple[tuple[object, ...], ImageProvider]] = {}

    @property
    def gateway_ready(self) -> bool:
        return bool(self._gateway_url)

    def unusable(self, connection: Connection) -> str | None:
        spec = connection.spec
        if spec.family is ProviderFamily.API and not self._gateway_url:
            return NO_GATEWAY
        if spec.family is ProviderFamily.SUBSCRIPTION and connection.logged_in_at is None:
            return NOT_LOGGED_IN
        if spec.asks_address and not connection.base_url:
            return NO_ADDRESS
        if spec.family is ProviderFamily.API and not connection.secret:
            return NO_KEY
        return None

    async def text(self, connection: Connection) -> ModelBackend:
        reason = self.unusable(connection)
        if reason is not None:
            raise LlmUnavailableError(reason)
        key = connection.same_credential()
        cached = self._text.get(connection.id)
        if cached is not None and cached[0] == key:
            return cached[1]
        if cached is not None:
            await cached[1].close()
        backend = self._build_text(connection)
        self._text[connection.id] = (key, backend)
        return backend

    async def images(self, connection: Connection, model: str) -> ImageProvider:
        reason = self.unusable(connection)
        if reason is not None:
            raise LlmUnavailableError(reason)
        key = connection.same_credential()
        cached = self._images.get((connection.id, model))
        if cached is not None and cached[0] == key:
            return cached[1]
        if cached is not None:
            await cached[1].aclose()
        provider = self._build_images(connection, model)
        self._images[(connection.id, model)] = (key, provider)
        return provider

    async def forget(self, connection_id: int) -> None:
        cached = self._text.pop(connection_id, None)
        if cached is not None:
            await cached[1].close()
        for key in [key for key in self._images if key[0] == connection_id]:
            await self._images.pop(key)[1].aclose()

    async def close(self) -> None:
        for connection_id in {*self._text, *(key[0] for key in self._images)}:
            await self.forget(connection_id)

    def _gateway_client(self, connection: Connection) -> AsyncOpenAI:
        return AsyncOpenAI(base_url=with_version(self._gateway_url), api_key=connection.secret, default_headers={GATEWAY_DIRECT_KEY_HEADER: "true"})

    def _build_text(self, connection: Connection) -> ModelBackend:
        spec = connection.spec
        if spec.agent is not None:
            return AcpBackend(agent_launch(spec.agent, connection, self._agents_dir), self._gate)
        if connection.kind is ProviderKind.LOCAL_SERVER:
            return OpenAIBackend(AsyncOpenAI(base_url=with_version(connection.base_url), api_key=connection.secret or LOCAL_KEY))
        return OpenAIBackend(self._gateway_client(connection), f"{spec.gateway_name}/")

    def _build_images(self, connection: Connection, model: str) -> ImageProvider:
        if connection.kind is ProviderKind.IMAGE_WORKER:
            return ImageWorkerClient(connection.base_url)
        return GatewayImages(self._gateway_client(connection), f"{PROVIDERS[connection.kind].gateway_name}/{model}")
