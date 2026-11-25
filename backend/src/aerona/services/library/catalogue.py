import asyncio
import secrets
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import Select, and_, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from aerona.constants.library import (
    LIBRARY_PAGE_DEFAULT,
    LIBRARY_PAGE_MAX,
    TAKEN_NAME_SUFFIX,
    UNIVERSE_ID_ALPHABET,
    UNIVERSE_ID_LENGTH,
    UNIVERSE_NAME_MAX_LENGTH,
    UNIVERSE_NOTES_MAX_LENGTH,
    UNIVERSE_TAG_MAX_LENGTH,
    UNIVERSE_TAGS_MAX,
)
from aerona.core.account_scope import current_account, current_workspace
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.inline_sqlite import inline_engine
from aerona.db.library.migrations import upgrade_library
from aerona.db.library.tables import LibraryEventRow, UniverseOverrideRow, UniverseRow, WorkspaceMemberRow
from aerona.db.record_context import UNCAPTURED
from aerona.domain.enums.accounts import UniverseRole, WorkspaceRole
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin, UniverseSort, UniverseStatus
from aerona.paths import ProcessPaths
from aerona.services.library.manifest import UniverseManifest, write_manifest

ASYNC_DRIVER_PREFIX = "sqlite+aiosqlite:///"
NO_SUCH_UNIVERSE = "No such universe."
NAME_REQUIRED = "A universe needs a name."
QUICK_CHECK = "PRAGMA quick_check"
QUICK_CHECK_OK = "ok"
SORT_ORDER = {
    UniverseSort.OPENED: (UniverseRow.pinned.desc(), func.coalesce(UniverseRow.opened_at, UniverseRow.created_at).desc()),
    UniverseSort.CREATED: (UniverseRow.created_at.desc(),),
    UniverseSort.NAME: (func.lower(UniverseRow.name).asc(),),
    UniverseSort.EPOCH: (UniverseRow.epoch.desc(),),
    UniverseSort.SIZE: (UniverseRow.size_bytes.desc(),),
}


@dataclass(frozen=True)
class UniverseRecord:
    id: str
    name: str
    summary: str
    notes: str
    cover_path: str | None
    status: UniverseStatus
    pinned: bool
    created_at: datetime
    opened_at: datetime | None
    updated_at: datetime
    epoch: int
    year: int
    population: int
    sons: int
    size_bytes: int
    schema_revision: str
    app_version: str
    origin: UniverseOrigin
    origin_note: str
    tags: tuple[str, ...]
    media_prefix: str
    workspace_id: int | None = None
    legacy_author_account_id: int | None = None
    legacy_author_name: str = ""
    canon_approval: bool = False

    @classmethod
    def of(cls, row: UniverseRow) -> "UniverseRecord":
        return cls(
            id=row.id,
            name=row.name,
            summary=row.summary,
            notes=row.notes,
            cover_path=row.cover_path,
            status=row.status,
            pinned=row.pinned,
            created_at=row.created_at,
            opened_at=row.opened_at,
            updated_at=row.updated_at,
            epoch=row.epoch,
            year=row.year,
            population=row.population,
            sons=row.sons,
            size_bytes=row.size_bytes,
            schema_revision=row.schema_revision,
            app_version=row.app_version,
            origin=row.origin,
            origin_note=row.origin_note,
            tags=tuple(row.tags or ()),
            media_prefix=row.media_prefix,
            workspace_id=row.workspace_id,
            legacy_author_account_id=row.legacy_author_account_id,
            legacy_author_name=row.legacy_author_name,
            canon_approval=row.canon_approval,
        )

    def manifest(self) -> UniverseManifest:
        return UniverseManifest(
            id=self.id,
            name=self.name,
            summary=self.summary,
            notes=self.notes,
            tags=self.tags,
            origin=self.origin,
            origin_note=self.origin_note,
            media_prefix=self.media_prefix,
            created_at=self.created_at,
            schema_revision=self.schema_revision,
            app_version=self.app_version,
            epoch=self.epoch,
            year=self.year,
        )


