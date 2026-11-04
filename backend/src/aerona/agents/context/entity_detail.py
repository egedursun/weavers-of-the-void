from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.bond_lines import bond_line_lists
from aerona.agents.context.entity_line import line_item, line_items
from aerona.agents.context.scope import Scope
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import ModifierOp
from aerona.engine.body.describe import body_lines
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.incidents import last_incident, recent_chain
from aerona.engine.interconnect.registry import Exposure
from aerona.engine.interconnect.sources import reason_text
from aerona.engine.mind.describe import mind_lines
from aerona.engine.primitives.modifiers import ModifierIndex
from aerona.engine.primitives.stats import base_stat
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import EntityAuthor, EntityDetailContext
from aerona.prompts.contexts.common import LabelValue, LexiconWord, NamedRecord, WorldItem
from aerona.tools.framework.economy_lines import economy_block
from aerona.tools.framework.views import fact_lines, society_lines

STAT_SKIP = frozenset({"kind"})
AUTHORS = {
    EntityOrigin.SON: EntityAuthor.SON,
    EntityOrigin.CREATOR: EntityAuthor.CREATOR,
    EntityOrigin.ENGINE: EntityAuthor.WORLD,
    EntityOrigin.MORTAL: EntityAuthor.WORLD,
    EntityOrigin.COSMOS: EntityAuthor.WORLD,
}
CONTENT_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD)


def stat_values(entity: EntityRow) -> list[LabelValue]:
    spec = ENTITY_TYPES[entity.entity_type]
    values = entity.stats.model_dump(exclude_none=True)
    found: list[LabelValue] = []
    for key, value in values.items():
        if key in STAT_SKIP:
            continue
        field = spec.stat(key)
        found.append(LabelValue(label=field.label if field else key.replace("_", " "), value=str(value)))
    return found


async def entity_detail_context(scope: Scope, entity: EntityRow, *, private: bool = False) -> EntityDetailContext:
    session = scope.session
    location = await session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
    son = await session.get(SonRow, entity.creator_son_id) if entity.creator_son_id is not None else None
    outgoing, incoming = await bond_line_lists(session, entity.id)
    contents = list(
        await session.scalars(select(EntityRow).where(EntityRow.location_id == entity.id, EntityRow.status.in_(CONTENT_STATUSES)).order_by(EntityRow.id))
    )
    context = scope.rules.context
    lexicon = None
    if entity.entity_type is EntityType.LANGUAGE:
        words = await session.scalars(
            select(LexemeRow).where(LexemeRow.language_entity_id == entity.id).order_by(LexemeRow.id.desc()).limit(context.inspect_lexicon_words)
        )
        lexicon = [LexiconWord(word=word.word, meaning=word.meaning) for word in words]
    return EntityDetailContext(
        entity=line_item(entity, location.name if location else None),
        author=EntityAuthor.SON if son is not None else AUTHORS.get(entity.origin, EntityAuthor.UNKNOWN),
        author_son=NamedRecord(id=son.id, name=son.name) if son is not None else None,
        age=entity.birth_epoch,
        world=WorldItem(id=entity.world_id, name=scope.world_name(entity.world_id)) if scope.multi_world else None,
        domain=DOMAIN_LABELS[entity.domain] if entity.domain else None,
        tags=await EntityRepository(session).tags(entity.id),
        stats=stat_values(entity),
        description=entity.description,
        history=entity.depth.history or None if entity.depth is not None else None,
        fate_note=entity.fate_note,
        outgoing=outgoing,
        incoming=incoming,
        contents=await line_items(session, contents, with_location=False),
        lexicon=lexicon,
        society=await society_lines(session, scope.rules, entity),
        facts=await fact_lines(session, scope.rules, entity),
        body=await body_lines(session, scope.rules, entity, private=private),
        mind=await mind_lines(session, scope.rules, entity, scope.epoch, private=private),
        effects=[
            *await effect_lines(session, entity, scope.epoch),
            *await mechanic_lines(session, entity, scope.epoch, scope.rules.context.mechanic_window_epochs),
        ],
        chain=chain.line if (chain := await recent_chain(session, entity.id, scope.rules.incidents.chain_depth)) is not None else None,
        economy=await economy_block(session, scope.rules, entity),
    )


async def mechanic_lines(session: AsyncSession, entity: EntityRow, epoch: int, window: int) -> list[str]:
    lines: list[str] = []
    for mechanic in sorted(REGISTERED.values(), key=lambda item: item.key):
        if mechanic.exposure is not Exposure.CONTEXT or entity.entity_type.value not in mechanic.targets:
            continue
        last = await last_incident(session, entity.id, mechanic.templates)
        if last is None or epoch - last.epoch > window or last.chronicle_id is None:
            continue
        chronicle = await session.get(ChronicleRow, last.chronicle_id)
        if chronicle is not None:
            lines.append(f"{mechanic.title} (age {last.epoch}): {chronicle.text}")
    return lines


async def effect_lines(session: AsyncSession, entity: EntityRow, epoch: int) -> list[str]:
    index = await ModifierIndex.load(session, epoch, [entity.id])
    lines: list[str] = []
    for key in index.keys_of(entity.id):
        base = base_stat(entity, key)
        breakdown = index.breakdown(entity.id, key, float(base or 0))
        for item in breakdown.applied:
            source = await session.get(EntityRow, item.source_node_id) if item.source_node_id is not None else None
            sign = f"{item.magnitude:+g}" if item.op is ModifierOp.ADD else f"x{item.magnitude:g}"
            lines.append(f"{key.replace('_', ' ')} {sign}: {reason_text(item.reason_key, source.name if source is not None else None)}")
    return lines


async def entity_detail(scope: Scope, entity: EntityRow, *, private: bool = False) -> str:
    return render(PromptId.ENTITY_DETAIL, await entity_detail_context(scope, entity, private=private))
