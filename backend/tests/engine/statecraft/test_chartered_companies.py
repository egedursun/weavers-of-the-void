from sqlalchemy import select

from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.factions.companies import CompanyTally, conquer, foreign_route, found_companies
from aerona.engine.primitives.queries import living_entity
from tests.engine.society.factories import Realm, context, make, settlement, trade_route, tuned
from tests.engine.statecraft.test_statecraft import polity


async def test_a_rich_guild_charters_a_company_for_a_foreign_road_and_it_seizes_the_far_end(realm: Realm) -> None:
    ctx = context(realm.session, tuned(companies={"found_pct": 100, "found_wealth": 0}))
    _, home_core = await polity(realm, "Lion Throne")
    _, far_core = await polity(realm, "Hart Throne")
    home = await settlement(realm, "Saltmere", location_id=realm.region.id)
    far = await settlement(realm, "Farwatch", location_id=realm.far_region.id)
    assert await foreign_route(ctx, home.id) is None
    lion = await realm.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home_core.id))
    hart = await realm.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == far_core.id))
    realm.session.add_all([PolityMemberRow(polity_entity_id=lion, member_entity_id=home.id), PolityMemberRow(polity_entity_id=hart, member_entity_id=far.id)])
    road = await trade_route(realm, home, far)
    guild = await make(realm.session, "Salt Guild", EntityType.FACTION, FactionStats(wealth=90), world_id=realm.world.id, location_id=home.id)
    realm.session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.MERCHANT_GUILD, home_entity_id=home.id, influence_over={}, locked=[]))
    await realm.session.flush()
    route = await foreign_route(ctx, home.id)
    assert route is not None and route.route_entity_id == road.id
    tally = CompanyTally()
    await found_companies(ctx, tally)
    company_row = await realm.session.scalar(select(CompanyProfileRow).where(CompanyProfileRow.route_entity_id == road.id))
    assert company_row is not None and company_row.polity_entity_id == lion
    assert await foreign_route(ctx, home.id) is None
    company = await living_entity(realm.session, company_row.faction_entity_id)
    assert company is not None
    await conquer(ctx, company, company_row, tally)
    assert company_row.region_entity_id == realm.far_region.id and tally.conquered == 1
    occupation = await realm.session.get(OccupationRow, realm.far_region.id)
    assert occupation is not None and occupation.occupier_entity_id == company.id
