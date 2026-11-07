from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import FavourRow, HookRow
from aerona.db.tables.justice import ProposalStanceRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import LawProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand, HookSource, HookStrength
from aerona.domain.enums.justice import ProposalStance, ProposalState
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, LegitimacyBasis, OfficeKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.enactment import EnactmentTally, Hearing, Stand, lean_on, propose, reward, tend_proposals
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned

QUICK = {"progress_pct": 300, "event_pct": 0}


async def realm_with(realm: Realm, town: EntityRow, ruler: EntityRow, rule: DecisionRule = DecisionRule.COUNCIL) -> EntityRow:
    polity = await make(realm.session, "Crown of Fenmark", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=rule,
            capital_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await realm.session.flush()
    return polity


async def test_a_backed_proposal_moves_each_epoch_and_passes_into_law(realm: Realm) -> None:
    ctx = context(realm.session, tuned(enactment=QUICK))
    town = await settlement(realm, "Fenmark")
    ruler = await mortal(realm, "Aldis", location_id=town.id)
    polity = await realm_with(realm, town, ruler)
    book = await RealmBook.load(realm.session)
    row = await propose(ctx, book.realms[polity.id], LawKind.QUARANTINE, {}, champion_id=ruler.id, basis=LegitimacyBasis.COUNCIL)
    assert row is not None and row.state is ProposalState.DEBATING and row.progress == 0
    assert await propose(ctx, book.realms[polity.id], LawKind.QUARANTINE, {}, champion_id=ruler.id, basis=LegitimacyBasis.COUNCIL) is None
    tally = EnactmentTally()
    for _ in range(3):
        await tend_proposals(ctx, tally)
    assert row.state is ProposalState.PASSED and tally.passed == 1 and row.law_entity_id is not None
    law = await realm.session.get(LawProfileRow, row.law_entity_id)
    assert law is not None and law.kind is LawKind.QUARANTINE
    champion = await realm.session.get(ProposalStanceRow, (row.id, ruler.id))
    assert champion is not None and champion.stance is ProposalStance.SUPPORT


async def test_a_stalled_proposal_fails_and_shames_its_champion(realm: Realm) -> None:
    ctx = context(realm.session, tuned(enactment={**QUICK, "stall_epochs": 1, "champion_cost": 10}))
    town = await settlement(realm, "Greyhithe")
    ruler = await mortal(realm, "Brann", location_id=town.id)
    rival = await mortal(realm, "Cass", location_id=town.id)
    polity = await realm_with(realm, town, ruler)
    book = await RealmBook.load(realm.session)
    row = await propose(ctx, book.realms[polity.id], LawKind.QUARANTINE, {}, champion_id=ruler.id, basis=LegitimacyBasis.COUNCIL)
    assert row is not None
    realm.session.add(ProposalStanceRow(proposal_id=row.id, node_id=rival.id, stance=ProposalStance.OPPOSE, weight=100, locked=True))
    profile = await realm.session.get(MortalProfileRow, ruler.id)
    before = profile.renown if profile is not None else 0
    tally = EnactmentTally()
    await tend_proposals(ctx, tally)
    assert row.state is ProposalState.FAILED and tally.failed == 1 and row.opposition == 100
    after = await realm.session.get(MortalProfileRow, ruler.id)
    assert after is not None and after.renown < max(before, 10)


async def test_a_hook_turns_a_council_vote_and_the_champion_owes_favours_to_free_votes(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Highmoor")
    ruler = await mortal(realm, "Dorran", location_id=town.id)
    member = await mortal(realm, "Esk", location_id=town.id)
    friend = await mortal(realm, "Fen", location_id=town.id)
    polity = await realm_with(realm, town, ruler)
    book = await RealmBook.load(realm.session)
    row = await propose(ctx, book.realms[polity.id], LawKind.QUARANTINE, {}, champion_id=ruler.id, basis=LegitimacyBasis.COUNCIL)
    assert row is not None
    realm.session.add(HookRow(holder_node_id=ruler.id, target_node_id=member.id, strength=HookStrength.STRONG, source=HookSource.SECRET, created_epoch=1))
    await realm.session.flush()
    hearing = Hearing(
        book.realms[polity.id],
        row,
        {member.id: Stand(ProposalStance.OPPOSE, 30), friend.id: Stand(ProposalStance.SUPPORT, 30), ruler.id: Stand(ProposalStance.SUPPORT, 30)},
    )
    tally = EnactmentTally()
    await lean_on(ctx, hearing, tally)
    assert hearing.stands[member.id].stance is ProposalStance.SUPPORT and hearing.stands[member.id].hooked and tally.hooked == 1
    hook = await realm.session.scalar(select(HookRow).where(HookRow.target_node_id == member.id))
    assert hook is not None and hook.last_demand is HookDemand.VOTE
    await reward(ctx, hearing)
    owed = list(await realm.session.scalars(select(FavourRow).where(FavourRow.owed_by_node_id == ruler.id)))
    assert [favour.owed_to_node_id for favour in owed] == [friend.id] and owed[0].origin is FavourOrigin.VOTE
