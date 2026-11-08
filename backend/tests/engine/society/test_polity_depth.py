from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OathRow, PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import OathKind, OathStatus, OfficeKind
from aerona.domain.enums.settlement import SizeTier, TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import REVOLT_CAUSES
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.phases.warfare import incite_uprising
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import found_polity, set_ruler, sync_members
from aerona.engine.polity.governance import collect
from aerona.engine.polity.houses import HouseBook, extinguish, found_house, join
from aerona.engine.polity.justice import offenders
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.oaths import break_oath, lapse, swear
from aerona.engine.polity.standing import legitimacy, secede
from aerona.engine.primitives.queries import connect, has_flag
from aerona.engine.services.war import WarBlock, can_open_war
from tests.engine.society.factories import Realm, context, make, mortal, settlement


async def town_with_purse(realm: Realm, name: str, treasury: int = 200) -> EntityRow:
    town = await settlement(realm, name)
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=treasury, unrest=10, locked=[], foreigners={}))
    await realm.session.flush()
    return town


async def test_the_law_finds_traitors_murderers_and_thieves_in_a_town(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Lawford")
    plotter = await mortal(realm, "Ivo", location_id=town.id)
    killer = await mortal(realm, "Rask", location_id=town.id)
    outcast = await mortal(realm, "Lune", location_id=town.id)
    honest = await mortal(realm, "Mira", location_id=town.id)
    outcast.social_class = SocialClass.OUTCAST
    band = await make(realm.session, "The Unbowed", EntityType.FACTION, FactionStats(), world_id=realm.world.id, location_id=town.id)
    realm.session.add(FactionProfileRow(faction_entity_id=band.id, kind=FactionKind.SECRET_SOCIETY, home_entity_id=town.id, influence_over={}, locked=[]))
    realm.session.add(FactionMembershipRow(faction_entity_id=band.id, mortal_entity_id=plotter.id, locked=[]))
    realm.session.add(MemoryRow(holder_node_id=honest.id, subject_node_id=killer.id, kind=MemoryKind.KILLED_KIN, magnitude=-40, epoch=ctx.epoch, decay_pct=10))
    await realm.session.flush()
    found = await offenders(ctx, town.id, await LawBook.load(realm.session))
    assert [person.id for person in found[CrimeKind.TREASON]] == [plotter.id]
    assert [person.id for person in found[CrimeKind.MURDER]] == [killer.id]
    assert [person.id for person in found[CrimeKind.THEFT]] == [outcast.id]
    assert honest.id not in {person.id for people in found.values() for person in people}


async def test_a_broken_oath_marks_the_swearer_and_its_recipient_remembers(realm: Realm) -> None:
    ctx = context(realm.session)
    lord = await mortal(realm, "Lord Avel")
    vassal = await mortal(realm, "Brann")
    oath = await swear(ctx, vassal, OathKind.FEALTY, recipient_id=lord.id)
    assert await swear(ctx, vassal, OathKind.FEALTY, recipient_id=lord.id) is oath
    await break_oath(ctx, oath, "turned against the hall")
    assert oath.status is OathStatus.BROKEN and oath.ended_epoch == ctx.epoch
    assert await has_flag(realm.session, vassal.id, EntityFlag.OATHBREAKER)
    remembered = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == lord.id, MemoryRow.subject_node_id == vassal.id))
    assert remembered is not None and remembered.kind is MemoryKind.BROKE_OATH


async def test_an_oath_of_the_dead_is_kept_when_oaths_lapse(realm: Realm) -> None:
    ctx = context(realm.session)
    pilgrim = await mortal(realm, "Seren")
    oath = await swear(ctx, pilgrim, OathKind.PILGRIMAGE, recipient_id=None)
    pilgrim.status, pilgrim.end_epoch = EntityStatus.DEAD, ctx.epoch
    await realm.session.flush()
    kept, broken = await lapse(ctx)
    assert (kept, broken) == (1, 0)
    stored = await realm.session.get(OathRow, oath.id)
    assert stored is not None and stored.status is OathStatus.FULFILLED


async def test_a_house_is_founded_takes_in_kin_and_dies_out(realm: Realm) -> None:
    ctx = context(realm.session)
    founder = await mortal(realm, "Edda Vane")
    child = await mortal(realm, "Orrin Vane")
    book = await HouseBook.load(ctx)
    house = await found_house(ctx, book, founder)
    await join(ctx, book, house.id, child, by_marriage=False)
    await realm.session.flush()
    members = set(await realm.session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house.id)))
    assert members == {founder.id, child.id}
    await extinguish(ctx, book, house.id, "the last of the line fell")
    profile = await realm.session.get(HouseProfileRow, house.id)
    assert profile is not None and profile.extinct_epoch == ctx.epoch
    assert house.status is EntityStatus.DESTROYED


async def test_a_realm_gathers_taxes_from_its_towns_and_reads_its_legitimacy(realm: Realm) -> None:
    ctx = context(realm.session)
    capital = await town_with_purse(realm, "Crownhold")
    market = await town_with_purse(realm, "Tollbridge")
    ruler = await mortal(realm, "Queen Ysolde", location_id=capital.id)
    book = await RealmBook.load(realm.session)
    state = await found_polity(ctx, book, capital)
    await sync_members(ctx, book, state, {capital.id, market.id})
    set_ruler(ctx, state, ruler.id, "crowned")
    for town in (capital, market):
        realm.session.add(SettlementTreasuryRow(settlement_entity_id=town.id, epoch=ctx.epoch, entry=TreasuryEntry.TAX, amount=100, balance=200, note="taxes"))
    await realm.session.flush()
    before = state.profile.treasury
    gathered = await collect(ctx, book, state)
    assert gathered > 0 and state.profile.treasury > before
    purse = await realm.session.get(SettlementProfileRow, market.id)
    assert purse is not None and purse.treasury < 200
    assert state.office(OfficeKind.RULER) is not None
    parts = await legitimacy(ctx, book, state, await LawBook.load(realm.session))
    assert parts["base"] == ctx.rules.legitimacy.base and "no ruler" not in parts


async def test_a_town_that_breaks_away_leaves_the_realm_as_its_enemy(realm: Realm) -> None:
    ctx = context(realm.session)
    capital = await town_with_purse(realm, "Highseat")
    rebel = await town_with_purse(realm, "Farwatch")
    book = await RealmBook.load(realm.session)
    state = await found_polity(ctx, book, capital)
    await sync_members(ctx, book, state, {capital.id, rebel.id})
    await realm.session.flush()
    await secede(ctx, book, state, rebel)
    await realm.session.flush()
    assert rebel.id not in state.members
    assert await realm.session.scalar(select(PolityMemberRow).where(PolityMemberRow.member_entity_id == rebel.id)) is None


async def test_a_subject_may_rise_against_its_ruler_but_not_wage_an_ordinary_war_on_it(realm: Realm) -> None:
    ctx = context(realm.session)
    lord = await settlement(realm, "Highcrown")
    subject = await settlement(realm, "Lowmarch")
    await connect(realm.session, lord.id, subject.id, BondKind.RULES, 1)
    assert await can_open_war(realm.session, ctx.rules, subject.id, lord.id, ctx.epoch, world_cap=False) is WarBlock.SUBJECT
    for cause in REVOLT_CAUSES:
        assert await can_open_war(realm.session, ctx.rules, subject.id, lord.id, ctx.epoch, world_cap=False, cause=cause) is None
    assert await incite_uprising(ctx, subject.id)
