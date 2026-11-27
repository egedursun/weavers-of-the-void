from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.affairs import ElectionRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.monetary import RATE_MAX, MonetaryAuthorityRow, MonetaryRateRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.monetary import MonetaryAim
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.finance.credit import realm_of
from aerona.engine.monetary.authorities import MonetaryTally, align, authority_of
from aerona.engine.monetary.pegs import defend_peg
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.standing import still_standing
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

PRINTING_AIMS = frozenset({MonetaryAim.FUND_THE_STATE})


async def target_rate(ctx: TickContext, authority: MonetaryAuthorityRow, currency: CurrencyRow) -> int | None:
    table = ctx.rules.monetary
    aim = authority.aim
    if aim is MonetaryAim.NONE:
        return None
    if aim is MonetaryAim.STABLE_VALUE:
        return table.neutral_rate + round_half_up((PERCENT - currency.trust) * table.trust_rate_pct / PERCENT)
    if aim in {MonetaryAim.CHEAP_CREDIT, MonetaryAim.FUND_THE_STATE}:
        return table.cheap_rate
    if aim is MonetaryAim.GROWTH:
        return max(0, table.neutral_rate - table.growth_rate_gap)
    if aim is MonetaryAim.PEG:
        anchor = await authority_of(ctx.session, authority.peg_currency_id)
        return anchor.rate if anchor is not None else table.neutral_rate
    return table.neutral_rate


async def pressed(ctx: TickContext, realm_id: int | None) -> bool:
    if realm_id is None:
        return False
    if await BondRepository(ctx.session).outgoing(realm_id, BondKind.ENEMY):
        return True
    recent = select(ElectionRow.id).where(ElectionRow.polity_entity_id == realm_id, ElectionRow.epoch >= ctx.epoch - 1).limit(1)
    return await ctx.session.scalar(recent) is not None


async def bend(ctx: TickContext, authority: MonetaryAuthorityRow, issuer: EntityRow | None, tally: MonetaryTally) -> bool:
    table = ctx.rules.monetary
    if issuer is None or authority.aim in PRINTING_AIMS or "aim" in (authority.locked or []):
        return False
    realm = await realm_of(ctx, issuer.id) or issuer.id
    if not await pressed(ctx, realm):
        return False
    chance = table.bend_chance_pct * (PERCENT - authority.independence) // PERCENT
    if ctx.rng(f"monetary.bend.{authority.id}.{ctx.epoch}").chance(chance):
        authority.aim = MonetaryAim.FUND_THE_STATE
        tally.bent += 1
        return True
    if realm is not None and authority.holder_node_id is not None and authority.holder_node_id != realm and authority.independence:
        await change_relation(ctx, realm, authority.holder_node_id, -table.resist_favour_loss, MemoryKind.ILL_WILL, note="refused to issue at the ruler's call")
        tally.resisted += 1
    return False


async def move_rate(ctx: TickContext, authority: MonetaryAuthorityRow, currency: CurrencyRow, tally: MonetaryTally) -> None:
    target = await target_rate(ctx, authority, currency)
    if target is None or "rate" in (authority.locked or []) or target == authority.rate:
        return
    step = ctx.rules.monetary.rate_step
    before = authority.rate
    authority.rate = clamp_int(before + max(-step, min(step, target - before)), 0, RATE_MAX)
    if authority.rate == before:
        return
    tally.rates_moved += 1
    await record(
        ctx,
        "money.rate_set",
        roles={IncidentRole.ACTOR: authority.holder_node_id, IncidentRole.SUBJECT: currency.item_entity_id},
        facts={"currency": currency.name, "rate": authority.rate, "before": before, "aim": authority.aim},
    )


async def print_for_state(
    ctx: TickContext, authority: MonetaryAuthorityRow, currency: CurrencyRow, issuer: EntityRow | None, *, bent: bool, tally: MonetaryTally
) -> None:
    table = ctx.rules.monetary
    if currency.held:
        return
    currency.supply += round_half_up(currency.supply * table.state_issue_pct / PERCENT)
    currency.trust = clamp_int(currency.trust - table.state_issue_trust_loss, 0, PERCENT)
    if issuer is not None:
        await give_coin(ctx.session, ctx.rules, issuer, table.state_issue_coin)
    tally.printed += 1
    await record(
        ctx,
        "money.printed_for_state",
        roles={
            IncidentRole.ACTOR: authority.holder_node_id,
            IncidentRole.BENEFICIARY: issuer.id if issuer is not None else None,
            IncidentRole.SUBJECT: currency.item_entity_id,
        },
        facts={
            "currency": currency.name,
            "supply": currency.supply,
            "trust": currency.trust,
            "coin": table.state_issue_coin,
            "bent": "pressed by the ruler" if bent else "by its own aim",
        },
    )


async def tend_authority(ctx: TickContext, authority: MonetaryAuthorityRow, tally: MonetaryTally) -> None:
    currency = await ctx.session.get(CurrencyRow, authority.currency_id)
    if currency is None or (authority.holder_node_id is not None and held(authority.holder_node_id)) or held(currency.issuer_entity_id):
        return
    if authority.holder_node_id is not None and not await still_standing(ctx.session, authority.holder_node_id):
        return
    locked = authority.locked or []
    align(authority, currency)
    issuer = await living_entity(ctx.session, currency.issuer_entity_id)
    if "effective_rate" not in locked:
        authority.effective_rate = authority.rate
    if "reserves" not in locked:
        authority.reserves += ctx.rules.monetary.reserve_gain
    bent = await bend(ctx, authority, issuer, tally)
    await move_rate(ctx, authority, currency, tally)
    if authority.aim in PRINTING_AIMS:
        await print_for_state(ctx, authority, currency, issuer, bent=bent, tally=tally)
    if authority.aim is MonetaryAim.PEG:
        await defend_peg(ctx, authority, currency, issuer, tally)
    ctx.session.add(
        MonetaryRateRow(authority_id=authority.id, epoch=ctx.epoch, rate=authority.rate, aim=authority.aim, supply=currency.supply, trust=currency.trust)
    )
