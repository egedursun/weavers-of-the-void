from collections.abc import Mapping

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.justice import CrimeCaseView, JusticeView, LawProposalView, StanceView, WitnessView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow, LawProposalRow, ProposalStanceRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.polity.enactment import law_title
from aerona.rules.registry import Rules

router = APIRouter(tags=["justice"])
NO_NODE = "Nothing lives there."


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def proposal_view(row: LawProposalRow, stances: list[ProposalStanceRow], refs: Mapping[int, NodeRef], rules: Rules) -> LawProposalView:
    return LawProposalView(
        id=row.id,
        polity=ref(refs, row.polity_entity_id),
        kind=row.kind,
        title=law_title(row.kind).capitalize(),
        params=dict(row.params),
        champion=ref(refs, row.champion_node_id),
        law=ref(refs, row.law_entity_id),
        basis=row.basis,
        progress=row.progress,
        support=row.support,
        opposition=row.opposition,
        stalled_epochs=row.stalled_epochs,
        stall_limit=rules.enactment.stall_epochs,
        state=row.state,
        last_event=row.last_event,
        amended=row.amended,
        proposed_epoch=row.proposed_epoch,
        resolved_epoch=row.resolved_epoch,
        locked=list(row.locked or []),
        stances=[
            StanceView(voice=refs[stance.node_id], stance=stance.stance, weight=stance.weight, hooked=stance.hooked, locked=stance.locked)
            for stance in stances
            if stance.node_id in refs
        ],
    )


def case_view(row: CrimeCaseRow, witnesses: list[CaseWitnessRow], refs: Mapping[int, NodeRef], rules: Rules) -> CrimeCaseView:
    return CrimeCaseView(
        id=row.id,
        crime=row.crime,
        settlement=ref(refs, row.settlement_entity_id),
        polity=ref(refs, row.polity_entity_id),
        culprit=ref(refs, row.culprit_entity_id),
        accused=ref(refs, row.accused_entity_id),
        investigator=ref(refs, row.investigator_entity_id),
        judge=ref(refs, row.judge_entity_id),
        stage=row.stage,
        trial=row.trial,
        evidence=row.evidence,
        standard=rules.trials.standard,
        tortured=row.tortured,
        forged=row.forged,
        verdict=row.verdict,
        wrongful=row.wrongful,
        penalty=row.penalty,
        opened_epoch=row.opened_epoch,
        closed_epoch=row.closed_epoch,
        locked=list(row.locked or []),
        witnesses=[
            WitnessView(witness=refs[witness.witness_entity_id], testimony=witness.testimony, reliability=witness.reliability, locked=witness.locked)
            for witness in witnesses
            if witness.witness_entity_id in refs
        ],
    )


@router.get("/justice/{node_id}", response_model=JusticeView)
async def justice_view(services: ServicesDep, node_id: int = Path(ge=1)) -> JusticeView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError(NO_NODE)
        entity = await session.get(EntityRow, node_id)
        rules = rules_from_snapshot((await CosmosRepository(session).require_cosmos()).rules_snapshot)
        voiced = select(ProposalStanceRow.proposal_id).where(ProposalStanceRow.node_id == node_id)
        proposals = list(
            await session.scalars(
                select(LawProposalRow)
                .where(or_(LawProposalRow.polity_entity_id == node_id, LawProposalRow.champion_node_id == node_id, LawProposalRow.id.in_(voiced)))
                .order_by(LawProposalRow.id.desc())
            )
        )
        stances = list(await session.scalars(select(ProposalStanceRow).where(ProposalStanceRow.proposal_id.in_([row.id for row in proposals]))))
        testified = select(CaseWitnessRow.case_id).where(CaseWitnessRow.witness_entity_id == node_id)
        cases = list(
            await session.scalars(
                select(CrimeCaseRow)
                .where(
                    or_(
                        CrimeCaseRow.settlement_entity_id == node_id,
                        CrimeCaseRow.polity_entity_id == node_id,
                        CrimeCaseRow.culprit_entity_id == node_id,
                        CrimeCaseRow.accused_entity_id == node_id,
                        CrimeCaseRow.investigator_entity_id == node_id,
                        CrimeCaseRow.judge_entity_id == node_id,
                        CrimeCaseRow.id.in_(testified),
                    )
                )
                .order_by(CrimeCaseRow.id.desc())
            )
        )
        witnesses = list(await session.scalars(select(CaseWitnessRow).where(CaseWitnessRow.case_id.in_([row.id for row in cases]))))
        home = entity.location_id if entity is not None and entity.entity_type is EntityType.MORTAL else None
        ids: set[int] = {node_id, *([home] if home is not None else [])}
        for row in proposals:
            ids.update(item for item in (row.polity_entity_id, row.champion_node_id, row.law_entity_id) if item is not None)
        ids.update(stance.node_id for stance in stances)
        for case in cases:
            ids.update(
                item
                for item in (
                    case.settlement_entity_id,
                    case.polity_entity_id,
                    case.culprit_entity_id,
                    case.accused_entity_id,
                    case.investigator_entity_id,
                    case.judge_entity_id,
                )
                if item is not None
            )
        ids.update(witness.witness_entity_id for witness in witnesses)
        refs = await node_refs(session, ids)
        return JusticeView(
            node_id=node_id,
            is_realm=entity is not None and entity.entity_type is EntityType.POLITY,
            is_city=entity is not None and entity.entity_type is EntityType.SETTLEMENT,
            is_mortal=entity is not None and entity.entity_type is EntityType.MORTAL,
            home=ref(refs, home),
            proposals=[proposal_view(row, [stance for stance in stances if stance.proposal_id == row.id], refs, rules) for row in proposals],
            cases=[case_view(row, [witness for witness in witnesses if witness.case_id == row.id], refs, rules) for row in cases],
        )
