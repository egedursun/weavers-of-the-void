from collections.abc import Collection, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import BOND_KINDS
from aerona.catalog.civilization import TIER_LABELS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import CanonFactRow, LexemeRow
from aerona.db.tables.society import CommunityRelationRow, CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import CivilizationTier, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.war import WarStatus
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import (
    BondEndpoint,
    BondLine,
    ClassShare,
    CommunityRelationLine,
    EntityAuthor,
    EntityDetailContext,
    EntityLineContext,
    Granary,
    SocietyLines,
    WarLine,
)
from aerona.prompts.contexts.common import EntityLineItem, LabelValue, LexiconWord, NamedRecord, WorldItem
from aerona.rules.registry import Rules
from aerona.tools.framework.validation import label_of

PERCENT = 100
CLASS_KEYS = ("farmer", "artisan", "merchant", "priest", "warrior", "scribe")
AUTHORS = {
    EntityOrigin.SON: EntityAuthor.SON,
    EntityOrigin.CREATOR: EntityAuthor.CREATOR,
    EntityOrigin.ENGINE: EntityAuthor.WORLD,
    EntityOrigin.MORTAL: EntityAuthor.WORLD,
    EntityOrigin.COSMOS: EntityAuthor.WORLD,
}
VISIBLE_STATES = (BondState.ACTIVE,)


async def line_item(session: AsyncSession, entity: EntityRow) -> EntityLineItem:
    location = await session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
    return EntityLineItem(
        id=entity.id,
        name=entity.name,
        type_label=ENTITY_TYPES[entity.entity_type].label,
        subtype=entity.subtype,
        power_level=entity.power_level,
        location=location.name if location is not None else None,
        status_label=None if entity.status is EntityStatus.CANON else label_of(entity.status),
    )


async def entity_line(session: AsyncSession, entity: EntityRow, with_location: bool = True) -> str:
    return render(PromptId.ENTITY_LINE, EntityLineContext(entity=await line_item(session, entity), with_location=with_location))


async def entity_lines(session: AsyncSession, entities: Sequence[EntityRow]) -> str:
    return "\n".join([await entity_line(session, entity) for entity in entities])


async def _bond_lines(session: AsyncSession, bonds: Sequence[BondRow], entity_id: int) -> list[BondLine]:
    nodes = NodeRepository(session)
    others = [bond.other_end(entity_id) for bond in bonds]
    names = await nodes.names_of(others)
    kinds = await nodes.kinds_of(others)
    return [
        BondLine(
            label=BOND_KINDS[bond.kind].label,
            other=BondEndpoint(kind=kinds[other], id=other, name=names.get(other, "")),
            description=bond.description,
        )
        for bond, other in zip(bonds, others, strict=True)
        if other in kinds
    ]


def _stats(entity: EntityRow) -> list[LabelValue]:
    spec = ENTITY_TYPES[entity.entity_type]
    values: list[LabelValue] = []
    for field in spec.stats:
        value = getattr(entity.stats, field.key, None)
        if value is not None:
            values.append(LabelValue(label=field.label, value=str(value)))
    return values


async def _lexicon(session: AsyncSession, entity: EntityRow, limit: int) -> list[LexiconWord] | None:
    if entity.entity_type is not EntityType.LANGUAGE:
        return None
    statement = select(LexemeRow).where(LexemeRow.language_entity_id == entity.id).order_by(LexemeRow.id).limit(limit)
    return [
        LexiconWord(word=row.word, meaning=row.meaning, kind=row.part_of_speech.value if row.part_of_speech else None)
        for row in await session.scalars(statement)
    ]


