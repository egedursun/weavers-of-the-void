from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.war import DebtStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.recording.record import StepDraft, record


async def open_debt(session: AsyncSession, debtor_id: int, creditor_id: int) -> BondRow | None:
    found = await active_bonds(session, [BondKind.OWES], sources=[debtor_id], targets=[creditor_id])
    return found[0] if found else None


def commodity_word(commodity: CommodityKind) -> str:
    return COMMODITIES[commodity].label.lower()


async def sell_on_credit(ctx: TickContext, buyer: EntityRow, seller: EntityRow, commodity: CommodityKind, moved: int) -> bool:
    table = ctx.rules.market
    if moved <= 0 or await open_debt(ctx.session, buyer.id, seller.id) is not None:
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
    await record(
        ctx,
        "market.credit",
        roles={IncidentRole.BORROWER: buyer.id, IncidentRole.LENDER: seller.id},
        facts={"good": commodity, "moved": moved, "owed": amount, "due_epoch": due},
        steps=(
            StepDraft(StepAction.DELIVER, actor=seller.id, target=buyer.id, amount=moved, unit=FactUnit.COUNT),
            StepDraft(StepAction.LEND, actor=seller.id, target=buyer.id, amount=amount, unit=FactUnit.COUNT),
        ),
    )
    return True
