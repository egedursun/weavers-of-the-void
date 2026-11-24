from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.deepener import deepen_entity
from aerona.agents.image_prompter import missing_image_prompts
from aerona.agents.network_repair import network_fate_repair
from aerona.api.actions import Alias, mount_all
from aerona.api.background import require_llm, submit
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel, JobAccepted, Page
from aerona.api.schemas.entities import ArchiveRequest, EntityDetail, EntityQuery, FactView, Importance, Perspective, SimilarRecord
from aerona.api.schemas.records import BondView, ChronicleLineRecord, EntityRecord, EntitySummary, NodeRef
from aerona.api.views.common import bond_count, bond_views, images_of, mentioning, node_ref, node_refs
from aerona.api.views.insight import entity_insight
from aerona.api.views.levels import level_of
from aerona.constants.api import RELATION_PAGE_DEFAULT, RELATION_PAGE_MAX
from aerona.constants.player import ANCESTOR_SEARCH_DEPTH
from aerona.core.errors import NotFoundError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityFlagRow, EntityRow, EntityTagRow, EntityTraitRow
from aerona.db.tables.lore import CanonFactRow, HistorianViewRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.job import JobKind
from aerona.jobs.context import JobContext
from aerona.services.container import Services
from aerona.services.images.records import cover_of, covers_of
from aerona.services.importance import ArchiveMode, archived_ids, info_for, set_archive_mode
from aerona.services.wiki import favorites, similar_entities

router = APIRouter(tags=["entities"])

NO_ENTITY = "No such entity."
VISIBLE_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.DESTROYED, EntityStatus.FULFILLED)
ALL_STATUSES = "all"
ARCHIVE_TOOL = "record:archive"
CONTENTS_SHOWN = 50
SIMILAR_SHOWN = 6
FAVORITE_SUGGESTIONS = 12
EID = {"entity_id": "entity_id"}

ALIASES = (
    Alias("PATCH", "/entities/{entity_id}", "record:edit", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/canon", "canon:set", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/intervene", "intervene", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/knowledge", "knowledge:set", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/dream", "dream", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/favorite", "record:favorite", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/note", "record:note", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/merge", "record:merge", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/stat", "entity:stat", path_fields=EID),
    Alias("PATCH", "/entities/{entity_id}/tags", "entity:tags", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/location", "entity:move", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/patron", "entity:patron", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/decree", "decree", path_fields=EID),
    Alias("PUT", "/entities/{entity_id}/agent", "entity:agent", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/explore", "explore", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/seek-route", "seek_route", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/expedition", "expedition", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/exile", "exile", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/pardon", "pardon", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/rite", "rite", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/take-life", "take_life", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/drain", "drain:mortal", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/harvest", "harvest", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/resurrect", "resurrect:mortal", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/deify", "deify", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/prophet", "prophet", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/manifest", "manifest", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/bloodline-curse", "bloodline_curse", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/convert", "convert", path_fields=EID),
    Alias("POST", "/entities/{entity_id}/wrath", "wrath", path_fields=EID),
    Alias("POST", "/links", "bond:add"),
    Alias("DELETE", "/links/{bond_id}", "bond:remove", path_fields={"bond_id": "bond_id"}),
    Alias("POST", "/facts", "fact:add"),
    Alias("DELETE", "/facts/{fact_id}", "fact:remove", path_fields={"fact_id": "fact_id"}),
    Alias("PUT", "/beliefs", "belief:edit"),
)


async def require_entity(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        raise NotFoundError(NO_ENTITY)
    return entity


async def breadcrumb(session: AsyncSession, entity: EntityRow) -> list[NodeRef]:
    trail: list[NodeRef] = []
    current = entity.location_id
    seen: set[int] = set()
    while current is not None and current not in seen and len(trail) < ANCESTOR_SEARCH_DEPTH:
        seen.add(current)
        parent = await session.get(EntityRow, current)
        if parent is None:
            break
        trail.append(NodeRef(id=parent.id, kind=parent.kind, name=parent.name))
        current = parent.location_id
    return list(reversed(trail))


@router.get("/entities", response_model=Page[EntitySummary])
async def list_entities(services: ServicesDep, query: Annotated[EntityQuery, Query()]) -> Page[EntitySummary]:
    statement = select(EntityRow)
    status_filter, entity_type, world_id, q = query.status, query.entity_type, query.world_id, query.q
    offset, limit = query.offset, query.limit
    if status_filter != ALL_STATUSES:
        statuses = [EntityStatus(status_filter)] if status_filter in {item.value for item in EntityStatus} else list(VISIBLE_STATUSES)
        statement = statement.where(EntityRow.status.in_(statuses))
    if entity_type is not None:
        statement = statement.where(EntityRow.entity_type == entity_type)
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(EntityRow.name.ilike(pattern), EntityRow.subtype.ilike(pattern), EntityRow.description.ilike(pattern)))
    async with reader(services) as session:
        if query.hide_archived:
            rules = await world_rules(services, session)
            epoch = (await CosmosRepository(session).require_cosmos()).epoch
            hidden = await archived_ids(session, rules, epoch)
            if hidden:
                statement = statement.where(EntityRow.id.not_in(hidden))
        total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        rows = await session.scalars(statement.order_by(EntityRow.id).offset(offset).limit(limit))
        return Page[EntitySummary](items=[EntitySummary.model_validate(row) for row in rows], total=total, offset=offset, limit=limit)


@router.get("/favorites", response_model=list[EntitySummary])
async def list_favorites(services: ServicesDep) -> list[EntitySummary]:
    async with reader(services) as session:
        return [EntitySummary.model_validate(row) for row in await favorites(session)]


class FavoriteCard(ApiModel):
    entity: EntitySummary
    cover: str | None


class FavoriteBoard(ApiModel):
    favorites: list[FavoriteCard]
    suggestions: list[FavoriteCard]


@router.get("/favorites/board", response_model=FavoriteBoard)
async def favorite_board(services: ServicesDep) -> FavoriteBoard:
    async with reader(services) as session:
        chosen = await favorites(session)
        suggested = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.favorite.is_(False), EntityRow.status == EntityStatus.CANON, EntityRow.importance.is_not(None))
                .order_by(EntityRow.importance.desc(), EntityRow.id)
                .limit(FAVORITE_SUGGESTIONS)
            )
        )
        covers = await covers_of(session, [row.id for row in [*chosen, *suggested]])
    return FavoriteBoard(
        favorites=[FavoriteCard(entity=EntitySummary.model_validate(row), cover=covers.get(row.id)) for row in chosen],
        suggestions=[FavoriteCard(entity=EntitySummary.model_validate(row), cover=covers.get(row.id)) for row in suggested],
    )


