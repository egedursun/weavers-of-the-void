from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow, SpyNetworkRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.military import CaptiveFate, SpyCover
from aerona.domain.enums.mind import ActKind, ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import receive_coin
from aerona.engine.faith.book import faith_tenets
from aerona.engine.finance.contraband import traffic
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.taboos import forbidden
from aerona.engine.military.ransom import carry_language, cohort_ransom, pay_from_treasury, release_by_opinion
from aerona.engine.mind.book import values_for
from aerona.engine.mind.hooks import judged
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.levies import levies_from
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, stat
from aerona.engine.primitives.strength import patron_bonus

HUNDRED = 100


def settle_into(ctx: TickContext, community: EntityRow | None, count: int) -> int:
    if community is None or count <= 0 or not levies_from(community):
        return 0
    before = headcount(community)
    with flowing(FlowCategory.CAPTIVE):
        after = put_stat(ctx.rules, community, headcount_key(community), before + count)
    return (after or before) - before


async def slavery_lawful(ctx: TickContext, captor: EntityRow) -> bool:
    status = await law_param(ctx.session, captor.id, LawKind.SLAVERY, "status")
    return status == "allowed"


async def ransom_lawful(ctx: TickContext, captor: EntityRow | None) -> bool:
    if captor is None:
        return True
    allowed = await law_param(ctx.session, captor.id, LawKind.RANSOM_CUSTOM, "allowed")
    return allowed is None or bool(allowed)


def rich(ctx: TickContext, home: EntityRow) -> bool:
    campaigns = ctx.rules.campaigns
    return (stat(home, "wealth") or 0) >= campaigns.ransom_min_wealth or (stat(home, "prosperity") or 0) >= campaigns.ransom_min_prosperity


async def sacrifice(ctx: TickContext, row: CaptiveCohortRow, captor: EntityRow) -> int:
    patron = (await patron_bonus(ctx.session, ctx.rules, captor)).son
    if patron is not None:
        before = patron.essence
        patron.essence += row.count * ctx.rules.captivity.sacrifice_essence_per_100 // HUNDRED
        cap_gained_essence(ctx.rules, patron, before)
    if row.origin_entity_id is not None:
        await judged(ctx, captor.id, row.origin_entity_id, ActKind.HUMAN_SACRIFICE, note=f"{row.count} captives")
    return row.count


async def ransom(ctx: TickContext, row: CaptiveCohortRow, captor: EntityRow, home: EntityRow) -> int:
    cost = await pay_from_treasury(ctx, home, cohort_ransom(ctx, row))
    if cost <= 0:
        return 0
    await receive_coin(ctx.session, ctx.rules, captor, cost)
    return settle_into(ctx, home, row.count)


async def put_to_work(ctx: TickContext, row: CaptiveCohortRow, captor: EntityRow, home: EntityRow | None) -> CaptiveFate:
    enslaved = await slavery_lawful(ctx, captor)
    market = None if enslaved else await traffic(ctx, captor, row.count, row.origin_entity_id)
    if market is not None:
        settle_into(ctx, market, row.count)
        return CaptiveFate.ENSLAVED
    settle_into(ctx, captor, row.count)
    await carry_language(ctx, row, captor)
    if enslaved and home is not None:
        await judged(ctx, captor.id, home.id, ActKind.SLAVERY)
    return CaptiveFate.ENSLAVED if enslaved else CaptiveFate.LABOUR