async def society_lines(session: AsyncSession, rules: Rules, entity: EntityRow) -> SocietyLines | None:
    society = await session.get(CommunitySocietyRow, entity.id)
    relations = list(
        await session.scalars(
            select(CommunityRelationRow)
            .where(or_(CommunityRelationRow.entity_a_id == entity.id, CommunityRelationRow.entity_b_id == entity.id))
            .order_by(CommunityRelationRow.value)
        )
    )
    wars = list(
        await session.execute(
            select(WarRow, EntityRow.name)
            .join(WarSideRow, WarSideRow.war_id == WarRow.id)
            .join(EntityRow, EntityRow.id == WarRow.event_entity_id)
            .where(WarSideRow.entity_id == entity.id, WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        )
    )
    if society is None and not relations and not wars and entity.civ_tier is None and entity.sanity is None:
        return None
    others = [relation.entity_b_id if relation.entity_a_id == entity.id else relation.entity_a_id for relation in relations]
    names = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(others)))} if others else {}
    limit = rules.context.inspect_canon_facts
    return SocietyLines(
        tier_label=TIER_LABELS[CivilizationTier(entity.civ_tier)] if entity.civ_tier is not None else None,
        sanity=entity.sanity,
        clouded=entity.sanity is not None and entity.sanity < rules.cosmic_horror.clouding_threshold,
        classes=[
            ClassShare(label=key, share=round(getattr(society, f"share_{key}") * PERCENT), satisfaction=getattr(society, f"satisfaction_{key}"))
            for key in CLASS_KEYS
        ]
        if society is not None
        else [],
        granary=Granary(
            food=society.stock_food,
            ore=society.stock_ore,
            goods=society.stock_goods,
            bread_price=society.price_food,
            ore_price=society.price_ore,
            goods_price=society.price_goods,
        )
        if society is not None
        else None,
        relations=[
            CommunityRelationLine(
                id=other,
                name=names.get(other, "?"),
                label="hostile" if relation.value < 0 else "friendly",
                value=relation.value,
                blood_feud=relation.blood_feud_since_epoch is not None,
            )
            for relation, other in list(zip(relations, others, strict=True))[:limit]
        ],
        wars=[WarLine(id=war.event_entity_id, name=name, clashes=war.battles) for war, name in wars],
    )


async def fact_lines(session: AsyncSession, rules: Rules, entity: EntityRow) -> list[str]:
    facts = list(
        await session.scalars(
            select(CanonFactRow)
            .where(CanonFactRow.active.is_(True), or_(CanonFactRow.subject_entity_id == entity.id, CanonFactRow.object_entity_id == entity.id))
            .order_by(CanonFactRow.id.desc())
            .limit(rules.context.inspect_canon_facts)
        )
    )
    ids = {fact.subject_entity_id for fact in facts} | {fact.object_entity_id for fact in facts if fact.object_entity_id is not None}
    names = await NodeRepository(session).names_of(sorted(ids))
    lines: list[str] = []
    for fact in facts:
        subject = names.get(fact.subject_entity_id, "") if fact.subject_entity_id != entity.id else ""
        target = names.get(fact.object_entity_id, "") if fact.object_entity_id is not None else ""
        lines.append(" ".join(part for part in (subject, fact.predicate, fact.object_text or target) if part))
    return lines


async def entity_detail(session: AsyncSession, rules: Rules, entity: EntityRow) -> str:
    bonds = BondRepository(session)
    outgoing = [bond for bond in await bonds.outgoing(entity.id) if bond.state in VISIBLE_STATES]
    incoming = [bond for bond in await bonds.incoming(entity.id) if bond.state in VISIBLE_STATES]
    author_son = await session.get(SonRow, entity.creator_son_id) if entity.creator_son_id is not None else None
    world = await session.get(WorldRow, entity.world_id)
    contents = await EntityRepository(session).contents(entity.id)
    tags = sorted(await EntityRepository(session).tags(entity.id))
    context = EntityDetailContext(
        entity=await line_item(session, entity),
        author=AUTHORS.get(entity.origin, EntityAuthor.UNKNOWN),
        author_son=NamedRecord(id=author_son.id, name=author_son.name) if author_son is not None else None,
        age=entity.birth_epoch,
        world=WorldItem(id=world.id, name=world.name) if world is not None else None,
        domain=DOMAIN_LABELS[entity.domain] if entity.domain is not None else None,
        tags=tags,
        stats=_stats(entity),
        description=entity.description,
        fate_note=entity.fate_note,
        outgoing=await _bond_lines(session, outgoing, entity.id),
        incoming=await _bond_lines(session, incoming, entity.id),
        contents=[await line_item(session, item) for item in contents],
        lexicon=await _lexicon(session, entity, rules.context.inspect_lexicon_words),
        society=await society_lines(session, rules, entity),
        facts=await fact_lines(session, rules, entity),
    )
    return render(PromptId.ENTITY_DETAIL, context)


async def search(
    session: AsyncSession,
    query: str,
    *,
    entity_type: EntityType | None,
    limit: int,
    world_ids: Collection[int] | None = None,
    entity_ids: Collection[int] | None = None,
) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED)
    text = query.strip()
    if text:
        pattern = f"%{text}%"
        statement = statement.where(or_(EntityRow.name.ilike(pattern), EntityRow.description.ilike(pattern), EntityRow.subtype.ilike(pattern)))
    if entity_type is not None:
        statement = statement.where(EntityRow.entity_type == entity_type)
    if world_ids is not None:
        statement = statement.where(EntityRow.world_id.in_(list(world_ids)))
    if entity_ids is not None:
        statement = statement.where(EntityRow.id.in_(list(entity_ids)))
    return list(await session.scalars(statement.order_by(EntityRow.id.desc()).limit(limit)))
