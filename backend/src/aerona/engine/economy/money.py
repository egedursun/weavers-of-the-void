from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.materials import COIN_MATERIALS
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.economy import CommunityStockRow, CurrencyRow, LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, LoanStatus
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import DebtRemedy
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.debt_law import bind_debtor, debt_law_of, jail_debtor
from aerona.engine.economy.stocks import goods_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.community_relations import change_relation

MINTERS = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION})


@dataclass
class MoneyTally:
    minted: int = 0
    adopted: int = 0
    debased: int = 0
    lent: int = 0
    repaid: int = 0
    defaulted: int = 0
    collapsed: int = 0


def riches(entity: EntityRow) -> int:
    for key in ("wealth", "prosperity"):
        value = stat(entity, key)
        if value is not None:
            return value
    return 0


def gain(entity: EntityRow, amount: int) -> None:
    for key in ("wealth", "prosperity"):
        value = stat(entity, key)
        if value is not None:
            set_stats(entity, **{key: clamp_int(value + amount, 0, PERCENT)})
            return


async def currencies(ctx: TickContext) -> dict[int, CurrencyRow]:
    return {row.id: row for row in await ctx.session.scalars(select(CurrencyRow).order_by(CurrencyRow.id))}


async def issued_by(ctx: TickContext, issuer_id: int) -> CurrencyRow | None:
    return await ctx.session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == issuer_id).order_by(CurrencyRow.id).limit(1))


async def coin_metal(ctx: TickContext, community_id: int) -> CommunityStockRow | None:
    statement = select(CommunityStockRow).where(
        CommunityStockRow.community_entity_id == community_id,
        CommunityStockRow.commodity == CommodityKind.ORE,
        CommunityStockRow.material.in_(list(COIN_MATERIALS)),
        CommunityStockRow.quantity > 0,
    )
    lots = list(await ctx.session.scalars(statement))
    return min(lots, key=lambda lot: (COIN_MATERIALS.index(lot.material) if lot.material is not None else len(COIN_MATERIALS), lot.id), default=None)


