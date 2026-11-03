from sqlalchemy import select

from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.entity_line import line_items
from aerona.agents.context.geography import region_records
from aerona.agents.context.language_lines import language_lines
from aerona.agents.context.recent_chronicle import prompt_text, recent_rows
from aerona.agents.context.scope import Scope
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_line import world_line
from aerona.agents.context.world_summary import route_lines
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.chronicle import ChronicleRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import FolkBeliefRow, LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.prompts.contexts.common import ChronicleRow, LabelValue, LexiconWord, NamedRecord
from aerona.prompts.contexts.mortal import (
    FolkGodName,
    KnowledgeItem,
    MortalContextContext,
    MortalGod,
    MortalGodKind,
    MortalLand,
    MortalLanguage,
    OwnedResource,
)

NEAR_LIMIT_FACTOR = 1


async def horizon_regions(scope: Scope, me: EntityRow, atlas: RegionAtlas) -> set[int]:
    home = atlas.top_region(me.id)
    if home is None:
        return set()
    records = {record.id: record for record in await region_records(scope, me.world_id)}
    record = records.get(home)
    return {home, *(record.neighbours if record is not None else [])}


async def near_entities(scope: Scope, me: EntityRow, atlas: RegionAtlas, regions: set[int]) -> list[EntityRow]:
    if not regions:
        return []
    candidates = await scope.session.scalars(
        select(EntityRow).where(EntityRow.world_id == me.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.id != me.id).order_by(EntityRow.id)
    )
    return [entity for entity in candidates if atlas.top_region(entity.id) in regions or entity.id in regions]


async def mortal_god(scope: Scope, me: EntityRow) -> MortalGod:
    patron = await BondRepository(scope.session).patron(me.id)
    if patron is None:
        return MortalGod(kind=MortalGodKind.NONE)
    son = await scope.session.get(SonRow, patron)
    if son is not None:
        return MortalGod(
            kind=MortalGodKind.SON,
            id=son.id,
            name=son.name,
            title=son.title,
            domain_1=DOMAIN_LABELS[son.domain_primary],
            domain_2=DOMAIN_LABELS[son.domain_secondary],
        )
    foreign = await scope.session.get(ForeignGodRow, patron)
    if foreign is not None:
        return MortalGod(kind=MortalGodKind.FOREIGN_GOD, id=foreign.id, name=foreign.name, title=foreign.title)
    return MortalGod(kind=MortalGodKind.NONE)


async def spoken_language(scope: Scope, me: EntityRow) -> MortalLanguage | None:
    bonds = await BondRepository(scope.session).outgoing(me.id, BondKind.SPEAKS)
    language = await scope.session.get(EntityRow, bonds[0].target_node_id) if bonds else None
    if language is None:
        return None
    words = await scope.session.scalars(
        select(LexemeRow).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id.desc()).limit(scope.rules.context.son_words_per_language)
    )
    return MortalLanguage(id=language.id, name=language.name, words=[LexiconWord(word=word.word, meaning=word.meaning) for word in words])


async def owned(scope: Scope, me: EntityRow, entity_type: EntityType | None) -> list[EntityRow]:
    bonds = await BondRepository(scope.session).outgoing(me.id, BondKind.OWNS)
    found = []
    for bond in bonds:
        entity = await scope.session.get(EntityRow, bond.target_node_id)
        if entity is not None and entity.status is EntityStatus.CANON and (entity_type is None or entity.entity_type is entity_type):
            found.append(entity)
    return found


async def known_knowledge(scope: Scope, me: EntityRow) -> list[KnowledgeItem]:
    bonds = await BondRepository(scope.session).outgoing(me.id, BondKind.KNOWS)
    items = []
    for bond in bonds:
        entity = await scope.session.get(EntityRow, bond.target_node_id)
        if entity is not None and entity.knowledge_branch is not None:
            label = entity.knowledge_branch.value.replace("_", " ")
            items.append(KnowledgeItem(id=entity.id, name=entity.name, branch_label=label, level=knowledge_level(scope.rules, entity)))
    return items


async def mortal_context(scope: Scope, me: EntityRow, full: bool = False) -> MortalContextContext:
    atlas = await RegionAtlas.load(scope.session)
    regions = await horizon_regions(scope, me, atlas)
    home = atlas.top_region(me.id)
    land_row = await scope.session.get(EntityRow, home) if home is not None else None
    neighbours = [await scope.session.get(EntityRow, region_id) for region_id in sorted(regions - {home} if home else set())]
    near = await near_entities(scope, me, atlas, regions)
    mentions = await ChronicleRepository(scope.session).mentioning(me.id, scope.rules.mortal_tools.ctx_event_lines)
    beliefs = await scope.session.execute(select(FolkBeliefRow).where(FolkBeliefRow.people_entity_id == me.id))
    depth = me.depth
    return MortalContextContext(
        rules=scope.rules,
        full=full,
        world_header=await world_header(scope, me.world_id, short=True),
        world_line=await world_line(scope, me.world_id),
        self_detail=await entity_detail(scope, me, private=True),
        character=[LabelValue(label=key, value=value) for key, value in (depth.specifics if depth is not None else {}).items()],
        god=await mortal_god(scope, me),
        folk_gods=[FolkGodName(name=belief.local_name or "", son_id=belief.god_node_id, story=belief.account) for (belief,) in beliefs if belief.local_name],
        language=await spoken_language(scope, me),
        land=MortalLand(
            id=land_row.id,
            name=land_row.name,
            neighbours=[NamedRecord(id=region.id, name=region.name) for region in neighbours if region is not None],
        )
        if land_row is not None
        else None,
        near=await line_items(scope.session, near[: scope.rules.context.son_location_tree_lines * NEAR_LIMIT_FACTOR]),
        recent_events=await recent_rows(scope, scope.rules.mortal_tools.ctx_event_lines, me.world_id),
        known=await known_knowledge(scope, me),
        resources=[
            OwnedResource(id=entity.id, name=entity.name, abundance=int(getattr(entity.stats, "abundance", 0) or 0))
            for entity in await owned(scope, me, EntityType.RESOURCE)
        ],
        items=[NamedRecord(id=entity.id, name=entity.name) for entity in await owned(scope, me, EntityType.ITEM)],
        mentions=[ChronicleRow(age=row.epoch, text=prompt_text(row.text)) for row in reversed(mentions)],
        languages=await language_lines(scope, me.world_id),
        routes=[route for route in await route_lines(scope) if scope.world_name(me.world_id) in (route.world_a, route.world_b)],
    )
