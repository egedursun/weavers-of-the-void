from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.polity import LawKind
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.money import MoneyTally, collect, defaulted_before
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, context, make, people, tuned


async def overdue(realm: Realm, *, bank_wealth: int) -> tuple[LoanRow, EntityRow, EntityRow]:
    borrower = await people(realm, "Reed Folk", wealth=0, prosperity=0)
    bank = await make(realm.session, "Salt Bank", EntityType.FACTION, FactionStats(wealth=bank_wealth), world_id=realm.world.id)
    bank.engine_kind = EngineKind.MERCHANT_GUILD
    loan = LoanRow(
        lender_entity_id=bank.id,
        borrower_entity_id=borrower.id,
        principal=40,
        interest_pct=10,
        repaid=0,
        issued_epoch=1,
        due_epoch=1,
        status=LoanStatus.OPEN,
        purpose="trade",
    )
    realm.session.add(loan)
    await realm.session.flush()
    return loan, borrower, bank


async def test_an_unpaid_loan_defaults_and_a_poor_bank_collapses(realm: Realm) -> None:
    ctx = context(realm.session, tuned(banking={"collapse_wealth": 100, "repay_wealth_floor": 0}))
    loan, borrower, bank = await overdue(realm, bank_wealth=10)
    assert not await defaulted_before(ctx, borrower.id)
    tally = MoneyTally()
    await collect(ctx, await EconomyBook.load(ctx), tally)
    assert loan.status is LoanStatus.DEFAULTED and tally.defaulted == 1 and tally.collapsed == 1
    assert stat(bank, "wealth") == 0 and await defaulted_before(ctx, borrower.id)


async def test_a_jubilee_forgives_the_debt_at_the_banks_cost(realm: Realm) -> None:
    ctx = context(realm.session, tuned(banking={"collapse_wealth": 0, "repay_wealth_floor": 0}))
    loan, borrower, bank = await overdue(realm, bank_wealth=80)
    await enact(ctx, borrower, LawKind.DEBT_LAW, {"remedy": "jubilee"})
    await collect(ctx, await EconomyBook.load(ctx), MoneyTally())
    assert loan.status is LoanStatus.FORGIVEN and (stat(bank, "wealth") or 0) < 80
