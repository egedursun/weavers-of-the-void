from sqlalchemy import select

from aerona.catalog.finance import OWED_LOANS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.governance import OrgGovernanceRow, OrgMergerRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.governance import OPEN_MERGER_STAGES, MergerKind, MergerStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.competition.law import merger_barred
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, give_coin, take_coin
from aerona.engine.factions.book import move_member
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.records import retire_in
from aerona.engine.recording.record import record
from aerona.engine.securities.holdings import holds_majority

STAGE_LOCK = "stage"
FRIENDLY = frozenset({MergerKind.MERGER, MergerKind.FRIENDLY_ACQUISITION, MergerKind.BUYOUT, MergerKind.ABSORPTION_BY_POLITY})


async def worth(ctx: TickContext, org: EntityRow) -> int:
    return await coin_of(ctx.session, ctx.rules, org)


async def asking_price(ctx: TickContext, target: EntityRow, kind: MergerKind) -> int:
    base = await worth(ctx, target)
    premium = ctx.rules.governance.takeover_premium_pct if kind is MergerKind.HOSTILE_TAKEOVER else 0
    return round_half_up(base * (PERCENT + premium) / PERCENT)


async def open_bid(ctx: TickContext, acquirer_id: int, target: EntityRow, kind: MergerKind, price: int | None) -> OrgMergerRow:
    merger = OrgMergerRow(
        acquirer_node_id=acquirer_id,
        target_node_id=target.id,
        kind=kind,
        price=price if price is not None else await asking_price(ctx, target, kind),
        share_offer_pct=0,
        stage=MergerStage.BID,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(merger)
    await ctx.session.flush()
    await record(
        ctx,
        "org.takeover_bid",
        roles={IncidentRole.ACTOR: acquirer_id, IncidentRole.TARGET: target.id},
        facts={"kind": kind, "price": merger.price},
    )
    return merger


async def open_bids(ctx: TickContext) -> list[OrgMergerRow]:
    return list(await ctx.session.scalars(select(OrgMergerRow).where(OrgMergerRow.stage.in_(sorted(OPEN_MERGER_STAGES))).order_by(OrgMergerRow.id)))


async def friendly_buyer(ctx: TickContext, merger: OrgMergerRow, target: EntityRow) -> EntityRow | None:
    profile = await ctx.session.get(FactionProfileRow, target.id)
    if profile is None:
        return None
    rivals = await ctx.session.scalars(
        select(EntityRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(
            FactionProfileRow.kind == profile.kind,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id.not_in([target.id, merger.acquirer_node_id]),
        )
        .order_by(EntityRow.id)
    )
    able = [rival for rival in rivals if not held(rival.id) and await worth(ctx, rival) >= merger.price]
    return able[0] if able else None


async def resist(ctx: TickContext, merger: OrgMergerRow, target: EntityRow) -> bool:
    body = await ctx.session.get(OrgGovernanceRow, target.id)
    trust = body.trust if body is not None else PERCENT // 2
    if not ctx.rng(f"governance.resist.{merger.id}.{ctx.epoch}").chance(trust):
        return False
    buyer = await friendly_buyer(ctx, merger, target)
    merger.friendly_buyer_node_id = buyer.id if buyer is not None else None
    merger.stage = MergerStage.RESISTED
    how = "a friendly buyer" if buyer is not None else "poison terms"
    await record(
        ctx,
        "org.takeover_resisted",
        roles={IncidentRole.TARGET: target.id, IncidentRole.ACTOR: merger.acquirer_node_id} | ({IncidentRole.ALLY: buyer.id} if buyer is not None else {}),
        facts={"how": how},
    )
    return True


async def answer_resistance(ctx: TickContext, merger: OrgMergerRow, target: EntityRow, acquirer: EntityRow) -> None:
    if merger.friendly_buyer_node_id is not None:
        buyer = await ctx.session.get(EntityRow, merger.friendly_buyer_node_id)
        merger.stage, merger.ended_epoch = MergerStage.WITHDRAWN, ctx.epoch
        if buyer is not None and buyer.status is EntityStatus.CANON and not held(buyer.id):
            await open_bid(ctx, buyer.id, target, MergerKind.FRIENDLY_ACQUISITION, merger.price)
        return
    raised = round_half_up(merger.price * (PERCENT + ctx.rules.governance.takeover_premium_pct) / PERCENT)
    if await worth(ctx, acquirer) >= raised:
        merger.price, merger.stage = raised, MergerStage.AGREED
    else:
        merger.stage, merger.ended_epoch = MergerStage.WITHDRAWN, ctx.epoch


async def pay_owners(ctx: TickContext, target: EntityRow, amount: int) -> None:
    shares = list(
        await ctx.session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == target.id).order_by(CompanyShareRow.holder_node_id))
    )
    whole = sum(share.share for share in shares)
    if whole <= 0:
        await give_coin(ctx.session, ctx.rules, target, amount)
        return
    for share in shares:
        holder = await ctx.session.get(EntityRow, share.holder_node_id)
        if holder is not None and not held(holder.id):
            await give_coin(ctx.session, ctx.rules, holder, round_half_up(amount * share.share / whole))


