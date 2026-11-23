from sqlalchemy import select

from aerona.catalog.estates import PRIVILEGES
from aerona.catalog.life.customs import COOP_GAINS
from aerona.catalog.life.factions import GOAL_WEIGHTS
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import ClaimRow, OfficeRow
from aerona.db.tables.regime import PatronageTieRow
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.customs import CoopPurpose
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import EstatePrivilege, FactionGoalKind, FactionKind
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.enums.regime import ClientRole
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import ArtworkStats, FactionStats
from aerona.engine.factions.privileges import landed_class, reserved_class
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.offices import appoint, make_claim
from aerona.engine.regime.patronage import PatronageTally, bind_clients
from tests.engine.society.factories import Realm, context, make, mortal
from tests.engine.statecraft.test_affairs import realm_of


def test_every_new_faction_estate_and_coop_value_has_its_rule() -> None:
    assert GOAL_WEIGHTS[FactionGoalKind.RUIN_RIVAL] == "ruin_rival_weight"
    assert PRIVILEGES[EstatePrivilege.RESERVED_OFFICES].cost == "reserved_offices_cost"
    assert COOP_GAINS[CoopPurpose.GRANARY] == "granary_gain"


async def test_reserved_offices_keep_others_out_and_land_belongs_to_one_estate(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, town, _ = await realm_of(realm, "Corvane")
    estate = await make(realm.session, "Lords", EntityType.FACTION, FactionStats(), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=estate.id, kind=FactionKind.ESTATE, home_entity_id=town.id, influence_over={}, locked=[]))
    realm.session.add(
        EstateProfileRow(faction_entity_id=estate.id, polity_entity_id=polity.id, social_class=SocialClass.NOBLE, loyalty=50, influence=50, locked=[])
    )
    for privilege in (EstatePrivilege.RESERVED_OFFICES, EstatePrivilege.LAND_HOLDING):
        realm.session.add(EstatePrivilegeRow(estate_entity_id=estate.id, privilege=privilege, granted_epoch=3))
    office = OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.TREASURER, powers=[])
    realm.session.add(office)
    commoner = await mortal(realm, "Tam", location_id=town.id)
    commoner.social_class = SocialClass.FARMER
    await realm.session.flush()
    assert await reserved_class(realm.session, polity.id) is SocialClass.NOBLE
    assert await landed_class(realm.session, polity.id) is SocialClass.NOBLE
    book = await RealmBook.load(realm.session)
    await appoint(ctx, book.realms[polity.id], office, commoner, by_id=None, reason="test")
    assert office.holder_entity_id is None


async def test_an_artist_becomes_a_client_and_an_adopted_heir_holds_a_claim(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, town, ruler = await realm_of(realm, "Corvane")
    painter = await mortal(realm, "Lune", location_id=town.id)
    work = await make(realm.session, "The Bright Field", EntityType.ARTWORK, ArtworkStats(), world_id=realm.world.id, location_id=town.id)
    realm.session.add(ArtworkProfileRow(artwork_entity_id=work.id, medium=next(iter(ArtMode)), author_entity_id=painter.id, patron_entity_id=ruler.id))
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    await bind_clients(ctx, book, PatronageTally())
    tie = await realm.session.scalar(select(PatronageTieRow).where(PatronageTieRow.client_entity_id == painter.id))
    assert tie is not None and tie.role is ClientRole.ARTIST
    claim = await make_claim(ctx, book.realms[polity.id], painter, ClaimBasis.ADOPTION, 60, backer=ruler.id)
    assert claim is not None and claim.backer_entity_id == ruler.id
    found = await realm.session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == painter.id))
    assert found is not None and found.basis is ClaimBasis.ADOPTION
