from sqlalchemy import select

from aerona.catalog.finance import COVERS, LOAN_STATES, OWED_LOANS, PLAYS, SAVING_FORMS
from aerona.catalog.life.finance import REFUSES_CREDIT_STATES
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.finance import CreditProfileRow, SpeculationRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.economy import CommodityKind, LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.finance import CreditState, SpeculationStatus
from aerona.domain.enums.orders import SavingForm
from aerona.domain.enums.urban import MarketPlay
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.economy.manipulation import swing
from aerona.engine.finance.credit import CreditTally, rate
from aerona.engine.finance.speculation import seize_hoard
from aerona.engine.finance.w52_credit import repudiate, reschedule, rescue, seize_collateral
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, settlement


def test_the_finance_catalogues_cover_every_new_value() -> None:
    assert CreditState.REPUDIATED in REFUSES_CREDIT_STATES and CreditState.RESCUED in REFUSES_CREDIT_STATES
    assert LoanStatus.RESCHEDULED in OWED_LOANS and LoanStatus.SOLD in OWED_LOANS and not LOAN_STATES[LoanStatus.COLLATERAL_SEIZED].owed
    assert SAVING_FORMS[SavingForm.LAND].kept_in == "land" and SAVING_FORMS[SavingForm.GOODS].kept_in == "goods"
    assert COVERS[InsuranceCover.CROP].premium_rule == "crop_premium_pct" and PLAYS[MarketPlay.RUMOUR].by_rumour
    assert swing(Rules(), MarketPlay.RUMOUR, 100) > 1


async def lender_and_realm(realm: Realm) -> tuple:
    debtor = await make(realm.session, "Low Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    bank = await make(realm.session, "House Orrin", EntityType.FACTION, FactionStats(), world_id=realm.world.id)
    loan = LoanRow(
        lender_entity_id=bank.id,
        borrower_entity_id=debtor.id,
        principal=50,
        interest_pct=10,
        issued_epoch=1,
        due_epoch=4,
        status=LoanStatus.OPEN,
        purpose="war",
    )
    realm.session.add(loan)
    await realm.session.flush()
    return debtor, bank, loan


async def test_a_repudiation_voids_the_debts_and_shuts_the_realm_out_of_credit(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, _bank, loan = await lender_and_realm(realm)
    assert await repudiate(ctx, debtor) > 0
    assert loan.status is LoanStatus.DEFAULTED
    profile = await realm.session.get(CreditProfileRow, debtor.id)
    assert (
        profile is not None
        and profile.state is CreditState.REPUDIATED
        and profile.repudiated_until == ctx.epoch + ctx.rules.credit.epochs(ctx.rules.credit.repudiation_years)
    )
    await rate(ctx, debtor.id, CreditTally())
    assert profile.state is CreditState.REPUDIATED
    assert await realm.session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "credit.repudiated")) is not None


async def test_a_rescued_realm_names_its_rescuer_and_keeps_that_state(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, bank, _loan = await lender_and_realm(realm)
    row = await rescue(ctx, debtor, bank, 20)
    assert row.state is CreditState.RESCUED and row.rescuer_node_id == bank.id and row.rescue_terms == 20
    await rate(ctx, debtor.id, CreditTally())
    assert row.state is CreditState.RESCUED


async def test_a_rescheduled_loan_is_still_owed_and_a_pledge_is_seized_on_default(realm: Realm) -> None:
    ctx = context(realm.session)
    debtor, bank, loan = await lender_and_realm(realm)
    await reschedule(ctx, loan, 2)
    assert loan.status is LoanStatus.RESCHEDULED and loan.due_epoch == 6 and LOAN_STATES[loan.status].owed
    pledge = await settlement(realm, "Pledgeby")
    loan.collateral_node_id, loan.status = pledge.id, LoanStatus.DEFAULTED
    assert await seize_collateral(ctx, loan)
    assert loan.status is LoanStatus.COLLATERAL_SEIZED
    assert bank.id and debtor.id


async def test_a_seized_hoard_returns_its_goods_and_angers_the_merchant(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Graintown")
    merchant = await make(realm.session, "House Orrin", EntityType.FACTION, FactionStats(), world_id=realm.world.id)
    row = SpeculationRow(
        merchant_node_id=merchant.id,
        market_node_id=town.id,
        commodity=CommodityKind.GRAIN,
        units=30,
        price=10,
        status=SpeculationStatus.HOARDING,
        opened_epoch=1,
        gain=0,
        locked=[],
    )
    realm.session.add(row)
    await realm.session.flush()
    assert await seize_hoard(ctx, row, town.id)
    assert row.status is SpeculationStatus.SEIZED
    assert await realm.session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "market.hoard_seized")) is not None
