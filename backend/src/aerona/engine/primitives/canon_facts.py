from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import FACT_OBJECT_MAX_LENGTH, FACT_PREDICATE_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import CanonFactRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import LIVING_STATUSES, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.rules.registry import Rules


class Predicate:
    LOCATED_IN = "is located in"
    CREATOR = "was created by"
    LANGUAGE = "speaks"
    WORSHIPS = "worships"
    DESCENDS = "descends from"


@dataclass(frozen=True)
class FactDraft:
    subject_entity_id: int
    predicate: str
    object_entity_id: int | None = None
    object_text: str | None = None


async def _living(session: AsyncSession, entity_id: int | None) -> EntityRow | None:
    if entity_id is None:
        return None
    entity = await session.get(EntityRow, entity_id)
    return entity if entity is not None and entity.status in LIVING_STATUSES else None


async def fact_exists(session: AsyncSession, draft: FactDraft) -> bool:
    statement = select(CanonFactRow.id).where(
        CanonFactRow.subject_entity_id == draft.subject_entity_id,
        CanonFactRow.predicate == draft.predicate[:FACT_PREDICATE_MAX_LENGTH],
        CanonFactRow.active.is_(True),
        CanonFactRow.object_entity_id.is_(None) if draft.object_entity_id is None else CanonFactRow.object_entity_id == draft.object_entity_id,
        CanonFactRow.object_text.is_(None) if draft.object_text is None else CanonFactRow.object_text == draft.object_text[:FACT_OBJECT_MAX_LENGTH],
    )
    return await session.scalar(statement.limit(1)) is not None


async def has_fact(session: AsyncSession, subject_id: int, predicate: str) -> bool:
    statement = select(CanonFactRow.id).where(CanonFactRow.subject_entity_id == subject_id, CanonFactRow.predicate == predicate, CanonFactRow.active.is_(True))
    return await session.scalar(statement.limit(1)) is not None


async def _derived_facts(session: AsyncSession, entity: EntityRow) -> list[FactDraft]:
    facts: list[FactDraft] = []
    if await _living(session, entity.location_id) is not None and entity.location_id is not None:
        facts.append(FactDraft(entity.id, Predicate.LOCATED_IN, object_entity_id=entity.location_id))
    if entity.creator_son_id is not None:
        son_name = await session.scalar(select(SonRow.name).where(SonRow.id == entity.creator_son_id))
        if son_name:
            facts.append(FactDraft(entity.id, Predicate.CREATOR, object_text=son_name))
    bonds = BondRepository(session)
    for bond in await bonds.outgoing(entity.id, BondKind.SPEAKS):
        language = await session.get(EntityRow, bond.target_node_id)
        if language is not None and language.entity_type is EntityType.LANGUAGE:
            facts.append(FactDraft(entity.id, Predicate.LANGUAGE, object_entity_id=language.id))
            break
    for bond in await bonds.outgoing(entity.id, BondKind.WORSHIPS):
        kind = await NodeRepository(session).kind_of(bond.target_node_id)
        if kind is NodeKind.ENTITY:
            facts.append(FactDraft(entity.id, Predicate.WORSHIPS, object_entity_id=bond.target_node_id))
        else:
            name = await NodeRepository(session).name_of(bond.target_node_id)
            if name:
                facts.append(FactDraft(entity.id, Predicate.WORSHIPS, object_text=name))
        break
    for bond in await bonds.outgoing(entity.id, BondKind.DESCENDS_FROM):
        if await NodeRepository(session).kind_of(bond.target_node_id) is NodeKind.ENTITY:
            facts.append(FactDraft(entity.id, Predicate.DESCENDS, object_entity_id=bond.target_node_id))
            break
    return facts


async def store_fact(session: AsyncSession, draft: FactDraft, epoch: int, *, source_entity_id: int | None, deterministic: bool) -> CanonFactRow:
    row = CanonFactRow(
        subject_entity_id=draft.subject_entity_id,
        predicate=draft.predicate[:FACT_PREDICATE_MAX_LENGTH],
        object_entity_id=draft.object_entity_id,
        object_text=draft.object_text[:FACT_OBJECT_MAX_LENGTH] if draft.object_text else None,
        epoch=epoch,
        source_entity_id=source_entity_id,
        deterministic=deterministic,
    )
    session.add(row)
    await session.flush()
    return row


