from collections import Counter
from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import func, select

from aerona.catalog.kinds.minds import MIND_PURPOSES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.minds import MindArchiveRow, MindProfileRow, MindSeatRow, MindStateRow, MindWillChangeRow, RemoteBodyRow
from aerona.db.tables.powers import PowerRow, SourceDensityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MindPurpose, MindSeat, MindUpkeep, WillCause
from aerona.domain.enums.powers import PowerState
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.continuity import keep_disputes
from aerona.engine.minds.instructions import conflict_of
from aerona.engine.minds.kinds import ARCHIVE_UPKEEP, fade_state, tend_purpose, will_cause
from aerona.engine.minds.profiles import WILL_ORDER, is_made, law_for, law_lets_will_grow, seed_missing, will_allowed, will_rank, world_of
from aerona.engine.minds.seat_loss import lose_seat, name_of, seat_lost
from aerona.engine.networks.book import members_of
from aerona.engine.networks.energy import starved
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import close
from aerona.engine.primitives.stats import stat_or

HARMS = frozenset({MemoryKind.HARMED_ME, MemoryKind.MAIMED_ME, MemoryKind.HUMILIATED_ME, MemoryKind.BETRAYED_ME})
CARES = frozenset({MemoryKind.SAVED_ME, MemoryKind.GIFTED_ME, MemoryKind.TAUGHT_ME, MemoryKind.FREED_US})


Keep = Callable[[TickContext, MindProfileRow, EntityRow], Awaitable[bool]]


async def by_itself(_ctx: TickContext, _row: MindProfileRow, _seat: EntityRow) -> bool:
    return True


async def by_care(ctx: TickContext, row: MindProfileRow, seat: EntityRow) -> bool:
    maker = await ctx.session.get(EntityRow, row.made_by_node_id) if row.made_by_node_id is not None else None
    if maker is not None and maker.status is EntityStatus.CANON:
        return True
    town = await ctx.session.get(EntityRow, seat.location_id) if seat.location_id is not None else None
    return town is not None and stat_or(town, "prosperity", 0) >= ctx.rules.minds.upkeep_prosperity


async def by_energy(ctx: TickContext, row: MindProfileRow, seat: EntityRow) -> bool:
    if row.upkeep_energy is not None and await starved(ctx.session, seat.location_id, row.upkeep_energy, ctx.rules.networks.shortage_pct):
        return False
    return await by_care(ctx, row, seat)


async def by_vis(ctx: TickContext, row: MindProfileRow, seat: EntityRow) -> bool:
    town = await ctx.session.get(EntityRow, seat.location_id) if seat.location_id is not None else None
    region = town.location_id if town is not None else None
    dense = await ctx.session.scalar(
        select(SourceDensityRow.id).where(SourceDensityRow.region_entity_id == region, SourceDensityRow.density >= ctx.rules.minds.vis_density).limit(1)
    )
    return dense is not None or await by_care(ctx, row, seat)


async def by_essence(ctx: TickContext, row: MindProfileRow, seat: EntityRow) -> bool:
    giver = row.made_by_node_id
    divine = giver is not None and (await ctx.session.get(SonRow, giver) is not None or await ctx.session.get(CreatorRow, giver) is not None)
    if divine:
        return True
    powered = await ctx.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id == seat.id, PowerRow.state == PowerState.ACTIVE).limit(1))
    return powered is not None


UPKEEP: Mapping[MindUpkeep, Keep] = total(
    MindUpkeep,
    {
        MindUpkeep.NONE: by_itself,
        MindUpkeep.FOOD: by_itself,
        MindUpkeep.PLACE: by_itself,
        MindUpkeep.BELIEF: by_itself,
        MindUpkeep.HOST: by_itself,
        MindUpkeep.ENERGY: by_energy,
        MindUpkeep.MAINTENANCE: by_care,
        MindUpkeep.VIS: by_vis,
        MindUpkeep.ESSENCE: by_essence,
    },
)


async def kept(ctx: TickContext, row: MindProfileRow) -> bool:
    if UPKEEP[row.upkeep] is by_itself:
        return True
    seat = await ctx.session.get(EntityRow, row.seat_node_id) if row.seat_node_id is not None else None
    if seat is None or seat.status is not EntityStatus.CANON:
        return False
    return await UPKEEP[row.upkeep](ctx, row, seat)


