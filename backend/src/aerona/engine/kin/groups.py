from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kin_shapes import MEMBERSHIP_SHARE_PCT, SPLIT_SIZE_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.polity.held_titles import title_prestige
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.rules.registry import Rules

HALF = 2


@dataclass
class GroupTally:
    heads: int = 0
    splits: int = 0
    shares: int = 0


async def members_of(session: AsyncSession, group_id: int) -> list[KinGroupMemberRow]:
    return list(
        await session.scalars(
            select(KinGroupMemberRow).where(KinGroupMemberRow.group_id == group_id).order_by(KinGroupMemberRow.joined_epoch, KinGroupMemberRow.member_node_id)
        )
    )


async def alive(session: AsyncSession, node_id: int | None) -> bool:
    if node_id is None:
        return False
    entity = await session.get(EntityRow, node_id)
    return entity is not None and entity.status is EntityStatus.CANON


async def choose_head(ctx: TickContext, group: KinGroupRow, members: list[KinGroupMemberRow], tally: GroupTally) -> None:
    if await alive(ctx.session, group.head_node_id) or "head_node_id" in (group.locked or []):
        return
    ranked: list[tuple[int, int, int]] = []
    for member in members:
        profile = await ctx.session.get(MortalProfileRow, member.member_node_id)
        if profile is not None and await alive(ctx.session, member.member_node_id) and not held(member.member_node_id):
            ranked.append((-profile.renown, member.joined_epoch, member.member_node_id))
    if not ranked:
        return
    group.head_node_id = min(ranked)[2]
    await record(ctx, "kin.head_chosen", roles={IncidentRole.LEADER: group.head_node_id}, facts={"group": group.name})
    tally.heads += 1


async def split_group(ctx: TickContext, group: KinGroupRow, members: list[KinGroupMemberRow], prestige: int, tally: GroupTally) -> None:
    table = ctx.rules.kin
    bound = table.split_size * SPLIT_SIZE_PCT[group.form] // PERCENT + prestige * table.title_hold_pct // PERCENT
    if len(members) <= bound or "members" in (group.locked or []):
        return
    kindred = await ctx.session.scalar(select(func.count()).select_from(KinGroupRow).where(KinGroupRow.name.startswith(group.name)))
    offshoot = KinGroupRow(
        people_entity_id=group.people_entity_id,
        name=f"{group.name} {int(kindred or 0) + 1}",
        form=group.form,
        membership=group.membership,
        exogamy=group.exogamy,
        council_size=group.council_size,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(offshoot)
    await ctx.session.flush()
    leaving = members[len(members) // HALF :]
    for member in leaving:
        await ctx.session.delete(member)
    await ctx.session.flush()
    ctx.session.add_all(
        KinGroupMemberRow(group_id=offshoot.id, member_node_id=member.member_node_id, adopted=member.adopted, joined_epoch=ctx.epoch, locked=[])
        for member in leaving
    )
    await record(
        ctx,
        "kin.group_split",
        roles={IncidentRole.SUBJECT: group.people_entity_id},
        facts={"group": group.name, "offshoot": offshoot.name, "members": len(leaving)},
    )
    tally.splits += 1


async def share_land(ctx: TickContext, group: KinGroupRow, members: list[KinGroupMemberRow], tally: GroupTally) -> None:
    if group.land_region_id is None or held(group.land_region_id):
        return
    table = ctx.rules.kin
    helped = 0
    for member in members:
        profile = await ctx.session.get(MortalProfileRow, member.member_node_id)
        entity = await ctx.session.get(EntityRow, member.member_node_id)
        if profile is None or entity is None or entity.status is not EntityStatus.CANON or profile.wealth >= table.need_wealth or held(entity.id):
            continue
        share = max(1, table.need_wealth * table.help_share_pct * MEMBERSHIP_SHARE_PCT[group.membership] // (PERCENT * PERCENT))
        with explaining():
            term("kin.help_share_pct", share, source_node_id=group.land_region_id)
            await shift_points(ctx.session, entity, share)
        helped += 1
    if helped:
        await record(
            ctx, "kin.land_shared", roles={IncidentRole.PLACE: group.land_region_id}, facts={"group": group.name, "members": helped}, place=group.land_region_id
        )
        tally.shares += 1


async def keep_groups(ctx: TickContext, tally: GroupTally) -> None:
    groups = list(await ctx.session.scalars(select(KinGroupRow).order_by(KinGroupRow.id)))
    crowned = await title_prestige(ctx.session, {group.head_node_id for group in groups if group.head_node_id is not None})
    for group in groups:
        if held(group.people_entity_id):
            continue
        members = await members_of(ctx.session, group.id)
        await choose_head(ctx, group, members, tally)
        await split_group(ctx, group, members, crowned.get(group.head_node_id or 0, 0), tally)
        await share_land(ctx, group, await members_of(ctx.session, group.id), tally)
    await ctx.session.flush()


async def kin_group_bars(session: AsyncSession, rules: Rules, first: EntityRow, second: EntityRow) -> bool:
    shared = (
        select(func.count())
        .select_from(KinGroupMemberRow)
        .join(KinGroupRow, KinGroupRow.id == KinGroupMemberRow.group_id)
        .where(KinGroupMemberRow.member_node_id == second.id, KinGroupRow.exogamy >= rules.kin.exogamy_bar)
        .where(KinGroupMemberRow.group_id.in_(select(KinGroupMemberRow.group_id).where(KinGroupMemberRow.member_node_id == first.id)))
    )
    return bool(await session.scalar(shared))
