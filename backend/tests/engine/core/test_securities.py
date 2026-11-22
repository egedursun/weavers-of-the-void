from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.faction_kinds import kind_of
from aerona.db.tables.concealment import HiddenTruthRow, TruthKeeperRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.governance import OrgMergerRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, SecurityPriceRow, StockExchangeRow
from aerona.domain.enums.concealment import HiddenTruthKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.cycles import LongPlanKind, LongPlanStatus
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import CreditState
from aerona.domain.enums.governance import MergerKind, MergerStage
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind
from aerona.domain.enums.securities import SecurityKind
from aerona.domain.models.entity_stats import FactionStats, MortalStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.governance.mergers import answer_bid
from aerona.engine.lore.control import set_technique
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.securities.bonds import issue_bonds
from aerona.engine.securities.debts import mirror_loans, owed_now, tend_debts
from aerona.engine.securities.exchanges import list_unlisted, open_exchanges
from aerona.engine.securities.holdings import SecuritiesTally, default_premium
from aerona.engine.securities.pricing import SHOCKS, crash, move_price
from aerona.engine.securities.shares import float_shares, sync_shares
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def company(session: AsyncSession, world: CoreWorld, name: str, *, wealth: int = 50) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, f"{name} Town", world, world.regions[0], population=5000)
    firm = await entity(session, name, EntityType.FACTION, FactionStats(strength=20, wealth=wealth, sway=10), world_id=world.world.id, location_id=town.id)
    return town, firm


async def listed(session: AsyncSession, firm: EntityRow, town: EntityRow, *, price: int = 10, kind: SecurityKind = SecurityKind.SHARE) -> IssuedSecurityRow:
    exchange = StockExchangeRow(name=f"the exchange of {town.name}", settlement_entity_id=town.id, locked=[])
    session.add(exchange)
    await session.flush()
    security = IssuedSecurityRow(
        name=f"the shares of {firm.name}", issuer_node_id=firm.id, kind=kind, amount=100, face_value=10, price=price, exchange_id=exchange.id, locked=[]
    )
    session.add(security)
    await session.flush()
    return security


def test_every_shock_the_prices_feel_is_a_kind_the_record_knows_with_that_role() -> None:
    known = dict(INCIDENT_KINDS)
    for kind, role in SHOCKS:
        assert kind in known and role in {spec.role for spec in known[kind].roles}


async def test_company_shares_become_a_share_security_held_in_proportion(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _town, firm = await company(session, world, "Brightway")
    owner = await entity(session, "Owner One", EntityType.MORTAL, MortalStats(), world_id=world.world.id)
    other = await entity(session, "Owner Two", EntityType.MORTAL, MortalStats(), world_id=world.world.id)
    session.add_all(
        [
            CompanyShareRow(company_entity_id=firm.id, holder_node_id=owner.id, share=75),
            CompanyShareRow(company_entity_id=firm.id, holder_node_id=other.id, share=25),
        ]
    )
    await session.flush()
    await float_shares(ctx, SecuritiesTally())
    security = await session.scalar(select(IssuedSecurityRow).where(IssuedSecurityRow.issuer_node_id == firm.id))
    assert security is not None and security.kind is SecurityKind.SHARE and security.amount == 100
    held = {row.holder_node_id: row.amount for row in await session.scalars(select(SecurityHoldingRow).where(SecurityHoldingRow.security_id == security.id))}
    assert held == {owner.id: 75, other.id: 25}


async def test_a_claim_is_listed_on_the_exchange_of_its_issuers_town(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, firm = await company(session, world, "Listway")
    exchange = StockExchangeRow(name="the exchange of Listway", settlement_entity_id=town.id, locked=[])
    security = IssuedSecurityRow(name="the shares of Listway", issuer_node_id=firm.id, amount=100, locked=[])
    session.add_all([exchange, security])
    await session.flush()
    tally = SecuritiesTally()
    await list_unlisted(ctx, tally)
    assert security.exchange_id == exchange.id and tally.listed == 1


async def test_prices_run_ahead_into_a_bubble_and_burst(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "bubble", tuned_rules(securities={"burst_chance_pct": 100}))
    town, firm = await company(session, world, "Bubbleway", wealth=50)
    security = await listed(session, firm, town, price=40)
    tally = SecuritiesTally()
    await move_price(ctx, security, None, tally)
    assert security.bubble and tally.bubbles == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "securities.bubble_formed")) is not None
    await move_price(ctx, security, None, tally)
    assert tally.crashes == 1 and not security.bubble


