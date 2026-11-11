from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.law_depth import (
    AgentMotiveView,
    AppealView,
    CellView,
    DefectionView,
    JurisdictionView,
    KillingView,
    LegalSystemView,
    MoleHuntView,
    NetworkChoice,
    NodeLawView,
    OracleCaseView,
    OutlawView,
    PardonView,
    PrecedentView,
    PrisonerView,
    PrisonView,
    RegistryView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import (
    AppealRow,
    DefectionRow,
    JurisdictionRow,
    KillingRow,
    LegalSystemRow,
    MoleHuntRow,
    OutlawRow,
    PardonRow,
    PrecedentRow,
    PrisonerRow,
    PrisonRow,
    RegistryRow,
    SpyCellRow,
)
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.law_depth import LegalSystem
from aerona.domain.enums.structure import StructureKind

router = APIRouter(tags=["law"])
NodeId = Annotated[int, Path(ge=1)]


async def refs_for(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, [value for value in ids if value is not None])


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def appeal_views(session: AsyncSession, node_id: int) -> list[AppealView]:
    found = await session.execute(
        select(AppealRow, CrimeCaseRow)
        .join(CrimeCaseRow, CrimeCaseRow.id == AppealRow.case_id)
        .where(or_(CrimeCaseRow.accused_entity_id == node_id, CrimeCaseRow.polity_entity_id == node_id, CrimeCaseRow.settlement_entity_id == node_id))
        .order_by(AppealRow.case_id.desc())
    )
    pairs = list(found)
    refs = await refs_for(session, [case.accused_entity_id for _, case in pairs])
    return [
        AppealView(
            case_id=row.case_id,
            accused=at(refs, case.accused_entity_id),
            crime=case.crime,
            from_court=row.from_court,
            to_court=row.to_court,
            fee=row.fee,
            filed_epoch=row.filed_epoch,
            decided_epoch=row.decided_epoch,
            reversed=row.reversed,
            locked=list(row.locked),
        )
        for row, case in pairs
    ]


async def oracle_views(session: AsyncSession, node_id: int, system: LegalSystemRow | None) -> list[OracleCaseView]:
    if system is None or system.system is not LegalSystem.ORACLE:
        return []
    cases = list(
        await session.scalars(
            select(CrimeCaseRow)
            .where(CrimeCaseRow.stage == CaseStage.TRIAL, or_(CrimeCaseRow.polity_entity_id == node_id, CrimeCaseRow.settlement_entity_id == node_id))
            .order_by(CrimeCaseRow.id)
        )
    )
    refs = await refs_for(session, [case.accused_entity_id for case in cases])
    return [OracleCaseView(case_id=case.id, accused=at(refs, case.accused_entity_id), crime=case.crime, oracle_answer=case.oracle_answer) for case in cases]


async def registry_views(session: AsyncSession, node_id: int) -> list[RegistryView]:
    rows = list(
        await session.scalars(
            select(RegistryRow)
            .where(
                or_(
                    RegistryRow.holder_entity_id == node_id,
                    RegistryRow.owner_entity_id == node_id,
                    RegistryRow.counterparty_entity_id == node_id,
                    RegistryRow.subject_entity_id == node_id,
                )
            )
            .order_by(RegistryRow.id.desc())
        )
    )
    refs = await refs_for(
        session, [item for row in rows for item in (row.holder_entity_id, row.owner_entity_id, row.counterparty_entity_id, row.subject_entity_id)]
    )
    return [
        RegistryView(
            id=row.id,
            holder=at(refs, row.holder_entity_id),
            kind=row.kind,
            owner=at(refs, row.owner_entity_id),
            counterparty=at(refs, row.counterparty_entity_id),
            subject=at(refs, row.subject_entity_id),
            amount=row.amount,
            registered_epoch=row.registered_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def jurisdiction_views(session: AsyncSession, node_id: int) -> list[JurisdictionView]:
    rows = list(
        await session.scalars(
            select(JurisdictionRow)
            .where(or_(JurisdictionRow.holder_entity_id == node_id, JurisdictionRow.claimant_entity_id == node_id))
            .order_by(JurisdictionRow.holder_entity_id, JurisdictionRow.claimant_entity_id)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.holder_entity_id, row.claimant_entity_id)])
    return [
        JurisdictionView(
            holder=at(refs, row.holder_entity_id),
            claimant=at(refs, row.claimant_entity_id),
            claim=row.claim,
            strength=row.strength,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def pardon_views(session: AsyncSession, node_id: int) -> list[PardonView]:
    rows = list(
        await session.scalars(
            select(PardonRow).where(or_(PardonRow.granter_entity_id == node_id, PardonRow.pardoned_entity_id == node_id)).order_by(PardonRow.id.desc())
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.granter_entity_id, row.pardoned_entity_id)])
    return [
        PardonView(
            id=row.id,
            granter=at(refs, row.granter_entity_id),
            pardoned=at(refs, row.pardoned_entity_id),
            case_id=row.case_id,
            amnesty=row.amnesty,
            corrupt=row.corrupt,
            epoch=row.epoch,
        )
        for row in rows
    ]


async def outlaw_views(session: AsyncSession, node_id: int) -> list[OutlawView]:
    rows = list(
        await session.scalars(
            select(OutlawRow).where(or_(OutlawRow.mortal_entity_id == node_id, OutlawRow.polity_entity_id == node_id)).order_by(OutlawRow.mortal_entity_id)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.mortal_entity_id, row.polity_entity_id)])
    return [
        OutlawView(
            mortal=at(refs, row.mortal_entity_id),
            polity=at(refs, row.polity_entity_id),
            bounty=row.bounty,
            renown=row.renown,
            declared_epoch=row.declared_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def prisoner_views(session: AsyncSession, node_id: int) -> list[PrisonerView]:
    rows = list(
        await session.scalars(
            select(PrisonerRow)
            .where(or_(PrisonerRow.mortal_entity_id == node_id, PrisonerRow.prison_entity_id == node_id))
            .order_by(PrisonerRow.mortal_entity_id)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.mortal_entity_id, row.prison_entity_id)])
    return [
        PrisonerView(
            mortal=at(refs, row.mortal_entity_id),
            prison=at(refs, row.prison_entity_id),
            case_id=row.case_id,
            term=row.term,
            gang_rank=row.gang_rank,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def network_ids(session: AsyncSession, node_id: int) -> list[SpyNetworkRow]:
    return list(
        await session.scalars(
            select(SpyNetworkRow).where(or_(SpyNetworkRow.owner_entity_id == node_id, SpyNetworkRow.target_entity_id == node_id)).order_by(SpyNetworkRow.id)
        )
    )


async def agent_views(session: AsyncSession, node_id: int, networks: list[int]) -> list[AgentMotiveView]:
    rows = list(
        await session.scalars(
            select(SpyAgentRow).where(or_(SpyAgentRow.network_id.in_(networks), SpyAgentRow.mortal_entity_id == node_id)).order_by(SpyAgentRow.id)
        )
    )
    refs = await refs_for(session, [row.mortal_entity_id for row in rows])
    return [
        AgentMotiveView(
            agent_id=row.id, mortal=at(refs, row.mortal_entity_id), network_id=row.network_id, motive=row.motive, loyalty=row.loyalty, cell_id=row.cell_id
        )
        for row in rows
    ]


async def cell_views(session: AsyncSession, node_id: int, networks: list[int]) -> list[CellView]:
    rows = list(
        await session.scalars(
            select(SpyCellRow).where(
                or_(SpyCellRow.network_id.in_(networks), SpyCellRow.handler_entity_id == node_id, SpyCellRow.safe_house_entity_id == node_id)
            )
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.handler_entity_id, row.safe_house_entity_id)])
    return [
        CellView(
            id=row.id,
            network_id=row.network_id,
            handler=at(refs, row.handler_entity_id),
            safe_house=at(refs, row.safe_house_entity_id),
            dead_drops=row.dead_drops,
            locked=list(row.locked),
        )
        for row in sorted(rows, key=lambda item: item.id)
    ]


async def hunt_views(session: AsyncSession, node_id: int) -> list[MoleHuntView]:
    rows = list(
        await session.scalars(
            select(MoleHuntRow)
            .where(or_(MoleHuntRow.polity_entity_id == node_id, MoleHuntRow.spymaster_entity_id == node_id, MoleHuntRow.suspect_entity_id == node_id))
            .order_by(MoleHuntRow.id.desc())
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.polity_entity_id, row.spymaster_entity_id, row.suspect_entity_id)])
    return [
        MoleHuntView(
            id=row.id,
            polity=at(refs, row.polity_entity_id),
            spymaster=at(refs, row.spymaster_entity_id),
            suspect=at(refs, row.suspect_entity_id),
            mole=row.mole,
            outcome=row.outcome,
            epoch=row.epoch,
        )
        for row in rows
    ]


async def defection_views(session: AsyncSession, node_id: int) -> list[DefectionView]:
    rows = list(
        await session.scalars(
            select(DefectionRow)
            .where(or_(DefectionRow.defector_entity_id == node_id, DefectionRow.from_entity_id == node_id, DefectionRow.to_entity_id == node_id))
            .order_by(DefectionRow.id.desc())
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.defector_entity_id, row.from_entity_id, row.to_entity_id)])
    return [
        DefectionView(
            id=row.id,
            defector=at(refs, row.defector_entity_id),
            from_side=at(refs, row.from_entity_id),
            to_side=at(refs, row.to_entity_id),
            secrets=row.secrets,
            protected=row.protected,
            epoch=row.epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def killing_views(session: AsyncSession, node_id: int) -> list[KillingView]:
    rows = list(
        await session.scalars(
            select(KillingRow)
            .where(or_(KillingRow.victim_entity_id == node_id, KillingRow.killer_entity_id == node_id, KillingRow.examiner_entity_id == node_id))
            .order_by(KillingRow.id.desc())
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.victim_entity_id, row.killer_entity_id, row.examiner_entity_id)])
    return [
        KillingView(
            id=row.id,
            victim=at(refs, row.victim_entity_id),
            killer=at(refs, row.killer_entity_id),
            method=row.method,
            recognised=row.recognised,
            examiner=at(refs, row.examiner_entity_id),
            epoch=row.epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def prison_view(session: AsyncSession, node_id: int, refs: dict[int, NodeRef]) -> PrisonView | None:
    row = await session.get(PrisonRow, node_id)
    if row is None:
        return None
    return PrisonView(
        structure=at(refs, node_id), food=row.food, crowding=row.crowding, cruelty=row.cruelty, gang_strength=row.gang_strength, locked=list(row.locked)
    )


async def prisons_here(session: AsyncSession, node_id: int) -> list[NodeRef]:
    ids = list(
        await session.scalars(
            select(StructureProfileRow.structure_entity_id)
            .where(
                StructureProfileRow.kind == StructureKind.PRISON,
                or_(StructureProfileRow.host_entity_id == node_id, StructureProfileRow.structure_entity_id == node_id),
            )
            .order_by(StructureProfileRow.structure_entity_id)
        )
    )
    refs = await refs_for(session, ids)
    return [refs[item] for item in ids if item in refs]


@router.get("/law/of/{node_id}", response_model=NodeLawView)
async def node_law(services: ServicesDep, node_id: NodeId) -> NodeLawView:
    async with reader(services) as session:
        refs = await node_refs(session, [node_id])
        if node_id not in refs:
            raise NotFoundError("No such thing.")
        system = await session.get(LegalSystemRow, node_id)
        networks = await network_ids(session, node_id)
        network_refs = await refs_for(session, [item for row in networks for item in (row.owner_entity_id, row.target_entity_id)])
        precedents = await session.scalars(
            select(PrecedentRow).where(PrecedentRow.holder_entity_id == node_id).order_by(PrecedentRow.authority.desc(), PrecedentRow.id)
        )
        return NodeLawView(
            node=refs[node_id],
            system=LegalSystemView(system=system.system, since_epoch=system.since_epoch, locked=list(system.locked)) if system is not None else None,
            precedents=[
                PrecedentView(
                    id=row.id,
                    crime=row.crime,
                    verdict=row.verdict,
                    court=row.court,
                    case_id=row.case_id,
                    authority=row.authority,
                    overturned=row.overturned,
                    epoch=row.epoch,
                    locked=list(row.locked),
                )
                for row in precedents
            ],
            appeals=await appeal_views(session, node_id),
            oracle_cases=await oracle_views(session, node_id, system),
            registries=await registry_views(session, node_id),
            jurisdictions=await jurisdiction_views(session, node_id),
            pardons=await pardon_views(session, node_id),
            outlaws=await outlaw_views(session, node_id),
            prison=await prison_view(session, node_id, refs),
            prisons_here=await prisons_here(session, node_id),
            prisoners=await prisoner_views(session, node_id),
            agents=await agent_views(session, node_id, [row.id for row in networks]),
            cells=await cell_views(session, node_id, [row.id for row in networks]),
            networks=[NetworkChoice(id=row.id, owner=at(network_refs, row.owner_entity_id), target=at(network_refs, row.target_entity_id)) for row in networks],
            hunts=await hunt_views(session, node_id),
            defections=await defection_views(session, node_id),
            killings=await killing_views(session, node_id),
        )
