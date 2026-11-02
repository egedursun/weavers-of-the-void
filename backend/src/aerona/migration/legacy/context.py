from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.migration import BATCH_SIZE
from aerona.db.base import Base
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.migration.legacy.idmap import IdMap, LegacyKind
from aerona.migration.legacy.names import NameLedger
from aerona.migration.legacy.report import MigrationReport
from aerona.migration.legacy.source import LegacySource
from aerona.migration.legacy.tags import TagReading
from aerona.migration.legacy.vocabulary import Vocabulary
from aerona.rules.registry import Rules

CODE_KINDS = {
    "entity": LegacyKind.ENTITY,
    "son": LegacyKind.SON,
    "creator": LegacyKind.CREATOR,
    "foreign_god": LegacyKind.FOREIGN_GOD,
    "world": LegacyKind.WORLD,
}


@dataclass(frozen=True)
class EntityFacts:
    entity_type: EntityType
    status: EntityStatus
    world_id: int
    birth_epoch: int


@dataclass
class MigrationContext:
    session: AsyncSession
    source: LegacySource
    vocabulary: Vocabulary
    report: MigrationReport
    rules: Rules
    epoch: int
    ids: IdMap = field(default_factory=IdMap)
    names: NameLedger = field(default_factory=NameLedger)
    entities: dict[int, EntityFacts] = field(default_factory=dict)
    primary_world_id: int = 0
    readings: dict[int, TagReading] = field(default_factory=dict)
    war_stats: dict[int, dict[str, int]] = field(default_factory=dict)
    society_payloads: dict[int, dict[str, Any]] = field(default_factory=dict)
    rows: dict[int, EntityRow] = field(default_factory=dict)
    _pending: list[Base] = field(default_factory=list)

    def node(self, code: str | None, legacy_id: int | None) -> int | None:
        kind_name = self.vocabulary.node_kind_of(code)
        kind = CODE_KINDS.get(kind_name or "")
        if kind is None:
            return None
        if kind is LegacyKind.CREATOR:
            return self.ids.creator()
        return self.ids.get(kind, legacy_id)

    def entity(self, legacy_id: int | None) -> int | None:
        return self.ids.get(LegacyKind.ENTITY, legacy_id)

    def son(self, legacy_id: int | None) -> int | None:
        return self.ids.get(LegacyKind.SON, legacy_id)

    def world(self, legacy_id: int | None) -> int | None:
        return self.ids.get(LegacyKind.WORLD, legacy_id)

    def world_or_primary(self, legacy_id: int | None) -> int:
        return self.world(legacy_id) or self.primary_world_id

    def facts(self, new_id: int | None) -> EntityFacts | None:
        return self.entities.get(new_id) if new_id is not None else None

    def add(self, row: Base) -> None:
        self._pending.append(row)

    async def flush_if_full(self) -> None:
        if len(self._pending) >= BATCH_SIZE:
            await self.flush()

    async def flush(self) -> None:
        if self._pending:
            self.session.add_all(self._pending)
            self._pending = []
        await self.session.flush()