@dataclass(frozen=True)
class LibraryEventRecord:
    id: int
    at: datetime
    kind: LibraryEventKind
    universe_id: str
    universe_name: str
    detail: str
    account_id: int | None = None
    account_name: str = ""

    @classmethod
    def of(cls, row: LibraryEventRow) -> "LibraryEventRecord":
        return cls(row.id, row.at, row.kind, row.universe_id, row.universe_name, row.detail, row.account_id, row.account_name)


@dataclass(frozen=True)
class UniverseFacts:
    epoch: int
    year: int
    population: int
    sons: int
    size_bytes: int
    schema_revision: str
    seed: str


@dataclass(frozen=True)
class NewUniverse:
    name: str
    origin: UniverseOrigin
    media_prefix: str
    app_version: str
    schema_revision: str = ""
    notes: str = ""
    summary: str = ""
    origin_note: str = ""
    tags: tuple[str, ...] = ()
    workspace_id: int | None = None


@dataclass(frozen=True)
class UniverseEdit:
    name: str | None = None
    notes: str | None = None
    summary: str | None = None
    tags: tuple[str, ...] | None = None
    pinned: bool | None = None
    cover_path: str | None = None
    clear_cover: bool = False


@dataclass(frozen=True)
class UniverseQuery:
    text: str = ""
    status: UniverseStatus | None = UniverseStatus.ACTIVE
    origin: UniverseOrigin | None = None
    tag: str | None = None
    sort: UniverseSort = UniverseSort.OPENED
    offset: int = 0
    limit: int = LIBRARY_PAGE_DEFAULT
    workspace_id: int | None = None
    visible: frozenset[str] | None = None


@dataclass(frozen=True)
class UniversePage:
    universes: list[UniverseRecord]
    total: int
    tags: list[str]
    origins: dict[UniverseOrigin, int] = field(default_factory=dict)
    statuses: dict[UniverseStatus, int] = field(default_factory=dict)


def new_universe_id() -> str:
    return "".join(secrets.choice(UNIVERSE_ID_ALPHABET) for _ in range(UNIVERSE_ID_LENGTH))


def clean_name(name: str) -> str:
    cleaned = " ".join(name.split())[:UNIVERSE_NAME_MAX_LENGTH]
    if not cleaned:
        raise ValidationFailedError(NAME_REQUIRED)
    return cleaned


def clean_tags(tags: Iterable[str]) -> list[str]:
    kept: list[str] = []
    for tag in tags:
        cleaned = " ".join(tag.split())[:UNIVERSE_TAG_MAX_LENGTH]
        if cleaned and cleaned.casefold() not in {item.casefold() for item in kept}:
            kept.append(cleaned)
    return kept[:UNIVERSE_TAGS_MAX]


def numbered(name: str, number: int) -> str:
    suffix = TAKEN_NAME_SUFFIX.format(number=number)
    return f"{name[: UNIVERSE_NAME_MAX_LENGTH - len(suffix)]}{suffix}"


def scoped(statement: Select[UniverseRow], query: UniverseQuery) -> Select[UniverseRow]:
    if query.workspace_id is not None:
        statement = statement.where(UniverseRow.workspace_id == query.workspace_id)
    if query.visible is not None:
        statement = statement.where(UniverseRow.id.in_(sorted(query.visible)))
    return statement


def acting_event() -> dict[str, object]:
    account = current_account()
    return {"account_id": account.id, "account_name": account.name} if account is not None else {}


def filtered(statement: Select[UniverseRow], query: UniverseQuery) -> Select[UniverseRow]:
    statement = scoped(statement, query)
    if query.status is not None:
        statement = statement.where(UniverseRow.status == query.status)
    if query.origin is not None:
        statement = statement.where(UniverseRow.origin == query.origin)
    words = query.text.strip()
    if words:
        pattern = f"%{words.lower()}%"
        statement = statement.where(
            func.lower(UniverseRow.name).like(pattern) | func.lower(UniverseRow.summary).like(pattern) | func.lower(UniverseRow.notes).like(pattern)
        )
    return statement


