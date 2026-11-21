from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.monetary.authorities import authority_of, currency_for
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record


def home_of(bank: EntityRow) -> int | None:
    return bank.affiliated_entity_id or bank.location_id


async def rescue_bank(ctx: TickContext, bank: EntityRow) -> bool:
    table = ctx.rules.monetary
    currency_id = await currency_for(ctx.session, home_of(bank))
    authority = await authority_of(ctx.session, currency_id)
    currency = await ctx.session.get(CurrencyRow, currency_id) if currency_id is not None else None
    if authority is None or currency is None or not authority.lender_of_last_resort or authority.reserves < table.rescue_cost or held(bank.id):
        return False
    if authority.holder_node_id is not None and held(authority.holder_node_id):
        return False
    if "reserves" not in (authority.locked or []):
        authority.reserves -= table.rescue_cost
    set_stats(bank, wealth=table.rescue_wealth)
    if not currency.held:
        currency.supply += round_half_up(currency.supply * table.rescue_supply_pct / PERCENT)
        currency.trust = clamp_int(currency.trust - table.rescue_trust_loss, 0, PERCENT)
    await record(
        ctx,
        "money.bank_rescued",
        roles={IncidentRole.ACTOR: authority.holder_node_id, IncidentRole.BENEFICIARY: bank.id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"currency": currency.name, "spent": table.rescue_cost, "supply": currency.supply},
    )
    return True


async def spread_run(ctx: TickContext, bank: EntityRow, banks: list[EntityRow]) -> list[int]:
    table = ctx.rules.monetary
    currency_id = await currency_for(ctx.session, home_of(bank))
    if currency_id is None:
        return []
    struck: list[int] = []
    for other in banks:
        if other.id == bank.id or held(other.id) or await currency_for(ctx.session, home_of(other)) != currency_id:
            continue
        wealth = stat_or(other, "wealth", 0)
        set_stats(other, wealth=max(0, wealth - round_half_up(wealth * table.run_spread_pct / PERCENT)))
        struck.append(other.id)
    if struck:
        currency = await ctx.session.get(CurrencyRow, currency_id)
        await record(
            ctx,
            "money.bank_run",
            roles={IncidentRole.SUBJECT: bank.id, IncidentRole.VICTIM: struck},
            facts={"currency": currency.name if currency is not None else "its money", "lost": table.run_spread_pct},
        )
    return struck
