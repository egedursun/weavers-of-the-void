from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import PolityProfileRow, TreatyProfileRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import TreatyStatus
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.factions.book import FactionBook
from aerona.engine.factions.outlaws import contract, end_contract, pay_companies
from aerona.engine.polity.book import RealmBook
from tests.engine.society.factories import Realm, context, make
from tests.engine.statecraft.crowns import crown


async def hired(realm: Realm, treasury: int, loyalty: int) -> tuple[FactionProfileRow, PolityProfileRow]:
    ctx = context(realm.session)
    polity, _ = await crown(realm, "Velmar", treasury=treasury)
    band = await make(realm.session, "Iron Lances", EntityType.FACTION, FactionStats(strength=60), world_id=realm.world.id)
    profile = FactionProfileRow(faction_entity_id=band.id, kind=FactionKind.MERCENARY_COMPANY, influence_over={}, loyalty=loyalty, locked=[])
    realm.session.add(profile)
    await realm.session.flush()
    books = await FactionBook.load(realm.session), await RealmBook.load(realm.session)
    await contract(ctx, books[0], profile, books[1].realms[polity.id], pay=40, epochs=5)
    purse = await realm.session.get(PolityProfileRow, polity.id)
    assert purse is not None
    return profile, purse


async def pay(realm: Realm) -> dict[str, int]:
    return await pay_companies(context(realm.session), await FactionBook.load(realm.session), await RealmBook.load(realm.session))


async def test_a_paid_company_takes_its_wage_and_grows_loyal(realm: Realm) -> None:
    profile, purse = await hired(realm, treasury=100, loyalty=50)
    counts = await pay(realm)
    assert counts["paid"] == 1 and purse.treasury == 60 and profile.treasury == 40 and profile.loyalty > 50


async def test_an_unpaid_disloyal_company_turns_bandit_and_breaks_its_condotta(realm: Realm) -> None:
    profile, purse = await hired(realm, treasury=0, loyalty=20)
    treaty = await realm.session.get(TreatyProfileRow, profile.contract_entity_id)
    counts = await pay(realm)
    assert counts["unpaid"] == 1 and counts["bandits"] == 1
    assert profile.kind is FactionKind.BANDITS and profile.outlawed and profile.employer_entity_id is None
    assert treaty is not None and treaty.status is TreatyStatus.BROKEN
    assert purse.treasury == 0


async def test_a_held_company_is_neither_paid_nor_turned(realm: Realm) -> None:
    profile, _ = await hired(realm, treasury=0, loyalty=20)
    token = HELD_SCOPE.set(HeldScope(None, frozenset({profile.faction_entity_id})))
    try:
        counts = await pay(realm)
    finally:
        HELD_SCOPE.reset(token)
    assert counts["unpaid"] == 0 and profile.kind is FactionKind.MERCENARY_COMPANY


async def test_ending_a_contract_fulfils_the_condotta_and_frees_the_company(realm: Realm) -> None:
    profile, _ = await hired(realm, treasury=100, loyalty=50)
    treaty = await realm.session.get(TreatyProfileRow, profile.contract_entity_id)
    await end_contract(context(realm.session), profile)
    assert treaty is not None and treaty.status is TreatyStatus.FULFILLED
    assert profile.employer_entity_id is None and profile.contract_entity_id is None
