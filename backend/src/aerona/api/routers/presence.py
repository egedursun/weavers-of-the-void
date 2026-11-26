from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.presence import (
    PresenceClosedView,
    PresenceEventView,
    PresenceExchangeAccepted,
    PresenceExchangeView,
    PresenceOpenRequest,
    PresenceSayRequest,
    PresenceSessionSummary,
    PresenceSessionView,
    PresenceSpeakerCard,
    PresenceSpeakerItem,
    PresenceSpeakerPage,
    PresenceSpeakerView,
)
from aerona.api.schemas.team import SharedUpdate
from aerona.api.views.team import author_view
from aerona.core.errors import ForbiddenError, NotFoundError
from aerona.db.authorship import may_see, owns
from aerona.db.repositories.presence import (
    events_by_exchange,
    exchange_counts,
    kept_sessions,
    memory_boundary,
    open_session_of,
    open_sessions,
    session_exchanges,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.presence import PresenceExchangeRow, PresenceSessionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.accounts import Permission
from aerona.domain.enums.presence import PresenceRecord, PresenceStatus, SpeakerGroup
from aerona.domain.enums.providers import ModelRole
from aerona.services.accounts.guard import ensure_allowed
from aerona.services.container import Services
from aerona.services.images.records import covers_of
from aerona.services.presence.runtime import PresenceRuntime
from aerona.services.presence.speakers import SpeakerCard, heard_speaker, speaker_card, speaker_lines
from aerona.services.presence.tools import may_act

router = APIRouter(prefix="/presence", tags=["presence"])

SPEAKER_PAGE = 30
SPEAKER_PAGE_MAX = 200
QUERY_MAX = 200
NO_SESSION = "No such audience."
NOT_YOURS = "Only the one who summoned this audience can continue or change it."
NO_EXCHANGE = "No such exchange of an audience."


async def summaries(session: AsyncSession, rows: Sequence[PresenceSessionRow]) -> list[PresenceSessionSummary]:
    counts = await exchange_counts(session, [row.id for row in rows])
    return [
        PresenceSessionSummary.model_validate(
            {
                **{column: getattr(row, column) for column in PresenceSessionSummary.model_fields if hasattr(row, column)},
                "exchange_count": counts.get(row.id, 0),
                "author": author_view(row.author_account_id, row.author_name),
                "mine": owns(row.author_account_id),
            }
        )
        for row in rows
    ]


async def exchange_views(session: AsyncSession, rows: Sequence[PresenceExchangeRow]) -> list[PresenceExchangeView]:
    events = await events_by_exchange(session, [row.id for row in rows])
    return [
        PresenceExchangeView.model_validate(
            {
                **{column: getattr(row, column) for column in PresenceExchangeView.model_fields if hasattr(row, column)},
                "events": [PresenceEventView.model_validate(event) for event in events[row.id]],
            }
        )
        for row in rows
    ]


def card_view(card: SpeakerCard, cover: str | None) -> PresenceSpeakerCard:
    speaker = card.speaker
    node = speaker.node
    death = card.death
    return PresenceSpeakerCard(
        node_id=speaker.node_id,
        name=speaker.name,
        epithet=speaker.epithet,
        kind=speaker.kind,
        entity_type=speaker.entity_type,
        group=speaker.group,
        son_status=node.status if isinstance(node, SonRow) else None,
        foreign_god_status=node.status if isinstance(node, ForeignGodRow) else None,
        entity_status=node.status if isinstance(node, EntityRow) else None,
        place_name=card.place_name,
        world_name=card.world_name,
        patron_name=card.patron_name,
        faith=card.faith,
        languages=card.languages,
        dead=speaker.dead,
        death_epoch=death.epoch if death is not None else None,
        son_death_cause=death.son_cause if death is not None else None,
        mortal_death_cause=death.mortal_cause if death is not None else None,
        death_line=death.line if death is not None else "",
        cover=cover,
        can_act=may_act(speaker, PresenceRecord.ON_RECORD, world_busy=False),
    )


async def session_view(services: Services, holder: PresenceSessionRow) -> PresenceSessionView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        remembered = rules.presence.remembered_exchanges
        rows = await session_exchanges(session, holder.id)
        boundary = await memory_boundary(session, holder.id, remembered) if holder.status is PresenceStatus.OPEN else len(rows) + 1
        return PresenceSessionView(
            session=(await summaries(session, [holder]))[0],
            exchanges=await exchange_views(session, rows),
            memory_boundary=boundary,
            remembered_exchanges=remembered,
            running_exchange_id=PresenceRuntime(services).running_exchange_id(holder.id),
        )


async def one_session(services: Services, session_id: int) -> PresenceSessionView:
    async with reader(services) as session:
        holder = await session.get(PresenceSessionRow, session_id)
        if holder is None or not may_see(holder.author_account_id, holder.shared):
            raise NotFoundError(NO_SESSION)
    return await session_view(services, holder)


async def own_session(services: Services, session_id: int) -> None:
    async with reader(services) as session:
        holder = await session.get(PresenceSessionRow, session_id)
    if holder is None or not may_see(holder.author_account_id, holder.shared):
        raise NotFoundError(NO_SESSION)
    if not owns(holder.author_account_id):
        raise ForbiddenError(NOT_YOURS)


async def own_exchange(services: Services, exchange_id: int) -> None:
    async with reader(services) as session:
        row = await session.get(PresenceExchangeRow, exchange_id)
    if row is None:
        raise NotFoundError(NO_EXCHANGE)
    await own_session(services, row.session_id)


async def one_exchange(services: Services, exchange_id: int) -> PresenceExchangeView:
    async with reader(services) as session:
        row = await session.get(PresenceExchangeRow, exchange_id)
        holder = await session.get(PresenceSessionRow, row.session_id) if row is not None else None
        if row is None or holder is None or not may_see(holder.author_account_id, holder.shared):
            raise NotFoundError(NO_EXCHANGE)
        return (await exchange_views(session, [row]))[0]


@router.get("/speakers", response_model=PresenceSpeakerPage)
async def read_speakers(
    services: ServicesDep,
    *,
    q: Annotated[str, Query(max_length=QUERY_MAX)] = "",
    group: Annotated[SpeakerGroup | None, Query()] = None,
    dead: Annotated[bool, Query()] = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=SPEAKER_PAGE_MAX)] = SPEAKER_PAGE,
) -> PresenceSpeakerPage:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        lines = await speaker_lines(session, rules, query=q, group=group, dead=dead)
        shown = lines[offset : offset + limit]
        ids = [line.node_id for line in shown]
        covers = await covers_of(session, ids)
        opened = await open_sessions(session, ids)
    return PresenceSpeakerPage(
        speakers=[
            PresenceSpeakerItem(
                node_id=line.node_id,
                name=line.name,
                kind=line.kind,
                entity_type=line.entity_type,
                group=line.group,
                dead=line.dead,
                cover=covers.get(line.node_id),
                open_session_id=opened.get(line.node_id),
            )
            for line in shown
        ],
        total=len(lines),
        offset=offset,
        limit=limit,
        has_more=offset + len(shown) < len(lines),
    )


