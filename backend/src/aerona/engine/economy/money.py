from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.finance import OWED_LOANS
from aerona.catalog.life.domain import LENDER_KINDS
from aerona.catalog.life.economy import REFORM_MONEY_FORMS
from aerona.catalog.materials import COIN_MATERIALS
from aerona.catalog.money import MONEY_FORMS, REFORMS, issuer_kind_of
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.core.grammar import spoken
from aerona.db.faction_kinds import kinds_by_faction
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.stored import stored_id
from aerona.db.tables.economy import CommunityStockRow, CurrencyRow, LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, LoanStatus, MoneyBacking, MoneyForm, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.governance import OrgStrategy
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import DebtRemedy
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.debt_law import bind_debtor, debt_law_of, jail_debtor
from aerona.engine.economy.money_forms_w52 import backing_of, fitting_form, test_backing
from aerona.engine.economy.stocks import goods_of
from aerona.engine.finance.credit import interest_for, on_default, refuses
from aerona.engine.finance.w52_credit import seize_collateral
from aerona.engine.governance.insolvency import InsolvencyTally, file_case
from aerona.engine.loops.delay import lagged
from aerona.engine.monetary.authorities import borrow_factor, establish
from aerona.engine.monetary.rescue import rescue_bank, spread_run
from aerona.engine.polity.law_effects import may_coin
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.community_relations import change_relation

MINTERS = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION})


@dataclass
class MoneyTally:
    minted: int = 0
    adopted: int = 0
    debased: int = 0
    reformed: int = 0
    failed: int = 0
    lent: int = 0
    repaid: int = 0
    defaulted: int = 0
    collapsed: int = 0
    rescued: int = 0
    runs: int = 0


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
    return min(lots, key=lambda lot: (COIN_MATERIALS.index(lot.material) if lot.material in COIN_MATERIALS else len(COIN_MATERIALS), lot.id), default=None)


async def found_currency(ctx: TickContext, issuer: EntityRow, metal: MaterialKind | None, form: MoneyForm = MoneyForm.COIN) -> CurrencyRow:
    table = ctx.rules.money
    coin = await create_record(
        ctx,
        RecordSpec(
            name=f"{issuer.name} Coin" if metal is not None else f"{issuer.name} {MONEY_FORMS[form].label}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(
                damage=0,
                protection=0,
                might=clamp_int(ctx.rules.trade.currency_might_base + ctx.rng(f"coin.{issuer.id}").die(ctx.rules.trade.currency_might_die), 0, PERCENT),
                curse=0,
            ),
            body=f"{issuer.name} began to strike coins of {spoken(metal)}."
            if metal is not None
            else f"{issuer.name} began to issue {MONEY_FORMS[form].label.lower()}.",
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
        issuer_kind=issuer_kind_of(issuer.entity_type, issuer.engine_kind),
        form=form,
        backing=backing_of(form, metal is not None),
        convertible=metal is not None,
    )
    ctx.session.add(currency)
    await ctx.session.flush()
    await establish(ctx, currency)
    row = await ctx.session.get(CommunitySocietyRow, issuer.id)
    if row is not None:
        row.currency_id = currency.id
    if metal is not None:
        await record(
            ctx,
            "money.minted",
            roles={IncidentRole.MAKER: issuer.id, IncidentRole.PRODUCT: coin.id},
            facts={"metal": metal, "purity": currency.purity, "trust": currency.trust},
            steps=(StepDraft(StepAction.SHAPE, actor=issuer.id, target=coin.id),),
            place=coin.location_id,
        )
    else:
        await record(
            ctx,
            "money.issued",
            roles={IncidentRole.MAKER: issuer.id, IncidentRole.PRODUCT: coin.id},
            facts={"form": form, "trust": currency.trust},
            steps=(StepDraft(StepAction.SHAPE, actor=issuer.id, target=coin.id),),
            place=coin.location_id,
        )
    return currency


def unminted_form(book: EconomyBook, issuer_id: int) -> MoneyForm | None:
    techniques = book.techniques.get(issuer_id, set())
    known = [form for form in REFORMS if MONEY_FORMS[form].technique in techniques]
    return known[-1] if known else None


