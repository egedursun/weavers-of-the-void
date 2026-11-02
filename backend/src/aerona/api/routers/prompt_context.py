from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import Field

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import RequestModel
from aerona.db.tables.motifs import MotifOverrideMode
from aerona.prompts.contexts.blocks import SummarySection
from aerona.prompts.ids import PromptArea, PromptId
from aerona.services.prompt_preview import blocks, catalogue, motifs
from aerona.services.prompt_preview.models import (
    ContextBlock,
    ContextBlockInfo,
    ContextBlockKind,
    PromptCatalogue,
    PromptDetail,
    SonPromptPreview,
    TiredMotifReport,
)
from aerona.services.prompt_preview.son_prompt import preview_son_prompt
from aerona.tools.framework.runtime import ToolCatalogue
from aerona.tools.toolkit import Toolkits

router = APIRouter(prefix="/prompt-context", tags=["prompt-context"])

MOTIF_KEY_MAX = 120


class MotifOverrideRequest(RequestModel):
    motif: str = Field(min_length=1, max_length=MOTIF_KEY_MAX)
    mode: MotifOverrideMode
    world_id: int | None = Field(default=None, ge=1)


class MotifClearRequest(RequestModel):
    motif: str = Field(min_length=1, max_length=MOTIF_KEY_MAX)
    world_id: int | None = Field(default=None, ge=1)


@router.get("/blocks", response_model=list[ContextBlockInfo])
async def list_blocks() -> list[ContextBlockInfo]:
    return list(blocks.BLOCKS)


@router.get("/catalogue", response_model=PromptCatalogue)
async def prompt_catalogue(services: ServicesDep, area: PromptArea | None = None) -> PromptCatalogue:
    async with reader(services) as session:
        rules = await world_rules(services, session)
    return catalogue.catalogue(rules, area)


@router.get("/catalogue/{prompt_id}", response_model=PromptDetail)
async def prompt_detail(services: ServicesDep, prompt_id: PromptId) -> PromptDetail:
    async with reader(services) as session:
        rules = await world_rules(services, session)
    return catalogue.detail(prompt_id, rules)


@router.get("/son-prompt/{son_id}", response_model=SonPromptPreview)
async def son_prompt(services: ServicesDep, son_id: int = Path(ge=1)) -> SonPromptPreview:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        son = await blocks.require_son(session, son_id)
        toolkits = services.agents.toolkits
        tools = await toolkits.son_catalogue(session, son) if isinstance(toolkits, Toolkits) else ToolCatalogue()
        return await preview_son_prompt(session, rules, son_id, tools)


@router.get("/tired-motifs", response_model=TiredMotifReport)
async def tired_motifs(services: ServicesDep, world_id: int | None = Query(default=None, ge=1)) -> TiredMotifReport:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await motifs.report(session, rules, services.application.motifs, world_id)


@router.put("/tired-motifs/overrides", response_model=TiredMotifReport)
async def override_motif(request: MotifOverrideRequest, services: ServicesDep) -> TiredMotifReport:
    async with services.database.write() as session:
        await motifs.override(session, services.application.motifs, request.world_id, request.motif, request.mode)
        rules = await world_rules(services, session)
        return await motifs.report(session, rules, services.application.motifs, request.world_id)


@router.post("/tired-motifs/overrides/clear", response_model=TiredMotifReport)
async def clear_motif(request: MotifClearRequest, services: ServicesDep) -> TiredMotifReport:
    async with services.database.write() as session:
        await motifs.override(session, services.application.motifs, request.world_id, request.motif, None)
        rules = await world_rules(services, session)
        return await motifs.report(session, rules, services.application.motifs, request.world_id)


def block_query(
    *,
    son_id: int | None = Query(default=None, ge=1),
    world_id: int | None = Query(default=None, ge=1),
    entity_id: int | None = Query(default=None, ge=1),
    section: SummarySection | None = None,
    short: bool = False,
    full: bool = False,
) -> blocks.BlockQuery:
    return blocks.BlockQuery(son_id=son_id, world_id=world_id, entity_id=entity_id, section=section, short=short, full=full)


@router.get("/{kind}", response_model=ContextBlock)
async def context_block(services: ServicesDep, kind: ContextBlockKind, query: Annotated[blocks.BlockQuery, Depends(block_query)]) -> ContextBlock:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await blocks.render_block(session, rules, kind, query)