@router.get("/speakers/{node_id}", response_model=PresenceSpeakerView | None)
async def read_speaker(services: ServicesDep, node_id: int = Path(ge=1)) -> PresenceSpeakerView | None:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        speaker = await heard_speaker(session, rules, node_id)
        if speaker is None:
            return None
        card = await speaker_card(session, speaker)
        covers = await covers_of(session, [node_id])
        current = await open_session_of(session, node_id)
        opened = (await summaries(session, [current]))[0] if current is not None else None
        past = await summaries(session, await kept_sessions(session, node_id))
    return PresenceSpeakerView(
        card=card_view(card, covers.get(node_id)),
        open_session=opened,
        past_sessions=past,
        model_enabled=services.application.model.ready(ModelRole.CONVERSATION),
        remembered_exchanges=rules.presence.remembered_exchanges,
    )


@router.post("/sessions", response_model=PresenceSessionView, status_code=status.HTTP_201_CREATED)
async def open_session(services: ServicesDep, body: PresenceOpenRequest) -> PresenceSessionView:
    if body.record is PresenceRecord.ON_RECORD:
        ensure_allowed(Permission.PRESENCE_ON_RECORD)
    holder = await PresenceRuntime(services).open(body.node_id, body.guise, body.record)
    return await session_view(services, holder)


@router.get("/sessions/{session_id}", response_model=PresenceSessionView)
async def read_session(services: ServicesDep, session_id: int = Path(ge=1)) -> PresenceSessionView:
    return await one_session(services, session_id)


@router.post("/sessions/{session_id}/exchanges", response_model=PresenceExchangeAccepted, status_code=status.HTTP_202_ACCEPTED)
async def start_exchange(services: ServicesDep, body: PresenceSayRequest, session_id: int = Path(ge=1)) -> PresenceExchangeAccepted:
    await own_session(services, session_id)
    exchange = await PresenceRuntime(services).submit(session_id, body.text)
    return PresenceExchangeAccepted(exchange_id=exchange.id, session_id=exchange.session_id, ordinal=exchange.ordinal)


@router.get("/exchanges/{exchange_id}", response_model=PresenceExchangeView)
async def read_exchange(services: ServicesDep, exchange_id: int = Path(ge=1)) -> PresenceExchangeView:
    return await one_exchange(services, exchange_id)


@router.post("/exchanges/{exchange_id}/cancel", response_model=PresenceExchangeView)
async def cancel_exchange(services: ServicesDep, exchange_id: int = Path(ge=1)) -> PresenceExchangeView:
    await own_exchange(services, exchange_id)
    await PresenceRuntime(services).cancel(exchange_id)
    return await one_exchange(services, exchange_id)


@router.post("/sessions/{session_id}/close", response_model=PresenceClosedView)
async def close_session(services: ServicesDep, session_id: int = Path(ge=1)) -> PresenceClosedView:
    await own_session(services, session_id)
    holder, kept = await PresenceRuntime(services).close(session_id)
    return PresenceClosedView(session_id=holder.id, node_id=holder.node_id, kept=kept)


@router.patch("/sessions/{session_id}", response_model=PresenceSessionView)
async def share_session(services: ServicesDep, body: SharedUpdate, session_id: int = Path(ge=1)) -> PresenceSessionView:
    await own_session(services, session_id)
    async with services.database.write() as session:
        holder = await session.get(PresenceSessionRow, session_id)
        if holder is None:
            raise NotFoundError(NO_SESSION)
        holder.shared = body.shared
    return await one_session(services, session_id)
