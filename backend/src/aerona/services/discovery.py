import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from aerona.constants.maintenance import DISCOVERY_DIRNAME, DISCOVERY_STATE_FILENAME
from aerona.core.errors import ConflictError, ReadOnlyError
from aerona.services.backups import referenced_objects
from aerona.settings import Settings

READ_ONLY_MESSAGE = "Discovery mode: the guest world is open read-only. Return to your own world to make changes."
NOT_IN_DISCOVERY = "Discovery mode is not active."
ALREADY_IN_DISCOVERY = "Discovery mode is active; return to your own world first."
UNKNOWN_GUEST = "unknown guest world"
TEMP_SUFFIX = ".tmp"


@dataclass(frozen=True)
class GuestWorld:
    name: str
    epoch: int | None
    creator: str | None
    date: str | None


@dataclass(frozen=True)
class DiscoveryState:
    guest_db: str | None
    guest: GuestWorld | None
    images: list[str] = field(default_factory=list)
    started: str | None = None
    corrupt: bool = False


def _state_payload(state: DiscoveryState) -> dict[str, Any]:
    guest = state.guest
    return {
        "guest_db": state.guest_db,
        "guest": None if guest is None else {"name": guest.name, "epoch": guest.epoch, "creator": guest.creator, "date": guest.date},
        "images": state.images,
        "started": state.started,
    }


def _parse_state(raw: str) -> DiscoveryState:
    try:
        data = json.loads(raw)
        guest = data.get("guest")
        return DiscoveryState(
            guest_db=data.get("guest_db"),
            guest=GuestWorld(guest["name"], guest.get("epoch"), guest.get("creator"), guest.get("date")) if guest else None,
            images=[name for name in data.get("images", []) if isinstance(name, str)],
            started=data.get("started"),
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return DiscoveryState(guest_db=None, guest=None, corrupt=True)


def read_only_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///file:{path}?mode=ro&uri=true"


class DiscoveryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

    @property
    def directory(self) -> Path:
        return self._settings.data_dir / DISCOVERY_DIRNAME

    @property
    def state_path(self) -> Path:
        return self._settings.data_dir / DISCOVERY_STATE_FILENAME

    @property
    def active(self) -> bool:
        return self.state_path.exists()

    def state(self) -> DiscoveryState | None:
        if not self.state_path.exists():
            return None
        return _parse_state(self.state_path.read_text(encoding="utf-8"))

    def guest(self) -> GuestWorld | None:
        state = self.state()
        if state is None:
            return None
        return state.guest or GuestWorld(UNKNOWN_GUEST, None, None, None)

    def ensure_writable(self) -> None:
        if self.active:
            raise ReadOnlyError(READ_ONLY_MESSAGE)

    def ensure_not_active(self) -> None:
        if self.active:
            raise ConflictError(ALREADY_IN_DISCOVERY)

    def _write_state(self, state: DiscoveryState) -> None:
        temporary = self.state_path.with_suffix(TEMP_SUFFIX)
        temporary.write_text(json.dumps(_state_payload(state)), encoding="utf-8")
        os.replace(temporary, self.state_path)

    async def open(self, guest_db: Path, guest: GuestWorld, images: list[str]) -> DiscoveryState:
        self.ensure_not_active()
        target = await asyncio.to_thread(self._place, guest_db)
        state = DiscoveryState(guest_db=str(target), guest=guest, images=images, started=datetime.now(UTC).isoformat())
        self._write_state(state)
        await self._connect(target)
        return state

    def _place(self, guest_db: Path) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / guest_db.name
        if guest_db.resolve() != target.resolve():
            guest_db.replace(target)
        return target

    async def resume(self) -> bool:
        state = self.state()
        if state is None or state.guest_db is None or not await asyncio.to_thread(Path(state.guest_db).is_file):
            return False
        await self._connect(Path(state.guest_db))
        return True

    async def _connect(self, path: Path) -> None:
        await self._close()
        self._engine = create_async_engine(read_only_url(path), future=True)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    async def _close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._sessions = None

    @asynccontextmanager
    async def guest_session(self) -> AsyncIterator[AsyncSession]:
        if self._sessions is None and not await self.resume():
            raise ConflictError(NOT_IN_DISCOVERY)
        sessions = self._sessions
        if sessions is None:
            raise ConflictError(NOT_IN_DISCOVERY)
        async with sessions() as session:
            yield session

    async def end(self) -> GuestWorld | None:
        state = self.state()
        if state is None:
            raise ConflictError(NOT_IN_DISCOVERY)
        await self._close()
        await asyncio.to_thread(self._clean_up, state)
        return state.guest

    def pinned_objects(self) -> set[str]:
        state = self.state()
        if state is None:
            return set()
        pinned = set(state.images)
        if state.guest_db and Path(state.guest_db).is_file():
            pinned |= referenced_objects(Path(state.guest_db))
        return pinned

    def _clean_up(self, state: DiscoveryState) -> None:
        if state.guest_db:
            Path(state.guest_db).unlink(missing_ok=True)
        self.state_path.unlink(missing_ok=True)

    async def shutdown(self) -> None:
        await self._close()
