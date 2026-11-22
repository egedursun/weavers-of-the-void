from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import FACTION_KIND_TRAITS, having
from aerona.catalog.renown import ACT_RENOWN
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.renown import DeedRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.honours import HonourPrivilege
from aerona.domain.enums.life_traits import FactionKindTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points, take_coin
from aerona.engine.interconnect.guards import blocked
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.records import heir_of
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import members_of, ruler_of_realm

P = HonourPrivilege
ORDER_KINDS = having(FACTION_KIND_TRAITS, FactionKindTrait.ORDERS)


@dataclass
class HonourTally:
    founded: int = 0
    conferred: int = 0
    sold: int = 0
    revoked: int = 0
    inherited: int = 0
    pensions: int = 0


def privileges_of(kind: HonourKindRow) -> set[HonourPrivilege]:
    return {P(value) for value in kind.privileges or [] if value in P.__members__.values()}


async def head_of(session: AsyncSession, conferrer_id: int) -> int | None:
    conferrer = await session.get(EntityRow, conferrer_id)
    if conferrer is not None and conferrer.entity_type is EntityType.POLITY:
        return await ruler_of_realm(session, conferrer_id)
    return await session.scalar(select(OrgGovernanceRow.head_node_id).where(OrgGovernanceRow.org_node_id == conferrer_id))


async def places_of(session: AsyncSession, conferrer_id: int) -> list[int]:
    conferrer = await session.get(EntityRow, conferrer_id)
    if conferrer is None:
        return []
    found = await members_of(session, conferrer_id) if conferrer.entity_type is EntityType.POLITY else []
    return sorted({*found, *([conferrer.location_id] if conferrer.location_id is not None else [])})


async def holders_of(session: AsyncSession, kind_id: int) -> list[HonourHeldRow]:
    live = (HonourHeldRow.kind_id == kind_id, HonourHeldRow.revoked_epoch.is_(None))
    return list(await session.scalars(select(HonourHeldRow).where(*live).order_by(HonourHeldRow.id)))


async def holds(session: AsyncSession, holder_id: int, kind_id: int) -> bool:
    return any(row.holder_node_id == holder_id for row in await holders_of(session, kind_id))


async def grant_privileges(ctx: TickContext, kind: HonourKindRow, holder: EntityRow) -> None:
    granted = privileges_of(kind)
    if P.LAND in granted:
        await shift_points(ctx.session, holder, ctx.rules.honours.land_points)
    if P.SEAT in granted and not blocked(holder.id, "importance"):
        holder.importance = (holder.importance or 0) + 1
    if P.TITLE in granted and holder.title is None and not blocked(holder.id, "title"):
        holder.title = kind.name


async def confer(
    ctx: TickContext, kind: HonourKindRow, holder: EntityRow, *, tally: HonourTally, by: int | None, deed: int | None = None, sold: bool = False
) -> HonourHeldRow:
    table = ctx.rules.honours
    given = {"conferred_by_node_id": by, "deed_incident_id": deed, "epoch": ctx.epoch, "sold": sold}
    row = HonourHeldRow(holder_node_id=holder.id, kind_id=kind.id, locked=[], **given)
    ctx.session.add(row)
    await ctx.session.flush()
    gain = table.prestige_per_rank * kind.rank * kind.worth / PERCENT + (kind.rank if P.PRECEDENCE in privileges_of(kind) else 0)
    await shift_standing(ctx.session, holder, "renown", gain, ctx.epoch)
    if holder.entity_type is EntityType.MORTAL:
        loyalty = table.loyalty_gain
        await remember(
            ctx.session, ctx.rules, holder_id=holder.id, subject_id=kind.conferrer_node_id, kind=MemoryKind.GOODWILL, magnitude=loyalty, epoch=ctx.epoch
        )
    await grant_privileges(ctx, kind, holder)
    roles = {IncidentRole.ACTOR: kind.conferrer_node_id, IncidentRole.SUBJECT: holder.id}
    await record(ctx, "honour.conferred", roles=roles, facts={"honour": kind.name, "rank": kind.rank, "worth": kind.worth})
    if sold:
        if "worth" not in kind.locked:
            kind.worth = max(0, kind.worth - table.sale_worth_loss_pct)
        await record(ctx, "honour.sold", roles=roles, facts={"honour": kind.name, "worth": kind.worth})
        tally.sold += 1
    tally.conferred += 1
    return row


