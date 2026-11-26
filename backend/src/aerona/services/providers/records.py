from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from aerona.catalog.providers import PROVIDERS, ProviderSpec
from aerona.db.library.tables import ProviderChainEntryRow, ProviderConnectionRow
from aerona.domain.enums.providers import ModelRole, ProviderFamily, ProviderKind


@dataclass(frozen=True)
class Connection:
    id: int
    workspace_id: int | None
    kind: ProviderKind
    label: str
    secret: str
    secret_hint: str
    base_url: str
    logged_in_at: datetime | None
    created_by: int | None
    created_at: datetime
    home: Path

    @property
    def spec(self) -> ProviderSpec:
        return PROVIDERS[self.kind]

    @property
    def has_credential(self) -> bool:
        spec = self.spec
        if spec.family is ProviderFamily.SUBSCRIPTION:
            return self.logged_in_at is not None
        if spec.asks_address:
            return bool(self.base_url)
        return bool(self.secret)

    def same_credential(self) -> tuple[object, ...]:
        return (self.id, self.kind, self.secret, self.base_url, self.logged_in_at)


@dataclass(frozen=True)
class ChainEntry:
    id: int
    workspace_id: int | None
    role: ModelRole
    position: int
    connection: Connection
    model: str
    tools_work: bool | None
    sees_images: bool | None
    checked_at: datetime | None
    check_note: str

    @property
    def usable(self) -> bool:
        return self.connection.has_credential and self.tools_work is not False


def connection_of(row: ProviderConnectionRow, secret: str, home: Path) -> Connection:
    return Connection(
        row.id, row.workspace_id, row.kind, row.label, secret, row.secret_hint, row.base_url, row.logged_in_at, row.created_by, row.created_at, home
    )


def entry_of(row: ProviderChainEntryRow, connection: Connection) -> ChainEntry:
    return ChainEntry(row.id, row.workspace_id, row.role, row.position, connection, row.model, row.tools_work, row.sees_images, row.checked_at, row.check_note)