@router.get("/entities/{entity_id}", response_model=EntityDetail)
async def read_entity(services: ServicesDep, entity_id: int = Path(ge=1)) -> EntityDetail:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        entity = await require_entity(session, entity_id)
        server = rules.server
        cosmos = await CosmosRepository(session).require_cosmos()
        contents_query = select(EntityRow).where(EntityRow.location_id == entity.id, EntityRow.status.in_(VISIBLE_STATUSES))
        content_total = int(await session.scalar(select(func.count()).select_from(contents_query.subquery())) or 0)
        contents = list(await session.scalars(contents_query.order_by(EntityRow.id).limit(CONTENTS_SHOWN)))
        facts = list(
            await session.scalars(
                select(CanonFactRow)
                .where(CanonFactRow.active.is_(True), or_(CanonFactRow.subject_entity_id == entity.id, CanonFactRow.object_entity_id == entity.id))
                .order_by(CanonFactRow.id.desc())
                .limit(server.entity_canon_facts)
            )
        )
        fact_refs = await node_refs(session, [*(f.subject_entity_id for f in facts), *(f.object_entity_id for f in facts if f.object_entity_id)])
        histories = list(
            await session.scalars(
                select(HistorianViewRow)
                .where(HistorianViewRow.people_entity_id == entity.id)
                .order_by(HistorianViewRow.epoch.desc())
                .limit(server.people_perspective_lines)
            )
        )
        chronicle, chronicle_total = await mentioning(session, entity.id, offset=0, limit=RELATION_PAGE_DEFAULT)
        anchored = list(await session.scalars(select(SonRow).where(SonRow.anchor_entity_id == entity.id)))
        patron = await BondRepository(session).patron(entity.id)
        importance = await info_for(session, rules, cosmos.epoch, entity.id) if entity.status is not EntityStatus.REJECTED else None
        return EntityDetail(
            entity=EntityRecord.model_validate(entity),
            cover=await cover_of(session, entity.id),
            creator_son=await node_ref(session, entity.creator_son_id),
            maker=await node_ref(session, entity.maker_entity_id),
            patron=await node_ref(session, patron),
            breadcrumb=await breadcrumb(session, entity),
            level=await level_of(session, entity),
            contents=[EntitySummary.model_validate(row) for row in contents],
            content_total=content_total,
            flags=sorted(await session.scalars(select(EntityFlagRow.flag).where(EntityFlagRow.entity_id == entity.id))),
            traits=sorted(await session.scalars(select(EntityTraitRow.trait).where(EntityTraitRow.entity_id == entity.id))),
            tags=sorted(await session.scalars(select(EntityTagRow.tag).where(EntityTagRow.entity_id == entity.id))),
            bonds=await bond_views(session, entity.id, offset=0, limit=RELATION_PAGE_DEFAULT),
            bond_total=await bond_count(session, entity.id, active_only=False),
            chronicle=chronicle,
            chronicle_total=chronicle_total,
            facts=[
                FactView(
                    id=fact.id,
                    subject=fact_refs.get(fact.subject_entity_id),
                    predicate=fact.predicate,
                    object=fact_refs.get(fact.object_entity_id) if fact.object_entity_id else None,
                    object_text=fact.object_text,
                    epoch=fact.epoch,
                )
                for fact in facts
            ],
            perspectives=[
                Perspective(
                    id=row.id,
                    epoch=row.epoch,
                    people_id=row.people_entity_id,
                    people_name=entity.name,
                    historian=row.historian,
                    historian_entity_id=row.historian_entity_id,
                    text=row.text,
                )
                for row in histories
            ],
            similar=[
                SimilarRecord(entity=EntitySummary.model_validate(item.entity), score=item.score, reasons=item.reasons)
                for item in await similar_entities(session, entity.id, SIMILAR_SHOWN)
            ],
            anchored_sons=[NodeRef(id=son.id, kind=son.kind, name=son.name) for son in anchored],
            importance=Importance.model_validate(importance) if importance else None,
            images=await images_of(session, entity.id),
            insight=await entity_insight(session, rules, entity),
        )


