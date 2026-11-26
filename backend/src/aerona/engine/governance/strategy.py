from sqlalchemy import select

from aerona.catalog.governance import STRATEGY_TREASURY_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.governance import OrgGovernanceRow, OrgMergerRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.governance import OPEN_MERGER_STAGES, MergerKind, OrgStrategy
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import held_coin
from aerona.engine.factions.companies import realm_of
from aerona.engine.governance.heads import STRATEGY_LOCK, set_strategy
from aerona.engine.governance.mergers import open_bid, worth
from aerona.engine.governance.research import reachable, research_for_strategy
from aerona.engine.primitives.numbers import clamp_int, round_half_up

BIDDING = frozenset({OrgStrategy.EXPAND_ABROAD, OrgStrategy.INTEGRATE_UP, OrgStrategy.INTEGRATE_DOWN})
TREASURY_LOCK = "treasury"
INFLUENCE_LOCK = "influence_over"


async def bid_target(ctx: TickContext, org: EntityRow, profile: FactionProfileRow, strategy: OrgStrategy) -> EntityRow | None:
    home = await realm_of(ctx, profile.home_entity_id or org.location_id)
    own_worth = await worth(ctx, org)
    rows = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.id != org.id, EntityRow.world_id == org.world_id)
        .order_by(EntityRow.id)
    )
    pending = set(await ctx.session.scalars(select(OrgMergerRow.target_node_id).where(OrgMergerRow.stage.in_(sorted(OPEN_MERGER_STAGES)))))
    fits: list[EntityRow] = []
    for other, other_profile in rows:
        if held(other.id) or other.id in pending or await worth(ctx, other) >= own_worth:
            continue
        abroad = await realm_of(ctx, other_profile.home_entity_id or other.location_id) != home
        same_kind = other_profile.kind is profile.kind
        if (strategy is OrgStrategy.EXPAND_ABROAD and abroad and same_kind) or (strategy is not OrgStrategy.EXPAND_ABROAD and not abroad and not same_kind):
            fits.append(other)
    return ctx.rng(f"governance.bid_target.{org.id}.{ctx.epoch}").pick(fits) if fits else None


async def follow_strategy(ctx: TickContext, row: OrgGovernanceRow, org: EntityRow) -> str | None:
    table = ctx.rules.governance
    profile = await ctx.session.get(FactionProfileRow, org.id)
    strategy = row.strategy
    if profile is not None and TREASURY_LOCK not in (profile.locked or []):
        change = round_half_up(held_coin(profile.treasury) * STRATEGY_TREASURY_PCT[strategy] * table.strategy_treasury_pct / PERCENT / PERCENT)
        profile.treasury = max(0, profile.treasury + change)
    if strategy is OrgStrategy.LOBBY and profile is not None and INFLUENCE_LOCK not in (profile.locked or []):
        realm = await realm_of(ctx, profile.home_entity_id or org.location_id)
        if realm is not None:
            sway = dict(profile.influence_over or {})
            sway[str(realm)] = clamp_int(sway.get(str(realm), 0) + table.lobby_influence, 0, PERCENT)
            profile.influence_over = sway
            return "lobbied"
    if strategy is OrgStrategy.RESEARCH:
        return "research" if await research_for_strategy(ctx, org) is not None else None
    if strategy in BIDDING and profile is not None and ctx.rng(f"governance.bid.{org.id}.{ctx.epoch}").chance(table.strategy_bid_chance_pct):
        target = await bid_target(ctx, org, profile, strategy)
        if target is not None:
            target_body = await ctx.session.get(OrgGovernanceRow, target.id)
            kind = MergerKind.FRIENDLY_ACQUISITION if target_body is None or target_body.trust < table.removal_trust else MergerKind.HOSTILE_TAKEOVER
            await open_bid(ctx, org.id, target, kind, None)
            return "bid"
    return None


STEADY = (OrgStrategy.HOLD, OrgStrategy.GROW, OrgStrategy.SPECIALISE, OrgStrategy.DIVERSIFY)


async def courses_open(ctx: TickContext, org: EntityRow, profile: FactionProfileRow) -> list[OrgStrategy]:
    table = ctx.rules.governance
    found = list(STEADY)
    if profile.treasury >= table.research_budget:
        found.extend((OrgStrategy.EXPAND_ABROAD, OrgStrategy.INTEGRATE_UP, OrgStrategy.INTEGRATE_DOWN))
        if await reachable(ctx, org):
            found.append(OrgStrategy.RESEARCH)
    if await realm_of(ctx, profile.home_entity_id or org.location_id) is not None:
        found.append(OrgStrategy.LOBBY)
    if profile.treasury < table.research_cost_per_staff:
        found.append(OrgStrategy.WITHDRAW)
    return found


async def set_course(ctx: TickContext, row: OrgGovernanceRow, org: EntityRow) -> bool:
    profile = await ctx.session.get(FactionProfileRow, org.id)
    if profile is None or row.head_node_id is None or STRATEGY_LOCK in (row.locked or []):
        return False
    if not ctx.rng(f"governance.course.{org.id}.{ctx.epoch}").chance(ctx.rules.governance.course_change_pct):
        return False
    options = [course for course in await courses_open(ctx, org, profile) if course is not row.strategy]
    if not options:
        return False
    await set_strategy(ctx, row, ctx.rng(f"governance.course_pick.{org.id}.{ctx.epoch}").pick(options), row.head_node_id, "the head set a new course")
    return True