async def mint(ctx: TickContext, book: EconomyBook, issuer: EntityRow, tally: MoneyTally) -> None:
    table = ctx.rules.money
    if not book.knowledge.knows(issuer.id, KnowledgeBranch.TRADE):
        return
    lot = await coin_metal(ctx, issuer.id)
    metal = lot.material if lot is not None else None
    currency = await issued_by(ctx, issuer.id)
    if currency is None:
        form = unminted_form(book, issuer.id) or (
            MoneyForm.COIN if metal is not None and not book.lacks(issuer.id, Technique.COINAGE) else await fitting_form(ctx, book, issuer)
        )
        if form is None or not await may_coin(ctx.session, ctx.rules, issuer.id):
            return
        if riches(issuer) < ctx.rules.trade.coinage_min_wealth or not ctx.rng(f"mint.{issuer.id}.{ctx.epoch}").chance(ctx.rules.trade.coinage_chance):
            return
        currency = await found_currency(ctx, issuer, metal if form is MoneyForm.COIN else None, form)
    if not MONEY_FORMS[currency.form].uses_metal or lot is None or metal is None:
        return
    mint_works = book.workshop(issuer.id, WorkshopKind.MINT)
    units = min(lot.quantity, table.mint_ore_units * (mint_works.level if mint_works is not None else 1))
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
                await record(ctx, "money.adopted", roles={IncidentRole.RECEIVER: taker, IncidentRole.GIVER: giver}, facts={"currency": using[giver]})


def users_of(book: EconomyBook, currency_id: int) -> list[int]:
    return [entity_id for entity_id, row in book.societies.items() if row.currency_id == currency_id]


async def debase(ctx: TickContext, book: EconomyBook, currency: CurrencyRow, *, forced: bool = False) -> bool:
    table = ctx.rules.money
    issuer = book.entities.get(currency.issuer_entity_id) or await ctx.session.get(EntityRow, currency.issuer_entity_id)
    if issuer is None or currency.purity <= 0 or (currency.held and not forced):
        return False
    if MONEY_FORMS[currency.form].uses_metal:
        currency.purity = clamp_int(currency.purity - table.debase_step, 0, PERCENT)
    currency.trust = clamp_int(currency.trust - table.debase_trust_loss, 0, PERCENT)
    currency.supply = round_half_up(currency.supply * (PERCENT + table.debase_step) / PERCENT)
    currency.debased_epoch = ctx.epoch
    gain(issuer, table.debase_treasury_gain)
    for user in users_of(book, currency.id):
        row = book.societies[user]
        row.satisfaction_merchant = clamp_int(row.satisfaction_merchant - table.debase_merchant_loss, 0, PERCENT)
    await record(
        ctx,
        "money.debased_by_creator" if forced else "money.debased",
        roles={IncidentRole.ACTOR: issuer.id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"purity": currency.purity, "trust": currency.trust, "supply": currency.supply, "treasury_gain": table.debase_treasury_gain},
    )
    return True


async def reform(ctx: TickContext, book: EconomyBook, currency: CurrencyRow, issuer: EntityRow) -> bool:
    later = REFORMS[REFORMS.index(currency.form) + 1 :] if currency.form in REFORMS else REFORMS
    known = [form for form in later if (technique := MONEY_FORMS[form].technique) is None or not book.lacks(issuer.id, technique)]
    if not known or not ctx.rng(f"reform.{currency.id}.{ctx.epoch}").chance(ctx.rules.money.reform_chance):
        return False
    form = known[-1]
    if currency.form in REFORM_MONEY_FORMS:
        currency.backing = MoneyBacking.METAL if currency.metal is not None else MoneyBacking.DECREE
        currency.convertible = currency.metal is not None
    currency.form = form
    currency.metal = None
    currency.purity = PERCENT
    await record(
        ctx,
        "money.reformed",
        roles={IncidentRole.ACTOR: issuer.id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"form": form, "backing": currency.backing},
    )
    return True