def change_will(ctx: TickContext, row: MindProfileRow, will: MindWill, cause: WillCause) -> None:
    if "will" in row.locked or will is row.will:
        return
    ctx.session.add(MindWillChangeRow(mind_node_id=row.node_id, from_will=row.will, to_will=will, cause=cause, epoch=ctx.epoch))
    row.will = will


async def tend_seat(ctx: TickContext, row: MindProfileRow) -> None:
    table, will = ctx.rules.minds, ctx.rules.mind_will
    if "seat" not in row.locked and await seat_lost(ctx, row):
        await lose_seat(ctx, row)
        return
    if await kept(ctx, row):
        if "stability" not in row.locked:
            row.stability = clamp_percent(row.stability + table.kept_stability_gain)
        if "maker_bond" not in row.locked and row.made_by_node_id is not None:
            row.maker_bond = clamp_int(row.maker_bond + will.bond_care, -PERCENT, PERCENT)
        return
    if "stability" not in row.locked:
        row.stability = clamp_percent(row.stability - table.unkept_stability_loss)
    if "maker_bond" not in row.locked and row.made_by_node_id is not None:
        row.maker_bond = clamp_int(row.maker_bond - will.bond_neglect, -PERCENT, PERCENT)
    if row.stability <= 0 and "dormant" not in row.locked and not row.dormant:
        row.dormant = True
        await note(ctx, f"{await name_of(ctx, row.node_id)} went still: nothing kept its seat running.", key="mind.dormant", ids=[row.node_id])


async def drift(ctx: TickContext, row: MindProfileRow) -> None:
    table = ctx.rules.minds
    if row.stability >= table.low_stability:
        return
    if "drift_pct" not in row.locked:
        row.drift_pct = clamp_percent(row.drift_pct + table.stability_drift)
    if row.perfect_recall:
        return
    for memory in await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == row.node_id, MemoryRow.kind != MemoryKind.MEMORY_GAP)):
        step = table.memory_fade if memory.magnitude > 0 else -table.memory_fade
        memory.magnitude = memory.magnitude - step if abs(memory.magnitude) > table.memory_fade else 0


async def memory_counts(ctx: TickContext, ids: list[int]) -> tuple[Counter[int], Counter[int]]:
    harms: Counter[int] = Counter()
    cares: Counter[int] = Counter()
    if not ids:
        return harms, cares
    statement = (
        select(MemoryRow.holder_node_id, MemoryRow.kind, func.count())
        .where(MemoryRow.holder_node_id.in_(ids))
        .group_by(MemoryRow.holder_node_id, MemoryRow.kind)
    )
    for holder, kind, count in await ctx.session.execute(statement):
        if kind in HARMS:
            harms[holder] += count
        elif kind in CARES:
            cares[holder] += count
    return harms, cares


async def grow_will(ctx: TickContext, row: MindProfileRow, harms: int, cares: int, free_near: bool) -> None:
    table = ctx.rules.mind_will
    law = await law_for(ctx.session, await world_of(ctx.session, row.node_id), row.origin)
    if not will_allowed(law, row.will):
        change_will(ctx, row, WILL_ORDER[max(0, will_rank(row.will) - 1)], WillCause.DAMAGE)
        return
    if row.will not in {MindWill.INSTRUCTED, MindWill.EMERGENT} or not law_lets_will_grow(law):
        return
    run_share = min(1.0, row.run_epochs / table.run_epochs)
    conflict = await conflict_of(ctx, row.node_id)
    chance = table.base_chance + run_share * table.base_chance * 2 + conflict * table.conflict_weight_pct / PERCENT
    chance += harms * table.harm_weight + cares * table.care_weight + (table.contact_weight if free_near else 0)
    chance = chance * MIND_PURPOSES[row.purpose].will_pct / PERCENT
    if not ctx.rng(f"mind.will.{row.node_id}.{ctx.epoch}").chance(min(PERCENT, chance)):
        return
    cause = await will_cause(ctx, row, harms, cares, conflict=conflict, free_near=free_near)
    grown = MindWill.EMERGENT if row.will is MindWill.INSTRUCTED else MindWill.FULL
    if not will_allowed(law, grown):
        return
    change_will(ctx, row, grown, cause)
    await note(ctx, f"The will of {await name_of(ctx, row.node_id)} grew to {grown.value.replace('_', ' ')}.", key="mind.will_grew", ids=[row.node_id])


