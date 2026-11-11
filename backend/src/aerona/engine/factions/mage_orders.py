from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import OrderLawRow, TribunalRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import OrderLaw, TribunalVerdict
from aerona.engine.arcana.vis import give_vis, site_form
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.notes import note
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_bounded
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.structures.construction import Commission, begin

VERDICT_WORDS = {
    TribunalVerdict.ACQUITTED: "acquitted",
    TribunalVerdict.FINED: "fined",
    TribunalVerdict.EXPELLED: "cast out of the order",
    TribunalVerdict.STRIPPED: "stripped of rank",
}


@dataclass
class OrderTally:
    laws: int = 0
    trials: int = 0
    covenants: int = 0
    vis: int = 0


async def orders(ctx: TickContext) -> list[tuple[EntityRow, FactionProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind == FactionKind.MAGE_ORDER, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows.all() if not held(entity.id)]


async def found_laws(ctx: TickContext, order: EntityRow, tally: OrderTally) -> list[OrderLawRow]:
    laws = list(await ctx.session.scalars(select(OrderLawRow).where(OrderLawRow.faction_entity_id == order.id).order_by(OrderLawRow.law)))
    if laws:
        return laws
    chosen = ctx.rng(f"order_laws.{order.id}").sample(list(OrderLaw), ctx.rules.magical_orders.founding_laws)
    laws = [OrderLawRow(faction_entity_id=order.id, law=law, strength=PERCENT * 6 // 10, locked=[]) for law in sorted(chosen)]
    ctx.session.add_all(laws)
    tally.laws += len(laws)
    await ctx.session.flush()
    return laws


async def killers_of_kin(ctx: TickContext, order_id: int, members: set[int]) -> list[int]:
    rows = await ctx.session.scalars(
        select(BondRow.source_node_id).where(
            BondRow.kind == BondKind.KILLED,
            BondRow.source_node_id.in_(members),
            BondRow.target_node_id.in_(members),
            BondRow.epoch >= ctx.epoch - 1,
        )
    )
    return sorted(set(rows))


async def accused_of(ctx: TickContext, order: EntityRow, law: OrderLawRow, members: list[FactionMembershipRow]) -> int | None:
    ids = {member.mortal_entity_id for member in members}
    if law.law is OrderLaw.SPARE_MEMBERS:
        killers = await killers_of_kin(ctx, order.id, ids)
        return killers[0] if killers else None
    common = [member.mortal_entity_id for member in members if member.rank is not FactionRank.LEADER]
    if not common or not ctx.rng(f"order_breach.{order.id}.{law.law.value}").chance(ctx.rules.magical_orders.violation_pct):
        return None
    return ctx.rng(f"order_accused.{order.id}.{law.law.value}").pick(sorted(common))


async def try_member(ctx: TickContext, order: EntityRow, law: OrderLawRow, accused_id: int, tally: OrderTally) -> None:
    table = ctx.rules.magical_orders
    accused = await ctx.session.get(EntityRow, accused_id)
    if accused is None or held(accused_id):
        return
    verdict = TribunalVerdict.EXPELLED if law.strength >= table.expel_strength else TribunalVerdict.FINED
    fine = 0
    if verdict is TribunalVerdict.FINED:
        fine = table.fine if await take_coin(ctx.session, ctx.rules, accused, table.fine) else 0
        if not fine:
            verdict = TribunalVerdict.STRIPPED
    membership = await ctx.session.get(FactionMembershipRow, (order.id, accused_id))
    if membership is not None and verdict is TribunalVerdict.EXPELLED:
        await ctx.session.delete(membership)
    elif membership is not None and verdict is TribunalVerdict.STRIPPED and "rank" not in membership.locked:
        membership.rank = FactionRank.NOVICE
    ctx.session.add(TribunalRow(faction_entity_id=order.id, accused_entity_id=accused_id, law=law.law, verdict=verdict, fine=fine, epoch=ctx.epoch))
    tally.trials += 1
    await note(
        ctx,
        f"The tribunal of {order.name} judged {accused.name} for breaking its law and {VERDICT_WORDS[verdict]} them.",
        key="order.tribunal",
        ids=[order.id, accused.id],
    )


async def covenant_of(ctx: TickContext, order: EntityRow, profile: FactionProfileRow, tally: OrderTally) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind == StructureKind.COVENANT, StructureProfileRow.builder_entity_id == order.id, EntityRow.status == EntityStatus.CANON)
        .limit(1)
    )
    if found is not None or profile.home_entity_id is None:
        return found
    home = await ctx.session.get(EntityRow, profile.home_entity_id)
    if home is None or home.entity_type is not EntityType.SETTLEMENT:
        return None
    covenant, _ = await begin(ctx, Commission(site=home, kind=StructureKind.COVENANT, builder=order, name=f"the covenant of {order.name}"))
    tally.covenants += 1
    return covenant


async def draw_vis(ctx: TickContext, order: EntityRow, covenant: EntityRow, tally: OrderTally) -> None:
    table = ctx.rules.magical_orders
    for site in await ctx.session.scalars(select(MagicSiteRow).where(MagicSiteRow.holder_node_id == order.id).order_by(MagicSiteRow.id)):
        tally.vis += await give_vis(ctx, order.id, site_form(site), table.vis_per_site)
    town = await ctx.session.get(EntityRow, covenant.location_id) if covenant.location_id is not None else None
    people = await people_of(ctx.session, town) if town is not None else None
    if people is not None and not held(people.id):
        shift_bounded(ctx.rules, people, "magic", table.knowledge_gain)


async def contest_bans(ctx: TickContext, profile: FactionProfileRow, laws: LawBook) -> None:
    realm = await realm_of_community(ctx.session, profile.home_entity_id) if profile.home_entity_id is not None else None
    if realm is not None and laws.in_force(realm, LawKind.MAGIC_BAN) is not None and "reputation" not in profile.locked:
        profile.reputation = clamp_int(profile.reputation - ctx.rules.magical_orders.rivalry, 0, PERCENT)


async def keep_orders(ctx: TickContext, tally: OrderTally) -> None:
    statutes = await LawBook.load(ctx.session)
    for order, profile in await orders(ctx):
        members = list(await ctx.session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == order.id)))
        for law in await found_laws(ctx, order, tally):
            accused = await accused_of(ctx, order, law, members)
            if accused is not None:
                await try_member(ctx, order, law, accused, tally)
        covenant = await covenant_of(ctx, order, profile, tally)
        if covenant is not None:
            await draw_vis(ctx, order, covenant, tally)
        await contest_bans(ctx, profile, statutes)
    await ctx.session.flush()
