from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow, LawProposalRow, ProposalStanceRow
from aerona.db.tables.polity import LawProfileRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.justice import CaseStage, Deposition, ProposalStance, ProposalState, TrialKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind
from aerona.domain.models.entity_stats import MortalStats, PolityStats
from aerona.services.player import justice
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_brings_a_law_weighs_its_voices_and_carries_it(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Vellis", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    polity = await make_entity(session, "Realm of Vellis", EntityType.POLITY, world_id=world.world.id, stats=PolityStats())
    voice = await make_entity(session, "Orla", EntityType.MORTAL, world_id=world.world.id, location_id=town.id, stats=MortalStats())
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.COUNCIL,
            capital_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    made = await justice.create_proposal(scope, justice.CreateProposal(polity_id=polity.id, kind=LawKind.TAX_RATE, params={"rate": 20}, champion_id=voice.id))
    proposal_id = int(made.values["proposal_id"])
    await justice.edit_proposal(scope, justice.EditProposal(proposal_id=proposal_id, progress=40, support=60, params={"rate": 15}))
    row = await session.get(LawProposalRow, proposal_id)
    assert row is not None and row.progress == 40 and row.params["rate"] == 15 and {"progress", "support", "params"} <= set(row.locked)
    await justice.set_stance(scope, justice.SetStance(proposal_id=proposal_id, node_id=voice.id, stance=ProposalStance.OPPOSE, weight=25))
    stance = await session.get(ProposalStanceRow, (proposal_id, voice.id))
    assert stance is not None and stance.stance is ProposalStance.OPPOSE and stance.locked
    await justice.remove_stance(scope, justice.StanceTarget(proposal_id=proposal_id, node_id=voice.id))
    await justice.hold_proposal(scope, justice.HoldProposal(proposal_id=proposal_id, hold=False))
    assert row.locked == []
    carried = await justice.pass_proposal(scope, justice.ProposalTarget(proposal_id=proposal_id))
    law = await session.get(LawProfileRow, int(carried.values["law_id"]))
    assert row.state is ProposalState.PASSED and law is not None and law.params["rate"] == 15
    await justice.delete_proposal(scope, justice.ProposalTarget(proposal_id=proposal_id))
    assert await session.get(LawProposalRow, proposal_id) is None


async def test_the_god_brings_a_charge_calls_witnesses_and_tries_it(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Corrin", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    accused = await make_entity(session, "Pell", EntityType.MORTAL, world_id=world.world.id, location_id=town.id, stats=MortalStats())
    witness = await make_entity(session, "Rue", EntityType.MORTAL, world_id=world.world.id, location_id=town.id, stats=MortalStats())
    opened = await justice.open_case(
        scope, justice.OpenCase(settlement_id=town.id, crime=CrimeKind.THEFT, accused_id=accused.id, culprit_id=accused.id, trial=TrialKind.JURY, evidence=80)
    )
    case_id = int(opened.values["case_id"])
    await justice.set_witness(scope, justice.SetWitness(case_id=case_id, witness_id=witness.id, testimony=Deposition.ACCUSES, reliability=70))
    assert await session.get(CaseWitnessRow, (case_id, witness.id)) is not None
    await justice.edit_case(scope, justice.EditCase(case_id=case_id, evidence=90, trial=TrialKind.JUDGE, judge_id=witness.id))
    case = await session.get(CrimeCaseRow, case_id)
    assert case is not None and case.evidence == 90 and case.judge_entity_id == witness.id and "evidence" in case.locked
    await justice.hold_case(scope, justice.HoldCase(case_id=case_id, hold=False))
    tried = await justice.try_now(scope, justice.CaseTarget(case_id=case_id))
    assert case.stage is CaseStage.CLOSED and tried.values["verdict"] == "guilty"
    await justice.remove_witness(scope, justice.WitnessTarget(case_id=case_id, witness_id=witness.id))
    await justice.delete_case(scope, justice.CaseTarget(case_id=case_id))
    assert await session.get(CrimeCaseRow, case_id) is None
