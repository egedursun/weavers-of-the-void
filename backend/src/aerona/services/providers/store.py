from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.library.tables import ProviderChainEntryRow, ProviderConnectionRow, UniverseRow
from aerona.domain.enums.providers import ModelRole, ProviderKind
from aerona.services.library.catalogue import Catalogue


@dataclass(frozen=True)
class NewConnection:
    workspace_id: int | None
    kind: ProviderKind
    label: str
    secret: str
    secret_hint: str
    base_url: str
    created_by: int | None
    created_at: datetime


@dataclass(frozen=True)
class ChainLink:
    connection_id: int
    model: str


@dataclass(frozen=True)
class CheckResult:
    tools_work: bool | None
    sees_images: bool | None
    note: str
    at: datetime


class ProviderStore:
    def __init__(self, catalogue: Catalogue) -> None:
        self.catalogue = catalogue

    @asynccontextmanager
    async def read(self) -> AsyncIterator[AsyncSession]:
        async with self.catalogue.read_session() as session:
            yield session

    @asynccontextmanager
    async def write(self) -> AsyncIterator[AsyncSession]:
        async with self.catalogue.write_session() as session:
            yield session

    async def connections(self) -> list[ProviderConnectionRow]:
        async with self.read() as session:
            return list(await session.scalars(select(ProviderConnectionRow).order_by(ProviderConnectionRow.id)))

    async def entries(self) -> list[ProviderChainEntryRow]:
        async with self.read() as session:
            return list(await session.scalars(select(ProviderChainEntryRow).order_by(ProviderChainEntryRow.position, ProviderChainEntryRow.id)))

    async def universe_workspaces(self) -> dict[str, int | None]:
        async with self.read() as session:
            rows = await session.execute(select(UniverseRow.id, UniverseRow.workspace_id).order_by(UniverseRow.id))
            return {universe_id: workspace_id for universe_id, workspace_id in rows.all()}

    async def add_connection(self, new: NewConnection) -> int:
        async with self.write() as session:
            row = ProviderConnectionRow(
                workspace_id=new.workspace_id,
                kind=new.kind,
                label=new.label,
                secret=new.secret,
                secret_hint=new.secret_hint,
                base_url=new.base_url,
                created_by=new.created_by,
                created_at=new.created_at,
            )
            session.add(row)
            await session.flush()
            return row.id

    async def edit_connection(
        self,
        connection_id: int,
        *,
        label: str | None = None,
        secret: tuple[str, str] | None = None,
        base_url: str | None = None,
    ) -> bool:
        async with self.write() as session:
            row = await session.get(ProviderConnectionRow, connection_id)
            if row is None:
                return False
            if label is not None:
                row.label = label
            if secret is not None:
                row.secret, row.secret_hint = secret
            if base_url is not None:
                row.base_url = base_url
            return True

    async def mark_login(self, connection_id: int, at: datetime | None) -> None:
        async with self.write() as session:
            row = await session.get(ProviderConnectionRow, connection_id)
            if row is not None:
                row.logged_in_at = at

    async def remove_connection(self, connection_id: int) -> None:
        async with self.write() as session:
            await session.execute(delete(ProviderChainEntryRow).where(ProviderChainEntryRow.connection_id == connection_id))
            await session.execute(delete(ProviderConnectionRow).where(ProviderConnectionRow.id == connection_id))

    async def replace_chain(self, workspace_id: int | None, role: ModelRole, links: Sequence[ChainLink]) -> None:
        async with self.write() as session:
            scope = ProviderChainEntryRow.workspace_id.is_(None) if workspace_id is None else ProviderChainEntryRow.workspace_id == workspace_id
            current = list(
                await session.scalars(select(ProviderChainEntryRow).where(scope, ProviderChainEntryRow.role == role).order_by(ProviderChainEntryRow.id))
            )
            kept = {(row.connection_id, row.model): row for row in current}
            wanted = {(link.connection_id, link.model) for link in links}
            for key, stale in kept.items():
                if key not in wanted:
                    await session.delete(stale)
            for position, link in enumerate(links):
                found = kept.get((link.connection_id, link.model))
                if found is None:
                    session.add(
                        ProviderChainEntryRow(workspace_id=workspace_id, role=role, position=position, connection_id=link.connection_id, model=link.model)
                    )
                else:
                    found.position = position

    async def record_check(self, entry_id: int, result: CheckResult) -> None:
        async with self.write() as session:
            row = await session.get(ProviderChainEntryRow, entry_id)
            if row is not None:
                row.tools_work = result.tools_work
                row.sees_images = result.sees_images
                row.check_note = result.note
                row.checked_at = result.at
