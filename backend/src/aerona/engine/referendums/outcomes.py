from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import PolityLeagueRow
from aerona.db.tables.orders import OrderTransitionRow
from aerona.db.tables.polity import OfficeRow, TreatyProfileRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leagues import LeagueStanding
from aerona.domain.enums.orders import TransitionStage
from aerona.domain.enums.polity import TreatyStatus
from aerona.domain.enums.referendums import ReferendumResult, ReferendumSubject
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import core_of, living_polity
from aerona.engine.leagues.founding import join
from aerona.engine.polity.control import merge, split
from aerona.engine.polity.laws import repeal
from aerona.engine.referendums.book import realm_of_holder, realm_profile
from aerona.engine.services.war import declare_war
from aerona.engine.services.war_resolution import make_peace

OPEN_STAGES = (TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING)


async def on_law(ctx: TickContext, row: ReferendumRow, passed: bool) -> bool:
    law = await ctx.session.get(EntityRow, row.target_node_id) if row.target_node_id is not None else None
    if passed or law is None or law.entity_type is not EntityType.LAW or law.status is not EntityStatus.CANON or held(law.id):
        return False
    await repeal(ctx, law, "the people voted it down")
    return True


async def on_independence(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    target = row.target_node_id if holder.entity_type is EntityType.POLITY else holder.id
    realm = holder.id if holder.entity_type is EntityType.POLITY else await realm_of_holder(ctx.session, holder)
    if not passed or realm is None or target is None or held(target) or held(realm):
        return False
    return await split(ctx, realm, [target]) > 0


async def on_union(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    target = await living_polity(ctx.session, row.target_node_id)
    if not passed or target is None or held(target.id) or held(holder.id):
        return False
    if holder.entity_type is EntityType.LEAGUE and await ctx.session.get(PolityLeagueRow, holder.id) is not None:
        await join(ctx, holder, target, LeagueStanding.MEMBER)
        return True
    if holder.entity_type is EntityType.POLITY and target.id != holder.id:
        await merge(ctx, target.id, holder.id)
        return True
    return False


async def on_treaty(ctx: TickContext, row: ReferendumRow, passed: bool) -> bool:
    treaty = await ctx.session.get(TreatyProfileRow, row.target_node_id) if row.target_node_id is not None else None
    if passed or treaty is None or treaty.status is not TreatyStatus.IN_FORCE or held(treaty.treaty_entity_id) or "status" in (treaty.locked or []):
        return False
    treaty.status, treaty.ended_epoch = TreatyStatus.BROKEN, ctx.epoch
    return True


async def on_war(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    realm = await realm_of_holder(ctx.session, holder)
    ours = await core_of(ctx.session, realm) if realm is not None else None
    theirs = await core_of(ctx.session, row.target_node_id) if row.target_node_id is not None else None
    theirs = theirs or row.target_node_id
    if ours is None or theirs is None or held(ours) or held(theirs):
        return False
    if passed:
        return await declare_war(ctx, ours, theirs, "the people voted for war", world_cap=False)
    return await make_peace(ctx, ours, theirs, "the people voted for peace")


async def on_transition(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    realm = await realm_of_holder(ctx.session, holder)
    query = select(OrderTransitionRow).where(OrderTransitionRow.polity_entity_id == realm, OrderTransitionRow.stage.in_(OPEN_STAGES))
    change = await ctx.session.scalar(query.order_by(OrderTransitionRow.id).limit(1))
    if passed or change is None or "stage" in (change.locked or []) or (realm is not None and held(realm)):
        return False
    change.stage, change.ended_epoch = TransitionStage.FAILED, ctx.epoch
    return True


async def on_recall(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    realm = await realm_of_holder(ctx.session, holder)
    if not passed or realm is None or row.target_node_id is None or held(row.target_node_id):
        return False
    offices = await ctx.session.scalars(select(OfficeRow).where(OfficeRow.polity_entity_id == realm, OfficeRow.holder_entity_id == row.target_node_id))
    recalled = False
    for office in list(offices):
        if "holder_entity_id" not in (office.locked or []):
            office.holder_entity_id, office.since_epoch = None, ctx.epoch
            recalled = True
    return recalled


async def on_faith(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    profile = await realm_profile(ctx.session, await realm_of_holder(ctx.session, holder))
    if not passed or profile is None or row.target_node_id is None or "state_religion_id" in (profile.locked or []):
        return False
    profile.state_religion_id = row.target_node_id
    return True


async def on_law_vote(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    return await on_law(ctx, row, passed)


async def on_treaty_vote(ctx: TickContext, row: ReferendumRow, holder: EntityRow, passed: bool) -> bool:
    return await on_treaty(ctx, row, passed)


Outcome = Callable[[TickContext, ReferendumRow, EntityRow, bool], Awaitable[bool]]
OUTCOMES: Mapping[ReferendumSubject, Outcome] = total(
    ReferendumSubject,
    {
        ReferendumSubject.LAW: on_law_vote,
        ReferendumSubject.CONSTITUTION: on_law_vote,
        ReferendumSubject.INDEPENDENCE: on_independence,
        ReferendumSubject.UNION: on_union,
        ReferendumSubject.TREATY: on_treaty_vote,
        ReferendumSubject.WAR: on_war,
        ReferendumSubject.TRANSITION: on_transition,
        ReferendumSubject.RECALL: on_recall,
        ReferendumSubject.FAITH: on_faith,
    },
)


async def carry_out(ctx: TickContext, row: ReferendumRow, holder: EntityRow) -> bool:
    return await OUTCOMES[row.subject](ctx, row, holder, row.result is ReferendumResult.PASSED)
