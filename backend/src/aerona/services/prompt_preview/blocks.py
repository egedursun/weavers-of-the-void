from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.bond_lines import bond_lines
from aerona.agents.context.chronicler import chronicler_context
from aerona.agents.context.cosmos_lines import cosmos_lines
from aerona.agents.context.dialect_block import dialect_block
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.entity_line import entity_line_text
from aerona.agents.context.geography import geography_lines
from aerona.agents.context.language_lines import language_lines
from aerona.agents.context.location_tree import location_tree
from aerona.agents.context.mortal import mortal_context
from aerona.agents.context.powers import powers_text
from aerona.agents.context.recent_chronicle import recent_chronicle
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.siblings import siblings
from aerona.agents.context.sky_calendar import sky_calendar
from aerona.agents.context.son_memory import son_memory
from aerona.agents.context.thread_lines import thread_lines
from aerona.agents.context.tired_images import tired_images, tired_images_text
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_line import world_line
from aerona.agents.context.world_summary import world_summary
from aerona.constants.prompt_preview import CHARACTERS_PER_TOKEN
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import SummarySection
from aerona.rules.registry import Rules
from aerona.services.prompt_preview.models import ContextBlock, ContextBlockInfo, ContextBlockKind

NO_SON = "No such son."
NO_ENTITY = "No such record."
NEEDS_SON = "This block needs a son_id."
NEEDS_ENTITY = "This block needs an entity_id."
NO_WORLD = "No such world."

K = ContextBlockKind

BLOCKS: tuple[ContextBlockInfo, ...] = (
    ContextBlockInfo(
        kind=K.WORLD_HEADER,
        needs_son=False,
        needs_entity=False,
        audience="every prompt",
        rows=["CTX-001", "CTX-002", "CTX-003", "CTX-004", "CTX-005", "CTX-006"],
    ),
    ContextBlockInfo(kind=K.DIALECT, needs_son=False, needs_entity=False, audience="Fate, chronicler, voices", rows=["CTX-007"]),
    ContextBlockInfo(kind=K.WORLD_LINE, needs_son=False, needs_entity=False, audience="son, mortal", rows=["CTX-008"]),
    ContextBlockInfo(kind=K.COSMOS, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-009"]),
    ContextBlockInfo(kind=K.PANTHEON, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-010"]),
    ContextBlockInfo(kind=K.THREADS, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-011", "CTX-012", "CTX-013"]),
    ContextBlockInfo(
        kind=K.WORLD_SUMMARY,
        needs_son=True,
        needs_entity=False,
        audience="son",
        rows=["CTX-015", "CTX-016", "CTX-017", "CTX-018", "CTX-019", "CTX-020", "CTX-021"],
    ),
    ContextBlockInfo(kind=K.FATE_SUMMARY, needs_son=False, needs_entity=False, audience="Fate", rows=["CTX-016", "CTX-021"]),
    ContextBlockInfo(kind=K.GEOGRAPHY, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-022"]),
    ContextBlockInfo(kind=K.MAP, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-016"]),
    ContextBlockInfo(kind=K.LANGUAGES, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-033", "CTX-034"]),
    ContextBlockInfo(kind=K.ENTITY_LINE, needs_son=False, needs_entity=True, audience="every listing", rows=["CTX-023"]),
    ContextBlockInfo(kind=K.ENTITY_DETAIL, needs_son=False, needs_entity=True, audience="inspect tools, Fate", rows=["CTX-025", "CTX-026", "CTX-027"]),
    ContextBlockInfo(kind=K.BOND_LINES, needs_son=False, needs_entity=True, audience="inspect tools, Fate", rows=["CTX-024"]),
    ContextBlockInfo(kind=K.SON_MEMORY, needs_son=True, needs_entity=False, audience="son, council, son chat", rows=["CTX-029", "CTX-030", "CTX-031"]),
    ContextBlockInfo(
        kind=K.TIRED_IMAGES,
        needs_son=False,
        needs_entity=False,
        audience="every writing prompt",
        rows=["CTX-035", "CORE-054", "CORE-055", "CORE-056", "CORE-058", "CORE-059"],
    ),
    ContextBlockInfo(kind=K.RECENT_EVENTS, needs_son=False, needs_entity=False, audience="son, Fate", rows=["CTX-032", "CORE-014"]),
    ContextBlockInfo(kind=K.POWERS, needs_son=True, needs_entity=False, audience="son", rows=["CTX-028"]),
    ContextBlockInfo(kind=K.SKY_CALENDAR, needs_son=False, needs_entity=False, audience="son", rows=["CTX-006"]),
    ContextBlockInfo(kind=K.MORTAL, needs_son=False, needs_entity=True, audience="mortal", rows=["CTX-002"]),
    ContextBlockInfo(kind=K.CHRONICLER, needs_son=False, needs_entity=False, audience="chronicler", rows=["CTX-001"]),
)


@dataclass(frozen=True)
class BlockQuery:
    son_id: int | None = None
    world_id: int | None = None
    entity_id: int | None = None
    section: SummarySection | None = None
    short: bool = False
    full: bool = False


def estimate_tokens(characters: int) -> int:
    return -(-characters // CHARACTERS_PER_TOKEN)


async def require_son(session: AsyncSession, son_id: int | None) -> SonRow:
    if son_id is None:
        raise ValidationFailedError(NEEDS_SON)
    son = await session.get(SonRow, son_id)
    if son is None:
        raise NotFoundError(NO_SON)
    return son


async def require_entity(session: AsyncSession, entity_id: int | None) -> EntityRow:
    if entity_id is None:
        raise ValidationFailedError(NEEDS_ENTITY)
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError(NO_ENTITY)
    return entity


def resolve_world(scope: Scope, query: BlockQuery, viewer: SonRow | None, entity: EntityRow | None = None) -> int | None:
    if query.world_id is not None:
        if query.world_id not in scope.worlds:
            raise NotFoundError(NO_WORLD)
        return query.world_id
    if viewer is not None:
        return viewer.current_world_id
    return entity.world_id if entity is not None else None


def event_rows(scope: Scope, viewer: SonRow | None) -> int:
    context = scope.rules.context
    if viewer is not None:
        return context.son_chronicle_lines + viewer.wisdom // context.son_chronicle_wisdom_step
    return context.fate_chronicle_lines


def tree_rows(scope: Scope, viewer: SonRow | None) -> int:
    context = scope.rules.context
    return context.son_location_tree_lines + viewer.wisdom if viewer is not None else context.fate_location_tree_lines


async def optional_son(session: AsyncSession, son_id: int | None) -> SonRow | None:
    return await require_son(session, son_id) if son_id is not None else None


@dataclass(frozen=True)
class Rendered:
    text: str
    world_id: int | None = None
    entity_id: int | None = None


Renderer = Callable[[Scope, BlockQuery, SonRow | None], Awaitable[Rendered]]


def world_of(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> int | None:
    return resolve_world(scope, query, viewer)


def needs(viewer: SonRow | None) -> SonRow:
    if viewer is None:
        raise ValidationFailedError(NEEDS_SON)
    return viewer


async def world_header_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer)
    return Rendered(await world_header(scope, world_id, short=query.short), world_id)


async def dialect_block_text(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    return Rendered(dialect_block(scope))


async def world_line_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer) or scope.primary_world_id
    return Rendered(await world_line(scope, world_id), world_id)


async def cosmos_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer)
    return Rendered(await cosmos_lines(scope, world_id), world_id)


async def pantheon_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    return Rendered(await siblings(scope, viewer))


async def threads_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    return Rendered(await thread_lines(scope, viewer))


async def son_summary_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    son = needs(viewer)
    return Rendered(await world_summary(scope, son, query.section), son.current_world_id)


async def fate_summary_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    return Rendered(await world_summary(scope, None, query.section))


async def geography_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer)
    text, _, _ = await location_tree(scope, world_id, tree_rows(scope, viewer))
    return Rendered(text, world_id)


async def map_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer) or scope.primary_world_id
    return Rendered(await geography_lines(scope, world_id), world_id)


async def languages_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer)
    return Rendered(await language_lines(scope, world_id, viewer), world_id)


async def entity_line_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    entity = await require_entity(scope.session, query.entity_id)
    return Rendered(await entity_line_text(scope.session, entity), entity.world_id, entity.id)


async def entity_detail_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    entity = await require_entity(scope.session, query.entity_id)
    return Rendered(await entity_detail(scope, entity), entity.world_id, entity.id)


async def bond_lines_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    entity = await require_entity(scope.session, query.entity_id)
    return Rendered(await bond_lines(scope.session, entity.id), entity.world_id, entity.id)


async def memory_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    son = needs(viewer)
    return Rendered(await son_memory(scope, son, full=query.full), son.current_world_id)


async def tired_images_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer)
    return Rendered(tired_images_text(await tired_images(scope, world_id)), world_id)


async def recent_events_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    world_id = world_of(scope, query, viewer)
    return Rendered(await recent_chronicle(scope, event_rows(scope, viewer), world_id), world_id)


async def powers_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    son = needs(viewer)
    powers = list(await scope.session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == son.id)))
    return Rendered(powers_text(scope.rules, son, powers), son.current_world_id)


