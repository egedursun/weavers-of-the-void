from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.transform import TransformationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.transform import TransformKind, TransformTrigger
from aerona.rules.registry import Rules

K = TransformKind
LINKS = (
    (K.DEIFICATION, BondKind.DESCENDS_FROM, EntityType.MORTAL, EntityFlag.DEIFIED, None),
    (K.UPLIFT, BondKind.DESCENDS_FROM, EntityType.SPECIES, EntityFlag.SPECIES_BECAME_PEOPLE, None),
    (K.SPIRIT_RISING, BondKind.DESCENDS_FROM, EntityType.MORTAL, None, "their spirit"),
    (K.BEAST_PROMOTION, BondKind.DESCENDS_FROM, EntityType.SPECIES, None, "the greatest of its kind"),
    (K.MANIFESTATION, BondKind.SOURCE_OF, EntityType.LEGEND, None, "born of belief"),
)


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(sorted(ids))))}


async def backfill_transformations(session: AsyncSession, rules: Rules, epoch: int) -> int:
    del rules, epoch
    known = {(row.kind, row.subject_node_id, row.result_node_id) for row in await session.scalars(select(TransformationRow))}
    found: list[tuple[TransformKind, int, int, int]] = []
    for kind, bond_kind, subject_type, flag, description in LINKS:
        statement = (
            select(BondRow)
            .join(EntityRow, EntityRow.id == (BondRow.source_node_id if kind is K.MANIFESTATION else BondRow.target_node_id))
            .where(BondRow.kind == bond_kind, EntityRow.entity_type == subject_type)
        )
        if description is not None:
            statement = statement.where(BondRow.description == description)
        for bond in await session.scalars(statement.order_by(BondRow.id)):
            subject, result = (bond.source_node_id, bond.target_node_id) if kind is K.MANIFESTATION else (bond.target_node_id, bond.source_node_id)
            if flag is not None:
                marked = await session.scalar(select(EntityFlagRow.entity_id).where(EntityFlagRow.entity_id == subject, EntityFlagRow.flag == flag))
                if marked is None:
                    continue
            found.append((kind, subject, result, bond.epoch))
    for son in await session.scalars(select(SonRow).where(SonRow.corpse_entity_id.is_not(None)).order_by(SonRow.id)):
        found.append((K.DEAD_GOD, son.id, son.corpse_entity_id or 0, son.death_epoch or 0))
    names = await names_of(session, {node for _, subject, result, _ in found for node in (subject, result)})
    added = 0
    for kind, subject, result, when in found:
        if (kind, subject, result) in known or subject not in names or result not in names:
            continue
        known.add((kind, subject, result))
        session.add(
            TransformationRow(
                kind=kind,
                epoch=max(0, when),
                trigger=TransformTrigger.BACKFILL,
                subject_node_id=subject,
                result_node_id=result,
                subject_name=names[subject],
                result_name=names[result],
                undo=[],
                locked=[],
            )
        )
        added += 1
    await session.flush()
    return added
