from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.war import DebtStatus
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.queries import active_bonds


async def open_debt(session: AsyncSession, debtor_id: int, creditor_id: int) -> BondRow | None:
    found = await active_bonds(session, [BondKind.OWES], sources=[debtor_id], targets=[creditor_id])
    return found[0] if found else None


def commodity_word(commodity: CommodityKind) -> str:
    return COMMODITIES[commodity].label.lower()


async def sell_on_credit(ctx: TickContext, buyer: EntityRow, seller: EntityRow, commodity: CommodityKind, moved: int, *, noted: bool) -> bool:
    table = ctx.rules.market
    if await open_debt(ctx.session, buyer.id, seller.id) is not None:
        return False
    amount = max(1, round(moved / table.credit_divisor))
    due = ctx.epoch + table.credit_term
    what = commodity_word(commodity)
    society = await ctx.session.get(CommunitySocietyRow, buyer.id)
    bond = await BondRepository(ctx.session).connect(
        BondDraft(
            buyer.id,
            seller.id,
            BondKind.OWES,
            ctx.epoch,
            f"bought {what} on credit",
            debt_amount=amount,
            debt_what=what,
            debt_due_epoch=due,
            debt_currency_id=society.currency_id if society is not None else None,
        )
    )
    bond.debt_status = DebtStatus.OPEN
    text = f"{buyer.name} bought {what} from {seller.name} on credit and owes {amount} {what}, due Epoch {due}."
    await ctx.chronicle(ChronicleKind.DEBT, text, template_key="market.credit", entity_ids=[buyer.id, seller.id])
    if noted:
        await note(
            ctx, f"{buyer.name} bought {what} from {seller.name} on credit.", key="market.credit_note", ids=[buyer.id, seller.id], kind=ChronicleKind.TRADE
        )
    return True