async def certain_facts(session: AsyncSession, entity_ids: Iterable[int], epoch: int | None = None) -> int:
    written = 0
    for entity_id in dict.fromkeys(entity_ids):
        entity = await _living(session, entity_id)
        if entity is None:
            continue
        for draft in await _derived_facts(session, entity):
            if await has_fact(session, entity.id, draft.predicate):
                continue
            await store_fact(session, draft, epoch if epoch is not None else entity.birth_epoch, source_entity_id=entity.id, deterministic=True)
            written += 1
    return written


async def fact_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(CanonFactRow).where(CanonFactRow.active.is_(True))) or 0)


async def living_entity_ids(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(EntityRow.id).where(EntityRow.status.in_(list(LIVING_STATUSES))).order_by(EntityRow.id)))


async def seed_if_empty(session: AsyncSession) -> int:
    if await fact_count(session) > 0:
        return 0
    return await certain_facts(session, await living_entity_ids(session))


RECONCILED_PREDICATES = (Predicate.WORSHIPS, Predicate.LANGUAGE, Predicate.LOCATED_IN)


async def reconcile_derived_facts(session: AsyncSession) -> int:
    statement = select(CanonFactRow).where(
        CanonFactRow.active.is_(True),
        CanonFactRow.deterministic.is_(True),
        CanonFactRow.source_entity_id == CanonFactRow.subject_entity_id,
        CanonFactRow.predicate.in_(RECONCILED_PREDICATES),
    )
    current: dict[int, list[FactDraft]] = {}
    closed = 0
    for fact in list(await session.scalars(statement.order_by(CanonFactRow.id))):
        subject = await session.get(EntityRow, fact.subject_entity_id)
        if subject is None:
            continue
        if subject.id not in current:
            current[subject.id] = await _derived_facts(session, subject)
        if any(
            draft.predicate == fact.predicate and draft.object_entity_id == fact.object_entity_id and draft.object_text == fact.object_text
            for draft in current[subject.id]
        ):
            continue
        fact.active = False
        closed += 1
    await session.flush()
    return closed


async def rebuild_certain_facts(session: AsyncSession) -> int:
    await reconcile_derived_facts(session)
    return await certain_facts(session, await living_entity_ids(session))


async def apply_fate_facts(session: AsyncSession, rules: Rules, drafts: Sequence[FactDraft], epoch: int, judged_ids: Iterable[int]) -> list[CanonFactRow]:
    judged = set(judged_ids)
    stored: list[CanonFactRow] = []
    for draft in drafts[: rules.fate.canon_facts_max]:
        if not draft.predicate.strip() or await _living(session, draft.subject_entity_id) is None:
            continue
        object_id = draft.object_entity_id if await session.get(EntityRow, draft.object_entity_id or 0) is not None else None
        text = draft.object_text.strip() if draft.object_text else None
        if object_id is None and not text:
            continue
        source = draft.subject_entity_id if draft.subject_entity_id in judged else None
        cleaned = FactDraft(draft.subject_entity_id, draft.predicate.strip(), object_id, None if object_id is not None else text)
        if await fact_exists(session, cleaned):
            continue
        stored.append(await store_fact(session, cleaned, epoch, source_entity_id=source, deterministic=False))
    return stored


async def add_manual_fact(session: AsyncSession, draft: FactDraft, epoch: int) -> CanonFactRow:
    if await _living(session, draft.subject_entity_id) is None:
        raise NotFoundError("No such record.")
    if not draft.predicate.strip():
        raise ValidationFailedError("A fact needs a relation.")
    if draft.object_entity_id is None and not (draft.object_text or "").strip():
        raise ValidationFailedError("A fact needs an object.")
    if draft.object_entity_id is not None and await session.get(EntityRow, draft.object_entity_id) is None:
        raise NotFoundError("No such object record.")
    return await store_fact(session, draft, epoch, source_entity_id=None, deterministic=False)


async def retract_fact(session: AsyncSession, fact_id: int) -> CanonFactRow:
    fact = await session.get(CanonFactRow, fact_id)
    if fact is None:
        raise NotFoundError("No such fact.")
    fact.active = False
    await session.flush()
    return fact


async def facts_about(session: AsyncSession, entity_id: int, limit: int) -> list[CanonFactRow]:
    statement = (
        select(CanonFactRow)
        .where(CanonFactRow.active.is_(True), (CanonFactRow.subject_entity_id == entity_id) | (CanonFactRow.object_entity_id == entity_id))
        .order_by(CanonFactRow.id.desc())
        .limit(limit)
    )
    return list(await session.scalars(statement))
