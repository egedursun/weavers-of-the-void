from aerona.db.tables.justice import ProposalStanceRow
from aerona.domain.enums.justice import ProposalStance
from aerona.domain.enums.polity import LawKind, LegitimacyBasis
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.enactment import back_law, pledge_vote, propose
from tests.engine.justice.test_enactment import realm_with
from tests.engine.society.factories import Realm, context, mortal, settlement


async def test_a_champion_binds_a_vote_and_a_backer_binds_the_ruler(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Highmoor")
    ruler = await mortal(realm, "Dorran", location_id=town.id)
    champion = await mortal(realm, "Esk", location_id=town.id)
    member = await mortal(realm, "Fen", location_id=town.id)
    polity = await realm_with(realm, town, ruler)
    book = await RealmBook.load(realm.session)
    assert await pledge_vote(ctx, champion.id, member.id) == 0
    row = await propose(ctx, book.realms[polity.id], LawKind.QUARANTINE, {}, champion_id=champion.id, basis=LegitimacyBasis.COUNCIL)
    assert row is not None
    assert await pledge_vote(ctx, champion.id, member.id) == 1
    bound = await realm.session.get(ProposalStanceRow, (row.id, member.id))
    assert bound is not None and bound.stance is ProposalStance.SUPPORT and bound.hooked and bound.weight == ctx.rules.enactment.council_weight
    assert await back_law(ctx, champion.id, ruler.id) == 1
    backed = await realm.session.get(ProposalStanceRow, (row.id, ruler.id))
    assert backed is not None and backed.weight == ctx.rules.enactment.ruler_weight
    bound.locked, bound.stance, bound.hooked = True, ProposalStance.OPPOSE, False
    await pledge_vote(ctx, champion.id, member.id)
    assert bound.stance is ProposalStance.OPPOSE and not bound.hooked
