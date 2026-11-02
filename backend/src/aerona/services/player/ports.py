from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_capture import LedgerDraft
from aerona.domain.enums.world import StarType, WorldType


class LedgerCapture(Protocol):
    async def seal(self, draft: LedgerDraft) -> int | None: ...


class ActionLedger(Protocol):
    def capture(self, session: AsyncSession) -> AbstractAsyncContextManager[LedgerCapture]: ...


@dataclass(frozen=True)
class RevelationRequest:
    content: str
    entity_type: str | None
    world_id: int | None
    mechanic: str | None


@dataclass(frozen=True)
class WorldCreationRequest:
    world_type: WorldType | None
    inspiration: str
    star_id: int | None
    parent_world_id: int | None
    new_star: bool
    new_star_type: StarType | None


class ContentJobKind(StrEnum):
    CREATOR_PORTRAIT = "creator_portrait"
    CREATOR_EPIC = "creator_epic"
    CREATOR_DEEPEN = "creator_deepen"
    SON_EPIC = "son_epic"
    FOREIGN_GOD_DEEPEN = "foreign_god_deepen"
    FOREIGN_GOD_AWAKENED = "foreign_god_awakened"


@dataclass(frozen=True)
class ContentJob:
    kind: ContentJobKind
    target_id: int | None


class SonSummoner(Protocol):
    async def summon(self, world_id: int | None) -> int: ...

    async def birth(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> int: ...


class MortalActor(Protocol):
    async def act(self, entity_id: int) -> str: ...


class RevelationAuthor(Protocol):
    async def reveal(self, request: RevelationRequest) -> int: ...


class WorldMaker(Protocol):
    async def create(self, request: WorldCreationRequest) -> int: ...


class PeopleAwakener(Protocol):
    async def awaken(self, count: int, world_id: int | None) -> list[int]: ...


class ContentWriter(Protocol):
    async def write(self, job: ContentJob) -> str: ...


class FateControls(Protocol):
    async def retry_fate(self) -> dict[str, int]: ...

    async def rejudge_debt(self) -> dict[str, int]: ...

    async def rejudge_limbo(self) -> dict[str, int]: ...

    async def retry_voices(self) -> dict[str, int]: ...

    async def retry_births(self) -> dict[str, int]: ...

    async def audit_chronicle(self, epoch: int) -> dict[str, int]: ...


@dataclass(frozen=True)
class CreativePorts:
    summoner: SonSummoner | None = None
    revelations: RevelationAuthor | None = None
    worlds: WorldMaker | None = None
    awakener: PeopleAwakener | None = None
    writer: ContentWriter | None = None
    fate: FateControls | None = None
    mortals: MortalActor | None = None