async def found_currency(ctx: TickContext, issuer: EntityRow, metal: MaterialKind) -> CurrencyRow:
    table = ctx.rules.money
    coin = await create_record(
        ctx,
        RecordSpec(
            name=f"{issuer.name} Coin",
            entity_type=EntityType.ITEM,
            stats=ItemStats(
                damage=0,
                protection=0,
                might=clamp_int(ctx.rules.trade.currency_might_base + ctx.rng(f"coin.{issuer.id}").die(ctx.rules.trade.currency_might_die), 0, PERCENT),
                curse=0,
            ),
            body=f"{issuer.name} began to strike coins of {metal.value.replace('_', ' ')}.",
            power=ctx.rules.trade.currency_power,
            world_id=issuer.world_id,
            location_id=issuer.id if issuer.entity_type is EntityType.SETTLEMENT else issuer.location_id,
            subtype="currency",
            engine_kind=EngineKind.CURRENCY,
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(issuer.id, coin.id, BondKind.PRODUCED, ctx.epoch, "minting"))
    await bonds.connect(BondDraft(issuer.id, coin.id, BondKind.OWNS, ctx.epoch, "minting"))
    currency = CurrencyRow(
        issuer_entity_id=issuer.id,
        item_entity_id=coin.id,
        name=coin.name,
        metal=metal,
        purity=table.start_purity,
        supply=0,
        trust=table.start_trust,
        minted_epoch=ctx.epoch,
    )
    ctx.session.add(currency)
    await ctx.session.flush()
    row = await ctx.session.get(CommunitySocietyRow, issuer.id)
    if row is not None:
        row.currency_id = currency.id
    await note(
        ctx,
        f"{issuer.name} began minting its own coin of {metal.value.replace('_', ' ')}.",
        key="money.minted",
        ids=[issuer.id, coin.id],
        kind=ChronicleKind.TRADE,
    )
    return currency


async def mint(ctx: TickContext, book: EconomyBook, issuer: EntityRow, tally: MoneyTally) -> None:
    table = ctx.rules.money
    if not book.knowledge.knows(issuer.id, KnowledgeBranch.TRADE):
        return
    lot = await coin_metal(ctx, issuer.id)
    if lot is None or lot.material is None:
        return
    currency = await issued_by(ctx, issuer.id)
    if currency is None:
        if book.lacks(issuer.id, Technique.COINAGE):
            return
        if riches(issuer) < ctx.rules.trade.coinage_min_wealth or not ctx.rng(f"mint.{issuer.id}.{ctx.epoch}").chance(ctx.rules.trade.coinage_chance):
            return
        currency = await found_currency(ctx, issuer, lot.material)
    units = min(lot.quantity, table.mint_ore_units)
    taken = await goods_of(ctx.session, ctx.epoch).take(issuer.id, CommodityKind.ORE, units, GoodsFlow.INPUT, material=lot.material)
    struck = sum(item.quantity for item in taken) * table.coins_per_unit * PERCENT // max(1, currency.purity)
    if not currency.held:
        currency.supply += struck
    tally.minted += struck


async def adopt(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    statement = select(CommunitySocietyRow.entity_id, CommunitySocietyRow.currency_id)
    using = dict((entity_id, currency) for entity_id, currency in await ctx.session.execute(statement))
    for bond in await active_bonds(ctx.session, [BondKind.TRADES_WITH]):
        pair = (bond.source_node_id, bond.target_node_id)
        shared = using.get(pair[0]) is not None and using.get(pair[0]) == using.get(pair[1])
        for member in pair if shared else ():
            entity = book.entities.get(member)
            if entity is not None:
                add_prosperity(ctx.rules, entity, ctx.rules.trade.shared_currency_prosperity)
        for taker, giver in (pair, pair[::-1]):
            row = book.societies.get(taker)
            if row is None or row.currency_id is not None or using.get(giver) is None:
                continue
            if ctx.rng(f"adopt.{taker}.{giver}.{ctx.epoch}").chance(ctx.rules.trade.currency_adopt_chance):
                row.currency_id = using[giver]
                using[taker] = using[giver]
                tally.adopted += 1
                taker_row, giver_row = book.entities.get(taker), book.entities.get(giver)
                if taker_row is not None and giver_row is not None:
                    await note(
                        ctx, f"{taker_row.name} began using the money of {giver_row.name}.", key="money.adopted", ids=[taker, giver], kind=ChronicleKind.TRADE
                    )


def users_of(book: EconomyBook, currency_id: int) -> list[int]:
    return [entity_id for entity_id, row in book.societies.items() if row.currency_id == currency_id]


async def debase(ctx: TickContext, book: EconomyBook, currency: CurrencyRow, *, forced: bool = False) -> bool:
    table = ctx.rules.money
    issuer = book.entities.get(currency.issuer_entity_id) or await ctx.session.get(EntityRow, currency.issuer_entity_id)
    if issuer is None or currency.purity <= 0 or (currency.held and not forced):
        return False
    currency.purity = clamp_int(currency.purity - table.debase_step, 0, PERCENT)
    currency.trust = clamp_int(currency.trust - table.debase_trust_loss, 0, PERCENT)
    currency.supply = round_half_up(currency.supply * (PERCENT + table.debase_step) / PERCENT)
    currency.debased_epoch = ctx.epoch
    gain(issuer, table.debase_treasury_gain)
    for user in users_of(book, currency.id):
        row = book.societies[user]
        row.satisfaction_merchant = clamp_int(row.satisfaction_merchant - table.debase_merchant_loss, 0, PERCENT)
    how = "by decree of the Creator" if forced else "to fill an empty treasury"
    await ctx.chronicle(
        ChronicleKind.TRADE,
        f"{issuer.name} debased {currency.name} {how}: its purity fell to {currency.purity}, and merchants no longer trust it.",
        template_key="money.debased",
        entity_ids=[issuer.id, *([currency.item_entity_id] if currency.item_entity_id else [])],
    )
    return True


async def tend_currencies(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.money
    for currency in (await currencies(ctx)).values():
        if currency.held:
            continue
        issuer = book.entities.get(currency.issuer_entity_id)
        if issuer is None:
            currency.trust = clamp_int(currency.trust - table.debase_trust_loss, 0, PERCENT)
            continue
        currency.trust = clamp_int(currency.trust + (currency.purity - currency.trust) * table.trust_drift_pct / PERCENT, 0, PERCENT)
        at_war = await _at_war(ctx, issuer.id)
        tempted = at_war and riches(issuer) < table.debase_wealth_below and ctx.rng(f"debase.{currency.id}.{ctx.epoch}").chance(table.debase_chance)
        if tempted and await debase(ctx, book, currency):
            tally.debased += 1


async def _at_war(ctx: TickContext, community_id: int) -> bool:
    return bool(await BondRepository(ctx.session).outgoing(community_id, BondKind.ENEMY))


async def inject_hoard(ctx: TickContext, community: EntityRow, units: int, metal: MaterialKind, world_material_id: int | None = None) -> int:
    table = ctx.rules.money
    added = await goods_of(ctx.session, ctx.epoch).add(
        community.id,
        CommodityKind.LUXURIES,
        units,
        GoodsFlow.LOOT,
        material=metal if world_material_id is None else None,
        world_material_id=world_material_id,
        quality=70,
        force=True,
    )
    row = await ctx.session.get(CommunitySocietyRow, community.id)
    currency = await ctx.session.get(CurrencyRow, row.currency_id) if row is not None and row.currency_id is not None else None
    if currency is not None and not currency.held:
        currency.supply += round_half_up(units * table.coins_per_unit * table.hoard_supply_pct / PERCENT)
        if currency.metal is metal:
            currency.trust = clamp_int(currency.trust - table.debase_trust_loss // 2, 0, PERCENT)
    await ctx.chronicle(
        ChronicleKind.TRADE,
        f"A hoard of {metal.value.replace('_', ' ')} flooded the market of {community.name}; prices of fine things fell and coin lost its worth.",
        template_key="money.hoard",
        entity_ids=[community.id],
    )
    return added


async def defaulted_before(ctx: TickContext, borrower_id: int) -> bool:
    found = await ctx.session.scalar(select(LoanRow.id).where(LoanRow.borrower_entity_id == borrower_id, LoanRow.status == LoanStatus.DEFAULTED).limit(1))
    return found is not None


async def banks(ctx: TickContext, book: EconomyBook) -> list[EntityRow]:
    table = ctx.rules.banking
    return [
        entity
        for entity in book.entities.values()
        if entity.entity_type is EntityType.FACTION
        and entity.engine_kind is EngineKind.MERCHANT_GUILD
        and riches(entity) >= table.bank_wealth
        and not book.lacks(entity.location_id or 0, Technique.BANKING)
    ]


async def lend(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.banking
    lenders = await banks(ctx, book)
    if not lenders:
        return
    for borrower in book.communities:
        if riches(borrower) >= table.borrower_wealth_below or not await _at_war(ctx, borrower.id):
            continue
        open_loan = await ctx.session.scalar(select(LoanRow.id).where(LoanRow.borrower_entity_id == borrower.id, LoanRow.status == LoanStatus.OPEN).limit(1))
        if open_loan is not None or not ctx.rng(f"lend.{borrower.id}.{ctx.epoch}").chance(table.lend_chance):
            continue
        lender = min(lenders, key=lambda bank: (bank.world_id != borrower.world_id, -riches(bank), bank.id))
        risky = await defaulted_before(ctx, borrower.id)
        if risky and lender.affiliated_entity_id == borrower.id:
            continue
        row = book.societies.get(borrower.id)
        loan = LoanRow(
            lender_entity_id=lender.id,
            borrower_entity_id=borrower.id,
            currency_id=row.currency_id if row is not None else None,
            principal=table.principal,
            interest_pct=table.interest_pct + (table.risk_interest_pct if risky else 0),
            issued_epoch=ctx.epoch,
            due_epoch=ctx.epoch + table.term_epochs,
            status=LoanStatus.OPEN,
            purpose="war",
        )
        ctx.session.add(loan)
        gain(borrower, table.principal)
        gain(lender, -table.principal // 2)
        tally.lent += 1
        await ctx.chronicle(
            ChronicleKind.DEBT,
            f"{lender.name} lent {borrower.name} the means to keep fighting, at {loan.interest_pct}% interest, due Epoch {loan.due_epoch}.",
            template_key="banking.war_loan",
            entity_ids=[lender.id, borrower.id],
        )


def owed(loan: LoanRow) -> int:
    return round_half_up(loan.principal * (PERCENT + loan.interest_pct) / PERCENT) - loan.repaid


async def collect(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.banking
    statement = select(LoanRow).where(LoanRow.status == LoanStatus.OPEN, LoanRow.held.is_(False)).order_by(LoanRow.id)
    for loan in await ctx.session.scalars(statement):
        borrower = book.entities.get(loan.borrower_entity_id)
        lender = book.entities.get(loan.lender_entity_id)
        if borrower is not None and borrower.entity_type is EntityType.POLITY:
            continue
        if borrower is None or lender is None:
            loan.status = LoanStatus.FORGIVEN
            continue
        spare = max(0, riches(borrower) - table.repay_wealth_floor)
        payment = min(owed(loan), max(0, round_half_up(owed(loan) * table.repay_pct / PERCENT)), spare)
        if payment > 0:
            gain(borrower, -payment)
            gain(lender, payment)
            loan.repaid += payment
        if owed(loan) <= 0:
            loan.status = LoanStatus.REPAID
            tally.repaid += 1
        elif ctx.epoch >= loan.due_epoch and payment < owed(loan):
            await default(ctx, book, loan, borrower, lender)
            tally.defaulted += 1
            if riches(lender) < table.collapse_wealth:
                await collapse(ctx, book, lender)
                tally.collapsed += 1


async def default(ctx: TickContext, book: EconomyBook, loan: LoanRow, borrower: EntityRow, lender: EntityRow) -> None:
    table = ctx.rules.banking
    law = await debt_law_of(ctx, borrower, lender)
    if law is not None and law.remedy is DebtRemedy.JUBILEE:
        loan.status = LoanStatus.FORGIVEN
        gain(lender, -table.default_bank_loss)
        await ctx.chronicle(
            ChronicleKind.DEBT,
            f"The jubilee wiped the loan {borrower.name} owed {lender.name}; the bank bore the loss.",
            template_key="banking.jubilee",
            entity_ids=[borrower.id, lender.id],
        )
        return
    if law is not None and law.remedy is DebtRemedy.BONDAGE:
        await bind_debtor(ctx, borrower, lender)
    elif law is not None and law.remedy is DebtRemedy.PRISON:
        await jail_debtor(ctx, borrower, lender, f"{max(0, owed(loan))} silver")
    loan.status = LoanStatus.DEFAULTED
    gain(lender, -table.default_bank_loss)
    await change_relation(ctx, lender.id, borrower.id, -table.default_relation_loss, MemoryKind.BETRAYED_ME, note="defaulted on a loan")
    await ctx.chronicle(
        ChronicleKind.DEBT,
        f"{borrower.name} could not repay {lender.name}; the loan was defaulted and the bank will remember.",
        template_key="banking.default",
        entity_ids=[borrower.id, lender.id],
    )


async def collapse(ctx: TickContext, book: EconomyBook, bank: EntityRow) -> None:
    table = ctx.rules.banking
    set_stats(bank, wealth=0)
    home = bank.affiliated_entity_id or bank.location_id
    row = book.societies.get(home) if home is not None else None
    if row is not None:
        row.satisfaction_merchant = clamp_int(row.satisfaction_merchant - table.collapse_merchant_loss, 0, PERCENT)
    await ctx.chronicle(
        ChronicleKind.TRADE,
        f"{bank.name} collapsed under its bad loans; the merchants who trusted it were ruined.",
        template_key="banking.collapse",
        entity_ids=[bank.id, *([home] if home is not None else [])],
    )


async def forgive_loan(ctx: TickContext, loan: LoanRow) -> None:
    loan.status = LoanStatus.FORGIVEN
    lender = await ctx.session.get(EntityRow, loan.lender_entity_id)
    borrower = await ctx.session.get(EntityRow, loan.borrower_entity_id)
    if lender is not None and borrower is not None and lender.status is EntityStatus.CANON and borrower.status is EntityStatus.CANON:
        await change_relation(ctx, borrower.id, lender.id, ctx.rules.banking.default_relation_loss // 2, MemoryKind.GIFTED_ME, note="loan forgiven")