async def test_a_default_crashes_the_issuers_claims_and_forces_sales_bought_on_credit(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, firm = await company(session, world, "Debtway")
    security = await listed(session, firm, town, price=20)
    buyer = await entity(session, "Margin Buyer", EntityType.MORTAL, MortalStats(), world_id=world.world.id)
    session.add(SecurityHoldingRow(holder_node_id=buyer.id, security_id=security.id, amount=10, bought_price=20, on_margin=150, locked=[]))
    session.add(CreditProfileRow(subject_node_id=firm.id, state=CreditState.DEFAULT, epoch=ctx.epoch))
    await session.flush()
    tally = SecuritiesTally()
    await move_price(ctx, security, None, tally)
    assert tally.crashes == 1 and tally.margin_calls == 1
    row = await session.scalar(select(SecurityHoldingRow).where(SecurityHoldingRow.holder_node_id == buyer.id))
    assert row is not None and row.amount == 0 and row.on_margin == 0


async def test_a_keeper_of_a_secret_sells_before_the_crash_and_is_fined_where_the_law_bans_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "insider", tuned_rules(securities={"insider_exposure_pct": 100}))
    town, firm = await company(session, world, "Secretway")
    security = await listed(session, firm, town, price=20)
    exchange = await session.get(StockExchangeRow, security.exchange_id)
    keeper = await entity(session, "The Knower", EntityType.MORTAL, MortalStats(), world_id=world.world.id)
    truth = HiddenTruthRow(title="the ledgers lie", subject_node_id=firm.id, kind=next(iter(HiddenTruthKind)), locked=[])
    session.add(truth)
    await session.flush()
    session.add_all(
        [
            TruthKeeperRow(truth_id=truth.id, keeper_node_id=keeper.id, locked=[]),
            SecurityHoldingRow(holder_node_id=keeper.id, security_id=security.id, amount=10, bought_price=20, locked=[]),
        ]
    )
    await session.flush()
    await enact(ctx, town, LawKind.COMPETITION_LAW, {"insider_ban": 100})
    tally = SecuritiesTally()
    await crash(ctx, security, exchange, "the ledgers came out", tally)
    row = await session.scalar(select(SecurityHoldingRow).where(SecurityHoldingRow.holder_node_id == keeper.id))
    assert row is not None and row.amount == 0 and tally.insiders == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "securities.insider_exposed")) is not None


