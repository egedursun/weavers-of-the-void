from sqlalchemy import select

from aerona.catalog.life.securities import LOSING_ENDINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.concealment import HiddenTruthRow, TruthKeeperRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.securities import MOOD_MAX, MOOD_MIN, IssuedSecurityRow, SecurityPriceRow, StockExchangeRow
from aerona.db.write_guard import held
from aerona.domain.enums.competition import CompetitionClause
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.finance import CreditState
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.securities import DEBT_KINDS, SecurityKind
from aerona.engine.competition.clauses import clause_strength
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, riches_of, take_coin
from aerona.engine.governance.insolvency import InsolvencyTally, file_case
from aerona.engine.monetary.authorities import authority_of, currency_for, price_factor
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.securities.holdings import SecuritiesTally, holdings_of

RESULTS_MIDPOINT = 50
DEFAULTED_WORTH_PCT = 10
FUTURE_HERDING = 2
SHOCKS: tuple[tuple[str, IncidentRole], ...] = (
    *((f"war.ended_{ending.value}", IncidentRole.OPPONENT) for ending in LOSING_ENDINGS),
    ("companies.collapsed", IncidentRole.SUBJECT),
    ("org.liquidated", IncidentRole.SUBJECT),
    ("market.cartel_exposed", IncidentRole.SUBJECT),
    ("securities.insider_exposed", IncidentRole.SUBJECT),
)


