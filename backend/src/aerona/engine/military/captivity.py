from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow, SpyNetworkRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.military import CaptiveFate, SpyCover
from aerona.domain.enums.mind import ActKind, MemoryKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import receive_coin
from aerona.engine.faith.book import faith_tenets
from aerona.engine.finance.contraband import traffic
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.lore.taboos import forbidden
from aerona.engine.military.ransom import carry_language, cohort_ransom, pay_from_treasury, release_by_opinion
from aerona.engine.military.units import stacks_of, sync
from aerona.engine.mind.book import values_for
from aerona.engine.mind.hooks import judged
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.levies import add_heads, levies_from
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.strength import patron_bonus
from aerona.engine.recording.record import RoleValue, record
from aerona.engine.services.community_relations import change_relation

HUNDRED = 100


def settle_into(ctx: TickContext, community: EntityRow | None, count: int) -> int:
    if community is None or count <= 0 or not levies_from(community):
        return 0
    return add_heads(ctx.rules, community, count, FlowCategory.CAPTIVE)


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
        await judged(ctx, captor.id, row.origin_entity_id, ActKind.SACRIFICE_OF_PEOPLE, note=f"{several(row.count, 'captive', 'captives')}")
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
    sacrificial = values.get(ValueAxis.DEATH, 0) >= table.sacrifice_death or TenetKind.SACRIFICE_OF_PEOPLE in await faith_tenets(ctx.session, captor.id)
    if sacrificial and rng.chance(table.sacrifice_chance) and not await forbidden(ctx, captor.id, ActKind.SACRIFICE_OF_PEOPLE):
        await sacrifice(ctx, row, captor)
        return CaptiveFate.SACRIFICED
    if values.get(ValueAxis.MERCY, 0) >= 0 and rng.chance(ctx.rules.captives.adopt_pct) and settle_into(ctx, captor, row.count):
        return CaptiveFate.ADOPTED
    harsh = await harsher_fate(ctx, row, captor, home, mercy=values.get(ValueAxis.MERCY, 0), rng=rng)
    return harsh or CaptiveFate.HELD


async def harsher_fate(
    ctx: TickContext, row: CaptiveCohortRow, captor: EntityRow, home: EntityRow | None, *, mercy: int, rng: SeededRandom
) -> CaptiveFate | None:
    if await press_into_army(ctx, row, captor, rng.chance(ctx.rules.captives.recruit_pct)):
        return CaptiveFate.RECRUITED
    if rng.chance(ctx.rules.captivity.labour_pct) or ctx.epoch - row.since_epoch >= ctx.rules.campaigns.captive_defection_epochs:
        return await put_to_work(ctx, row, captor, home)
    if mercy < 0 and rng.chance(ctx.rules.captives.execute_pct) and await execute(ctx, row, captor, home):
        return CaptiveFate.EXECUTED
    return None


async def execute(ctx: TickContext, row: CaptiveCohortRow, captor: EntityRow, home: EntityRow | None) -> bool:
    if await forbidden(ctx, captor.id, ActKind.KILLING_CAPTIVE):
        return False
    if home is not None:
        await judged(ctx, captor.id, home.id, ActKind.KILLING_CAPTIVE, note=f"{several(row.count, 'captive', 'captives')}")
        await change_relation(ctx, home.id, captor.id, -ctx.rules.captives.executed_dread, MemoryKind.KILLED_KIN, note="killed its captives")
    return True


async def press_into_army(ctx: TickContext, row: CaptiveCohortRow, captor: EntityRow, rolled: bool, *, forced: bool = False) -> bool:
    if not rolled:
        return False
    if not forced and (row.social_class is not SocialClass.WARRIOR or not await BondRepository(ctx.session).outgoing(captor.id, BondKind.ENEMY)):
        return False
    army = await ctx.session.scalar(
        select(ArmyRow).where(ArmyRow.owner_entity_id == captor.id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id).limit(1)
    )
    host = await living_entity(ctx.session, army.entity_id) if army is not None else None
    if host is None or held(host.id):
        return False
    stacks = await stacks_of(ctx.session, host.id)
    if not stacks:
        return False
    table = ctx.rules.captives
    kept = row.count - round_half_up(row.count * table.recruited_desertion_pct / PERCENT)
    stack = stacks[0]
    if "count" not in stack.locked:
        total = stack.count + kept
        stack.morale = round_half_up((stack.morale * stack.count + table.recruited_loyalty * kept) / max(1, total))
        stack.count = total
    sync(host, stacks, ctx.rules)
    return kept > 0


CohortFate = tuple[int, int | None, CaptiveFate]


async def cohort_fates(ctx: TickContext) -> dict[CohortFate, int]:
    found: dict[CohortFate, int] = {}
    rows = await ctx.session.scalars(
        select(CaptiveCohortRow).where(CaptiveCohortRow.fate == CaptiveFate.HELD, CaptiveCohortRow.since_epoch < ctx.epoch).order_by(CaptiveCohortRow.id)
    )
    for row in list(rows):
        if held(row.captor_entity_id):
            continue
        fate = await decide(ctx, row)
        key = (row.captor_entity_id, row.origin_entity_id, fate)
        found[key] = found.get(key, 0) + row.count
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


async def announce(ctx: TickContext, fates: dict[CohortFate, int]) -> None:
    for (captor, origin, fate), count in sorted(fates.items(), key=lambda item: (item[0][0], item[0][1] or 0, item[0][2].value)):
        if fate is CaptiveFate.HELD or not count:
            continue
        roles: dict[IncidentRole, RoleValue] = {IncidentRole.ACTOR: captor, IncidentRole.ORIGIN: origin}
        await record(ctx, "captives.fates", roles=roles, facts={"fate": fate, "count": count})
