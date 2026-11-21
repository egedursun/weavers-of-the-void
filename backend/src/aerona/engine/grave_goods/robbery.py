from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, or_, select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.collective.accounts import record as record_account
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.grave_goods.furnish import furnish_grave
from aerona.engine.lore import items
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.nature.seasons import region_of
from aerona.engine.primitives.folk import folk_among, present_among
from aerona.engine.primitives.queries import add_flag, living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

G = GraveGuard
GUARD_STEPS = total(GraveGuard, {G.NONE: 0, G.HIDDEN: 1, G.SEALED: 1, G.GUARDED: 2, G.TRAPPED: 2, G.CURSED: 1, G.WARDED: 2})
CATCHING = frozenset({G.GUARDED, G.TRAPPED})
MAGICAL = frozenset({G.CURSED, G.WARDED})
LEGACY_FIXUP = "grave_goods.legacy"
ITEM_WORTH = 10
CANDIDATES = 12


@dataclass
class GraveTally:
    robbed: int = 0
    caught: int = 0
    cursed: int = 0
    found: int = 0
    legacy: int = 0


async def magic_at(ctx: TickContext, place_id: int | None) -> int:
    region_id = await region_of(ctx.session, place_id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    return stat_or(region, "magic", 0) if region is not None else 0


async def steps_of(ctx: TickContext, row: GraveGoodsRow, place_id: int | None) -> int:
    steps = GUARD_STEPS[row.guard]
    return steps if row.guard not in MAGICAL or await magic_at(ctx, place_id) > 0 else 0


async def rob_chance(ctx: TickContext, row: GraveGoodsRow, place_id: int | None) -> float:
    table = ctx.rules.grave_goods
    worth = row.goods_value + ITEM_WORTH * len(row.items or [])
    base = table.rob_chance_per_value_pct * worth / ITEM_WORTH
    return min(PERCENT, base * (1 - table.guard_cut_pct / PERCENT) ** await steps_of(ctx, row, place_id))


async def robber_at(ctx: TickContext, row: GraveGoodsRow, place_id: int) -> EntityRow | None:
    kin = set(await close_kin_of(ctx.session, row.dead_entity_id))
    here = await present_among(ctx.session, [place_id])
    query = select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    folk = [mortal for mortal in await ctx.session.scalars(query.limit(CANDIDATES)) if mortal.id not in kin and not held(mortal.id)]
    return ctx.rng(f"grave.robber.{row.id}.{ctx.epoch}").pick(folk) if folk else None


async def charge(ctx: TickContext, row: GraveGoodsRow, robber: EntityRow, place_id: int) -> None:
    await shift_standing(ctx.session, robber, "infamy", ctx.rules.grave_goods.grief, ctx.epoch)
    case = CrimeCaseRow(
        settlement_entity_id=place_id,
        crime=CrimeKind.THEFT,
        culprit_entity_id=robber.id,
        accused_entity_id=robber.id,
        stage=CaseStage.INVESTIGATION,
        evidence=ctx.rules.grave_goods.caught_pct,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    roles = {IncidentRole.SUBJECT: row.dead_entity_id, IncidentRole.ACTOR: robber.id, IncidentRole.PLACE: row.grave_entity_id}
    await record(ctx, "dead.robber_caught", roles=roles, facts={"guard": row.guard}, place=place_id)


async def grieve(ctx: TickContext, row: GraveGoodsRow, dead: EntityRow, robber: EntityRow) -> None:
    mourners = await close_kin_of(ctx.session, dead.id)
    people = await people_of(ctx.session, dead)
    for holder in sorted({*mourners, *([people.id] if people is not None else [])}):
        if not held(holder):
            grief = ctx.rules.grave_goods.grief
            await remember(ctx.session, ctx.rules, holder_id=holder, subject_id=robber.id, kind=MemoryKind.DESECRATED_HOLY, magnitude=-grief, epoch=ctx.epoch)
    if row.guard is G.CURSED and ctx.rng(f"grave.curse.{row.id}").chance(ctx.rules.grave_goods.curse_pct * await magic_at(ctx, dead.location_id) / PERCENT):
        await add_flag(ctx.session, robber.id, EntityFlag.CURSED, ctx.epoch)


async def rob(ctx: TickContext, row: GraveGoodsRow, robber: EntityRow | None, tally: GraveTally, *, sure: bool = False) -> bool:
    dead = await ctx.session.get(EntityRow, row.dead_entity_id)
    place = await living_entity(ctx.session, dead.location_id) if dead is not None and dead.location_id is not None else None
    if dead is None or place is None:
        return False
    caught = ctx.rng(f"grave.caught.{row.id}.{ctx.epoch}").chance(ctx.rules.grave_goods.caught_pct)
    if robber is not None and row.guard in CATCHING and caught and not sure:
        await charge(ctx, row, robber, place.id)
        tally.caught += 1
        return False
    taker = robber or place
    for item_id in row.items or []:
        item = await ctx.session.get(EntityRow, item_id)
        if item is not None:
            await items.give(ctx, item, taker.id, ItemDeed.THEFT, f"taken from the grave of {dead.name}")
    await shift_points(ctx.session, taker, row.goods_value)
    worth, taken = row.goods_value, list(row.items or [])
    row.goods_value, row.items, row.robbed_epoch, row.robber_node_id = 0, [], ctx.epoch, robber.id if robber is not None else None
    if robber is not None:
        await grieve(ctx, row, dead, robber)
    roles = {IncidentRole.SUBJECT: dead.id, IncidentRole.ACTOR: row.robber_node_id, IncidentRole.PLACE: row.grave_entity_id, IncidentRole.INSTRUMENT: taken}
    await record(ctx, "dead.grave_robbed", roles=roles, facts={"value": worth, "items": len(taken), "guard": row.guard}, place=place.id)
    tally.robbed += 1
    return True


def untouched() -> ColumnElement[bool]:
    return and_(GraveGoodsRow.robbed_epoch.is_(None), GraveGoodsRow.found_epoch.is_(None))


async def try_graves(ctx: TickContext, tally: GraveTally) -> None:
    rows = list(await ctx.session.scalars(select(GraveGoodsRow).where(untouched()).order_by(GraveGoodsRow.id)))
    tried = 0
    for row in rows:
        dead = await ctx.session.get(EntityRow, row.dead_entity_id)
        place_id = dead.location_id if dead is not None else None
        if place_id is None or held(row.dead_entity_id) or "robbed_epoch" in (row.locked or []) or tried >= ctx.rules.grave_goods.robbers:
            continue
        if not row.items and row.goods_value <= 0:
            continue
        if not ctx.rng(f"grave.rob.{row.id}.{ctx.epoch}").chance(await rob_chance(ctx, row, place_id)):
            continue
        tried += 1
        await rob(ctx, row, await robber_at(ctx, row, place_id), tally)


async def graves_in(ctx: TickContext, place_ids: list[int]) -> list[GraveGoodsRow]:
    tombs = select(StructureProfileRow.structure_entity_id).where(
        StructureProfileRow.kind == StructureKind.TOMB, StructureProfileRow.host_entity_id.in_(place_ids)
    )
    here = or_(GraveGoodsRow.grave_entity_id.in_(place_ids), GraveGoodsRow.grave_entity_id.in_(tombs))
    return list(await ctx.session.scalars(select(GraveGoodsRow).where(here, untouched()).order_by(GraveGoodsRow.id)))


async def unearth_graves(ctx: TickContext, place_ids: list[int], finder: EntityRow) -> int:
    found = 0
    for row in await graves_in(ctx, place_ids):
        if held(finder.id) or held(row.dead_entity_id) or "found_epoch" in (row.locked or []):
            continue
        dead = await ctx.session.get(EntityRow, row.dead_entity_id)
        for item_id in row.items or []:
            item = await ctx.session.get(EntityRow, item_id)
            if item is not None:
                await items.give(ctx, item, finder.id, ItemDeed.OWNED, f"unearthed from the grave of {dead.name if dead is not None else 'one long dead'}")
        await shift_points(ctx.session, finder, row.goods_value)
        worth, taken = row.goods_value, list(row.items or [])
        row.goods_value, row.items, row.found_epoch, row.finder_node_id = 0, [], ctx.epoch, finder.id
        keeper = await living_entity(ctx.session, finder.location_id) if finder.location_id is not None else None
        if keeper is not None:
            stances = {row.dead_entity_id: AccountStance.NEUTRAL}
            fidelity = ctx.rules.grave_goods.find_fidelity
            await record_account(
                ctx, keeper, AccountKind.INSCRIPTION, fidelity=fidelity, stances=stances, subject_id=row.dead_entity_id, medium=AccountMedium.INSCRIPTION
            )
        roles = {
            IncidentRole.SUBJECT: row.dead_entity_id,
            IncidentRole.ACTOR: finder.id,
            IncidentRole.PLACE: row.grave_entity_id,
            IncidentRole.INSTRUMENT: taken,
        }
        await record(ctx, "dead.grave_found", roles=roles, facts={"value": worth, "items": len(taken)})
        found += 1
    return found


async def legacy_graves(ctx: TickContext, tally: GraveTally) -> None:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return
    tombs = select(StructureProfileRow.host_entity_id).where(StructureProfileRow.kind == StructureKind.TOMB)
    hosts = sorted({host for host in await ctx.session.scalars(tombs) if host is not None})
    notable = (EntityRow.status == EntityStatus.DEAD, EntityRow.entity_type == EntityType.MORTAL, await folk_among(ctx.session, hosts))
    for dead in list(await ctx.session.scalars(select(EntityRow).where(*notable).order_by(EntityRow.id))):
        if await furnish_grave(ctx, dead):
            tally.legacy += 1
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"graves": tally.legacy}))
    await ctx.session.flush()


async def tend_graves(ctx: TickContext) -> GraveTally:
    tally = GraveTally()
    await legacy_graves(ctx, tally)
    await try_graves(ctx, tally)
    return tally
