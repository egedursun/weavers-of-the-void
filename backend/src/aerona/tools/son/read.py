from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.powers import unlocked_power_slots
from aerona.catalog.rarities import RARITY_LABELS
from aerona.catalog.stats import max_hp
from aerona.constants.tool_inputs import QUERY_MAX
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.prompts import PromptId, SonToolId, render
from aerona.prompts.contexts.blocks import InspectSiblingContext, RelationToViewer, SummarySection
from aerona.prompts.tools.results import CommonResult, SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import EmptyInput, ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost
from aerona.tools.framework.validation import fail, label_of
from aerona.tools.framework.views import entity_detail, entity_lines, line_item, search
from aerona.tools.son.support import has_covenant, relation

READ = ToolMeta(ActionKind.OTHER, no_cost, read_only=True)


class WorldSummaryInput(ToolInput):
    section: SummarySection | None = None


class InspectEntityInput(ToolInput):
    id: int


class SearchInput(ToolInput):
    query: Annotated[str, Field(max_length=QUERY_MAX)] = ""
    type: EntityType | None = None


class InspectSiblingInput(ToolInput):
    son_id: int


async def world_summary(call: SonCall, args: WorldSummaryInput) -> str:
    views = call.ports.views
    if views is None:
        fail(CommonResult.NOT_AVAILABLE, tool=SonToolId.WORLD_SUMMARY.value)
    return await views.world_summary(call.session, call.rules, call.son, args.section)


async def my_memory(call: SonCall, _args: EmptyInput) -> str:
    views = call.ports.views
    if views is None:
        fail(CommonResult.NOT_AVAILABLE, tool=SonToolId.MY_MEMORY.value)
    return await views.son_memory(call.session, call.rules, call.son)


async def inspect_entity(call: SonCall, args: InspectEntityInput) -> str:
    entity = await call.session.get(EntityRow, args.id)
    if entity is None:
        fail(CommonResult.NO_SUCH_ENTITY, id=args.id)
    return await entity_detail(call.session, call.rules, entity)


async def search_entities(call: SonCall, args: SearchInput) -> str:
    found = await search(call.session, args.query, entity_type=args.type, limit=call.rules.context.search_results_max)
    return await entity_lines(call.session, found) if found else result(CommonResult.NO_RESULTS)


async def inspect_sibling(call: SonCall, args: InspectSiblingInput) -> str:
    sibling = await call.session.get(SonRow, args.son_id)
    if sibling is None:
        fail(SonResult.NO_SUCH_SIBLING)
    slots = unlocked_power_slots(call.rules, sibling.level)
    powers = [power.name for power in await SonRepository(call.session).powers(sibling.id) if power.slot in slots]
    statement = (
        select(EntityRow)
        .where(EntityRow.creator_son_id == sibling.id, EntityRow.status == EntityStatus.CANON, EntityRow.origin == EntityOrigin.SON)
        .order_by(EntityRow.id.desc())
        .limit(call.rules.son_tools.inspect_sibling_creations)
    )
    creations = [await line_item(call.session, entity) for entity in await call.session.scalars(statement)]
    bond = await relation(call, sibling.id)
    personality = sibling.personality
    context = InspectSiblingContext(
        id=sibling.id,
        name=sibling.name,
        title=sibling.title,
        rarity_label=RARITY_LABELS[sibling.rarity],
        domain_1=DOMAIN_LABELS[sibling.domain_primary],
        domain_2=DOMAIN_LABELS[sibling.domain_secondary],
        level=sibling.level,
        status_label=label_of(sibling.status),
        appearance=personality.appearance or None,
        temperament=personality.temperament or None,
        speech=personality.speech_style or None,
        known_powers=powers,
        strength=sibling.strength,
        wisdom=sibling.wisdom,
        cunning=sibling.cunning,
        charisma=sibling.charisma,
        will=sibling.will,
        hp=sibling.hp,
        max_hp=max_hp(call.rules, sibling.endurance),
        faith=sibling.faith,
        fame=sibling.fame,
        relation=RelationToViewer(label=bond.label, value=bond.value),
        covenant=await has_covenant(call, sibling.id),
        creations=creations,
    )
    return render(PromptId.INSPECT_SIBLING, context)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.WORLD_SUMMARY, son, WorldSummaryInput, READ, world_summary, frozenset({"views"})),
        ToolSpec(SonToolId.INSPECT_ENTITY, son, InspectEntityInput, READ, inspect_entity),
        ToolSpec(SonToolId.SEARCH_ENTITIES, son, SearchInput, READ, search_entities),
        ToolSpec(SonToolId.MY_MEMORY, son, EmptyInput, READ, my_memory, frozenset({"views"})),
        ToolSpec(SonToolId.INSPECT_SIBLING, son, InspectSiblingInput, READ, inspect_sibling),
    ]
