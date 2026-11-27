from typing import Any

from fastapi import APIRouter, Query, status

from aerona.agents.network_repair import network_fate_repair
from aerona.api.background import require_llm, submit
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import Done, JobAccepted
from aerona.api.schemas.graph import FateLinkRequest, GraphWindow, RepairResult
from aerona.constants.api import GRAPH_PAGE_DEFAULT, GRAPH_PAGE_MAX, PATH_MAX_DEPTH
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.job import JobKind
from aerona.jobs.context import JobContext
from aerona.services.integrity.network import NetworkHealth, health, repair_dangling_ends
from aerona.services.search import Graph, PathResult, find_path, graph
from aerona.services.state_memo import per_state

router = APIRouter(tags=["graph"])

FATE_LINK_GROUP = "network:fate"
FATE_LINK_LABEL = "Fate's network repair"
REPAIR_TOOL = "network:repair"
GRAPH_KEY = "graph"


@router.get("/graph", response_model=GraphWindow)
async def read_graph(
    services: ServicesDep,
    node_offset: int = Query(default=0, ge=0),
    node_limit: int = Query(default=GRAPH_PAGE_DEFAULT, ge=1, le=GRAPH_PAGE_MAX),
    link_offset: int = Query(default=0, ge=0),
    link_limit: int = Query(default=GRAPH_PAGE_DEFAULT, ge=1, le=GRAPH_PAGE_MAX),
) -> GraphWindow:
    async def built() -> Graph:
        async with reader(services) as session:
            return await graph(session)

    full = await per_state(services.database, GRAPH_KEY, built)
    return GraphWindow(
        nodes=full.nodes[node_offset : node_offset + node_limit],
        links=full.links[link_offset : link_offset + link_limit],
        node_total=len(full.nodes),
        link_total=len(full.links),
        node_offset=node_offset,
        link_offset=link_offset,
    )


@router.get("/graph/path", response_model=PathResult)
async def read_path(
    services: ServicesDep, a: int = Query(ge=1), b: int = Query(ge=1), depth: int = Query(default=PATH_MAX_DEPTH, ge=1, le=PATH_MAX_DEPTH)
) -> PathResult:
    async with reader(services) as session:
        return await find_path(session, a, b, depth)


@router.get("/graph/health", response_model=NetworkHealth)
async def read_health(services: ServicesDep) -> NetworkHealth:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        return await health(session, rules, services.application.repair_log, epoch)


@router.post("/graph/repair", response_model=RepairResult)
async def repair_graph(services: ServicesDep) -> RepairResult:
    application = services.application
    async with services.database.write() as session:
        rules = await world_rules(services, session)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        async with application.ledger.creator_action(session, REPAIR_TOOL, ActionKind.NETWORK_REPAIR) as handle:
            counters = await repair_dangling_ends(session, rules, epoch, application.repair_log, services.bus)
    return RepairResult(counters=counters.as_dict(), ledger_entry_id=handle.entry_id)


@router.post("/graph/fate-link", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def fate_link(services: ServicesDep, request: FateLinkRequest | None = None) -> JobAccepted:
    require_llm(services, FATE_LINK_LABEL)
    order = request or FateLinkRequest()
    services.stop_requests.discard(FATE_LINK_GROUP)

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, FATE_LINK_GROUP)
        summary = await network_fate_repair(
            services.agents,
            order.entity_ids or None,
            related=order.related,
            full=order.full,
            stop=lambda: FATE_LINK_GROUP in services.stop_requests,
        )
        services.stop_requests.discard(FATE_LINK_GROUP)
        return {"looked": summary.looked, "built": summary.built, "named": summary.named, "closed": summary.closed}

    return await submit(services, JobKind.CONTENT, FATE_LINK_GROUP, work, order.model_dump(), label=FATE_LINK_LABEL)


@router.post("/graph/fate-link/stop", response_model=Done)
async def stop_fate_link(services: ServicesDep) -> Done:
    running = services.jobs.busy_group(FATE_LINK_GROUP) is not None
    if running:
        services.stop_requests.add(FATE_LINK_GROUP)
    return Done(ok=running)