@router.get("/entities/{entity_id}/bonds", response_model=Page[BondView])
async def entity_bonds(
    services: ServicesDep,
    entity_id: int = Path(ge=1),
    active_only: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=RELATION_PAGE_DEFAULT, ge=1, le=RELATION_PAGE_MAX),
) -> Page[BondView]:
    async with reader(services) as session:
        await require_entity(session, entity_id)
        items = await bond_views(session, entity_id, offset=offset, limit=limit, active_only=active_only)
        total = await bond_count(session, entity_id, active_only)
    return Page[BondView](items=items, total=total, offset=offset, limit=limit)


@router.get("/entities/{entity_id}/chronicle", response_model=Page[ChronicleLineRecord])
async def entity_chronicle(
    services: ServicesDep,
    entity_id: int = Path(ge=1),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=RELATION_PAGE_DEFAULT, ge=1, le=RELATION_PAGE_MAX),
) -> Page[ChronicleLineRecord]:
    async with reader(services) as session:
        await require_entity(session, entity_id)
        items, total = await mentioning(session, entity_id, offset=offset, limit=limit)
    return Page[ChronicleLineRecord](items=items, total=total, offset=offset, limit=limit)


@router.put("/entities/{entity_id}/archive", response_model=Importance)
async def set_archive(request: ArchiveRequest, services: ServicesDep, entity_id: int = Path(ge=1)) -> Importance:
    application = services.application
    async with services.database.write() as session:
        rules = await world_rules(services, session)
        await require_entity(session, entity_id)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        async with application.ledger.creator_action(session, ARCHIVE_TOOL, ActionKind.ARCHIVE_RECORD, {"entity_id": entity_id, "mode": request.mode.value}):
            info = await set_archive_mode(session, rules, epoch, entity_id, ArchiveMode(request.mode))
    return Importance.model_validate(info)


async def known_entity(services: Services, entity_id: int) -> EntityRow:
    async with services.database.read() as session:
        return await require_entity(session, entity_id)


@router.post("/entities/{entity_id}/deepen", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def deepen(services: ServicesDep, entity_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Deepening a record")
    entity = await known_entity(services, entity_id)

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "deepen")
        await deepen_entity(services.agents, entity.id)
        return {"entity_id": entity.id}

    return await submit(services, JobKind.DEEPEN, f"entity:{entity.id}:depth", work, {"entity_id": entity.id}, label=f"deepening of {entity.name}")


@router.post("/entities/{entity_id}/image-prompt", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def write_image_prompt(services: ServicesDep, entity_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Writing an image prompt")
    entity = await known_entity(services, entity_id)

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "prompt")
        return {"written": await missing_image_prompts(services.agents, 1, [entity.id])}

    return await submit(services, JobKind.CONTENT, f"entity:{entity.id}:prompt", work, {"entity_id": entity.id}, label=f"image prompt of {entity.name}")


@router.post("/entities/{entity_id}/suggest-links", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def suggest_links(services: ServicesDep, entity_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Fate's bond proposals")
    entity = await known_entity(services, entity_id)

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "bonds")
        summary = await network_fate_repair(services.agents, [entity.id], related=False)
        return {"looked": summary.looked, "built": summary.built}

    return await submit(services, JobKind.CONTENT, f"entity:{entity.id}:bonds", work, {"entity_id": entity.id}, label=f"bond proposals for {entity.name}")


mount_all(router, ALIASES, tag="entities")
