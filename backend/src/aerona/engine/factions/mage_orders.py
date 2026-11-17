from dataclasses import dataclass
from itertools import pairwise

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
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import OrderLaw, TribunalVerdict
from aerona.engine.arcana.vis import give_vis, site_form
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.factions.order_laws import keep_law, outer_dealers
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_bounded, stat_or
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.services.community_relations import change_relation
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
    defiant: int = 0
    feuds: int = 0


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
    if law.law is OrderLaw.NO_OUTER_DEALINGS:
        dealers = await outer_dealers(ctx, members)
        return dealers[0] if dealers else None
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
    await record(
        ctx, "order.tribunal", roles={IncidentRole.SUBJECT: order.id, IncidentRole.ACCUSED: accused.id}, facts={"verdict_words": str(VERDICT_WORDS[verdict])}
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


async def contest_bans(ctx: TickContext, order: EntityRow, profile: FactionProfileRow, laws: LawBook, tally: OrderTally) -> None:
    table = ctx.rules.magical_orders
    realm = await realm_of_community(ctx.session, profile.home_entity_id) if profile.home_entity_id is not None else None
    if realm is None or laws.in_force(realm, LawKind.MAGIC_BAN) is None:
        return
    if "reputation" not in profile.locked:
        profile.reputation = clamp_int(profile.reputation - table.rivalry, 0, PERCENT)
    if profile.outlawed or "outlawed" in profile.locked or profile.reputation > table.defiance_at or held(realm):
        return
    profile.outlawed = True
    await change_relation(ctx, realm, order.id, -table.feud_loss, MemoryKind.BETRAYED_ME, note="defied the ban on magic")
    tally.defiant += 1
    await record(ctx, "order.outlawed", roles={IncidentRole.SUBJECT: [order.id, realm]})


async def rival_orders(ctx: TickContext, found: list[tuple[EntityRow, FactionProfileRow]], tally: OrderTally) -> None:
    table = ctx.rules.magical_orders
    by_home: dict[int, list[tuple[EntityRow, FactionProfileRow]]] = {}
    for order, profile in found:
        if profile.home_entity_id is not None and not held(order.id):
            by_home.setdefault(profile.home_entity_id, []).append((order, profile))
    for home, rivals in sorted(by_home.items()):
        for (first, one), (second, other) in pairwise(rivals):
            if not ctx.rng(f"order.feud.{first.id}.{second.id}.{ctx.epoch}").chance(table.feud_pct):
                continue
            loser = one if stat_or(first, "strength", 0) < stat_or(second, "strength", 0) else other
            if "reputation" not in loser.locked:
                loser.reputation = clamp_int(loser.reputation - table.feud_loss, 0, PERCENT)
            await change_relation(ctx, first.id, second.id, -table.feud_loss, MemoryKind.BETRAYED_ME, note="a war among mages")
            tally.feuds += 1
            await record(
                ctx, "order.feud", roles={IncidentRole.SUBJECT: [first.id, second.id, home]}, facts={"first": str(first.name), "second": str(second.name)}
            )


async def keep_orders(ctx: TickContext, tally: OrderTally) -> None:
    statutes = await LawBook.load(ctx.session)
    for order, profile in await orders(ctx):
        members = list(await ctx.session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == order.id)))
        for law in await found_laws(ctx, order, tally):
            await keep_law(ctx, profile, law, members)
            accused = await accused_of(ctx, order, law, members)
            if accused is not None:
                await try_member(ctx, order, law, accused, tally)
        covenant = await covenant_of(ctx, order, profile, tally)
        if covenant is not None:
            await draw_vis(ctx, order, covenant, tally)
        await contest_bans(ctx, order, profile, statutes, tally)
    await rival_orders(ctx, await orders(ctx), tally)
    await ctx.session.flush()