async def decide(ctx: TickContext, row: CaptiveCohortRow) -> CaptiveFate:
    table = ctx.rules.captivity
    captor = await living_entity(ctx.session, row.captor_entity_id)
    home = await living_entity(ctx.session, row.origin_entity_id)
    if captor is None:
        settle_into(ctx, home, row.count)
        return CaptiveFate.RELEASED
    rng = ctx.rng(f"captive_cohort.{row.id}.{ctx.epoch}")
    values = await values_for(ctx.session, captor.id)
    if home is not None and rich(ctx, home) and await ransom_lawful(ctx, captor) and rng.chance(table.ransom_pct) and await ransom(ctx, row, captor, home):
        return CaptiveFate.RANSOMED
    if values.get(ValueAxis.MERCY, 0) >= table.release_mercy or await release_by_opinion(ctx, captor, home):
        settle_into(ctx, home, row.count)
        if home is not None:
            await judged(ctx, captor.id, home.id, ActKind.MERCY_TO_ENEMY)
        return CaptiveFate.RELEASED
    sacrificial = values.get(ValueAxis.DEATH, 0) >= table.sacrifice_death or TenetKind.HUMAN_SACRIFICE in await faith_tenets(ctx.session, captor.id)
    if sacrificial and rng.chance(table.sacrifice_chance) and not await forbidden(ctx, captor.id, ActKind.HUMAN_SACRIFICE):
        await sacrifice(ctx, row, captor)
        return CaptiveFate.SACRIFICED
    if rng.chance(table.labour_pct) or ctx.epoch - row.since_epoch >= ctx.rules.campaigns.captive_defection_epochs:
        return await put_to_work(ctx, row, captor, home)
    return CaptiveFate.HELD


async def cohort_fates(ctx: TickContext) -> dict[CaptiveFate, int]:
    found: dict[CaptiveFate, int] = {}
    rows = await ctx.session.scalars(
        select(CaptiveCohortRow).where(CaptiveCohortRow.fate == CaptiveFate.HELD, CaptiveCohortRow.since_epoch < ctx.epoch).order_by(CaptiveCohortRow.id)
    )
    for row in list(rows):
        if held(row.captor_entity_id):
            continue
        fate = await decide(ctx, row)
        found[fate] = found.get(fate, 0) + row.count
        if fate is not CaptiveFate.HELD:
            row.fate, row.settled_epoch = fate, ctx.epoch
    return found


async def exchange_at_peace(ctx: TickContext, war_id: int) -> int:
    returned = 0
    rows = await ctx.session.scalars(select(CaptiveCohortRow).where(CaptiveCohortRow.war_id == war_id, CaptiveCohortRow.fate == CaptiveFate.HELD))
    for row in list(rows):
        home = await living_entity(ctx.session, row.origin_entity_id)
        moving = round_half_up(row.count * ctx.rules.captivity.exchange_pct / PERCENT)
        returned += settle_into(ctx, home, moving)
        row.count -= moving
        if row.count <= 0:
            row.fate, row.settled_epoch = CaptiveFate.EXCHANGED, ctx.epoch
    return returned


async def wring_intel(ctx: TickContext, captor: EntityRow, home: EntityRow) -> None:
    found = await ctx.session.scalar(
        select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == captor.id, SpyNetworkRow.target_entity_id == home.id).order_by(SpyNetworkRow.id).limit(1)
    )
    if found is None:
        found = SpyNetworkRow(
            owner_entity_id=captor.id,
            target_entity_id=home.id,
            agents=0,
            agent_ids=[],
            depth=0,
            exposure=0,
            cover=SpyCover.BEGGAR,
            since_epoch=ctx.epoch,
            intel=0,
        )
        ctx.session.add(found)
    found.intel = clamp_int(found.intel + ctx.rules.captivity.torture_intel, 0, PERCENT)
    found.last_operation, found.last_epoch = "torture", ctx.epoch
    await judged(ctx, captor.id, home.id, ActKind.TORTURE)


async def announce(ctx: TickContext, fates: dict[CaptiveFate, int]) -> None:
    moved = {fate: count for fate, count in fates.items() if fate is not CaptiveFate.HELD and count}
    if not moved:
        return
    parts = ", ".join(f"{count} {fate.value}" for fate, count in sorted(moved.items()))
    await ctx.chronicle(ChronicleKind.WAR, f"Captives of war met their fates: {parts}.", template_key="captives.fates", feed_category=FeedCategory.WAR)
