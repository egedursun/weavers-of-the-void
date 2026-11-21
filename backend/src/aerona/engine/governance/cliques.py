from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.governance import OrgCliqueRow, OrgGovernanceRow, OrgMergerRow
from aerona.db.write_guard import held
from aerona.domain.enums.governance import OPEN_MERGER_STAGES, CliqueAim, MergerKind, OrgStrategy
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.factions.offshoots import found_offshoot
from aerona.engine.governance.heads import cliques_of, living, standing
from aerona.engine.governance.mergers import open_bid
from aerona.engine.governance.seats import members_of, seats_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

STRENGTH_LOCK = "strength"
AIM_LOCK = "aim"


async def form_clique(ctx: TickContext, row: OrgGovernanceRow) -> OrgCliqueRow | None:
    table = ctx.rules.governance
    seats = await seats_of(ctx, row.org_node_id)
    if len(seats) < table.clique_min_seats:
        return None
    if not ctx.rng(f"governance.clique.{row.org_node_id}.{ctx.epoch}").chance(table.clique_form_chance_pct):
        return None
    aligned = {member for clique in await cliques_of(ctx, row.org_node_id) for member in (clique.members or [])}
    free = [entity for entity in [await living(ctx, seat.member_node_id) for seat in seats if seat.member_node_id not in aligned] if entity is not None]
    free = [entity for entity in free if entity.id != row.head_node_id and not held(entity.id)]
    if not free:
        return None
    rng = ctx.rng(f"governance.clique_aim.{row.org_node_id}.{ctx.epoch}")
    leader = max(free, key=lambda entity: (standing(entity), -entity.id))
    followers = [entity.id for entity in rng.sample(free, max(1, len(free) // 2)) if entity.id != leader.id]
    aim, wish = (
        (CliqueAim.HEAD, None)
        if row.trust < table.removal_trust + table.challenge_margin
        else (
            CliqueAim.STRATEGY,
            rng.pick([item for item in OrgStrategy if item is not row.strategy]),
        )
    )
    clique = OrgCliqueRow(
        org_node_id=row.org_node_id,
        name=f"those around {leader.name}",
        leader_node_id=leader.id,
        members=sorted({leader.id, *followers}),
        aim=aim,
        aim_strategy=wish,
        aim_node_id=leader.id if aim is CliqueAim.HEAD else None,
        strength=0,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(clique)
    await ctx.session.flush()
    return clique


async def weigh_clique(ctx: TickContext, clique: OrgCliqueRow) -> None:
    weights = {seat.member_node_id: seat.vote_weight for seat in await seats_of(ctx, clique.org_node_id)}
    member_ids = {member.mortal_entity_id for member in await members_of(ctx, clique.org_node_id)}
    if "members" not in (clique.locked or []):
        clique.members = sorted(node for node in clique.members or [] if node in weights or node in member_ids)
    if STRENGTH_LOCK not in (clique.locked or []):
        clique.strength = clamp_int(sum(weights.get(node, 0) for node in clique.members or []), 0, PERCENT)


async def lost_heart(ctx: TickContext, row: OrgGovernanceRow, clique: OrgCliqueRow) -> None:
    if AIM_LOCK in (clique.locked or []):
        return
    lost_head = clique.aim is CliqueAim.HEAD and row.head_node_id is not None and row.head_node_id != clique.aim_node_id
    lost_vote = clique.aim is CliqueAim.STRATEGY and clique.aim_strategy is not row.strategy and ctx.epoch - clique.since_epoch >= row.term_epochs
    if (lost_head or lost_vote) and ctx.rng(f"governance.leave.{clique.id}.{ctx.epoch}").chance(ctx.rules.governance.split_turn_chance_pct):
        clique.aim, clique.aim_strategy, clique.aim_node_id = CliqueAim.SPLIT, None, None


async def split_away(ctx: TickContext, row: OrgGovernanceRow, clique: OrgCliqueRow, name: str | None = None) -> EntityRow | None:
    parent = await ctx.session.get(EntityRow, row.org_node_id)
    profile = await ctx.session.get(FactionProfileRow, row.org_node_id)
    if parent is None or profile is None or held(parent.id):
        return None
    leaving = [
        member
        for member in await members_of(ctx, row.org_node_id)
        if member.mortal_entity_id in (clique.members or []) and member.mortal_entity_id != row.head_node_id and not held(member.mortal_entity_id)
    ]
    if not leaving:
        return None
    leader = await living(ctx, clique.leader_node_id)
    child = await found_offshoot(
        ctx,
        parent,
        profile,
        name=name or f"{parent.name.removeprefix('the ')} under {leader.name if leader is not None else clique.name}",
        body=f"Those of {parent.name} who followed {clique.name} and left it.",
        share_pct=clique.strength,
        leaving=leaving,
    )
    await record(
        ctx,
        "org.split",
        roles={IncidentRole.PREDECESSOR: parent.id, IncidentRole.PRODUCT: child.id} | ({IncidentRole.ACTOR: leader.id} if leader is not None else {}),
        facts={"members_left": len(leaving), "share": clique.strength},
    )
    await ctx.session.delete(clique)
    await ctx.session.flush()
    return child


async def bid_from_clique(ctx: TickContext, row: OrgGovernanceRow, clique: OrgCliqueRow) -> OrgMergerRow | None:
    if clique.aim_node_id is None or clique.strength < row.quorum_pct:
        return None
    target = await living(ctx, clique.aim_node_id)
    if target is None or held(target.id) or target.id == row.org_node_id:
        return None
    pending = await ctx.session.scalar(
        select(OrgMergerRow.id).where(OrgMergerRow.target_node_id == target.id, OrgMergerRow.stage.in_(sorted(OPEN_MERGER_STAGES))).limit(1)
    )
    if pending is not None:
        return None
    merger = await open_bid(ctx, row.org_node_id, target, MergerKind.MERGER, None)
    if AIM_LOCK not in (clique.locked or []):
        clique.aim, clique.aim_node_id = CliqueAim.STRATEGY, None
    return merger


async def tend_cliques(ctx: TickContext, row: OrgGovernanceRow) -> tuple[int, int]:
    formed = 1 if await form_clique(ctx, row) is not None else 0
    split = 0
    for clique in await cliques_of(ctx, row.org_node_id):
        await weigh_clique(ctx, clique)
        if not clique.members:
            await ctx.session.delete(clique)
            continue
        await lost_heart(ctx, row, clique)
        if clique.aim is CliqueAim.SPLIT and clique.strength >= ctx.rules.governance.split_clique_threshold:
            split += 1 if await split_away(ctx, row, clique) is not None else 0
        elif clique.aim is CliqueAim.MERGER:
            await bid_from_clique(ctx, row, clique)
    await ctx.session.flush()
    return formed, split
