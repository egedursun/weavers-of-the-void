import math
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.meta import ImageRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import ArchiveOverride, EntityStatus, EntityType
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

PERMANENT_TYPES = frozenset(
    {
        EntityType.REGION,
        EntityType.PEOPLE,
        EntityType.LANGUAGE,
        EntityType.CELESTIAL,
        EntityType.MORTAL,
        EntityType.SPECIES,
        EntityType.NATURAL_LAW,
        EntityType.LAW,
        EntityType.CULT,
    }
)
ENDED = frozenset({EntityStatus.DEAD, EntityStatus.DESTROYED})


class ArchiveMode(StrEnum):
    HISTORY = "history"
    ATLAS = "atlas"
    AUTOMATIC = "automatic"


class ArchiveReason(StrEnum):
    MANUAL = "manually sent to history"
    DEAD = "dead; no longer mentioned"
    VANISHED = "vanished"
    FULFILLED = "fulfilled"
    UNMENTIONED = "epochs without mention"


@dataclass(frozen=True)
class ImportanceInfo:
    entity_id: int
    importance: int
    archived: bool
    reason: str | None
    last_mention: int


def age_threshold(rules: Rules, entity_type: EntityType) -> int | None:
    archive = rules.archive
    thresholds = {
        EntityType.EVENT: archive.event_epochs,
        EntityType.PROPHECY: archive.prophecy_epochs,
        EntityType.SPIRIT: archive.spirit_epochs,
        EntityType.SETTLEMENT: archive.settlement_epochs,
        EntityType.ITEM: archive.item_epochs,
        EntityType.TRADITION: archive.tradition_epochs,
    }
    return thresholds.get(entity_type)


def score(rules: Rules, entity: EntityRow, *, bonds: int, mentions: int, age: int) -> int:
    weights = rules.archive
    population = stat(entity, "population")
    value: float = entity.power_level * weights.w_power_level
    value += min(weights.w_link_cap, bonds * weights.w_link)
    value += min(weights.w_mention_cap, mentions * weights.w_mention)
    value += weights.w_favorite if entity.favorite else 0
    value += max(0, weights.w_freshness - age * weights.w_freshness_decay)
    if population:
        value += min(weights.w_population_cap, math.log10(population + 1) * weights.w_population_log)
    if entity.status is not EntityStatus.CANON:
        value -= weights.w_not_living_penalty
    return round(value)


def archive_decision(rules: Rules, entity: EntityRow, importance: int, age: int) -> tuple[bool, str | None]:
    if entity.archive_override is ArchiveOverride.HISTORY:
        return True, ArchiveReason.MANUAL.value
    if entity.archive_override is ArchiveOverride.ATLAS or entity.favorite:
        return False, None
    if entity.status in ENDED and age >= rules.archive.dead_epochs:
        return True, (ArchiveReason.DEAD if entity.status is EntityStatus.DEAD else ArchiveReason.VANISHED).value
    if entity.status is EntityStatus.FULFILLED and age >= rules.archive.dead_epochs:
        return True, ArchiveReason.FULFILLED.value
    threshold = age_threshold(rules, entity.entity_type)
    if entity.entity_type not in PERMANENT_TYPES and threshold is not None and age >= threshold and importance < rules.archive.importance_threshold:
        return True, f"{age} {ArchiveReason.UNMENTIONED.value}"
    return False, None


async def _bond_counts(session: AsyncSession) -> dict[int, int]:
    counts: dict[int, int] = {}
    for column in (BondRow.source_node_id, BondRow.target_node_id):
        rows = await session.execute(select(column, func.count()).where(BondRow.state == BondState.ACTIVE).group_by(column))
        for node_id, count in rows:
            counts[node_id] = counts.get(node_id, 0) + int(count)
    return counts


async def _mentions(session: AsyncSession) -> dict[int, tuple[int, int]]:
    statement = (
        select(ChronicleEntityRow.entity_id, func.count(), func.max(ChronicleRow.epoch))
        .join(ChronicleRow, ChronicleRow.id == ChronicleEntityRow.chronicle_id)
        .group_by(ChronicleEntityRow.entity_id)
    )
    return {entity_id: (int(count), int(last or 0)) for entity_id, count, last in await session.execute(statement)}


async def compute(session: AsyncSession, rules: Rules, epoch: int) -> dict[int, ImportanceInfo]:
    bonds = await _bond_counts(session)
    mentions = await _mentions(session)
    result: dict[int, ImportanceInfo] = {}
    for entity in await session.scalars(select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED)):
        count, last = mentions.get(entity.id, (0, 0))
        last_mention = max(last, entity.birth_epoch)
        age = max(0, epoch - last_mention)
        importance = score(rules, entity, bonds=bonds.get(entity.id, 0), mentions=count, age=age)
        archived, reason = archive_decision(rules, entity, importance, age)
        result[entity.id] = ImportanceInfo(entity.id, importance, archived, reason, last_mention)
    return result


async def persist(session: AsyncSession, rules: Rules, epoch: int) -> int:
    infos = await compute(session, rules, epoch)
    changed = 0
    for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(infos)))):
        value = infos[entity.id].importance
        if entity.importance != value:
            entity.importance = value
            changed += 1
    await session.flush()
    return changed


async def any_missing(session: AsyncSession) -> bool:
    statement = select(EntityRow.id).where(EntityRow.status != EntityStatus.REJECTED, EntityRow.importance.is_(None)).limit(1)
    return await session.scalar(statement) is not None


async def persist_if_missing(session: AsyncSession, rules: Rules, epoch: int) -> int:
    return await persist(session, rules, epoch) if await any_missing(session) else 0


async def info_for(session: AsyncSession, rules: Rules, epoch: int, entity_id: int) -> ImportanceInfo:
    infos = await compute(session, rules, epoch)
    if entity_id not in infos:
        raise NotFoundError("No such record.")
    return infos[entity_id]


async def set_archive_mode(session: AsyncSession, rules: Rules, epoch: int, entity_id: int, mode: ArchiveMode) -> ImportanceInfo:
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError("No such record.")
    entity.archive_override = {ArchiveMode.HISTORY: ArchiveOverride.HISTORY, ArchiveMode.ATLAS: ArchiveOverride.ATLAS}.get(mode)
    await session.flush()
    return await info_for(session, rules, epoch, entity_id)


async def missing_images(session: AsyncSession, limit: int, entity_type: EntityType | None = None) -> list[EntityRow]:
    with_image = select(ImageRow.target_node_id)
    statement = select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED, EntityRow.id.not_in(with_image))
    if entity_type is not None:
        statement = statement.where(EntityRow.entity_type == entity_type)
    statement = statement.order_by(func.coalesce(EntityRow.importance, 0).desc(), EntityRow.id.desc()).limit(limit)
    return list(await session.scalars(statement))


async def archived_ids(session: AsyncSession, rules: Rules, epoch: int) -> set[int]:
    return {entity_id for entity_id, info in (await compute(session, rules, epoch)).items() if info.archived}
