from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.renown import RulerCurrencyRow
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.titles import TitleTier
from aerona.domain.models.entity_stats import CultStats, FactionStats
from aerona.engine.polity.seats import SeatTally, seat_of, tend_seats
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned


async def test_faiths_companies_and_guilds_raise_seats_held_by_their_leaders(realm: Realm) -> None:
    ctx = context(realm.session, tuned(titles={"faith_local_followers": 100, "faith_high_followers": 1000, "seat_prestige": 3}))
    town = await settlement(realm, "Morrowdeep")
    great = await make(realm.session, "Choir of Dawn", EntityType.CULT, CultStats(followers=5000), world_id=realm.world.id, location_id=town.id)
    lesser = await make(realm.session, "Choir of Dusk", EntityType.CULT, CultStats(followers=1500), world_id=realm.world.id, location_id=town.id)
    small = await make(realm.session, "Choir of Noon", EntityType.CULT, CultStats(followers=150), world_id=realm.world.id, location_id=town.id)
    await make(realm.session, "Choir of None", EntityType.CULT, CultStats(followers=10), world_id=realm.world.id, location_id=town.id)
    cleric = await mortal(realm, "Nadia", location_id=town.id)
    cleric.mortal_role = MortalRole.PRIEST
    company = await make(realm.session, "the Grey Lances", EntityType.FACTION, FactionStats(strength=40), world_id=realm.world.id, location_id=town.id)
    guild = await make(realm.session, "the Weavers", EntityType.FACTION, FactionStats(wealth=40), world_id=realm.world.id, location_id=town.id)
    captain = await mortal(realm, "Orla", location_id=town.id)
    master = await mortal(realm, "Pell", location_id=town.id)
    for faction, kind, leader in ((company, FactionKind.MERCENARY_COMPANY, captain), (guild, FactionKind.CRAFT_GUILD, master)):
        realm.session.add(FactionProfileRow(faction_entity_id=faction.id, kind=kind, home_entity_id=town.id, influence_over={}, locked=[]))
        realm.session.add(FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=leader.id, rank=FactionRank.LEADER))
    realm.session.add(RulerCurrencyRow(subject_node_id=captain.id, prestige=0, piety=0, dread=0, tyranny=0, updated_epoch=1, locked=[]))
    await realm.session.flush()
    tally = SeatTally()
    await tend_seats(ctx, tally)
    assert tally.founded == 5
    ranks = {cult.id: (await seat_of(ctx, cult.id)) for cult in (great, lesser, small)}
    assert [row.rank if row else None for row in ranks.values()] == [TitleTier.FAITH_SUPREME, TitleTier.FAITH_HIGH, TitleTier.FAITH_LOCAL]
    assert all(row is not None and row.holder_node_id == cleric.id for row in ranks.values())
    captaincy = await seat_of(ctx, company.id)
    mastership = await seat_of(ctx, guild.id)
    assert captaincy is not None and captaincy.rank is TitleTier.MILITARY and captaincy.holder_node_id == captain.id
    assert mastership is not None and mastership.rank is TitleTier.GUILD and mastership.holder_node_id == master.id
    purse = await realm.session.get(RulerCurrencyRow, captain.id)
    assert purse is not None and purse.prestige == 3
    company.status, company.end_epoch = EntityStatus.DESTROYED, 3
    await realm.session.flush()
    await tend_seats(ctx, tally)
    assert tally.vacant == 1 and captaincy.holder_node_id is None