class Catalogue:
    def __init__(self, paths: ProcessPaths) -> None:
        self.paths = paths
        self._url = f"{ASYNC_DRIVER_PREFIX}{paths.library_database}"
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None
        self._writing = asyncio.Lock()

    async def open(self) -> None:
        if self._engine is not None:
            return
        self.paths.root.mkdir(parents=True, exist_ok=True)
        await upgrade_library(self._url)
        self._engine = inline_engine(self._url)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession, info={UNCAPTURED: True})

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._sessions = None

    @asynccontextmanager
    async def _read(self) -> AsyncIterator[AsyncSession]:
        if self._sessions is None:
            await self.open()
        assert self._sessions is not None
        async with self._sessions() as session:
            yield session

    @asynccontextmanager
    async def _write(self) -> AsyncIterator[AsyncSession]:
        async with self._writing, self._read() as session, session.begin():
            yield session

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[AsyncSession]:
        async with self._read() as session:
            yield session

    @asynccontextmanager
    async def write_session(self) -> AsyncIterator[AsyncSession]:
        async with self._write() as session:
            yield session

    async def healthy(self) -> bool:
        try:
            async with self._read() as session:
                return bool(await session.scalar(text(QUICK_CHECK)) == QUICK_CHECK_OK)
        except Exception:
            return False

    async def get(self, universe_id: str) -> UniverseRecord | None:
        async with self._read() as session:
            row = await session.get(UniverseRow, universe_id)
            return UniverseRecord.of(row) if row is not None else None

    async def require(self, universe_id: str) -> UniverseRecord:
        found = await self.get(universe_id)
        if found is None:
            raise NotFoundError(NO_SUCH_UNIVERSE)
        return found

    async def every(self) -> list[UniverseRecord]:
        async with self._read() as session:
            rows = await session.scalars(select(UniverseRow).order_by(UniverseRow.created_at, UniverseRow.id))
            return [UniverseRecord.of(row) for row in rows]

    async def page(self, query: UniverseQuery) -> UniversePage:
        limit = max(1, min(query.limit, LIBRARY_PAGE_MAX))
        async with self._read() as session:
            rows = list(await session.scalars(filtered(select(UniverseRow), query).order_by(*SORT_ORDER[query.sort], UniverseRow.id)))
            every = list(await session.scalars(scoped(select(UniverseRow), query).order_by(UniverseRow.id)))
        chosen = [row for row in rows if query.tag is None or query.tag.casefold() in {tag.casefold() for tag in row.tags or ()}]
        tags = sorted({tag for row in every for tag in row.tags or ()}, key=str.casefold)
        origins = {origin: sum(1 for row in every if row.origin is origin) for origin in UniverseOrigin}
        statuses = {status: sum(1 for row in every if row.status is status) for status in UniverseStatus}
        start = max(0, query.offset)
        return UniversePage(
            universes=[UniverseRecord.of(row) for row in chosen[start : start + limit]], total=len(chosen), tags=tags, origins=origins, statuses=statuses
        )

    async def free_name(self, name: str, *, keep: str | None = None) -> str:
        wanted = clean_name(name)
        async with self._read() as session:
            taken = {found.casefold() for found in await session.scalars(select(UniverseRow.name).where(UniverseRow.id != (keep or "")))}
        if wanted.casefold() not in taken:
            return wanted
        number = 2
        while numbered(wanted, number).casefold() in taken:
            number += 1
        return numbered(wanted, number)

    async def add(self, universe_id: str, new: NewUniverse) -> UniverseRecord:
        now = datetime.now(UTC)
        row = UniverseRow(
            id=universe_id,
            name=clean_name(new.name),
            summary=new.summary,
            notes=new.notes[:UNIVERSE_NOTES_MAX_LENGTH],
            status=UniverseStatus.ACTIVE,
            pinned=False,
            created_at=now,
            updated_at=now,
            schema_revision=new.schema_revision,
            app_version=new.app_version,
            origin=new.origin,
            origin_note=new.origin_note,
            tags=clean_tags(new.tags),
            media_prefix=new.media_prefix,
            workspace_id=new.workspace_id if new.workspace_id is not None else current_workspace(),
        )
        async with self._write() as session:
            session.add(row)
            await session.flush()
            await self._seat_maker(session, row)
            record = UniverseRecord.of(row)
        await self._mirror(record)
        return record

    async def _seat_maker(self, session: AsyncSession, row: UniverseRow) -> None:
        account = current_account()
        if account is None or row.workspace_id is None:
            return
        role = await session.scalar(
            select(WorkspaceMemberRow.role).where(WorkspaceMemberRow.workspace_id == row.workspace_id, WorkspaceMemberRow.account_id == account.id)
        )
        if role is WorkspaceRole.ADMIN:
            return
        session.add(UniverseOverrideRow(universe_id=row.id, account_id=account.id, role=UniverseRole.ADMIN, set_by=account.id, set_at=datetime.now(UTC)))

    async def restore_row(self, manifest: UniverseManifest, workspace_id: int | None = None) -> UniverseRecord:
        now = datetime.now(UTC)
        row = UniverseRow(
            id=manifest.id,
            name=clean_name(manifest.name),
            summary=manifest.summary,
            notes=manifest.notes,
            status=UniverseStatus.ACTIVE,
            pinned=False,
            created_at=manifest.created_at,
            updated_at=now,
            schema_revision=manifest.schema_revision,
            app_version=manifest.app_version,
            origin=manifest.origin,
            origin_note=manifest.origin_note,
            tags=clean_tags(manifest.tags),
            media_prefix=manifest.media_prefix,
            epoch=manifest.epoch,
            year=manifest.year,
            workspace_id=workspace_id if workspace_id is not None else current_workspace(),
        )
        async with self._write() as session:
            session.add(row)
            await session.flush()
            await self._seat_maker(session, row)
            return UniverseRecord.of(row)

    async def edit(self, universe_id: str, change: UniverseEdit) -> UniverseRecord:
        async with self._write() as session:
            row = await session.get(UniverseRow, universe_id)
            if row is None:
                raise NotFoundError(NO_SUCH_UNIVERSE)
            former = row.name
            if change.name is not None:
                row.name = clean_name(change.name)
            if change.notes is not None:
                row.notes = change.notes[:UNIVERSE_NOTES_MAX_LENGTH]
            if change.summary is not None:
                row.summary = change.summary
            if change.tags is not None:
                row.tags = clean_tags(change.tags)
            if change.pinned is not None:
                row.pinned = change.pinned
            if change.cover_path is not None or change.clear_cover:
                row.cover_path = None if change.clear_cover else change.cover_path
            row.updated_at = datetime.now(UTC)
            renamed = row.name != former
            session.add(
                LibraryEventRow(
                    kind=LibraryEventKind.RENAMED if renamed else LibraryEventKind.EDITED,
                    universe_id=row.id,
                    universe_name=row.name,
                    detail=former if renamed else "",
                    at=row.updated_at,
                    workspace_id=row.workspace_id,
                    **acting_event(),
                )
            )
            record = UniverseRecord.of(row)
        await self._mirror(record)
        return record

    async def set_status(self, universe_id: str, status: UniverseStatus) -> UniverseRecord:
        async with self._write() as session:
            row = await session.get(UniverseRow, universe_id)
            if row is None:
                raise NotFoundError(NO_SUCH_UNIVERSE)
            row.status = status
            row.updated_at = datetime.now(UTC)
            kind = LibraryEventKind.ARCHIVED if status is UniverseStatus.ARCHIVED else LibraryEventKind.RESTORED
            session.add(
                LibraryEventRow(kind=kind, universe_id=row.id, universe_name=row.name, at=row.updated_at, workspace_id=row.workspace_id, **acting_event())
            )
            return UniverseRecord.of(row)

    async def mark_opened(self, universe_id: str) -> UniverseRecord:
        async with self._write() as session:
            row = await session.get(UniverseRow, universe_id)
            if row is None:
                raise NotFoundError(NO_SUCH_UNIVERSE)
            row.opened_at = datetime.now(UTC)
            session.add(
                LibraryEventRow(
                    kind=LibraryEventKind.OPENED, universe_id=row.id, universe_name=row.name, at=row.opened_at, workspace_id=row.workspace_id, **acting_event()
                )
            )
            return UniverseRecord.of(row)

    async def store_facts(self, universe_id: str, facts: UniverseFacts) -> UniverseRecord | None:
        async with self._write() as session:
            row = await session.get(UniverseRow, universe_id)
            if row is None:
                return None
            row.epoch = max(0, facts.epoch)
            row.year = facts.year
            row.population = max(0, facts.population)
            row.sons = max(0, facts.sons)
            row.size_bytes = max(0, facts.size_bytes)
            if facts.schema_revision:
                row.schema_revision = facts.schema_revision
            if not row.summary and facts.seed:
                row.summary = facts.seed
            record = UniverseRecord.of(row)
        await self._mirror(record)
        return record

    async def remove(self, universe_id: str) -> None:
        async with self._write() as session:
            await session.execute(delete(UniverseRow).where(UniverseRow.id == universe_id))

    async def ids_in(self, workspace_id: int | None) -> list[str]:
        if workspace_id is None:
            return []
        async with self._read() as session:
            return list(await session.scalars(select(UniverseRow.id).where(UniverseRow.workspace_id == workspace_id).order_by(UniverseRow.id)))

    async def log(
        self, kind: LibraryEventKind, universe_id: str, universe_name: str, detail: str = "", *, workspace_id: int | None = None
    ) -> LibraryEventRecord:
        async with self._write() as session:
            if workspace_id is None and universe_id:
                workspace_id = await session.scalar(select(UniverseRow.workspace_id).where(UniverseRow.id == universe_id))
            if workspace_id is None:
                workspace_id = current_workspace()
            row = LibraryEventRow(
                kind=kind,
                universe_id=universe_id,
                universe_name=universe_name,
                detail=detail,
                at=datetime.now(UTC),
                workspace_id=workspace_id,
                **acting_event(),
            )
            session.add(row)
            await session.flush()
            return LibraryEventRecord.of(row)

    async def events(
        self,
        *,
        offset: int = 0,
        limit: int = LIBRARY_PAGE_DEFAULT,
        universe_id: str | None = None,
        visible: frozenset[str] | None = None,
        workspace_id: int | None = None,
        hidden: frozenset[str] = frozenset(),
    ) -> tuple[list[LibraryEventRecord], int]:
        statement = select(LibraryEventRow)
        counted = select(func.count()).select_from(LibraryEventRow)
        if visible is not None:
            mine = and_(LibraryEventRow.workspace_id == workspace_id, LibraryEventRow.universe_id.not_in(sorted(hidden)))
            seen = or_(LibraryEventRow.universe_id.in_(sorted(visible)), mine)
            statement = statement.where(seen)
            counted = counted.where(seen)
        if universe_id is not None:
            statement = statement.where(LibraryEventRow.universe_id == universe_id)
            counted = counted.where(LibraryEventRow.universe_id == universe_id)
        async with self._read() as session:
            rows = await session.scalars(statement.order_by(LibraryEventRow.id.desc()).offset(max(0, offset)).limit(max(1, min(limit, LIBRARY_PAGE_MAX))))
            found = [LibraryEventRecord.of(row) for row in rows]
            total = int(await session.scalar(counted) or 0)
        return found, total

    async def _mirror(self, record: UniverseRecord) -> None:
        folder = self.paths.universe(record.id)
        if folder.root.is_dir():
            await asyncio.to_thread(write_manifest, folder.manifest, record.manifest())
