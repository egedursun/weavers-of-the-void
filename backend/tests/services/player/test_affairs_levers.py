from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.affairs import (
    CouncilSeatRow,
    CourtPositionRow,
    CourtRow,
    MandateRow,
    NobleDemandRow,
    PolicyApprovalRow,
    ResolutionRow,
    ResolutionVoteRow,
    TaxPolicyRow,
)
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, MandateKind, MandateState, NobleWant, ResolutionKind, ResolutionState, TaxKind
from aerona.domain.models.entity_stats import FactionStats, MortalStats, PolityStats
from aerona.services.player import affairs
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_steers_council_seats_corruption_taxes_mandates_demands_and_approval(
    scope: PlayerScope, session: AsyncSession, world: PlayerWorld
) -> None:
    town = await make_entity(session, "Orrin", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    polity = await make_entity(session, "Realm of Orrin", EntityType.POLITY, world_id=world.world.id, stats=PolityStats())
    noble = await make_entity(session, "Lady Ves", EntityType.MORTAL, world_id=world.world.id, location_id=town.id, stats=MortalStats())
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.ASSEMBLY,
            capital_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    office = OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.MARSHAL, holder_entity_id=noble.id, powers=[])
    session.add(office)
    await session.flush()
    await affairs.set_task(scope, affairs.SetTask(office_id=office.id, task=CouncilTask.TRAIN_TROOPS, diligence=80))
    assert office.task is CouncilTask.TRAIN_TROOPS and office.diligence == 80 and "task" in office.locked
    await affairs.set_seat(scope, affairs.SetSeat(polity_id=polity.id, holder_id=noble.id, seats=3, votes=40))
    assert await session.get(CouncilSeatRow, (polity.id, noble.id)) is not None
    await affairs.remove_seat(scope, affairs.SeatTarget(polity_id=polity.id, holder_id=noble.id))
    await affairs.call_election(scope, affairs.CallElection(polity_id=polity.id))
    await affairs.set_corruption(scope, affairs.SetCorruption(polity_id=polity.id, corruption=45))
    profile = await session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.corruption == 45
    await affairs.set_tax(scope, affairs.SetTax(polity_id=polity.id, kind=TaxKind.TRADE, rate=12, farmed=True))
    tax = await session.get(TaxPolicyRow, (polity.id, TaxKind.TRADE))
    assert tax is not None and tax.rate == 12 and tax.farmed
    await affairs.remove_tax(scope, affairs.TaxTarget(polity_id=polity.id, kind=TaxKind.TRADE))
    issued = await affairs.issue_mandate(scope, affairs.IssueMandate(polity_id=polity.id, kind=MandateKind.CURFEW, settlement_id=town.id))
    mandate_id = int(issued.values["mandate_id"])
    await affairs.edit_mandate(scope, affairs.EditMandate(mandate_id=mandate_id, state=MandateState.MET))
    mandate = await session.get(MandateRow, mandate_id)
    assert mandate is not None and mandate.state is MandateState.MET
    await affairs.delete_mandate(scope, affairs.MandateTarget(mandate_id=mandate_id))
    await affairs.set_demand(scope, affairs.SetDemand(mortal_id=noble.id, want=NobleWant.OFFICE, met=True))
    assert await session.get(NobleDemandRow, (noble.id, NobleWant.OFFICE)) is not None
    await affairs.remove_demand(scope, affairs.DemandTarget(mortal_id=noble.id, want=NobleWant.OFFICE))
    await affairs.set_approval(scope, affairs.SetApproval(polity_id=polity.id, social_class=SocialClass.FARMER, approval=-30))
    approval = await session.get(PolicyApprovalRow, (polity.id, SocialClass.FARMER))
    assert approval is not None and approval.approval == -30
    await affairs.remove_approval(scope, affairs.ApprovalTarget(polity_id=polity.id, social_class=SocialClass.FARMER))


async def test_the_god_steers_assemblies_and_courts(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    polity = await make_entity(session, "Realm of Pell", EntityType.POLITY, world_id=world.world.id, stats=PolityStats())
    courtier = await make_entity(session, "Rook", EntityType.MORTAL, world_id=world.world.id, stats=MortalStats())
    assembly = await make_entity(session, "Concord", EntityType.FACTION, world_id=world.world.id, stats=FactionStats())
    assembly.engine_kind = EngineKind.INTERWORLD_FEDERATION
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.COUNCIL, emblem={}, legitimacy_parts={}, locked=[]
        )
    )
    await session.flush()
    made = await affairs.propose_resolution(scope, affairs.ProposeResolution(assembly_id=assembly.id, kind=ResolutionKind.EMBARGO, target_id=polity.id))
    resolution_id = int(made.values["resolution_id"])
    await affairs.set_vote(scope, affairs.SetVote(resolution_id=resolution_id, member_id=courtier.id, aye=True, weight=3))
    assert await session.get(ResolutionVoteRow, (resolution_id, courtier.id)) is not None
    await affairs.remove_vote(scope, affairs.VoteTarget(resolution_id=resolution_id, member_id=courtier.id))
    await affairs.edit_resolution(scope, affairs.EditResolution(resolution_id=resolution_id, state=ResolutionState.PASSED, until_epoch=9))
    resolution = await session.get(ResolutionRow, resolution_id)
    assert resolution is not None and resolution.state is ResolutionState.PASSED and "state" in resolution.locked
    await affairs.hold_resolution(scope, affairs.HoldResolution(resolution_id=resolution_id, hold=False))
    await affairs.delete_resolution(scope, affairs.ResolutionTarget(resolution_id=resolution_id))
    await affairs.edit_court(scope, affairs.EditCourt(polity_id=polity.id, grandeur=60, courtiers=4))
    court = await session.get(CourtRow, polity.id)
    assert court is not None and court.grandeur == 60
    await affairs.set_position(scope, affairs.SetPosition(polity_id=polity.id, position=CourtPosition.CHRONICLER, holder_id=courtier.id))
    position = await session.get(CourtPositionRow, (polity.id, CourtPosition.CHRONICLER))
    assert position is not None and position.holder_entity_id == courtier.id and position.locked
    await affairs.remove_position(scope, affairs.PositionTarget(polity_id=polity.id, position=CourtPosition.CHRONICLER))