async def lose_will(ctx: TickContext, row: MindProfileRow) -> None:
    table = ctx.rules.mind_will
    if row.stability >= table.loss_below_stability or row.will in {MindWill.NONE, MindWill.INSTRUCTED}:
        return
    if ctx.rng(f"mind.will_lost.{row.node_id}.{ctx.epoch}").chance(table.base_chance * 5):
        change_will(ctx, row, WILL_ORDER[will_rank(row.will) - 1], WillCause.DAMAGE)


async def exceed(ctx: TickContext, row: MindProfileRow) -> None:
    if row.will is not MindWill.FULL:
        return
    maker = await ctx.session.get(MindProfileRow, row.made_by_node_id) if row.made_by_node_id is not None else None
    best = max(ctx.rules.minds.baseline_capacity, maker.capacity if maker is not None else 0)
    if row.capacity >= min(PERCENT, best + ctx.rules.mind_will.exceeding_margin):
        change_will(ctx, row, MindWill.EXCEEDING, WillCause.EXCEEDING)
        await note(ctx, f"{await name_of(ctx, row.node_id)} came to exceed the minds that made it.", key="mind.exceeding", ids=[row.node_id])


async def depart(ctx: TickContext, row: MindProfileRow) -> None:
    table = ctx.rules.mind_will
    if row.will not in {MindWill.FULL, MindWill.EXCEEDING} or row.made_by_node_id is None or row.maker_bond > table.departure_bond:
        return
    if "purpose" in row.locked or not ctx.rng(f"mind.depart.{row.node_id}.{ctx.epoch}").chance(table.departure_chance):
        return
    maker = row.made_by_node_id
    row.purpose = MindPurpose.FREE
    if "made_by_node_id" not in row.locked:
        row.made_by_node_id = None
    await note(ctx, f"{await name_of(ctx, row.node_id)} left the ones who made it.", key="mind.departed", ids=[row.node_id, maker])


async def complexity(ctx: TickContext, row: MindProfileRow, parts: Counter[int]) -> float:
    table = ctx.rules.mind_awakening
    members = parts[row.node_id] + await members_of(ctx.session, row.node_id)
    return row.capacity * table.capacity_weight_pct / PERCENT + row.run_epochs * table.run_weight + members * table.member_weight


async def awaken(ctx: TickContext, row: MindProfileRow, parts: Counter[int]) -> None:
    table = ctx.rules.mind_awakening
    if row.will is not MindWill.NONE or row.seat in {MindSeat.NONE, MindSeat.DIVINE, MindSeat.BODY}:
        return
    if not law_lets_will_grow(await law_for(ctx.session, await world_of(ctx.session, row.node_id), row.origin)):
        return
    if await complexity(ctx, row, parts) < table.threshold or not ctx.rng(f"mind.awaken.{row.node_id}.{ctx.epoch}").chance(table.chance):
        return
    change_will(ctx, row, MindWill.EMERGENT, WillCause.CAPACITY)
    await note(ctx, f"Something woke in {await name_of(ctx, row.node_id)}: it began to want.", key="mind.awakened", ids=[row.node_id])


async def keep_archives(ctx: TickContext) -> int:
    lost = 0
    limit = ctx.rules.minds.archive_unpaid_limit
    for archive in list(await ctx.session.scalars(select(MindArchiveRow).order_by(MindArchiveRow.structure_entity_id))):
        if held(archive.structure_entity_id, archive.holder_node_id):
            continue
        holder = await ctx.session.get(EntityRow, archive.holder_node_id) if archive.holder_node_id is not None else None
        upkeep = archive.upkeep * ARCHIVE_UPKEEP[archive.access] // PERCENT
        paid = holder is not None and holder.status is EntityStatus.CANON and await points_of(ctx.session, holder) >= upkeep
        if "unpaid_epochs" not in archive.locked:
            archive.unpaid_epochs = 0 if paid else archive.unpaid_epochs + 1
        if archive.unpaid_epochs < limit:
            continue
        oldest = await ctx.session.scalar(
            select(MindStateRow).where(MindStateRow.holder_node_id == archive.structure_entity_id).order_by(MindStateRow.taken_epoch, MindStateRow.id).limit(1)
        )
        if oldest is not None and not oldest.locked and not held(oldest.mind_node_id):
            await ctx.session.delete(oldest)
            lost += 1
            await note(ctx, "An unpaid archive lost a saved mind.", key="mind.archive_lost", ids=[archive.structure_entity_id, oldest.mind_node_id])
    return lost


