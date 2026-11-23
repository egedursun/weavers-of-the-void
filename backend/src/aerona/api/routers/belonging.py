from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.routers.foundations import current_epoch
from aerona.api.schemas.belonging import (
    BelongingNodeView,
    FugitiveView,
    HeldIdentityView,
    PeerGroupView,
    PeerMemberView,
    SanctuaryLawView,
    SanctuaryView,
    SatireView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.belonging import FugitiveRow, HeldIdentityRow, PeerGroupRow, PeerMemberRow, SanctuaryLawRow, SanctuaryRow, SatireRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.belonging.effects import realm_fault
from aerona.engine.cycles.book import realm_of

router = APIRouter(tags=["belonging"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


@router.get("/belonging/of/{node_id}", response_model=BelongingNodeView)
async def node_belonging(services: ServicesDep, node_id: NodeId) -> BelongingNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        epoch = await current_epoch(session)
        identities = list(await session.scalars(select(HeldIdentityRow).where(HeldIdentityRow.holder_entity_id == node_id).order_by(HeldIdentityRow.layer)))
        is_realm = await session.get(PolityProfileRow, node_id) is not None
        realm = node_id if is_realm else await realm_of(session, node_id)
        members = list(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == node_id))) if is_realm else []
        fault = await realm_fault(session, await world_rules(services, session), members) if is_realm else None
        mine = select(PeerMemberRow.group_id).where(PeerMemberRow.mortal_entity_id == node_id)
        groups = list(
            await session.scalars(
                select(PeerGroupRow).where(or_(PeerGroupRow.settlement_entity_id == node_id, PeerGroupRow.id.in_(mine))).order_by(PeerGroupRow.id.desc())
            )
        )
        group_members = list(
            await session.scalars(select(PeerMemberRow).where(PeerMemberRow.group_id.in_([row.id for row in groups])).order_by(PeerMemberRow.mortal_entity_id))
        )
        sanctuaries = list(
            await session.scalars(
                select(SanctuaryRow)
                .where(or_(SanctuaryRow.fugitive_entity_id == node_id, SanctuaryRow.host_entity_id == node_id, SanctuaryRow.pursuer_entity_id == node_id))
                .order_by(SanctuaryRow.id.desc())
            )
        )
        fled = list(
            await session.scalars(
                select(FugitiveRow)
                .where(or_(FugitiveRow.mortal_entity_id == node_id, FugitiveRow.pursuer_entity_id == node_id))
                .order_by(FugitiveRow.id.desc())
            )
        )
        law = await session.get(SanctuaryLawRow, node_id) if is_realm else None
        satires = list(
            await session.scalars(
                select(SatireRow)
                .where(or_(SatireRow.satirist_entity_id == node_id, SatireRow.target_entity_id == node_id, SatireRow.polity_entity_id == node_id))
                .order_by(SatireRow.id.desc())
            )
        )
        jester = (
            await session.scalar(select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == node_id, OfficeRow.kind == OfficeKind.JESTER).limit(1))
            if is_realm
            else None
        )
        refs = await refs_of(
            session,
            [
                node_id,
                realm,
                jester,
                *(row.value_node_id for row in identities),
                *(row.settlement_entity_id for row in groups),
                *(row.mortal_entity_id for row in group_members),
                *(item for row in sanctuaries for item in (row.fugitive_entity_id, row.host_entity_id, row.pursuer_entity_id)),
                *(item for row in fled for item in (row.mortal_entity_id, row.pursuer_entity_id)),
                *(item for row in satires for item in (row.satirist_entity_id, row.target_entity_id, row.polity_entity_id, row.work_entity_id)),
            ],
        )
    return BelongingNodeView(
        node=ref(refs, node_id),
        epoch=epoch,
        realm=at(refs, realm),
        identities=[
            HeldIdentityView(
                layer=row.layer,
                value=at(refs, row.value_node_id),
                value_label=row.value_label,
                strength=row.strength,
                salience=row.salience,
                driver=row.driver,
                updated_epoch=row.updated_epoch,
                locked=row.locked,
            )
            for row in identities
        ],
        fault_layer=fault,
        peer_groups=[
            PeerGroupView(
                id=row.id,
                settlement=ref(refs, row.settlement_entity_id),
                social_class=row.social_class,
                play=row.play,
                children=row.children,
                cohesion=row.cohesion,
                deprived=row.deprived,
                formed_epoch=row.formed_epoch,
                dissolved_epoch=row.dissolved_epoch,
                members=[
                    PeerMemberView(
                        mortal=ref(refs, member.mortal_entity_id),
                        joined_epoch=member.joined_epoch,
                        deprived_epochs=member.deprived_epochs,
                        locked=member.locked,
                    )
                    for member in group_members
                    if member.group_id == row.id
                ],
                locked=row.locked,
            )
            for row in groups
        ],
        sanctuaries=[
            SanctuaryView(
                id=row.id,
                fugitive=ref(refs, row.fugitive_entity_id),
                host=ref(refs, row.host_entity_id),
                kind=row.kind,
                fugitive_kind=row.fugitive_kind,
                pursuer=at(refs, row.pursuer_entity_id),
                state=row.state,
                fee=row.fee,
                granted_epoch=row.granted_epoch,
                siege_epochs=row.siege_epochs,
                locked=row.locked,
            )
            for row in sanctuaries
        ],
        fugitives=[
            FugitiveView(
                id=row.id,
                mortal=ref(refs, row.mortal_entity_id),
                kind=row.kind,
                pursuer=at(refs, row.pursuer_entity_id),
                fled_epoch=row.fled_epoch,
                caught_epoch=row.caught_epoch,
                freed_epoch=row.freed_epoch,
                locked=row.locked,
            )
            for row in fled
        ],
        sanctuary_law=SanctuaryLawView(restricted=law.restricted, fee_pct=law.fee_pct, locked=law.locked) if law is not None else None,
        satires=[
            SatireView(
                id=row.id,
                satirist=at(refs, row.satirist_entity_id),
                target=ref(refs, row.target_entity_id),
                polity=at(refs, row.polity_entity_id),
                work=at(refs, row.work_entity_id),
                source=row.source,
                bite=row.bite,
                tolerated=row.tolerated,
                punished=row.punished,
                judged=row.judged,
                epoch=row.epoch,
                locked=row.locked,
            )
            for row in satires
        ],
        jester=at(refs, jester),
    )