async def sky_calendar_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    return Rendered(sky_calendar(scope.rules, scope.epoch))


async def mortal_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    entity = await require_entity(scope.session, query.entity_id)
    context = await mortal_context(scope, entity, full=query.full)
    return Rendered(render(PromptId.MORTAL_CONTEXT, context), entity.world_id, entity.id)


async def chronicler_block(scope: Scope, query: BlockQuery, viewer: SonRow | None) -> Rendered:
    return Rendered(render(PromptId.CHRONICLER_USER, await chronicler_context(scope, scope.epoch)))


RENDERERS: dict[ContextBlockKind, Renderer] = {
    K.WORLD_HEADER: world_header_block,
    K.DIALECT: dialect_block_text,
    K.WORLD_LINE: world_line_block,
    K.COSMOS: cosmos_block,
    K.PANTHEON: pantheon_block,
    K.THREADS: threads_block,
    K.WORLD_SUMMARY: son_summary_block,
    K.FATE_SUMMARY: fate_summary_block,
    K.GEOGRAPHY: geography_block,
    K.MAP: map_block,
    K.LANGUAGES: languages_block,
    K.ENTITY_LINE: entity_line_block,
    K.ENTITY_DETAIL: entity_detail_block,
    K.BOND_LINES: bond_lines_block,
    K.SON_MEMORY: memory_block,
    K.TIRED_IMAGES: tired_images_block,
    K.RECENT_EVENTS: recent_events_block,
    K.POWERS: powers_block,
    K.SKY_CALENDAR: sky_calendar_block,
    K.MORTAL: mortal_block,
    K.CHRONICLER: chronicler_block,
}


async def render_block(session: AsyncSession, rules: Rules, kind: ContextBlockKind, query: BlockQuery) -> ContextBlock:
    scope = await load_scope(session, rules)
    viewer = await optional_son(session, query.son_id)
    rendered = await RENDERERS[kind](scope, query, viewer)
    return ContextBlock(
        kind=kind,
        text=rendered.text,
        characters=len(rendered.text),
        token_estimate=estimate_tokens(len(rendered.text)),
        world_id=rendered.world_id,
        son_id=query.son_id,
        entity_id=rendered.entity_id,
    )
