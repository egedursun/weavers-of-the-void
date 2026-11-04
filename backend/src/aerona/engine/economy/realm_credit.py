from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityTreasuryRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import DebtRemedy
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.debt_law import bind_debtor, debt_law_of, jail_debtor
from aerona.engine.economy.money import MoneyTally, banks, collapse, gain, owed, riches
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.services.community_relations import change_relation

WAR_PURPOSE = "war"
DEBT_PURPOSE = "debt"


def post(ctx: TickContext, realm: Realm, amount: int, label: str) -> None:
    profile = realm.profile
    profile.treasury += amount
    if profile.treasury < 0:
        profile.debt += -profile.treasury
        profile.treasury = 0
    row = PolityTreasuryRow(polity_entity_id=realm.entity.id, epoch=ctx.epoch, entry=TreasuryEntry.LOAN, amount=amount, balance=profile.treasury)
    row.note = label[:120]
    ctx.session.add(row)


def bank_share(ctx: TickContext, silver: int) -> int:
    return round_half_up(silver * ctx.rules.banking.polity_bank_wealth_per_silver / PERCENT)


async def realm_at_war(ctx: TickContext, realm: Realm) -> bool:
    bonds = BondRepository(ctx.session)
    for node in (realm.entity.id, *realm.members):
        if await bonds.outgoing(node, BondKind.ENEMY):
            return True
    return False


async def shy_of(ctx: TickContext, borrower_id: int, lender: EntityRow) -> bool:
    since = ctx.epoch - ctx.rules.banking.credit_shy_epochs
    found = await ctx.session.scalar(
        select(LoanRow.id).where(LoanRow.borrower_entity_id == borrower_id, LoanRow.status == LoanStatus.DEFAULTED, LoanRow.due_epoch >= since).limit(1)
    )
    return found is not None and lender.affiliated_entity_id != borrower_id


async def risky(ctx: TickContext, borrower_id: int) -> bool:
    found = await ctx.session.scalar(select(LoanRow.id).where(LoanRow.borrower_entity_id == borrower_id, LoanRow.status == LoanStatus.DEFAULTED).limit(1))
    return found is not None


async def realm_currency(ctx: TickContext, realm: Realm) -> int | None:
    for node in (realm.profile.capital_entity_id, *realm.members):
        society = await ctx.session.get(CommunitySocietyRow, node) if node is not None else None
        if society is not None and society.currency_id is not None:
            return society.currency_id
    return None