async def revoke(ctx: TickContext, row: HonourHeldRow, tally: HonourTally) -> None:
    kind = await ctx.session.get(HonourKindRow, row.kind_id)
    holder = await ctx.session.get(EntityRow, row.holder_node_id)
    row.revoked_epoch = ctx.epoch
    if holder is not None:
        await shift_standing(ctx.session, holder, "infamy", ctx.rules.honours.revoke_infamy, ctx.epoch)
        if kind is not None and holder.title == kind.name and not blocked(holder.id, "title"):
            holder.title = None
    roles = {IncidentRole.ACTOR: kind.conferrer_node_id if kind is not None else None, IncidentRole.SUBJECT: row.holder_node_id}
    await record(ctx, "honour.revoked", roles=roles, facts={"honour": kind.name if kind is not None else "an honour"})
    tally.revoked += 1


async def immune(session: AsyncSession, holder_id: int, polity_id: int | None) -> bool:
    if polity_id is None:
        return False
    for row in await session.scalars(select(HonourHeldRow).where(HonourHeldRow.holder_node_id == holder_id, HonourHeldRow.revoked_epoch.is_(None))):
        kind = await session.get(HonourKindRow, row.kind_id)
        if kind is not None and kind.conferrer_node_id == polity_id and P.IMMUNITY in privileges_of(kind):
            return True
    return False


async def worthy_deeds(ctx: TickContext, kind: HonourKindRow, places: list[int]) -> list[DeedRow]:
    table = ctx.rules.honours
    floor = table.deed_floor + table.rank_step * (kind.rank - 1)
    here = DeedRow.place_node_id.in_(places)
    query = select(DeedRow).where(DeedRow.epoch == ctx.epoch, DeedRow.magnitude >= floor, here).order_by(DeedRow.magnitude.desc(), DeedRow.id)
    return [deed for deed in await ctx.session.scalars(query) if praised(deed)]


def praised(deed: DeedRow) -> bool:
    if deed.act is None:
        return deed.axis is not ReputationAxis.TROUBLEMAKER
    spec = ACT_RENOWN[deed.act]
    return deed.axis is spec.approved and spec.approved is not spec.condemned


async def conferrers(session: AsyncSession) -> list[EntityRow]:
    realms = select(PolityProfileRow.polity_entity_id)
    orders = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind.in_(sorted(ORDER_KINDS)))
    faiths = select(EntityRow.id).where(EntityRow.entity_type == EntityType.CULT)
    query = select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(realms.union(orders, faiths))).order_by(EntityRow.id)
    founded = set(await session.scalars(select(HonourKindRow.conferrer_node_id)))
    return [row for row in await session.scalars(query) if row.id not in founded and not held(row.id)]


