from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.competition import MarketStructureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.governance import OrgMergerRow
from aerona.db.write_guard import held
from aerona.domain.enums.competition import CompetitionClause, MarketForm
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.competition.clauses import clause_strength
from aerona.engine.context import TickContext
from aerona.engine.factions.offshoots import found_offshoot
from aerona.engine.recording.record import record

MONOPOLY_LOCK = "monopoly"


async def shared_markets(ctx: TickContext, first: int, second: int) -> list[tuple[MarketStructureRow, int]]:
    found: list[tuple[MarketStructureRow, int]] = []
    for structure in await ctx.session.scalars(select(MarketStructureRow).order_by(MarketStructureRow.id)):
        sellers = structure.sellers or {}
        if str(first) in sellers and str(second) in sellers:
            found.append((structure, sellers[str(first)] + sellers[str(second)]))
    return found


async def merger_barred(ctx: TickContext, merger: OrgMergerRow) -> str | None:
    for structure, joined in await shared_markets(ctx, merger.acquirer_node_id, merger.target_node_id):
        review = await clause_strength(ctx, structure.market_entity_id, CompetitionClause.MERGER_REVIEW)
        if review and joined > PERCENT - review:
            return f"together they would hold {joined} percent of the market, beyond what the law allows"
    return None


async def breakable(ctx: TickContext, structure: MarketStructureRow) -> int | None:
    if structure.form is not MarketForm.ONE_SELLER or not structure.sellers:
        return None
    holder_id = int(max(structure.sellers, key=lambda node: (structure.sellers[node], node)))
    holder = await ctx.session.get(EntityRow, holder_id)
    profile = await ctx.session.get(FactionProfileRow, holder_id)
    if holder is None or profile is None or held(holder.id) or held(structure.market_entity_id):
        return None
    return holder_id


async def split_holder(ctx: TickContext, structure: MarketStructureRow) -> EntityRow | None:
    holder_id = await breakable(ctx, structure)
    holder = await ctx.session.get(EntityRow, holder_id) if holder_id is not None else None
    profile = await ctx.session.get(FactionProfileRow, holder_id) if holder_id is not None else None
    if holder is None or profile is None:
        return None
    members = list(
        await ctx.session.scalars(
            select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == holder.id).order_by(FactionMembershipRow.mortal_entity_id)
        )
    )
    child = await found_offshoot(
        ctx,
        holder,
        profile,
        name=f"{holder.name.removeprefix('the ')} of the second charter",
        body=f"Made when the hold of {holder.name} on its market was broken.",
        share_pct=PERCENT // 2,
        leaving=[member for member in members[len(members) // 2 :] if not held(member.mortal_entity_id)],
    )
    if MONOPOLY_LOCK not in (profile.locked or []):
        profile.monopoly = None
    await record(
        ctx,
        "market.monopoly_broken",
        roles={IncidentRole.PREDECESSOR: holder.id, IncidentRole.PRODUCT: child.id, IncidentRole.PLACE: structure.market_entity_id},
        facts={"commodity": structure.commodity},
        place=structure.market_entity_id,
    )
    return child


async def break_monopoly(ctx: TickContext, structure: MarketStructureRow) -> EntityRow | None:
    if await breakable(ctx, structure) is None:
        return None
    strength = await clause_strength(ctx, structure.market_entity_id, CompetitionClause.MONOPOLY_BREAK)
    if not strength or not ctx.rng(f"competition.break.{structure.id}.{ctx.epoch}").chance(strength):
        return None
    return await split_holder(ctx, structure)