async def join(ctx: TickContext, merger: OrgMergerRow, target: EntityRow, acquirer: EntityRow) -> None:
    into = await ctx.session.get(FactionProfileRow, acquirer.id)
    source = await ctx.session.get(FactionProfileRow, target.id)
    if into is not None:
        for member in list(await ctx.session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == target.id))):
            if await ctx.session.get(FactionMembershipRow, (acquirer.id, member.mortal_entity_id)) is None:
                await move_member(ctx.session, member, acquirer.id, ctx.epoch)
            else:
                await ctx.session.delete(member)
        if source is not None:
            into.treasury += source.treasury
            source.treasury = 0
    elif source is not None:
        await give_coin(ctx.session, ctx.rules, acquirer, source.treasury)
        source.treasury = 0
    for loan in await ctx.session.scalars(select(LoanRow).where(LoanRow.borrower_entity_id == target.id, LoanRow.status.in_(OWED_LOANS)).order_by(LoanRow.id)):
        if not loan.held:
            loan.borrower_entity_id = acquirer.id


async def close_merger(ctx: TickContext, merger: OrgMergerRow, target: EntityRow, acquirer: EntityRow) -> bool:
    if not await take_coin(ctx.session, ctx.rules, acquirer, merger.price):
        merger.stage, merger.ended_epoch = MergerStage.WITHDRAWN, ctx.epoch
        return False
    await pay_owners(ctx, target, merger.price)
    await join(ctx, merger, target, acquirer)
    merger.stage, merger.ended_epoch = MergerStage.CLOSED, ctx.epoch
    await ctx.session.flush()
    await retire_in(ctx, target, f"it was joined into {acquirer.name}", close_bonds=True)
    await record(
        ctx,
        "org.merged",
        roles={IncidentRole.PREDECESSOR: target.id, IncidentRole.SUCCESSOR: acquirer.id},
        facts={"kind": merger.kind, "price": merger.price},
    )
    return True


async def answer_bid(ctx: TickContext, merger: OrgMergerRow, target: EntityRow) -> str:
    if await holds_majority(ctx.session, target.id, merger.acquirer_node_id):
        merger.stage = MergerStage.AGREED
        return "agreed"
    if merger.kind is MergerKind.HOSTILE_TAKEOVER and await resist(ctx, merger, target):
        return "resisted"
    if merger.kind in FRIENDLY and merger.price < await worth(ctx, target):
        merger.stage, merger.ended_epoch = MergerStage.WITHDRAWN, ctx.epoch
        return "withdrawn"
    merger.stage = MergerStage.AGREED
    return "agreed"


async def conclude(ctx: TickContext, merger: OrgMergerRow, target: EntityRow, acquirer: EntityRow) -> str:
    if await merger_barred(ctx, merger) is not None:
        merger.stage, merger.ended_epoch = MergerStage.BLOCKED, ctx.epoch
        return "blocked"
    return "closed" if await close_merger(ctx, merger, target, acquirer) else "withdrawn"


async def advance_merger(ctx: TickContext, merger: OrgMergerRow) -> str | None:
    target = await ctx.session.get(EntityRow, merger.target_node_id)
    acquirer = await ctx.session.get(EntityRow, merger.acquirer_node_id)
    if target is None or acquirer is None or held(target.id) or held(acquirer.id) or STAGE_LOCK in (merger.locked or []):
        return None
    if target.status is not EntityStatus.CANON or acquirer.status is not EntityStatus.CANON:
        merger.stage, merger.ended_epoch = MergerStage.WITHDRAWN, ctx.epoch
        return "withdrawn"
    if merger.stage is MergerStage.BID:
        return await answer_bid(ctx, merger, target)
    if merger.stage is MergerStage.RESISTED:
        await answer_resistance(ctx, merger, target, acquirer)
        return merger.stage.value
    return await conclude(ctx, merger, target, acquirer)