async def strain(ctx: TickContext, currency: CurrencyRow, issuer: EntityRow) -> None:
    table = ctx.rules.money
    spec = MONEY_FORMS[currency.form]
    rng = ctx.rng(f"money.strain.{await stored_id(ctx.session, currency)}.{ctx.epoch}")
    copied = table.counterfeit_chance * spec.counterfeit_pct * (PERCENT - currency.trust) // (PERCENT * PERCENT)
    if rng.chance(copied):
        currency.trust = clamp_int(currency.trust - table.counterfeit_trust_loss, 0, PERCENT)
    if spec.intrusion and rng.chance(table.intrusion_chance):
        currency.supply = max(0, currency.supply - currency.supply * table.intrusion_supply_pct // PERCENT)
    if not spec.uses_metal:
        currency.supply += table.issue_units * max(1, stat_or(issuer, "population", 0) // PER_MILLE)


async def tend_currencies(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.money
    for currency in (await currencies(ctx)).values():
        if currency.held:
            continue
        issuer = book.entities.get(currency.issuer_entity_id)
        if issuer is None:
            currency.trust = clamp_int(currency.trust - table.debase_trust_loss, 0, PERCENT)
            continue
        if await reform(ctx, book, currency, issuer):
            tally.reformed += 1
        await strain(ctx, currency, issuer)
        if await test_backing(ctx, book, currency, issuer):
            tally.failed += 1
        standing = currency.purity if MONEY_FORMS[currency.form].uses_metal else riches(issuer)
        anchor = await lagged(ctx, BalanceLoop.DEBASEMENT, issuer.id, standing, subject=currency.id)
        currency.trust = clamp_int(currency.trust + (anchor - currency.trust) * table.trust_drift_pct / PERCENT, 0, PERCENT)
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
    await record(ctx, "money.hoard", roles={IncidentRole.RECEIVER: community.id}, facts={"metal": metal, "units": units, "added": added}, place=community.id)
    return added


async def defaulted_before(ctx: TickContext, borrower_id: int) -> bool:
    found = await ctx.session.scalar(select(LoanRow.id).where(LoanRow.borrower_entity_id == borrower_id, LoanRow.status == LoanStatus.DEFAULTED).limit(1))
    return found is not None


async def banks(ctx: TickContext, book: EconomyBook) -> list[EntityRow]:
    table = ctx.rules.banking
    kinds = await kinds_by_faction(ctx.session)
    return [
        entity
        for entity in book.entities.values()
        if entity.entity_type is EntityType.FACTION
        and entity.status is EntityStatus.CANON
        and kinds.get(entity.id) in LENDER_KINDS
        and riches(entity) >= table.bank_wealth
        and not book.lacks(entity.location_id or 0, Technique.BANKING)
    ]


async def lend(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.banking
    lenders = [bank for bank in await banks(ctx, book) if not held(bank.id)]
    if not lenders:
        return
    await lend_to_organisations(ctx, book, lenders, tally)
    for borrower in book.communities:
        if held(borrower.id) or riches(borrower) >= table.borrower_wealth_below or not await _at_war(ctx, borrower.id):
            continue
        open_loan = await ctx.session.scalar(select(LoanRow.id).where(LoanRow.borrower_entity_id == borrower.id, LoanRow.status.in_(OWED_LOANS)).limit(1))
        row = book.societies.get(borrower.id)
        lending = table.lend_chance * await borrow_factor(ctx, row.currency_id if row is not None else None)
        if open_loan is not None or not ctx.rng(f"lend.{borrower.id}.{ctx.epoch}").chance(lending):
            continue
        lender = min(lenders, key=lambda bank: (bank.world_id != borrower.world_id, -riches(bank), bank.id))
        risky = await defaulted_before(ctx, borrower.id)
        if (risky and lender.affiliated_entity_id == borrower.id) or await refuses(ctx, borrower.id):
            continue
        row = book.societies.get(borrower.id)
        loan = LoanRow(
            lender_entity_id=lender.id,
            borrower_entity_id=borrower.id,
            currency_id=row.currency_id if row is not None else None,
            principal=table.principal,
            interest_pct=await interest_for(ctx, borrower.id, table.interest_pct + (table.risk_interest_pct if risky else 0)),
            issued_epoch=ctx.epoch,
            due_epoch=ctx.epoch + table.term_epochs,
            status=LoanStatus.OPEN,
            purpose="war",
        )
        ctx.session.add(loan)
        gain(borrower, table.principal)
        gain(lender, -table.principal // 2)
        tally.lent += 1
        await record(
            ctx,
            "banking.war_loan",
            roles={IncidentRole.LENDER: lender.id, IncidentRole.BORROWER: borrower.id},
            facts={"principal": loan.principal, "interest": loan.interest_pct, "due_epoch": loan.due_epoch},
            steps=(StepDraft(StepAction.LEND, actor=lender.id, target=borrower.id, amount=loan.principal, unit=FactUnit.COIN),),
        )


ENTERPRISING = (OrgStrategy.GROW, OrgStrategy.RESEARCH, OrgStrategy.EXPAND_ABROAD, OrgStrategy.INTEGRATE_UP, OrgStrategy.INTEGRATE_DOWN)


async def lend_to_organisations(ctx: TickContext, book: EconomyBook, lenders: list[EntityRow], tally: MoneyTally) -> None:
    table = ctx.rules.banking
    query = select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.strategy.in_(ENTERPRISING)).order_by(OrgGovernanceRow.org_node_id)
    for org_id in list(await ctx.session.scalars(query)):
        borrower = book.entities.get(org_id)
        if borrower is None or held(org_id) or riches(borrower) >= table.borrower_wealth_below:
            continue
        open_loan = await ctx.session.scalar(select(LoanRow.id).where(LoanRow.borrower_entity_id == org_id, LoanRow.status.in_(OWED_LOANS)).limit(1))
        if open_loan is not None or not ctx.rng(f"lend.enterprise.{org_id}.{ctx.epoch}").chance(table.enterprise_lend_chance):
            continue
        others = [bank for bank in lenders if bank.id != org_id]
        if not others or await refuses(ctx, org_id):
            continue
        lender = min(others, key=lambda bank: (bank.world_id != borrower.world_id, -riches(bank), bank.id))
        risky = await defaulted_before(ctx, org_id)
        loan = LoanRow(
            lender_entity_id=lender.id,
            borrower_entity_id=org_id,
            principal=table.principal,
            interest_pct=await interest_for(ctx, org_id, table.interest_pct + (table.risk_interest_pct if risky else 0)),
            issued_epoch=ctx.epoch,
            due_epoch=ctx.epoch + table.term_epochs,
            status=LoanStatus.OPEN,
            purpose="enterprise",
        )
        ctx.session.add(loan)
        gain(borrower, table.principal)
        gain(lender, -table.principal // 2)
        tally.lent += 1
        await record(
            ctx,
            "banking.enterprise_loan",
            roles={IncidentRole.LENDER: lender.id, IncidentRole.BORROWER: org_id},
            facts={"principal": loan.principal, "interest": loan.interest_pct, "due_epoch": loan.due_epoch},
            steps=(StepDraft(StepAction.LEND, actor=lender.id, target=org_id, amount=loan.principal, unit=FactUnit.COIN),),
        )


async def governed(ctx: TickContext, borrower: EntityRow) -> bool:
    return borrower.entity_type is EntityType.FACTION and await ctx.session.get(OrgGovernanceRow, borrower.id) is not None


def owed(loan: LoanRow) -> int:
    return round_half_up(loan.principal * (PERCENT + loan.interest_pct) / PERCENT) - loan.repaid


async def collect(ctx: TickContext, book: EconomyBook, tally: MoneyTally) -> None:
    table = ctx.rules.banking
    statement = select(LoanRow).where(LoanRow.status.in_(OWED_LOANS), LoanRow.held.is_(False)).order_by(LoanRow.id)
    for loan in await ctx.session.scalars(statement):
        borrower = book.entities.get(loan.borrower_entity_id)
        lender = book.entities.get(loan.lender_entity_id)
        if borrower is not None and borrower.entity_type is EntityType.POLITY:
            continue
        if borrower is None or lender is None or lender.status is not EntityStatus.CANON:
            loan.status = LoanStatus.FORGIVEN
            continue
        if held(borrower.id) or held(lender.id):
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
        elif ctx.epoch >= loan.due_epoch and payment < owed(loan) and await governed(ctx, borrower):
            await file_case(ctx, borrower, None, InsolvencyTally())
        elif ctx.epoch >= loan.due_epoch and payment < owed(loan):
            await default(ctx, book, loan, borrower, lender)
            tally.defaulted += 1
            if riches(lender) >= table.collapse_wealth:
                continue
            if await rescue_bank(ctx, lender):
                tally.rescued += 1
                continue
            await collapse(ctx, book, lender)
            tally.runs += 1 if await spread_run(ctx, lender, await banks(ctx, book)) else 0
            tally.collapsed += 1


async def default(ctx: TickContext, book: EconomyBook, loan: LoanRow, borrower: EntityRow, lender: EntityRow) -> None:
    table = ctx.rules.banking
    law = await debt_law_of(ctx, borrower, lender)
    if law is not None and law.remedy is DebtRemedy.JUBILEE:
        loan.status = LoanStatus.FORGIVEN
        gain(lender, -table.default_bank_loss)
        await record(
            ctx,
            "banking.jubilee",
            roles={IncidentRole.BORROWER: borrower.id, IncidentRole.LENDER: lender.id},
            facts={"owed": max(0, owed(loan)), "bank_loss": table.default_bank_loss},
        )
        return
    if law is not None and law.remedy is DebtRemedy.BONDAGE:
        await bind_debtor(ctx, borrower, lender)
    elif law is not None and law.remedy is DebtRemedy.PRISON:
        await jail_debtor(ctx, borrower, lender, f"a debt of {max(0, owed(loan))}")
    loan.status = LoanStatus.DEFAULTED
    await seize_collateral(ctx, loan)
    gain(lender, -table.default_bank_loss)
    await on_default(ctx, borrower, lender)
    await change_relation(ctx, lender.id, borrower.id, -table.default_relation_loss, MemoryKind.BETRAYED_ME, note="defaulted on a loan")
    await record(
        ctx,
        "banking.default",
        roles={IncidentRole.BORROWER: borrower.id, IncidentRole.LENDER: lender.id},
        facts={"owed": max(0, owed(loan)), "remedy": law.remedy if law is not None else None, "relation": -table.default_relation_loss},
        steps=(StepDraft(StepAction.DEFAULT, actor=borrower.id, target=lender.id, amount=max(0, owed(loan)), unit=FactUnit.COIN, outcome=StepOutcome.FAILURE),),
    )


async def collapse(ctx: TickContext, book: EconomyBook, bank: EntityRow) -> None:
    table = ctx.rules.banking
    set_stats(bank, wealth=0)
    await retire_in(ctx, bank, "collapsed under its bad loans", close_bonds=True)
    home = bank.affiliated_entity_id or bank.location_id
    row = book.societies.get(home) if home is not None else None
    if row is not None:
        row.satisfaction_merchant = clamp_int(row.satisfaction_merchant - table.collapse_merchant_loss, 0, PERCENT)
    await record(
        ctx, "banking.collapse", roles={IncidentRole.SUBJECT: bank.id, IncidentRole.VICTIM: home}, facts={"merchant_loss": table.collapse_merchant_loss}
    )


async def forgive_loan(ctx: TickContext, loan: LoanRow) -> None:
    loan.status = LoanStatus.FORGIVEN
    lender = await ctx.session.get(EntityRow, loan.lender_entity_id)
    borrower = await ctx.session.get(EntityRow, loan.borrower_entity_id)
    if lender is not None and borrower is not None and lender.status is EntityStatus.CANON and borrower.status is EntityStatus.CANON:
        await change_relation(ctx, borrower.id, lender.id, ctx.rules.banking.default_relation_loss // 2, MemoryKind.GIFTED_ME, note="loan forgiven")