async def found_for_deeds(ctx: TickContext, tally: HonourTally) -> None:
    table = ctx.rules.honours
    for conferrer in await conferrers(ctx.session):
        if await head_of(ctx.session, conferrer.id) is None:
            continue
        here = DeedRow.place_node_id.in_(await places_of(ctx.session, conferrer.id))
        query = select(DeedRow).where(DeedRow.epoch == ctx.epoch, DeedRow.magnitude >= table.deed_floor, here).order_by(DeedRow.id)
        if not any(praised(deed) for deed in await ctx.session.scalars(query)):
            continue
        kind = HonourKindRow(
            conferrer_node_id=conferrer.id,
            name=f"the honour of {conferrer.name}",
            rank=1,
            privileges=[P.PRECEDENCE.value],
            founded_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(kind)
        await ctx.session.flush()
        await record(ctx, "honour.founded", roles={IncidentRole.ACTOR: conferrer.id}, facts={"honour": kind.name, "rank": kind.rank})
        tally.founded += 1


async def honour_deeds(ctx: TickContext, kind: HonourKindRow, tally: HonourTally, granted: dict[int, int]) -> None:
    places = await places_of(ctx.session, kind.conferrer_node_id)
    taken = len(await holders_of(ctx.session, kind.id))
    for deed in await worthy_deeds(ctx, kind, places):
        if granted.get(kind.conferrer_node_id, 0) >= ctx.rules.honours.confer_cap or (kind.holder_limit and taken >= kind.holder_limit):
            return
        doer = await ctx.session.get(EntityRow, deed.doer_node_id)
        if doer is None or doer.status is not EntityStatus.CANON or held(doer.id) or await holds(ctx.session, doer.id, kind.id):
            continue
        await confer(ctx, kind, doer, tally=tally, by=await head_of(ctx.session, kind.conferrer_node_id), deed=deed.incident_id)
        granted[kind.conferrer_node_id] = granted.get(kind.conferrer_node_id, 0) + 1
        taken += 1


async def favourites(ctx: TickContext, kind: HonourKindRow, head: int | None) -> list[EntityRow]:
    here = await present_among(ctx.session, await places_of(ctx.session, kind.conferrer_node_id))
    folk = select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    return [
        mortal for mortal in await ctx.session.scalars(folk) if mortal.id != head and not held(mortal.id) and not await holds(ctx.session, mortal.id, kind.id)
    ]


async def sell_to_favourite(ctx: TickContext, kind: HonourKindRow, tally: HonourTally) -> None:
    if not ctx.rng(f"honour.sale.{kind.id}.{ctx.epoch}").chance(ctx.rules.honours.favour_pct):
        return
    head = await head_of(ctx.session, kind.conferrer_node_id)
    candidates = await favourites(ctx, kind, head)
    if not candidates or (kind.holder_limit and len(await holders_of(ctx.session, kind.id)) >= kind.holder_limit):
        return
    wealth = {mortal.id: await points_of(ctx.session, mortal) for mortal in candidates}
    richest = max(candidates, key=lambda mortal: (wealth[mortal.id], -mortal.id))
    await confer(ctx, kind, richest, tally=tally, by=head, sold=True)


async def pay_pensions(ctx: TickContext, kind: HonourKindRow, tally: HonourTally) -> None:
    conferrer = await ctx.session.get(EntityRow, kind.conferrer_node_id)
    if conferrer is None or P.PENSION not in privileges_of(kind):
        return
    amount = ctx.rules.honours.pension_points
    for row in await holders_of(ctx.session, kind.id):
        holder = await ctx.session.get(EntityRow, row.holder_node_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        if await take_coin(ctx.session, ctx.rules, conferrer, amount * max(1, ctx.rules.taxation.wealth_per_treasury)):
            await shift_points(ctx.session, holder, amount)
            tally.pensions += 1


async def pass_on(ctx: TickContext, kind: HonourKindRow, tally: HonourTally) -> None:
    if not kind.hereditary:
        return
    for row in await holders_of(ctx.session, kind.id):
        holder = await ctx.session.get(EntityRow, row.holder_node_id)
        if holder is None or holder.status is EntityStatus.CANON or holder.end_epoch != ctx.epoch:
            continue
        heir = await heir_of(ctx.session, holder)
        if heir is None or held(heir.id) or await holds(ctx.session, heir.id, kind.id):
            continue
        inherited = await confer(ctx, kind, heir, tally=tally, by=row.conferred_by_node_id, deed=row.deed_incident_id)
        inherited.inherited = True
        tally.inherited += 1


async def tend_person_honours(ctx: TickContext) -> HonourTally:
    tally = HonourTally()
    granted: dict[int, int] = {}
    await found_for_deeds(ctx, tally)
    for kind in list(await ctx.session.scalars(select(HonourKindRow).order_by(HonourKindRow.conferrer_node_id, HonourKindRow.rank, HonourKindRow.id))):
        if held(kind.conferrer_node_id):
            continue
        await pass_on(ctx, kind, tally)
        await honour_deeds(ctx, kind, tally, granted)
        await sell_to_favourite(ctx, kind, tally)
        await pay_pensions(ctx, kind, tally)
    return tally