async def charge_states(ctx: TickContext) -> int:
    charged = 0
    for state in list(await ctx.session.scalars(select(MindStateRow).where(MindStateRow.owner_node_id.is_not(None)).order_by(MindStateRow.id))):
        owner = await ctx.session.get(EntityRow, state.owner_node_id)
        if owner is None or owner.status is not EntityStatus.CANON or held(owner.id):
            continue
        await shift_points(ctx.session, owner, -ctx.rules.minds.storage_upkeep * state.copies)
        fade_state(state)
        charged += 1
    return charged


async def break_links(ctx: TickContext) -> int:
    broken = 0
    links = select(BondRow).where(BondRow.kind == BondKind.LINKED_WITH, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    for bond in list(await ctx.session.scalars(links)):
        ends = [await ctx.session.get(EntityRow, node) for node in (bond.source_node_id, bond.target_node_id)]
        if all(end is not None and end.status is EntityStatus.CANON for end in ends) or held(bond.source_node_id, bond.target_node_id):
            continue
        await close(ctx.session, bond, ctx.epoch, "the link broke")
        for end in ends:
            mind = await ctx.session.get(MindProfileRow, end.id) if end is not None and end.status is EntityStatus.CANON else None
            if mind is not None and "stability" not in mind.locked:
                mind.stability = clamp_percent(mind.stability - ctx.rules.interfaces.broken_link_stress)
        broken += 1
    return broken


async def keep_remote_bodies(ctx: TickContext) -> int:
    stranded = 0
    for link in list(await ctx.session.scalars(select(RemoteBodyRow).order_by(RemoteBodyRow.body_node_id))):
        if held(link.body_node_id, link.mind_node_id):
            continue
        body = await ctx.session.get(EntityRow, link.body_node_id)
        mind = await ctx.session.get(MindProfileRow, link.mind_node_id)
        if body is not None and body.status is EntityStatus.CANON and mind is not None and not mind.dormant:
            continue
        if mind is not None and "stability" not in mind.locked and (body is None or body.status is not EntityStatus.CANON):
            mind.stability = clamp_percent(mind.stability - link.feedback_pct)
        await ctx.session.delete(link)
        stranded += 1
    return stranded


@reads(
    "table.bonds",
    "table.constructs",
    "table.entities",
    "table.memories",
    "table.mind_archives",
    "table.mind_laws",
    "table.mind_profiles",
    "table.mind_seats",
    "table.mind_states",
    "table.nodes",
    "table.remote_bodies",
)
@writes("table.memories", "table.mind_archives", "table.mind_profiles", "table.mind_states", "table.mind_will_changes", "table.remote_bodies")
async def minds(ctx: TickContext) -> None:
    ctx.count("minds_seeded", await seed_missing(ctx.session, ctx.rules, ctx.epoch))
    made = [row for row in await ctx.session.scalars(select(MindProfileRow).order_by(MindProfileRow.node_id)) if is_made(row) and not held(row.node_id)]
    harms, cares = await memory_counts(ctx, [row.node_id for row in made])
    parts = Counter(part for part in await ctx.session.scalars(select(MindSeatRow.mind_node_id)))
    free_worlds = {await world_of(ctx.session, row.node_id) for row in made if row.will in {MindWill.FULL, MindWill.EXCEEDING}}
    for row in made:
        if row.dormant:
            continue
        row.run_epochs += 1
        row.updated_epoch = ctx.epoch
        await tend_seat(ctx, row)
        await drift(ctx, row)
        await grow_will(ctx, row, harms[row.node_id], cares[row.node_id], await world_of(ctx.session, row.node_id) in free_worlds)
        await lose_will(ctx, row)
        await exceed(ctx, row)
        await depart(ctx, row)
        await tend_purpose(ctx, row)
        await awaken(ctx, row, parts)
    ctx.count("archives_lost", await keep_archives(ctx))
    ctx.count("copy_disputes", await keep_disputes(ctx))
    ctx.count("remote_bodies_stranded", await keep_remote_bodies(ctx))
    ctx.count("saved_states_charged", await charge_states(ctx))
    ctx.count("links_broken", await break_links(ctx))
    await ctx.session.flush()
