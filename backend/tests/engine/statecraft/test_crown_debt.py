from sqlalchemy import select

from aerona.db.tables.economy import LoanRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.governance import owed, service_debt
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import relation
from tests.engine.society.factories import Realm, bonded, context, make, tuned
from tests.engine.statecraft.crowns import crown


def loan(lender: int, borrower: int, *, principal: int = 100, repaid: int = 0, due: int = 10) -> LoanRow:
    return LoanRow(
        lender_entity_id=lender,
        borrower_entity_id=borrower,
        principal=principal,
        interest_pct=10,
        repaid=repaid,
        issued_epoch=1,
        due_epoch=due,
        status=LoanStatus.OPEN,
        purpose="crown debt",
    )


async def loans_of(realm: Realm, borrower: int) -> list[LoanRow]:
    return list(await realm.session.scalars(select(LoanRow).where(LoanRow.borrower_entity_id == borrower).order_by(LoanRow.id)))


async def test_a_crown_in_debt_borrows_from_its_richest_neighbour(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, _ = await crown(realm, "Hollow Crown", debt=100)
    await crown(realm, "Lesser Crown", treasury=300)
    lender, _ = await crown(realm, "Golden Crown", treasury=1000)
    book = await RealmBook.load(realm.session)
    await service_debt(ctx, book, book.realms[debtor.id])
    [opened] = await loans_of(realm, debtor.id)
    assert opened.lender_entity_id == lender.id and opened.principal == 100 and opened.status is LoanStatus.OPEN
    assert opened.due_epoch == ctx.epoch + ctx.rules.government.loan_epochs
    assert book.realms[lender.id].profile.treasury == 900
    assert book.realms[debtor.id].profile.debt == 100 + 100 * ctx.rules.government.loan_interest_pct // 100


async def test_a_merchant_guild_of_the_realm_lends_before_any_neighbour(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, core = await crown(realm, "Hollow Crown", debt=100)
    await crown(realm, "Golden Crown", treasury=1000)
    guild = await make(realm.session, "Counting House", EntityType.FACTION, FactionStats(wealth=80), world_id=realm.world.id)
    guild.engine_kind = EngineKind.MERCHANT_GUILD
    guild.affiliated_entity_id = core.id
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    await service_debt(ctx, book, book.realms[debtor.id])
    [opened] = await loans_of(realm, debtor.id)
    assert opened.lender_entity_id == guild.id


async def test_a_crown_with_its_debt_held_takes_no_loan(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, _ = await crown(realm, "Hollow Crown", debt=100)
    await crown(realm, "Golden Crown", treasury=1000)
    book = await RealmBook.load(realm.session)
    book.realms[debtor.id].profile.locked = ["debt"]
    await service_debt(ctx, book, book.realms[debtor.id])
    assert await loans_of(realm, debtor.id) == []


async def test_paying_down_the_debt_repays_the_oldest_loans_first(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, _ = await crown(realm, "Hollow Crown")
    lender, _ = await crown(realm, "Golden Crown", treasury=1000)
    first, second = loan(lender.id, debtor.id), loan(lender.id, debtor.id)
    realm.session.add_all([first, second])
    await realm.session.flush()
    assert owed(first) == 110
    book = await RealmBook.load(realm.session)
    book.realms[debtor.id].profile.debt = 50
    await service_debt(ctx, book, book.realms[debtor.id])
    assert first.status is LoanStatus.REPAID and first.repaid == 110
    assert second.status is LoanStatus.OPEN and second.repaid == 60 and owed(second) == 50


async def test_an_overdue_loan_defaults_writes_off_the_debt_and_angers_the_lender(realm: Realm) -> None:
    ctx = context(realm.session, tuned(government={"default_war_chance": 100}))
    debtor, debtor_core = await crown(realm, "Hollow Crown")
    lender, lender_core = await crown(realm, "Golden Crown", treasury=1000)
    overdue = loan(lender.id, debtor.id, due=1)
    realm.session.add(overdue)
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    book.realms[debtor.id].profile.debt = owed(overdue)
    before = await relation(realm.session, ctx.rules, lender_core.id, debtor_core.id)
    await service_debt(ctx, book, book.realms[debtor.id])
    assert overdue.status is LoanStatus.DEFAULTED and book.realms[debtor.id].profile.debt == 0
    assert await relation(realm.session, ctx.rules, lender_core.id, debtor_core.id) < before
    assert await bonded(realm.session, lender_core.id, debtor_core.id, BondKind.ENEMY)
    assert await realm.session.scalar(select(ChronicleRow).where(ChronicleRow.template_key == "polity.debt_default")) is not None


async def test_a_guild_that_is_cheated_gains_sway(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, _ = await crown(realm, "Hollow Crown")
    guild = await make(realm.session, "Counting House", EntityType.FACTION, FactionStats(sway=10), world_id=realm.world.id)
    overdue = loan(guild.id, debtor.id, due=1)
    realm.session.add(overdue)
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    book.realms[debtor.id].profile.debt = owed(overdue)
    await service_debt(ctx, book, book.realms[debtor.id])
    assert overdue.status is LoanStatus.DEFAULTED
    assert (stat(guild, "sway") or 0) > 10
