import time

from fastapi import APIRouter, Path, Query
from sqlalchemy import func, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.team import (
    CanonProposalView,
    NodeRevisionView,
    PresenceUpdate,
    PresentView,
    ProposalDecision,
    ProposalPage,
    QueuedActView,
    QueuePage,
    TeamView,
)
from aerona.api.views.team import author_view, proposal_view, queued_view
from aerona.constants.team import (
    PRESENCE_HEARTBEAT_SECONDS,
    PRESENCE_SCREEN_MAX_LENGTH,
    PROPOSAL_PAGE_DEFAULT,
    PROPOSAL_PAGE_MAX,
    QUEUE_PAGE_DEFAULT,
    QUEUE_PAGE_MAX,
)
from aerona.core.account_scope import current_account
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.team import CanonProposalRow, QueuedActRow
from aerona.domain.enums.team import ProposalStatus, QueuedActStatus
from aerona.events.kinds import EventKind
from aerona.services.accounts.guard import current_grant
from aerona.services.container import Services
from aerona.services.team.execute import world_busy
from aerona.services.team.gate import approve_now_or_later
from aerona.services.team.proposals import pending_count, reject, withdraw
from aerona.services.team.queue import cancel, retry, waiting_count
from aerona.services.team.revisions import latest_revision, node_revision

router = APIRouter(tags=["team"])

SIGNED_OUT_PRESENCE = "Sign in to be seen by the team."


def is_admin() -> bool:
    grant = current_grant()
    return grant is None or grant.access.admin


def present(services: Services) -> list[PresentView]:
    now = time.monotonic()
    seen = services.team.roster.live(services.settings.team_presence_ttl_seconds, now)
    return [
        PresentView(
            account_id=item.account_id,
            name=item.name,
            screen=item.screen,
            node_id=item.node_id,
            editing=item.editing,
            seen_seconds_ago=round(now - item.seen, 1),
        )
        for item in seen
    ]


def publish_presence(services: Services) -> None:
    services.bus.publish(EventKind.TEAM_PRESENCE, {"present": [item.model_dump(mode="json") for item in present(services)]})


@router.get("/team", response_model=TeamView)
async def read_team(services: ServicesDep) -> TeamView:
    grant = current_grant()
    account = current_account()
    async with reader(services) as session:
        queued = await waiting_count(session)
        proposals = await pending_count(session)
        revision = await latest_revision(session)
    return TeamView(
        role=grant.access.role if grant is not None else None,
        permissions=sorted(grant.access.permissions) if grant is not None else [],
        canon_approval=grant.canon_approval if grant is not None else False,
        present=present(services),
        queued=queued,
        proposals=proposals,
        revision=revision,
        world_busy=world_busy(services),
        me=author_view(account.id, account.name) if account is not None else None,
        heartbeat_seconds=PRESENCE_HEARTBEAT_SECONDS,
        presence_ttl_seconds=services.settings.team_presence_ttl_seconds,
    )


@router.post("/presence", response_model=list[PresentView])
async def mark_presence(services: ServicesDep, body: PresenceUpdate) -> list[PresentView]:
    account = current_account()
    if account is None:
        raise ValidationFailedError(SIGNED_OUT_PRESENCE)
    services.team.roster.mark(account, body.screen[:PRESENCE_SCREEN_MAX_LENGTH], body.node_id, body.editing)
    publish_presence(services)
    return present(services)


@router.delete("/presence", response_model=list[PresentView])
async def leave_presence(services: ServicesDep) -> list[PresentView]:
    account = current_account()
    if account is not None and services.team.roster.leave(account.id):
        publish_presence(services)
    return present(services)


@router.get("/team/revisions/{node_id}", response_model=NodeRevisionView)
async def read_revision(services: ServicesDep, node_id: int = Path(ge=1)) -> NodeRevisionView:
    async with reader(services) as session:
        found = await node_revision(session, node_id)
    return NodeRevisionView(node_id=node_id, revision=found.revision, changed_by=found.changed_by, changed_at=found.changed_at)


@router.get("/team/queue", response_model=QueuePage)
async def read_queue(
    services: ServicesDep,
    status: QueuedActStatus | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=QUEUE_PAGE_DEFAULT, ge=1, le=QUEUE_PAGE_MAX),
) -> QueuePage:
    statement = select(QueuedActRow)
    counted = select(func.count()).select_from(QueuedActRow)
    if status is not None:
        statement = statement.where(QueuedActRow.status == status)
        counted = counted.where(QueuedActRow.status == status)
    async with reader(services) as session:
        rows = list(await session.scalars(statement.order_by(QueuedActRow.id.desc()).offset(offset).limit(limit)))
        total = int(await session.scalar(counted) or 0)
    return QueuePage(items=[queued_view(row) for row in rows], total=total)


@router.delete("/team/queue/{act_id}", response_model=QueuedActView)
async def cancel_queued(services: ServicesDep, act_id: int = Path(ge=1)) -> QueuedActView:
    return queued_view(await cancel(services, act_id, current_account(), is_admin()))


@router.post("/team/queue/{act_id}/retry", response_model=QueuedActView)
async def retry_queued(services: ServicesDep, act_id: int = Path(ge=1)) -> QueuedActView:
    return queued_view(await retry(services, act_id, current_account(), is_admin()))


@router.get("/team/proposals", response_model=ProposalPage)
async def read_proposals(
    services: ServicesDep,
    status: ProposalStatus | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=PROPOSAL_PAGE_DEFAULT, ge=1, le=PROPOSAL_PAGE_MAX),
) -> ProposalPage:
    statement = select(CanonProposalRow)
    counted = select(func.count()).select_from(CanonProposalRow)
    if status is not None:
        statement = statement.where(CanonProposalRow.status == status)
        counted = counted.where(CanonProposalRow.status == status)
    async with reader(services) as session:
        rows = list(await session.scalars(statement.order_by(CanonProposalRow.id.desc()).offset(offset).limit(limit)))
        total = int(await session.scalar(counted) or 0)
    return ProposalPage(items=[proposal_view(row) for row in rows], total=total)


@router.post("/team/proposals/{proposal_id}/approve", response_model=CanonProposalView)
async def approve_proposal(services: ServicesDep, body: ProposalDecision, proposal_id: int = Path(ge=1)) -> CanonProposalView:
    return proposal_view(await approve_now_or_later(services, proposal_id, current_account(), body.note.strip()))


@router.post("/team/proposals/{proposal_id}/reject", response_model=CanonProposalView)
async def reject_proposal(services: ServicesDep, body: ProposalDecision, proposal_id: int = Path(ge=1)) -> CanonProposalView:
    return proposal_view(await reject(services, proposal_id, current_account(), body.note.strip()))


@router.post("/team/proposals/{proposal_id}/withdraw", response_model=CanonProposalView)
async def withdraw_proposal(services: ServicesDep, proposal_id: int = Path(ge=1)) -> CanonProposalView:
    return proposal_view(await withdraw(services, proposal_id, current_account()))
