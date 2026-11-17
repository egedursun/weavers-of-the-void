from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import BookContentRow, HolderLevelRow, IdeologyAdherentRow
from aerona.db.tables.discovery import BannedWorkRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.lore.research_depth import trade_partners
from aerona.engine.lore.theories import faiths_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import move_stat, stat
from aerona.engine.recording.record import record as record_incident


async def holders_of(session: AsyncSession, work: EntityRow) -> set[int]:
    if work.entity_type is EntityType.IDEOLOGY:
        return set(await session.scalars(select(IdeologyAdherentRow.adherent_entity_id).where(IdeologyAdherentRow.ideology_entity_id == work.id)))
    owners = await session.scalars(
        select(BondRow.source_node_id).where(BondRow.target_node_id == work.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    )
    found: set[int] = set()
    for owner_id in owners:
        owner = await session.get(EntityRow, owner_id)
        if owner is not None:
            found.add(owner.location_id if owner.entity_type is EntityType.MORTAL and owner.location_id is not None else owner.id)
    return found


async def deliver(ctx: TickContext, work: EntityRow, buyer: EntityRow) -> None:
    if work.entity_type is EntityType.IDEOLOGY:
        if await ctx.session.get(IdeologyAdherentRow, (work.id, buyer.id)) is None:
            ctx.session.add(
                IdeologyAdherentRow(ideology_entity_id=work.id, adherent_entity_id=buyer.id, strength=PERCENT // 10, state=False, since_epoch=ctx.epoch)
            )
        return
    pages = await ctx.session.execute(select(BookContentRow.knowledge_entity_id, BookContentRow.fidelity).where(BookContentRow.book_entity_id == work.id))
    for knowledge_id, fidelity in pages.all():
        knowledge = await ctx.session.get(EntityRow, knowledge_id)
        level = await ctx.session.get(HolderLevelRow, (buyer.id, knowledge.knowledge_branch)) if knowledge is not None and knowledge.knowledge_branch else None
        if level is not None and "progress" not in level.locked:
            level.progress = clamp_int(level.progress + round_half_up(ctx.rules.research.book_progress * fidelity / PERCENT), 0, PERCENT)


async def stir_heresy(ctx: TickContext, buyer: EntityRow) -> int:
    loss = ctx.rules.discovery.heresy_pct
    shaken = 0
    for cult in await faiths_of(ctx.session, buyer):
        doctrine = await ctx.session.get(CultDoctrineRow, cult)
        if doctrine is not None and "orthodoxy" not in doctrine.locked and not held(cult):
            doctrine.orthodoxy = clamp_int(doctrine.orthodoxy - loss, 0, PERCENT)
            shaken += 1
    return shaken


async def smuggle(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.discovery
    smuggled = shaken = 0
    for ban in list(await ctx.session.scalars(select(BannedWorkRow).order_by(BannedWorkRow.polity_entity_id, BannedWorkRow.work_entity_id))):
        work = await ctx.session.get(EntityRow, ban.work_entity_id)
        if work is None or work.status is not EntityStatus.CANON or held(ban.polity_entity_id):
            continue
        members = set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == ban.polity_entity_id)))
        abroad = await holders_of(ctx.session, work) - members
        for member_id in sorted(members):
            buyer = await ctx.session.get(EntityRow, member_id)
            sellers = sorted((await trade_partners(ctx.session, member_id)) & abroad)
            if buyer is None or not sellers or held(member_id):
                continue
            if not ctx.rng(f"smuggle.{work.id}.{member_id}.{ctx.epoch}").chance(table.ban_reading_pct):
                continue
            seller = await ctx.session.get(EntityRow, sellers[0])
            price = table.black_market_price
            if seller is None or held(seller.id) or (stat(buyer, "wealth") or 0) < price:
                continue
            move_stat(buyer, seller, "wealth", price)
            await deliver(ctx, work, buyer)
            shaken += await stir_heresy(ctx, buyer)
            smuggled += 1
            await record_incident(
                ctx,
                "discovery.smuggled",
                roles={IncidentRole.BUYER: buyer.id, IncidentRole.SELLER: seller.id, IncidentRole.TARGET: work.id},
                facts={"price": price},
                place=buyer.id,
                terms=[Term("rules.discovery.black_market_price", price)],
            )
    return {"works_smuggled": smuggled, "faiths_shaken": shaken}
