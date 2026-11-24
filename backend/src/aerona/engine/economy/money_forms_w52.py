from aerona.catalog.money import FORM_BACKINGS, STORE_WORKSHOPS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import MoneyBacking, MoneyForm
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record


def backing_of(form: MoneyForm, metal: bool) -> MoneyBacking:
    if metal:
        return MoneyBacking.METAL
    return FORM_BACKINGS.get(form, MoneyBacking.DECREE)


def has_store(book: EconomyBook, issuer_id: int) -> bool:
    return any(book.workshop(issuer_id, kind) is not None for kind in STORE_WORKSHOPS)


async def fitting_form(ctx: TickContext, book: EconomyBook, issuer: EntityRow) -> MoneyForm | None:
    table = ctx.rules.money
    partners = await active_bonds(ctx.session, [BondKind.TRADES_WITH], sources=[issuer.id])
    if len(partners) >= table.bill_partners and not book.lacks(issuer.id, Technique.DOUBLE_ENTRY):
        return MoneyForm.BILL_OF_EXCHANGE
    if has_store(book, issuer.id) and stat_or(issuer, "prosperity", 0) >= table.receipt_prosperity:
        return MoneyForm.WAREHOUSE_RECEIPT
    if await active_bonds(ctx.session, [BondKind.ENEMY], sources=[issuer.id]) and stat_or(issuer, "population", 0) >= table.scrip_population:
        return MoneyForm.LAND_SCRIP
    return None


def fails(ctx: TickContext, book: EconomyBook, currency: CurrencyRow, issuer: EntityRow) -> str | None:
    table = ctx.rules.money
    if currency.form is MoneyForm.BILL_OF_EXCHANGE and stat_or(issuer, "prosperity", 0) < table.bill_drawer_prosperity:
        return "its drawer could not pay"
    if currency.form is MoneyForm.WAREHOUSE_RECEIPT and not has_store(book, issuer.id):
        return "the store behind it was lost"
    if currency.backing is MoneyBacking.LAND and issuer.location_id is None:
        return "the land behind it was lost"
    if currency.backing is MoneyBacking.LABOUR and stat_or(issuer, "population", 0) * table.labour_backing_per_person < currency.supply:
        return "the work owed behind it outran the hands to give it"
    return None


async def test_backing(ctx: TickContext, book: EconomyBook, currency: CurrencyRow, issuer: EntityRow) -> bool:
    why = fails(ctx, book, currency, issuer)
    if why is None or currency.trust <= 0:
        return False
    table = ctx.rules.money
    currency.trust = clamp_int(currency.trust - table.failed_trust_loss, 0, PERCENT)
    currency.supply = currency.supply * (PERCENT - table.failed_supply_loss_pct) // PERCENT
    await record(
        ctx,
        "money.failed",
        roles={IncidentRole.ACTOR: issuer.id, **({IncidentRole.SUBJECT: currency.item_entity_id} if currency.item_entity_id is not None else {})},
        facts={"form": currency.form, "backing": currency.backing, "trust": currency.trust},
    )
    return True