async def lend_to_realms(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.banking
    lenders = await banks(ctx, book)
    if not lenders:
        return
    realms = await RealmBook.load(ctx.session)
    for realm in sorted(realms.realms.values(), key=lambda item: item.entity.id):
        profile = realm.profile
        at_war = await realm_at_war(ctx, realm)
        if profile.treasury >= table.polity_treasury_below or not (at_war or profile.debt > 0):
            continue
        statement = select(LoanRow.id).where(LoanRow.borrower_entity_id == realm.entity.id, LoanRow.status == LoanStatus.OPEN)
        open_loan = await ctx.session.scalar(statement.limit(1))
        if open_loan is not None or not ctx.rng(f"realm_loan.{realm.entity.id}.{ctx.epoch}").chance(table.polity_lend_chance):
            continue
        lender = min(lenders, key=lambda bank: (bank.world_id != realm.entity.world_id, -riches(bank), bank.id))
        if await shy_of(ctx, realm.entity.id, lender):
            continue
        loan = LoanRow(
            lender_entity_id=lender.id,
            borrower_entity_id=realm.entity.id,
            currency_id=await realm_currency(ctx, realm),
            principal=table.polity_principal,
            interest_pct=table.interest_pct + (table.risk_interest_pct if await risky(ctx, realm.entity.id) else 0),
            issued_epoch=ctx.epoch,
            due_epoch=ctx.epoch + table.term_epochs,
            status=LoanStatus.OPEN,
            purpose=WAR_PURPOSE if at_war else DEBT_PURPOSE,
        )
        ctx.session.add(loan)
        post(ctx, realm, table.polity_principal, f"loan from {lender.name}")
        gain(lender, -bank_share(ctx, table.polity_principal))
        tally.lent += 1
        reason = "to keep its armies in the field" if at_war else "to carry its debts"
        await ctx.chronicle(
            ChronicleKind.DEBT,
            f"{lender.name} lent the realm of {realm.entity.name} {loan.principal} silver {reason}, "
            f"at {loan.interest_pct}% interest, due Epoch {loan.due_epoch}.",
            template_key="banking.realm_loan",
            entity_ids=[lender.id, realm.entity.id],
        )


async def realm_default(ctx: TickContext, book: EconomyBook, loan: LoanRow, realm: Realm, lender: EntityRow) -> str:
    table = ctx.rules.banking
    law = await debt_law_of(ctx, realm.entity, lender)
    left = max(0, owed(loan))
    if law is not None and law.remedy is DebtRemedy.JUBILEE:
        loan.status = LoanStatus.FORGIVEN
        gain(lender, -bank_share(ctx, left))
        await ctx.chronicle(
            ChronicleKind.DEBT,
            f"The jubilee of {realm.entity.name} wiped its loan from {lender.name}; the bank lost {left} silver.",
            template_key="banking.realm_jubilee",
            entity_ids=[realm.entity.id, lender.id],
        )
        return "jubilee"
    loan.status = LoanStatus.DEFAULTED
    realm.profile.debt += round_half_up(left * table.polity_default_debt_pct / PERCENT)
    gain(lender, -table.default_bank_loss)
    await change_relation(ctx, lender.id, realm.entity.id, -table.default_relation_loss, MemoryKind.BETRAYED_ME, note="a realm defaulted on a loan")
    outcome = "default"
    if law is not None and law.remedy is DebtRemedy.BONDAGE and realm.profile.capital_entity_id is not None:
        capital = await ctx.session.get(EntityRow, realm.profile.capital_entity_id)
        if capital is not None:
            await bind_debtor(ctx, capital, lender)
            outcome = "bondage"
    elif law is not None and law.remedy is DebtRemedy.PRISON:
        jailed = await jail_debtor(ctx, realm.entity, lender, f"{left} silver")
        if jailed is not None:
            outcome = "prison"
    await ctx.chronicle(
        ChronicleKind.DEBT,
        f"The realm of {realm.entity.name} could not repay {lender.name}; {left} silver became the realm's standing debt and the bank will remember.",
        template_key=f"banking.realm_{outcome}",
        entity_ids=[realm.entity.id, lender.id],
    )
    if riches(lender) < table.collapse_wealth:
        await collapse(ctx, book, lender)
    return outcome


async def collect_from_realms(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.banking
    realms = await RealmBook.load(ctx.session)
    statement = select(LoanRow).where(LoanRow.status == LoanStatus.OPEN, LoanRow.held.is_(False)).order_by(LoanRow.id)
    for loan in await ctx.session.scalars(statement):
        realm = realms.realms.get(loan.borrower_entity_id)
        lender = book.entities.get(loan.lender_entity_id)
        if realm is None:
            continue
        if lender is None or lender.entity_type is not EntityType.FACTION:
            loan.status = LoanStatus.FORGIVEN
            continue
        payment = min(max(0, owed(loan)), round_half_up(max(0, owed(loan)) * table.polity_repay_pct / PERCENT), max(0, realm.profile.treasury))
        if payment > 0:
            post(ctx, realm, -payment, f"repaid to {lender.name}")
            gain(lender, bank_share(ctx, payment))
            loan.repaid += payment
        if owed(loan) <= 0:
            loan.status = LoanStatus.REPAID
            tally.repaid += 1
        elif ctx.epoch >= loan.due_epoch:
            outcome = await realm_default(ctx, book, loan, realm, lender)
            if outcome != "jubilee":
                tally.defaulted += 1
