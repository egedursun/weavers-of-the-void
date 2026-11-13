from dataclasses import dataclass
from typing import Protocol

from aerona.catalog.rarities import DEFAULT_FIRST_SONS
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.genesis import GenesisOutcome, GenesisSettings
from aerona.services.player.ports import ContentWriter, PeopleAwakener, RevelationAuthor, WorldMaker


@dataclass(frozen=True)
class GenesisRequest:
    creator_name: str
    seed: str
    tone: str | None
    lore_language: LoreLanguage
    rng_seed: int
    settings: GenesisSettings | None
    first_sons: tuple[Rarity, ...] = DEFAULT_FIRST_SONS


class EntityDeepener(Protocol):
    async def deepen_entity(self, entity_id: int) -> None: ...

    async def deepen_foreign_god(self, god_id: int) -> None: ...


class PendingNamer(Protocol):
    async def name_pending(self) -> int: ...


class ImagePromptWriter(Protocol):
    async def write_prompt(self, node_id: int) -> str | None: ...

    async def write_batch(self, node_ids: list[int]) -> int: ...


class GenesisAuthor(Protocol):
    async def create(self, request: GenesisRequest) -> GenesisOutcome: ...


class SonPowerWriter(Protocol):
    async def write_powers(self, son_id: int) -> None: ...


class EpochNarrator(Protocol):
    async def narrate(self, epoch: int) -> None: ...


@dataclass(frozen=True)
class LorePorts:
    deepener: EntityDeepener | None = None
    namer: PendingNamer | None = None
    prompts: ImagePromptWriter | None = None
    genesis: GenesisAuthor | None = None
    powers: SonPowerWriter | None = None
    narrator: EpochNarrator | None = None
    awakener: PeopleAwakener | None = None
    worlds: WorldMaker | None = None
    revelations: RevelationAuthor | None = None
    writer: ContentWriter | None = None