async def fundamental(ctx: TickContext, security: IssuedSecurityRow, issuer: EntityRow | None) -> int:
    if issuer is None or issuer.status is not EntityStatus.CANON:
        return 1
    if security.kind not in DEBT_KINDS:
        return max(1, round_half_up(security.face_value * max(1, riches_of(issuer)) / RESULTS_MIDPOINT))
    if security.defaulted_epoch is not None:
        return max(1, security.face_value * DEFAULTED_WORTH_PCT // PERCENT)
    credit = await ctx.session.get(CreditProfileRow, issuer.id)
    rating = credit.rating if credit is not None else RESULTS_MIDPOINT
    authority = await authority_of(ctx.session, await currency_for(ctx.session, issuer.id))
    rate = authority.effective_rate if authority is not None else ctx.rules.monetary.neutral_rate
    return max(1, round_half_up(security.face_value * rating / PERCENT * (PERCENT + security.coupon_pct - rate) / PERCENT))


async def shocked(ctx: TickContext, issuer_id: int) -> str | None:
    credit = await ctx.session.get(CreditProfileRow, issuer_id)
    if credit is not None and credit.state is CreditState.DEFAULT:
        return "its issuer defaulted"
    for kind, role in SHOCKS:
        found = await ctx.session.scalar(
            select(IncidentRow.id)
            .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
            .where(IncidentRow.kind == kind, IncidentRow.epoch == ctx.epoch, IncidentParticipantRow.node_id == issuer_id, IncidentParticipantRow.role == role)
            .limit(1)
        )
        if found is not None:
            return kind.split(".")[1].replace("_", " ")
    return None


async def last_price(ctx: TickContext, security: IssuedSecurityRow) -> int:
    query = select(SecurityPriceRow.price).where(SecurityPriceRow.security_id == security.id, SecurityPriceRow.epoch < ctx.epoch)
    found = await ctx.session.scalar(query.order_by(SecurityPriceRow.epoch.desc(), SecurityPriceRow.id.desc()).limit(1))
    return int(found) if found is not None else security.price


async def price_row(ctx: TickContext, security: IssuedSecurityRow) -> SecurityPriceRow:
    query = select(SecurityPriceRow).where(SecurityPriceRow.security_id == security.id, SecurityPriceRow.epoch == ctx.epoch)
    row = await ctx.session.scalar(query.order_by(SecurityPriceRow.id).limit(1))
    if row is None:
        row = SecurityPriceRow(security_id=security.id, issuer_node_id=security.issuer_node_id, epoch=ctx.epoch, price=security.price, volume=0, locked=[])
        ctx.session.add(row)
    return row


async def traded(ctx: TickContext, security: IssuedSecurityRow, units: int) -> None:
    row = await price_row(ctx, security)
    if units > 0 and "volume" not in (row.locked or []):
        row.volume += units


async def margin_calls(ctx: TickContext, security: IssuedSecurityRow, tally: SecuritiesTally) -> None:
    table = ctx.rules.securities
    insolvency = InsolvencyTally()
    for row in await holdings_of(ctx.session, security.id):
        worth = row.amount * security.price
        if not row.on_margin or row.on_margin * PERCENT <= worth * table.margin_call_pct or held(row.holder_node_id) or "amount" in (row.locked or []):
            continue
        holder = await living_entity(ctx.session, row.holder_node_id)
        shortfall = max(0, row.on_margin - worth)
        sold, row.amount, row.on_margin = row.amount, 0, 0
        tally.margin_calls += 1
        await traded(ctx, security, sold)
        bankrupt = holder is not None and shortfall and not await take_coin(ctx.session, ctx.rules, holder, shortfall)
        if bankrupt and holder is not None:
            await file_case(ctx, holder, None, insolvency)
        await record(
            ctx,
            "securities.margin_called",
            roles={IncidentRole.VICTIM: row.holder_node_id, IncidentRole.SUBJECT: security.issuer_node_id},
            facts={"security": security.name, "sold": sold, "shortfall": shortfall, "outcome": "went before the court" if bankrupt else "paid the rest"},
        )


async def insiders(ctx: TickContext, security: IssuedSecurityRow, before: int, exchange: StockExchangeRow | None, tally: SecuritiesTally) -> None:
    table = ctx.rules.securities
    keepers = (
        select(TruthKeeperRow.keeper_node_id)
        .join(HiddenTruthRow, HiddenTruthRow.id == TruthKeeperRow.truth_id)
        .where(HiddenTruthRow.subject_node_id == security.issuer_node_id)
    )
    knowing = set(await ctx.session.scalars(keepers))
    ban = (
        await clause_strength(ctx, exchange.settlement_entity_id, CompetitionClause.INSIDER_BAN)
        if exchange is not None and exchange.settlement_entity_id
        else 0
    )
    for row in await holdings_of(ctx.session, security.id):
        if row.holder_node_id not in knowing or held(row.holder_node_id) or "amount" in (row.locked or []):
            continue
        holder = await living_entity(ctx.session, row.holder_node_id)
        if holder is None:
            continue
        escaped = row.amount * max(0, before - security.price)
        await give_coin(ctx.session, ctx.rules, holder, row.amount * before)
        await traded(ctx, security, row.amount)
        row.amount = 0
        if not ban or not ctx.rng(f"securities.insider.{security.id}.{holder.id}.{ctx.epoch}").chance(table.insider_exposure_pct * ban // PERCENT):
            continue
        fine = round_half_up(escaped * table.insider_fine_pct / PERCENT)
        await take_coin(ctx.session, ctx.rules, holder, fine)
        tally.insiders += 1
        await record(
            ctx,
            "securities.insider_exposed",
            roles={IncidentRole.SUBJECT: holder.id, IncidentRole.TARGET: security.issuer_node_id},
            facts={"security": security.name, "escaped": escaped, "fine": fine},
        )


async def crash(ctx: TickContext, security: IssuedSecurityRow, exchange: StockExchangeRow | None, why: str, tally: SecuritiesTally) -> None:
    table = ctx.rules.securities
    before = security.price
    if "price" not in (security.locked or []):
        security.price = max(1, round_half_up(before * (PERCENT - table.crash_drop_pct) / PERCENT))
    security.bubble = False
    if exchange is not None and "mood" not in (exchange.locked or []):
        exchange.mood = clamp_int(exchange.mood - table.crash_mood, MOOD_MIN, MOOD_MAX)
    tally.crashes += 1
    await record(
        ctx,
        "securities.crash",
        roles={IncidentRole.SUBJECT: security.issuer_node_id},
        facts={"security": security.name, "before": before, "price": security.price, "why": why},
    )
    await insiders(ctx, security, before, exchange, tally)
    await margin_calls(ctx, security, tally)


async def move_price(ctx: TickContext, security: IssuedSecurityRow, exchange: StockExchangeRow | None, tally: SecuritiesTally) -> None:
    table = ctx.rules.securities
    issuer = await ctx.session.get(EntityRow, security.issuer_node_id)
    worth = await fundamental(ctx, security, issuer)
    price = security.price
    herding = table.herding_pct * (FUTURE_HERDING if security.kind is SecurityKind.FUTURE else 1)
    drift = (worth - price) * table.anchor_pct / PERCENT + (price - await last_price(ctx, security)) * herding / PERCENT
    mood = price * (exchange.mood if exchange is not None else 0) * table.mood_pct / (PERCENT * PERCENT)
    moved = max(1, round_half_up((price + drift + mood) * await price_factor(ctx, await currency_for(ctx.session, security.issuer_node_id))))
    if "price" not in (security.locked or []):
        security.price = moved
    if "belief" not in (security.locked or []):
        security.belief = clamp_int(RESULTS_MIDPOINT + (security.price - worth) * RESULTS_MIDPOINT // max(1, worth), 0, PERCENT)
    tally.moved += 1
    why = await shocked(ctx, security.issuer_node_id)
    if why is not None:
        await crash(ctx, security, exchange, why, tally)
    elif security.price * PERCENT > worth * (PERCENT + table.bubble_threshold_pct):
        if not security.bubble:
            security.bubble = True
            tally.bubbles += 1
            await record(
                ctx,
                "securities.bubble_formed",
                roles={IncidentRole.SUBJECT: security.issuer_node_id},
                facts={"security": security.name, "price": security.price, "worth": worth},
            )
        elif ctx.rng(f"securities.burst.{security.id}.{ctx.epoch}").chance(table.burst_chance_pct):
            await crash(ctx, security, exchange, "the bubble burst", tally)
    elif security.bubble:
        security.bubble = False
    row = await price_row(ctx, security)
    if "price" not in (row.locked or []):
        row.price = security.price
