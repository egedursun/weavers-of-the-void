from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.models.entity_stats import HouseStats
from aerona.engine.economy.purse import wealth_points
from aerona.engine.military.spycraft import blackmail_office, plant_claimant
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import relation
from tests.engine.society.factories import Realm, context, make, mortal, people, settlement
from tests.engine.statecraft.crowns import crown


async def office(realm: Realm, polity: EntityRow, kind: OfficeKind, name: str) -> EntityRow:
    holder = await mortal(realm, name)
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=kind, holder_entity_id=holder.id, powers=[], locked=[]))
    await realm.session.flush()
    return holder


async def network(realm: Realm, owner: EntityRow, target: EntityRow) -> SpyNetworkRow:
    row = SpyNetworkRow(owner_entity_id=owner.id, target_entity_id=target.id, intel=10, exposure=60, since_epoch=1, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    return row


async def profile_of(realm: Realm, polity: EntityRow) -> PolityProfileRow:
    found = await realm.session.get(PolityProfileRow, polity.id)
    assert found is not None
    return found


async def test_a_blackmailed_treasurer_drains_coin_into_the_spying_realms_treasury(realm: Realm) -> None:
    ctx = context(realm.session)
    victim, core = await crown(realm, "Reed Throne", treasury=100000)
    spy, _ = await crown(realm, "Iron Crown")
    await office(realm, victim, OfficeKind.TREASURER, "Treasurer")
    assert await blackmail_office(ctx, spy, core, await network(realm, spy, core)) is not None
    owed = ctx.rules.espionage.blackmail_wealth * ctx.rules.taxation.wealth_per_treasury
    assert (await profile_of(realm, victim)).treasury == 100000 - owed
    assert (await profile_of(realm, spy)).treasury == owed


async def test_a_spy_without_a_purse_takes_the_drained_coin_as_wealth_points(realm: Realm) -> None:
    ctx = context(realm.session)
    victim, core = await crown(realm, "Reed Throne", treasury=100000)
    spy = await people(realm, "Wandering Eyes", wealth=10)
    await office(realm, victim, OfficeKind.TREASURER, "Treasurer")
    await blackmail_office(ctx, spy, core, await network(realm, spy, core))
    owed = ctx.rules.espionage.blackmail_wealth * ctx.rules.taxation.wealth_per_treasury
    assert stat(spy, "wealth") == 10 + wealth_points(ctx.rules, owed)


async def test_a_held_treasury_cannot_be_drained(realm: Realm) -> None:
    ctx = context(realm.session)
    victim, core = await crown(realm, "Reed Throne", treasury=100000)
    spy, _ = await crown(realm, "Iron Crown")
    (await profile_of(realm, victim)).locked = ["treasury"]
    await office(realm, victim, OfficeKind.TREASURER, "Treasurer")
    await blackmail_office(ctx, spy, core, await network(realm, spy, core))
    assert (await profile_of(realm, victim)).treasury == 100000 and (await profile_of(realm, spy)).treasury == 0


async def test_each_blackmailed_office_serves_the_spy_in_its_own_way(realm: Realm) -> None:
    ctx = context(realm.session)
    table = ctx.rules.espionage
    victim, core = await crown(realm, "Reed Throne")
    spy, _ = await crown(realm, "Iron Crown")
    spymaster = await office(realm, victim, OfficeKind.SPYMASTER, "Spymaster")
    watched = await network(realm, spy, core)
    await blackmail_office(ctx, spy, core, watched)
    assert watched.exposure == 0
    await realm.session.delete(await realm.session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == spymaster.id)))
    await realm.session.flush()
    await office(realm, victim, OfficeKind.MARSHAL, "Marshal")
    await blackmail_office(ctx, spy, core, watched)
    assert watched.intel == 10 + table.intel_gain and watched.warned_epoch == ctx.epoch


async def test_a_blackmailed_envoy_speaks_for_the_spy(realm: Realm) -> None:
    ctx = context(realm.session)
    victim, core = await crown(realm, "Reed Throne")
    spy, _ = await crown(realm, "Iron Crown")
    await office(realm, victim, OfficeKind.AMBASSADOR, "Ambassador")
    before = await relation(realm.session, ctx.rules, core.id, spy.id)
    holder_id = await blackmail_office(ctx, spy, core, await network(realm, spy, core))
    held = await realm.session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == holder_id, OfficeRow.kind == OfficeKind.AMBASSADOR))
    assert holder_id is not None and held is not None
    assert await relation(realm.session, ctx.rules, core.id, spy.id) > before


async def test_a_blackmailed_lesser_officer_pays_from_their_own_purse_and_a_penniless_one_pays_nothing(realm: Realm) -> None:
    ctx = context(realm.session)
    table = ctx.rules.espionage
    victim, core = await crown(realm, "Reed Throne")
    spy = await people(realm, "Wandering Eyes", wealth=10)
    judge = await office(realm, victim, OfficeKind.HIGH_JUDGE, "Judge")
    purse, _ = await ensure_profile(realm.session, judge.id, ctx.epoch)
    purse.wealth = 40
    await blackmail_office(ctx, spy, core, await network(realm, spy, core))
    assert purse.wealth == 40 - table.blackmail_wealth and stat(spy, "wealth") == 10 + table.blackmail_wealth
    purse.wealth = 0
    await blackmail_office(ctx, spy, core, await network(realm, spy, core))
    assert purse.wealth == 0 and stat(spy, "wealth") == 10 + table.blackmail_wealth


async def test_a_target_outside_any_realm_or_without_officers_yields_nothing(realm: Realm) -> None:
    ctx = context(realm.session)
    spy = await people(realm, "Wandering Eyes")
    loose = await people(realm, "Free Folk")
    assert await blackmail_office(ctx, spy, loose, await network(realm, spy, loose)) is None
    _, core = await crown(realm, "Empty Throne")
    assert await blackmail_office(ctx, spy, core, await network(realm, spy, core)) is None


async def noble(realm: Realm, name: str, location_id: int, importance: int = 1) -> EntityRow:
    house = await make(realm.session, f"House {name}", EntityType.HOUSE, HouseStats(), world_id=realm.world.id)
    member = await mortal(realm, name, location_id=location_id)
    member.importance = importance
    realm.session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member.id, joined_epoch=1, by_marriage=False))
    await realm.session.flush()
    return member


async def test_spies_plant_a_pretender_from_the_target_realms_own_nobility(realm: Realm) -> None:
    ctx = context(realm.session)
    victim, core = await crown(realm, "Reed Throne")
    town = await settlement(realm, "Reedmoor")
    realm.session.add(PolityMemberRow(polity_entity_id=victim.id, member_entity_id=town.id))
    foreign_town = await settlement(realm, "Far Keep")
    await noble(realm, "Foreign Lord", foreign_town.id, importance=99)
    lesser = await noble(realm, "Lesser Lady", town.id, importance=2)
    greater = await noble(realm, "Greater Lord", town.id, importance=8)
    spy, _ = await crown(realm, "Iron Crown")
    claimant = await plant_claimant(ctx, spy, core)
    assert claimant is not None and claimant.id == greater.id
    claim = await realm.session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == greater.id))
    assert claim is not None and claim.polity_entity_id == victim.id and claim.basis is ClaimBasis.FABRICATED
    second = await plant_claimant(ctx, spy, core)
    assert second is not None and second.id == lesser.id
    assert await plant_claimant(ctx, spy, core) is None