async def test_a_crown_loan_trades_as_a_bond_whose_largest_holder_lends_and_whose_default_costs_rates(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    realm = await entity(session, "The Bond Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule))))
    _town, lender = await company(session, world, "Lendway")
    _other, buyer = await company(session, world, "Buyway")
    loan = LoanRow(
        lender_entity_id=lender.id,
        borrower_entity_id=realm.id,
        principal=200,
        interest_pct=8,
        issued_epoch=0,
        due_epoch=5,
        status=LoanStatus.OPEN,
        purpose="crown debt",
    )
    session.add(loan)
    await session.flush()
    tally = SecuritiesTally()
    await mirror_loans(ctx, tally)
    bond = await session.scalar(select(IssuedSecurityRow).where(IssuedSecurityRow.loan_id == loan.id))
    assert bond is not None and bond.kind is SecurityKind.BOND and bond.amount == 200 // ctx.rules.securities.bond_face and tally.bonds == 1
    holding = await session.scalar(select(SecurityHoldingRow).where(SecurityHoldingRow.security_id == bond.id))
    assert holding is not None and holding.holder_node_id == lender.id
    holding.amount -= 15
    session.add(SecurityHoldingRow(holder_node_id=buyer.id, security_id=bond.id, amount=15, bought_price=10, locked=[]))
    await session.flush()
    await tend_debts(ctx, tally)
    assert loan.lender_entity_id == buyer.id
    loan.status = LoanStatus.DEFAULTED
    await tend_debts(ctx, tally)
    assert bond.defaulted_epoch == ctx.epoch and tally.defaults == 1
    assert await default_premium(session, realm.id, ctx.rules.securities.default_rate_rise) == ctx.rules.securities.default_rate_rise


async def test_a_listed_bond_pays_its_coupons_or_defaults_when_its_issuer_cannot(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, firm = await company(session, world, "Couponway", wealth=0)
    bond = await listed(session, firm, town, kind=SecurityKind.BOND)
    bond.coupon_pct = 50
    holder = await entity(session, "Coupon Holder", EntityType.MORTAL, MortalStats(), world_id=world.world.id)
    session.add(SecurityHoldingRow(holder_node_id=holder.id, security_id=bond.id, amount=100, bought_price=10, locked=[]))
    await session.flush()
    tally = SecuritiesTally()
    await tend_debts(ctx, tally)
    assert bond.defaulted_epoch == ctx.epoch and tally.defaults == 1


async def test_listed_shares_set_the_owners_and_a_majority_carries_a_takeover(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, firm = await company(session, world, "Ownway")
    security = await listed(session, firm, town)
    _home, raider = await company(session, world, "Raidway")
    session.add(SecurityHoldingRow(holder_node_id=raider.id, security_id=security.id, amount=60, bought_price=10, locked=[]))
    session.add(SecurityHoldingRow(holder_node_id=firm.id, security_id=security.id, amount=40, bought_price=10, locked=[]))
    await session.flush()
    await sync_shares(ctx, SecuritiesTally())
    shares = {row.holder_node_id: row.share for row in await session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == firm.id))}
    assert shares == {raider.id: 60, firm.id: 40}
    merger = OrgMergerRow(acquirer_node_id=raider.id, target_node_id=firm.id, kind=MergerKind.HOSTILE_TAKEOVER, price=1, locked=[])
    session.add(merger)
    await session.flush()
    assert await answer_bid(ctx, merger, firm) == "agreed" and merger.stage is MergerStage.AGREED


async def test_an_annuity_never_repays_its_face_and_a_note_pays_its_coupons_only_when_it_falls_due(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    annuity = IssuedSecurityRow(name="an annuity", issuer_node_id=1, kind=SecurityKind.ANNUITY, amount=10, face_value=10, coupon_pct=10, listed_epoch=0)
    note = IssuedSecurityRow(name="a note", issuer_node_id=1, kind=SecurityKind.NOTE, amount=10, face_value=10, coupon_pct=10, listed_epoch=0)
    bond = IssuedSecurityRow(name="a bond", issuer_node_id=1, kind=SecurityKind.BOND, amount=10, face_value=10, coupon_pct=10, listed_epoch=0)
    assert owed_now(ctx, annuity, 10, maturing=True) == 10
    assert owed_now(ctx, note, 10, maturing=False) == 0
    assert owed_now(ctx, note, 10, maturing=True) == 10 * max(1, ctx.epoch) + 100
    assert owed_now(ctx, bond, 10, maturing=True) == 110


async def test_a_realm_raising_a_wonder_on_an_empty_treasury_sells_bonds_to_the_bank_of_its_seat(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    seat, bank = await company(session, world, "Seatbank", wealth=90)
    bank.engine_kind = EngineKind.MERCHANT_GUILD
    realm = await entity(session, "The Building Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    profile = PolityProfileRow(
        polity_entity_id=realm.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), treasury=0, capital_entity_id=seat.id
    )
    session.add(profile)
    session.add(StockExchangeRow(name=f"the exchange of {seat.name}", settlement_entity_id=seat.id, locked=[]))
    session.add(LongPlanRow(holder_node_id=realm.id, kind=LongPlanKind.WONDER, name="the great work", status=LongPlanStatus.ACTIVE, locked=[]))
    await session.flush()
    tally = SecuritiesTally()
    await issue_bonds(ctx, tally)
    bond = await session.scalar(select(IssuedSecurityRow).where(IssuedSecurityRow.issuer_node_id == realm.id))
    table = ctx.rules.securities
    assert bond is not None and bond.kind is SecurityKind.BOND and bond.amount == table.bond_amount and tally.bonds == 1
    assert bond.maturity_epoch == ctx.epoch + table.bond_term_epochs and bond.exchange_id is not None
    holding = await session.scalar(select(SecurityHoldingRow).where(SecurityHoldingRow.security_id == bond.id))
    assert holding is not None and holding.holder_node_id == bank.id
    assert profile.treasury == table.bond_amount * table.bond_face
    priced = await session.scalar(select(SecurityPriceRow).where(SecurityPriceRow.security_id == bond.id))
    assert priced is not None and priced.volume == bond.amount
    await issue_bonds(ctx, tally)
    assert tally.bonds == 1


async def test_the_bank_of_a_town_is_known_by_the_kind_its_profile_holds(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "exchange", tuned_rules(securities={"exchange_chance_pct": 100, "exchange_min_population": 1000}))
    town, founded = await company(session, world, "Profiled", wealth=90)
    _, retyped = await company(session, world, "Retyped", wealth=95)
    retyped.location_id, retyped.engine_kind = town.id, EngineKind.MERCHANT_GUILD
    session.add(FactionProfileRow(faction_entity_id=founded.id, kind=FactionKind.FINANCIERS, influence_over={}, locked=[]))
    session.add(FactionProfileRow(faction_entity_id=retyped.id, kind=FactionKind.CRAFT_GUILD, influence_over={}, locked=[]))
    await set_technique(ctx, town.id, Technique.BANKING, held=True, secret=False)
    await session.flush()
    assert await kind_of(session, retyped.id) is FactionKind.CRAFT_GUILD
    tally = SecuritiesTally()
    await open_exchanges(ctx, tally)
    exchange = await session.scalar(select(StockExchangeRow).where(StockExchangeRow.settlement_entity_id == town.id))
    assert tally.opened == 1 and exchange is not None and exchange.owner_node_id == founded.id
    _, unprofiled = await company(session, world, "Unprofiled", wealth=80)
    unprofiled.engine_kind = EngineKind.MERCHANT_GUILD
    await session.flush()
    assert await kind_of(session, unprofiled.id) is FactionKind.MERCHANT_GUILD
