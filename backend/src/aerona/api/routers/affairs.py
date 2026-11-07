from collections.abc import Mapping

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.affairs import (
    AffairsView,
    ApprovalView,
    CouncilTaskView,
    CourtView,
    DemandView,
    ElectionView,
    MandateView,
    PositionView,
    ResolutionView,
    SeatView,
    TaxView,
    VoteView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.affairs import (
    RATE_MAX,
    CouncilSeatRow,
    CourtPositionRow,
    CourtRow,
    ElectionRow,
    MandateRow,
    NobleDemandRow,
    PolicyApprovalRow,
    ResolutionRow,
    ResolutionVoteRow,
    TaxPolicyRow,
)
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.engine.polity.book import RealmBook

router = APIRouter(tags=["affairs"])
NO_NODE = "Nothing lives there."


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


@router.get("/affairs/{node_id}", response_model=AffairsView)
async def affairs_view(services: ServicesDep, node_id: int = Path(ge=1)) -> AffairsView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError(NO_NODE)
        entity = await session.get(EntityRow, node_id)
        book = await RealmBook.load(session)
        realm = book.realm_for(node_id)
        realm_id = realm.entity.id if realm is not None else None
        offices = list(await session.scalars(select(OfficeRow).where(OfficeRow.polity_entity_id == realm_id).order_by(OfficeRow.id))) if realm_id else []
        elections = (
            list(await session.scalars(select(ElectionRow).where(ElectionRow.polity_entity_id == realm_id).order_by(ElectionRow.epoch.desc())))
            if realm_id
            else []
        )
        seats = (
            list(await session.scalars(select(CouncilSeatRow).where(CouncilSeatRow.polity_entity_id == realm_id).order_by(CouncilSeatRow.seats.desc())))
            if realm_id
            else []
        )
        taxes = (
            list(await session.scalars(select(TaxPolicyRow).where(TaxPolicyRow.polity_entity_id == realm_id).order_by(TaxPolicyRow.kind))) if realm_id else []
        )
        mandates = list(
            await session.scalars(
                select(MandateRow)
                .where(or_(MandateRow.polity_entity_id == (realm_id or -1), MandateRow.settlement_entity_id == node_id))
                .order_by(MandateRow.id.desc())
            )
        )
        demands = list(await session.scalars(select(NobleDemandRow).where(NobleDemandRow.mortal_entity_id == node_id).order_by(NobleDemandRow.want)))
        approvals = (
            list(
                await session.scalars(select(PolicyApprovalRow).where(PolicyApprovalRow.polity_entity_id == realm_id).order_by(PolicyApprovalRow.social_class))
            )
            if realm_id
            else []
        )
        core = realm.profile.core_entity_id if realm is not None else None
        joined = select(BondRow.target_node_id).where(
            BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_([node_id, *([core] if core else [])])
        )
        resolutions = list(
            await session.scalars(
                select(ResolutionRow)
                .where(or_(ResolutionRow.assembly_entity_id == node_id, ResolutionRow.target_node_id == node_id, ResolutionRow.assembly_entity_id.in_(joined)))
                .order_by(ResolutionRow.id.desc())
            )
        )
        votes = list(await session.scalars(select(ResolutionVoteRow).where(ResolutionVoteRow.resolution_id.in_([row.id for row in resolutions]))))
        court = await session.get(CourtRow, realm_id) if realm_id else None
        positions = (
            list(await session.scalars(select(CourtPositionRow).where(CourtPositionRow.polity_entity_id == realm_id).order_by(CourtPositionRow.position)))
            if realm_id
            else []
        )
        ids: set[int] = {node_id, *([realm_id] if realm_id else [])}
        ids.update(item for row in resolutions for item in (row.assembly_entity_id, row.target_node_id) if item is not None)
        ids.update(vote.member_node_id for vote in votes)
        ids.update(row.holder_entity_id for row in positions if row.holder_entity_id is not None)
        ids.update(item for office in offices for item in (office.holder_entity_id, office.task_target_node_id) if item is not None)
        ids.update(election.winner_node_id for election in elections if election.winner_node_id is not None)
        ids.update(int(key) for election in elections for key in election.results if key.isdigit())
        ids.update(seat.holder_node_id for seat in seats)
        ids.update(item for row in mandates for item in (row.polity_entity_id, row.issuer_node_id, row.settlement_entity_id) if item is not None)
        refs = await node_refs(session, ids)
        return AffairsView(
            node_id=node_id,
            realm=ref(refs, realm_id),
            is_mortal=entity is not None and entity.entity_type is EntityType.MORTAL,
            corruption=realm.profile.corruption if realm is not None else None,
            corruption_held=realm is not None and "corruption" in realm.profile.locked,
            tax_cap=RATE_MAX,
            council=[
                CouncilTaskView(
                    office_id=office.id,
                    office=office.kind,
                    holder=ref(refs, office.holder_entity_id),
                    task=office.task,
                    target=ref(refs, office.task_target_node_id),
                    diligence=office.diligence,
                    locked=list(office.locked or []),
                )
                for office in offices
            ],
            elections=[
                ElectionView(
                    id=row.id,
                    epoch=row.epoch,
                    seats=row.seats,
                    turnout=row.turnout,
                    winner=ref(refs, row.winner_node_id),
                    results=[
                        (refs[int(key)], share) for key, share in sorted(row.results.items(), key=lambda item: -item[1]) if key.isdigit() and int(key) in refs
                    ],
                )
                for row in elections
            ],
            seats=[
                SeatView(holder=refs[row.holder_node_id], seats=row.seats, votes=row.votes, since_epoch=row.since_epoch, locked=row.locked)
                for row in seats
                if row.holder_node_id in refs
            ],
            taxes=[
                TaxView(kind=row.kind, rate=row.rate, farmed=row.farmed, efficiency=row.efficiency, take=row.take, locked=list(row.locked or []))
                for row in taxes
            ],
            mandates=[
                MandateView(
                    id=row.id,
                    polity=ref(refs, row.polity_entity_id),
                    issuer=ref(refs, row.issuer_node_id),
                    kind=row.kind,
                    settlement=ref(refs, row.settlement_entity_id),
                    commodity=row.commodity,
                    district=row.district,
                    amount=row.amount,
                    issued_epoch=row.issued_epoch,
                    until_epoch=row.until_epoch,
                    state=row.state,
                    locked=list(row.locked or []),
                )
                for row in mandates
            ],
            demands=[
                DemandView(noble=refs[row.mortal_entity_id], want=row.want, since_epoch=row.since_epoch, met=row.met, locked=row.locked)
                for row in demands
                if row.mortal_entity_id in refs
            ],
            approvals=[
                ApprovalView(social_class=row.social_class, approval=row.approval, parts=dict(row.parts or {}), locked=list(row.locked or []))
                for row in approvals
            ],
            is_assembly=entity is not None and entity.engine_kind is EngineKind.INTERWORLD_FEDERATION,
            resolutions=[
                ResolutionView(
                    id=row.id,
                    assembly=ref(refs, row.assembly_entity_id),
                    kind=row.kind,
                    target=ref(refs, row.target_node_id),
                    votes_for=row.votes_for,
                    votes_against=row.votes_against,
                    state=row.state,
                    proposed_epoch=row.proposed_epoch,
                    until_epoch=row.until_epoch,
                    locked=list(row.locked or []),
                    votes=[
                        VoteView(member=refs[vote.member_node_id], aye=vote.aye, weight=vote.weight, locked=vote.locked)
                        for vote in votes
                        if vote.resolution_id == row.id and vote.member_node_id in refs
                    ],
                )
                for row in resolutions
            ],
            court=CourtView(grandeur=court.grandeur, courtiers=court.courtiers, parts=dict(court.parts or {}), locked=list(court.locked or []))
            if court is not None
            else None,
            positions=[
                PositionView(position=row.position, holder=ref(refs, row.holder_entity_id), since_epoch=row.since_epoch, locked=row.locked) for row in positions
            ],
        )
