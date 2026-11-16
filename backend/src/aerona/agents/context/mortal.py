from sqlalchemy import select

from aerona.agents.context.ages_lines import mortal_ages_lines
from aerona.agents.context.agrarian_lines import mortal_agrarian_lines
from aerona.agents.context.arts_lines import mortal_arts_lines
from aerona.agents.context.belonging_lines import mortal_belonging_lines
from aerona.agents.context.biology_lines import mortal_biology_lines
from aerona.agents.context.climes_lines import mortal_climes_lines
from aerona.agents.context.collective_lines import mortal_collective_lines
from aerona.agents.context.coupling_lines import register_lines
from aerona.agents.context.crafts_lines import mortal_crafts_lines
from aerona.agents.context.customs_lines import mortal_customs_lines
from aerona.agents.context.cycle_lines import mortal_cycle_lines
from aerona.agents.context.dominion_lines import mortal_dominion_lines
from aerona.agents.context.economy import resource_yield, stores_for
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.entity_line import line_items
from aerona.agents.context.era_lines import mortal_era_lines
from aerona.agents.context.evolution_lines import mortal_evolution_lines
from aerona.agents.context.folkways_lines import mortal_folkways_lines
from aerona.agents.context.gatherings import gathering_lines, site_lines
from aerona.agents.context.geography import environment_facts, region_records, weather_words
from aerona.agents.context.intrigue import estate_lines, intrigue_lines, letter_lines, title_lines
from aerona.agents.context.justice import case_lines, proposal_lines
from aerona.agents.context.language_lines import language_lines
from aerona.agents.context.law_lines import mortal_law_lines
from aerona.agents.context.lifecycle_lines import mortal_grounds_lines
from aerona.agents.context.lineage import lineage_lines
from aerona.agents.context.means_lines import mortal_economy_lines, mortal_honours_lines, mortal_means_lines
from aerona.agents.context.minds_lines import mortal_minds_lines
from aerona.agents.context.mythic_lines import mortal_magic_lines
from aerona.agents.context.nature_lines import mortal_nature_lines
from aerona.agents.context.operations_lines import mortal_operations_lines
from aerona.agents.context.recent_chronicle import prompt_text, recent_rows
from aerona.agents.context.regime_lines import mortal_regime_lines
from aerona.agents.context.research import research_for
from aerona.agents.context.sacred_lines import mortal_sacred_lines
from aerona.agents.context.scope import Scope
from aerona.agents.context.society import home_for
from aerona.agents.context.statecraft import affairs_lines, statecraft_lines
from aerona.agents.context.tongue_lines import mortal_tongue_lines
from aerona.agents.context.transform_lines import mantling_line, prospect_lines
from aerona.agents.context.urban_lines import mortal_urban_lines
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_line import world_line
from aerona.agents.context.world_summary import route_lines
from aerona.agents.context.world_view_lines import mortal_world_lines
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.chronicle import ChronicleRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import FolkBeliefRow, LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.lore.rumours import heard_by
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.prompts.contexts.common import ChronicleRow, LabelValue, LexiconWord, NamedRecord
from aerona.prompts.contexts.mortal import (
    FolkGodName,
    HeardRumour,
    HomeLine,
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


async def mortal_land(scope: Scope, land: EntityRow, neighbours: list[EntityRow | None]) -> MortalLand:
    record = next((item for item in await region_records(scope, land.world_id) if item.id == land.id), None)
    ground = await scope.session.get(RegionEnvironmentRow, land.id)
    book = await EnvironmentBook.load(scope.session, scope.rules, scope.epoch)
    facts = environment_facts(scope.rules, ground)
    soil = f"{facts['soil']} soil" if facts.get("soil") else None
    described = ", ".join(str(value) for value in (facts.get("land"), facts.get("climate"), soil, facts.get("river"), facts.get("harvest")) if value)
    return MortalLand(
        id=land.id,
        name=land.name,
        elevation_label=record.elevation_class.value.replace("_", " ") if record is not None else None,
        coastal=record.coastal if record is not None else False,
        neighbours=[NamedRecord(id=region.id, name=region.name) for region in neighbours if region is not None],
        ground=described or None,
        weather=weather_words(scope, book, ground),
    )


async def heard_rumours(scope: Scope, me: EntityRow) -> list[HeardRumour]:
    home = me.location_id if me.entity_type is EntityType.MORTAL else me.id
    if home is None:
        return []
    heard = await heard_by(scope.session, home)
    return [
        HeardRumour(age=incident.epoch, fidelity=rumour.fidelity, text=prompt_text(text))
        for rumour, incident, text in heard[: scope.rules.rumours.context_lines]
    ]


async def hearth_for(scope: Scope, me: EntityRow) -> HomeLine | None:
    home = await home_for(scope.session, me, scope.rules)
    if home is None:
        return None
    bits = await lineage_lines(scope.session, scope.rules, me)
    plots = await intrigue_lines(scope.session, scope.rules, me)
    letters, opinions = await letter_lines(scope.session, scope.rules, me)
    return home.model_copy(
        update={
            "looks": bits.looks,
            "gift": bits.gift,
            "household": bits.household,
            "dwelling": bits.dwelling,
            "secrets": plots.secrets,
            "leverage": plots.leverage,
            "mask": plots.mask,
            "scheme": plots.scheme,
            "true_names": plots.names,
            "beliefs": plots.beliefs,
            "letters": letters,
            "opinions": opinions,
            "titles": await title_lines(scope.session, me),
            "estates": await estate_lines(scope.session, me),
            "gatherings": await gathering_lines(scope.session, scope.rules, me, scope.epoch),
            "sites": await site_lines(scope.session, scope.rules, me),
            "proposals": await proposal_lines(scope.session, me),
            "cases": await case_lines(scope.session, me, scope.epoch),
            "abroad": await statecraft_lines(scope.session, me),
            "affairs": await affairs_lines(scope.session, me),
            "dominion": await mortal_dominion_lines(scope, me),
            "magic": await mortal_magic_lines(scope, me),
            "speech": await mortal_tongue_lines(scope, me),
            "contagion": await mortal_evolution_lines(scope, me),
            "streets": await mortal_urban_lines(scope, me),
            "courts": await mortal_law_lines(scope, me),
            "crowds": await mortal_collective_lines(scope, me),
            "obligations": await mortal_cycle_lines(scope, me),
            "rule": await mortal_regime_lines(scope, me),
            "land": await mortal_agrarian_lines(scope, me),
            "operations": await mortal_operations_lines(scope, me),
            "sacred": await mortal_sacred_lines(scope, me),
            "pursuits": await mortal_arts_lines(scope, me),
            "tales": await mortal_ages_lines(scope, me),
            "folkways": await mortal_folkways_lines(scope, me),
            "folk_customs": await mortal_customs_lines(scope, me),
            "crafts": await mortal_crafts_lines(scope, me),
            "climes": await mortal_climes_lines(scope, me),
            "belonging": await mortal_belonging_lines(scope, me),
            "eras": await mortal_era_lines(scope, me),
            "nature": await mortal_nature_lines(scope, me),
            "means": await mortal_means_lines(scope, me),
            "economy": await mortal_economy_lines(scope, me),
            "honours": await mortal_honours_lines(scope, me),
            "world_nature": await mortal_world_lines(scope, me),
            "biology": await mortal_biology_lines(scope, me),
            "grounds": await mortal_grounds_lines(scope, me),
            "made_world": await mortal_minds_lines(scope, me),
        }
    )


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
    mantle = await mantling_line(scope.session, me.id)
    circle = [me.id, *[node for node in (me.location_id, me.affiliated_entity_id) if node is not None]]
    changes = ([mantle] if mantle else []) + await prospect_lines(scope.session, scope.rules, subjects=circle)
    return MortalContextContext(
        rules=scope.rules,
        full=full,
        changes=changes,
        registers=await register_lines(scope.session, me),
        world_header=await world_header(scope, me.world_id, short=True),
        world_line=await world_line(scope, me.world_id),
        self_detail=await entity_detail(scope, me, private=True),
        character=[LabelValue(label=key, value=value) for key, value in (depth.specifics if depth is not None else {}).items()],
        god=await mortal_god(scope, me),
        folk_gods=[FolkGodName(name=belief.local_name or "", son_id=belief.god_node_id, story=belief.account) for (belief,) in beliefs if belief.local_name],
        language=await spoken_language(scope, me),
        land=await mortal_land(scope, land_row, neighbours) if land_row is not None else None,
        near=await line_items(scope.session, near[: scope.rules.context.son_location_tree_lines * NEAR_LIMIT_FACTOR]),
        recent_events=await recent_rows(scope, scope.rules.mortal_tools.ctx_event_lines, me.world_id),
        known=await known_knowledge(scope, me),
        resources=[
            OwnedResource(
                id=entity.id, name=entity.name, abundance=int(getattr(entity.stats, "abundance", 0) or 0), yields=await resource_yield(scope.session, entity.id)
            )
            for entity in await owned(scope, me, EntityType.RESOURCE)
        ],
        stores=await stores_for(scope.session, scope.rules, me),
        research=await research_for(scope.session, me),
        home=await hearth_for(scope, me),
        items=[NamedRecord(id=entity.id, name=entity.name) for entity in await owned(scope, me, EntityType.ITEM)],
        mentions=[ChronicleRow(age=row.epoch, text=prompt_text(row.text)) for row in reversed(mentions)],
        rumours=await heard_rumours(scope, me),
        languages=await language_lines(scope, me.world_id),
        routes=[route for route in await route_lines(scope) if scope.world_name(me.world_id) in (route.world_a, route.world_b)],
    )
