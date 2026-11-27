from dataclasses import dataclass
from typing import Protocol, cast

from aerona.domain.enums.divine_will import ChunkSource
from aerona.media.store import MediaStore
from aerona.tools.divine_will.framework import WillCall


@dataclass(frozen=True)
class LoreHit:
    source: ChunkSource
    record: str
    ordinal: int
    parts: int
    node_id: int | None
    cycle_id: int | None
    text: str
    tokens: int
    lexical_rank: int | None
    similarity: float | None


@dataclass(frozen=True)
class LoreSearch:
    hits: tuple[LoreHit, ...]
    semantic: bool
    passages: int
    embedded: int
    note: str
    total: int = 0


class LoreIndexPort(Protocol):
    async def search(self, query: str, *, sources: frozenset[ChunkSource] | None, attachments: frozenset[int], reach: int = 0) -> LoreSearch: ...


class RetrievalHost(Protocol):
    @property
    def lore_index(self) -> LoreIndexPort: ...

    @property
    def attachment_store(self) -> MediaStore: ...


def lore_index_of(call: WillCall) -> LoreIndexPort:
    return cast(RetrievalHost, call.services).lore_index


def attachment_store_of(call: WillCall) -> MediaStore:
    return cast(RetrievalHost, call.services).attachment_store
