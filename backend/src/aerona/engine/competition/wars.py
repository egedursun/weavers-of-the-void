from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.commerce import SupplyTierRow
from aerona.db.tables.competition import MarketStructureRow, PriceWarRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.write_guard import held
from aerona.domain.enums.competition import MarketForm, PriceWarOutcome
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.governance import OrgStrategy
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.governance.insolvency import InsolvencyTally, file_case
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.recording.record import record

OUTCOME_LOCK = "outcome"
AGGRESSIVE = frozenset({OrgStrategy.GROW, OrgStrategy.EXPAND_ABROAD, OrgStrategy.INTEGRATE_DOWN})


async def ongoing_wars(ctx: TickContext) -> list[PriceWarRow]:
    return list(await ctx.session.scalars(select(PriceWarRow).where(PriceWarRow.outcome == PriceWarOutcome.ONGOING).order_by(PriceWarRow.id)))


async def war_over(ctx: TickContext, market_id: int, commodity: CommodityKind) -> PriceWarRow | None:
    return await ctx.session.scalar(
        select(PriceWarRow)
        .where(PriceWarRow.market_entity_id == market_id, PriceWarRow.commodity == commodity, PriceWarRow.outcome == PriceWarOutcome.ONGOING)
        .limit(1)
    )


async def start_war(ctx: TickContext, aggressor: int, market_id: int, commodity: CommodityKind, *, cut: int, targets: list[int]) -> PriceWarRow:
    war = PriceWarRow(
        aggressor_node_id=aggressor,
        targets=sorted(set(targets) - {aggressor}),
        market_entity_id=market_id,
        commodity=commodity,
        cut_pct=cut,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(war)
    await ctx.session.flush()
    await record(
        ctx,
        "market.price_war_begun",
        roles={IncidentRole.ACTOR: aggressor, IncidentRole.TARGET: war.targets, IncidentRole.PLACE: market_id},
        facts={"commodity": commodity, "cut": cut},
        place=market_id,
    )
    return war


async def maybe_start(ctx: TickContext, structure: MarketStructureRow) -> PriceWarRow | None:
    if structure.form is not MarketForm.FEW_SELLERS or await war_over(ctx, structure.market_entity_id, structure.commodity) is not None:
        return None
    ranked = sorted(((int(node), share) for node, share in (structure.sellers or {}).items()), key=lambda item: (-item[1], item[0]))
    if len(ranked) < 2:
        return None
    leader = ranked[0][0]
    body = await ctx.session.get(OrgGovernanceRow, leader)
    if body is None or body.strategy not in AGGRESSIVE or held(leader):
        return None
    if not ctx.rng(f"competition.war.{structure.id}.{ctx.epoch}").chance(ctx.rules.competition.price_war_chance_pct):
        return None
    return await start_war(
        ctx, leader, structure.market_entity_id, structure.commodity, cut=ctx.rules.competition.default_cut_pct, targets=[node for node, _ in ranked[1:]]
    )


async def bleed(ctx: TickContext, payer: EntityRow, amount: int) -> bool:
    return await take_coin(ctx.session, ctx.rules, payer, amount)


async def take_shares(ctx: TickContext, war: PriceWarRow, beaten: list[int]) -> None:
    for tier in await ctx.session.scalars(
        select(SupplyTierRow).where(SupplyTierRow.market_entity_id == war.market_entity_id, SupplyTierRow.commodity == war.commodity).order_by(SupplyTierRow.id)
    ):
        if tier.holder_node_id in beaten and "holder_node_id" not in (tier.locked or []):
            tier.holder_node_id = war.aggressor_node_id


async def close_war(ctx: TickContext, war: PriceWarRow, outcome: PriceWarOutcome) -> None:
    war.outcome, war.ended_epoch = outcome, ctx.epoch


async def tend_war(ctx: TickContext, war: PriceWarRow, tally: InsolvencyTally) -> str | None:
    table = ctx.rules.competition
    aggressor = await ctx.session.get(EntityRow, war.aggressor_node_id)
    if aggressor is None or held(aggressor.id) or OUTCOME_LOCK in (war.locked or []) or any(held(node) for node in war.targets or []):
        return None
    cost = war.cut_pct * table.war_cost_per_cut
    if aggressor.status is not EntityStatus.CANON or not await bleed(ctx, aggressor, cost):
        await close_war(ctx, war, PriceWarOutcome.LOST)
        return "lost"
    war.losses += cost
    beaten: list[int] = []
    for node in war.targets or []:
        target = await ctx.session.get(EntityRow, node)
        if target is None or target.status is not EntityStatus.CANON:
            beaten.append(node)
            continue
        if not await bleed(ctx, target, round_half_up(cost * table.war_target_cost_pct / PERCENT)):
            beaten.append(node)
            await file_case(ctx, target, None, tally)
    standing = [node for node in war.targets or [] if node not in beaten]
    if not standing:
        await take_shares(ctx, war, beaten)
        await close_war(ctx, war, PriceWarOutcome.WON)
        await record(
            ctx,
            "market.price_war_won",
            roles={IncidentRole.ACTOR: aggressor.id, IncidentRole.VICTIM: beaten or war.targets, IncidentRole.PLACE: war.market_entity_id},
            facts={"commodity": war.commodity, "losses": war.losses},
            place=war.market_entity_id,
        )
        return "won"
    if ctx.epoch - war.started_epoch >= table.war_max_epochs:
        await close_war(ctx, war, PriceWarOutcome.CALLED_OFF)
        return "called_off"
    return None


async def tend_wars(ctx: TickContext, structures: list[MarketStructureRow], tally: InsolvencyTally) -> dict[str, int]:
    counts = {"begun": 0, "won": 0, "lost": 0, "called_off": 0}
    for structure in structures:
        counts["begun"] += 1 if await maybe_start(ctx, structure) is not None else 0
    for war in await ongoing_wars(ctx):
        outcome = await tend_war(ctx, war, tally)
        if outcome is not None:
            counts[outcome] += 1
    return counts
