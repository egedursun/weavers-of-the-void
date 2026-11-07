from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.intrigue import name_of
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow, LawProposalRow, ProposalStanceRow
from aerona.domain.enums.justice import CaseStage, ProposalState
from aerona.engine.mortal.justice import CRIME_TEXT
from aerona.engine.polity.enactment import law_title
from aerona.engine.polity.trials import TRIAL_TEXT

RECENT = 1


async def proposal_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    found: list[str] = []
    debating = select(LawProposalRow).where(LawProposalRow.state == ProposalState.DEBATING)
    for row in await session.scalars(debating.where(LawProposalRow.champion_node_id == me.id).order_by(LawProposalRow.id)):
        realm = await name_of(session, row.polity_entity_id)
        found.append(f"you champion {law_title(row.kind)} before {realm}: {row.progress} of 100, {row.support} for and {row.opposition} against")
    stances = await session.execute(
        select(ProposalStanceRow, LawProposalRow)
        .join(LawProposalRow, LawProposalRow.id == ProposalStanceRow.proposal_id)
        .where(ProposalStanceRow.node_id == me.id, LawProposalRow.state == ProposalState.DEBATING, LawProposalRow.champion_node_id != me.id)
        .order_by(LawProposalRow.id)
    )
    for stance, row in stances:
        hooked = ", bound by a hook" if stance.hooked else ""
        found.append(f"you {stance.stance.value} {law_title(row.kind)} in {await name_of(session, row.polity_entity_id)}{hooked}")
    return found


async def case_lines(session: AsyncSession, me: EntityRow, epoch: int) -> list[str]:
    found: list[str] = []
    for case in await session.scalars(select(CrimeCaseRow).where(CrimeCaseRow.accused_entity_id == me.id).order_by(CrimeCaseRow.id)):
        crime = CRIME_TEXT[case.crime]
        if case.stage is CaseStage.TRIAL:
            how = TRIAL_TEXT[case.trial] if case.trial is not None else "soon"
            found.append(f"you stand accused of {crime} in {await name_of(session, case.settlement_entity_id)}, to be tried {how}")
        elif case.verdict is not None and case.closed_epoch is not None and case.closed_epoch >= epoch - RECENT:
            found.append(f"you were {case.verdict.value} of {crime}")
    witnessed = await session.execute(
        select(CaseWitnessRow, CrimeCaseRow)
        .join(CrimeCaseRow, CrimeCaseRow.id == CaseWitnessRow.case_id)
        .where(CaseWitnessRow.witness_entity_id == me.id, CrimeCaseRow.stage == CaseStage.TRIAL)
        .order_by(CrimeCaseRow.id)
    )
    for witness, case in witnessed:
        found.append(f"you bear witness and {witness.testimony.value} {await name_of(session, case.accused_entity_id)} on a charge of {CRIME_TEXT[case.crime]}")
    judging = select(CrimeCaseRow).where(CrimeCaseRow.judge_entity_id == me.id, CrimeCaseRow.stage == CaseStage.TRIAL).order_by(CrimeCaseRow.id)
    for case in await session.scalars(judging):
        found.append(f"you will judge {await name_of(session, case.accused_entity_id)} for {CRIME_TEXT[case.crime]}, on evidence of {case.evidence}")
    return found
