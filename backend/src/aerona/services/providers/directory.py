from collections import defaultdict
from pathlib import Path

from aerona.domain.enums.providers import ModelRole
from aerona.services.providers.records import ChainEntry, Connection, connection_of, entry_of
from aerona.services.providers.secrets import SecretBox
from aerona.services.providers.store import ProviderStore

Scope = int | None


class ProviderDirectory:
    def __init__(self, store: ProviderStore, box: SecretBox, homes: Path) -> None:
        self._store = store
        self._box = box
        self._homes = homes
        self._connections: dict[int, Connection] = {}
        self._chains: dict[tuple[Scope, ModelRole], tuple[ChainEntry, ...]] = {}
        self._workspaces: dict[str, int | None] = {}

    def home_of(self, connection_id: int) -> Path:
        return self._homes / str(connection_id)

    async def refresh(self) -> None:
        connections = {row.id: connection_of(row, self._box.open(row.secret), self.home_of(row.id)) for row in await self._store.connections()}
        chains: defaultdict[tuple[Scope, ModelRole], list[ChainEntry]] = defaultdict(list)
        for row in await self._store.entries():
            connection = connections.get(row.connection_id)
            if connection is not None:
                chains[(row.workspace_id, row.role)].append(entry_of(row, connection))
        self._connections = connections
        self._chains = {key: tuple(entries) for key, entries in chains.items()}
        self._workspaces = await self._store.universe_workspaces()

    def place(self, universe_id: str, workspace_id: int | None) -> None:
        self._workspaces[universe_id] = workspace_id

    def workspace_of(self, universe_id: str) -> int | None:
        return self._workspaces.get(universe_id)

    def connection(self, connection_id: int) -> Connection | None:
        return self._connections.get(connection_id)

    def connections(self, scope: Scope) -> tuple[Connection, ...]:
        return tuple(connection for connection in self._connections.values() if connection.workspace_id == scope)

    def own_chain(self, scope: Scope, role: ModelRole) -> tuple[ChainEntry, ...]:
        return self._chains.get((scope, role), ())

    def chain_for_workspace(self, workspace_id: int | None, role: ModelRole) -> tuple[ChainEntry, ...]:
        own = self.own_chain(workspace_id, role) if workspace_id is not None else ()
        return own or self.own_chain(None, role)

    def chain(self, universe_id: str, role: ModelRole) -> tuple[ChainEntry, ...]:
        return self.chain_for_workspace(self.workspace_of(universe_id), role)

    def ready(self, universe_id: str, role: ModelRole) -> bool:
        return any(entry.usable for entry in self.chain(universe_id, role))

    def anything(self) -> bool:
        return bool(self._connections)
