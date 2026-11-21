from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.db.tables.intimacy import IntimacyNormRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.fertility_means import FertilityMeans, MeansSource
from aerona.domain.enums.intimacy import NormStance, RelationContext
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.population import PopulationInstrument
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.fertility_means.factor import DIRECTION, PREVENTING, conceives, means_of
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.numbers.book import AIM_DIRECTION, scope_of
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.recording.record import record

F = FertilityMeans
SIMPLE = (F.PREVENTION, F.REMEDY_FOR_BARRENNESS, F.ENDING_PREGNANCY)
LEARNED = (F.ASSISTED_CONCEPTION, F.SURROGACY)
HIDING = frozenset({NormStance.FORBIDDEN, NormStance.DISCOURAGED})
SPREAD_FLOOR = 20
FIRST_USE = 10
SPREAD_LOSS = 10
EXPOSED_INFAMY = {NormStance.FORBIDDEN: 20, NormStance.DISCOURAGED: 10}
SOURCE_RISK = total(MeansSource, {MeansSource.FOLK: 1.0, MeansSource.MEDICINE: 0.5, MeansSource.RITE: 0.0, MeansSource.POWER: 0.0})


@dataclass
class MeansTally:
    found: int = 0
    spread: int = 0
    banned: int = 0
    exposed: int = 0


async def peoples(ctx: TickContext) -> list[EntityRow]:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    return [people for people in await ctx.session.scalars(query) if not held(people.id) and await conceives(ctx.session, people.id)]


async def first_stance(ctx: TickContext, people_id: int, means: FertilityMeans) -> NormStance:
    context = RelationContext.BEFORE_UNION if means in PREVENTING else RelationContext.WITHIN_UNION
    norm = await ctx.session.get(IntimacyNormRow, (people_id, context))
    return norm.stance if norm is not None else NormStance.TOLERATED


@memoized(PopulationInstrumentRow)
async def made_birth_policies(session: AsyncSession) -> list[int]:
    made = select(PopulationInstrumentRow.policy_id).where(PopulationInstrumentRow.instrument == PopulationInstrument.MADE_BIRTH)
    return sorted(set(await session.scalars(made)))


async def makes_births(ctx: TickContext, people_id: int) -> bool:
    policies = await made_birth_policies(ctx.session)
    if not policies:
        return False
    towns = set(await towns_of_people(ctx.session, people_id))
    for policy_id in policies:
        policy = await ctx.session.get(PopulationPolicyRow, policy_id)
        if policy is not None and towns & set(await scope_of(ctx.session, policy)):
            return True
    return False


async def keeps_rites(ctx: TickContext, people_id: int) -> bool:
    towns = await towns_of_people(ctx.session, people_id)
    for bond in await active_bonds(ctx.session, [BondKind.CELEBRATES], sources=towns):
        target = await ctx.session.get(EntityRow, bond.target_node_id)
        if target is not None and target.entity_type is EntityType.RITE:
            return True
    return False


async def reachable(ctx: TickContext, people_id: int, medicine: int) -> list[FertilityMeans]:
    level = ctx.rules.fertility_means.discover_level
    found = list(SIMPLE)
    if medicine >= level * 2:
        found.extend(LEARNED)
    if await makes_births(ctx, people_id):
        found.append(F.MADE_BIRTH)
    return found


async def adopt(
    ctx: TickContext, people_id: int, means: FertilityMeans, source: MeansSource, *, reliability: int, tally: MeansTally, origin: int | None = None
) -> FertilityMeansRow:
    row = FertilityMeansRow(
        people_entity_id=people_id,
        means=means,
        source=source,
        reliability=clamp_int(reliability, 0, PERCENT),
        risk=round(ctx.rules.fertility_means.risk_pct * SOURCE_RISK[source]),
        stance=await first_stance(ctx, people_id, means),
        use_pct=FIRST_USE,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    roles = {IncidentRole.SUBJECT: people_id, IncidentRole.ORIGIN: origin}
    await record(ctx, "birth.means_found", roles=roles, facts={"means": means, "source": source, "reliability": row.reliability})
    tally.found += 1
    return row


async def discover(ctx: TickContext, people: EntityRow, tally: MeansTally) -> None:
    table = ctx.rules.fertility_means
    known = {row.means for row in await means_of(ctx.session, people.id)}
    medicine = await branch_level(ctx.session, people.id, KnowledgeBranch.MEDICINE)
    learned = medicine >= table.discover_level
    rng = ctx.rng(f"means.find.{people.id}.{ctx.epoch}")
    for means in await reachable(ctx, people.id, medicine):
        if means in known or not rng.chance(table.discover_pct):
            continue
        source = MeansSource.MEDICINE if learned else MeansSource.RITE if await keeps_rites(ctx, people.id) else MeansSource.FOLK
        reliability = table.prevention_reliability_pct + (table.medicine_gain * medicine if learned else 0)
        await adopt(ctx, people.id, means, source, reliability=reliability, tally=tally)


async def people_of_towns(ctx: TickContext, kinds: list[EntityRow]) -> dict[int, int]:
    found: dict[int, int] = {}
    for people in kinds:
        for town in await towns_of_people(ctx.session, people.id):
            found.setdefault(town, people.id)
    return found


async def spread(ctx: TickContext, kinds: list[EntityRow], tally: MeansTally) -> None:
    owner = await people_of_towns(ctx, kinds)
    links: dict[int, set[int]] = {}
    for route in await ctx.session.scalars(select(TradeRouteProfileRow).order_by(TradeRouteProfileRow.route_entity_id)):
        first, second = owner.get(route.first_market_id), owner.get(route.second_market_id)
        if first is not None and second is not None and first != second:
            links.setdefault(first, set()).add(second)
            links.setdefault(second, set()).add(first)
    for people in kinds:
        for row in await means_of(ctx.session, people.id):
            if row.use_pct < SPREAD_FLOOR:
                continue
            for neighbour in sorted(links.get(people.id, set())):
                if held(neighbour) or await ctx.session.get(FertilityMeansRow, (neighbour, row.means)) is not None:
                    continue
                if ctx.rng(f"means.spread.{people.id}.{neighbour}.{row.means.value}.{ctx.epoch}").chance(ctx.rules.fertility_means.spread_pct):
                    await adopt(ctx, neighbour, row.means, row.source, reliability=row.reliability - SPREAD_LOSS, tally=tally, origin=people.id)
                    tally.spread += 1


async def push(ctx: TickContext, row: FertilityMeansRow, direction: int, force: float, *, holder: int, tally: MeansTally) -> None:
    table = ctx.rules.fertility_means
    against = DIRECTION[row.means] * direction < 0
    if "use_pct" not in row.locked:
        shift = round(table.policy_push * force) * (-1 if against else 1)
        row.use_pct = clamp_int(row.use_pct + shift, 0, PERCENT)
    if against and force * PERCENT >= table.ban_force_pct and row.stance is not NormStance.FORBIDDEN and "stance" not in row.locked:
        row.stance = NormStance.FORBIDDEN
        await record(ctx, "birth.means_banned", roles={IncidentRole.AUTHORITY: holder, IncidentRole.SUBJECT: row.people_entity_id}, facts={"means": row.means})
        tally.banned += 1


async def follow_policies(ctx: TickContext, owner: dict[int, int], tally: MeansTally) -> None:
    for policy in list(await ctx.session.scalars(select(PopulationPolicyRow).order_by(PopulationPolicyRow.id))):
        direction = AIM_DIRECTION[policy.aim]
        if not direction:
            continue
        force = policy.strength * policy.enforcement / (PERCENT * PERCENT)
        for people_id in sorted({owner[town] for town in await scope_of(ctx.session, policy) if town in owner}):
            for row in await means_of(ctx.session, people_id):
                await push(ctx, row, direction, force, holder=policy.holder_node_id, tally=tally)


def drift(ctx: TickContext, row: FertilityMeansRow) -> None:
    if "use_pct" in row.locked:
        return
    step = ctx.rules.fertility_means.drift
    if row.stance is NormStance.FORBIDDEN:
        row.use_pct = clamp_int(row.use_pct - step, 0, PERCENT)
    elif row.stance is not NormStance.DISCOURAGED:
        row.use_pct = clamp_int(row.use_pct + step, 0, PERCENT)


async def expose(ctx: TickContext, tally: MeansTally) -> None:
    hidden = select(FertilityUseRow).where(FertilityUseRow.hidden.is_(True), FertilityUseRow.exposed.is_(False)).order_by(FertilityUseRow.id)
    for use in list(await ctx.session.scalars(hidden)):
        known = await ctx.session.get(FertilityMeansRow, (use.people_entity_id, use.means))
        user = await ctx.session.get(EntityRow, use.user_entity_id)
        if known is None or user is None or held(user.id) or "exposed" in use.locked:
            continue
        if not ctx.rng(f"means.exposed.{use.id}.{ctx.epoch}").chance(known.risk):
            continue
        use.exposed = True
        await shift_standing(ctx.session, user, "infamy", EXPOSED_INFAMY.get(known.stance, 0), ctx.epoch)
        roles = {IncidentRole.SUBJECT: user.id, IncidentRole.MEMBER: use.people_entity_id}
        await record(ctx, "birth.means_exposed", roles=roles, facts={"means": use.means, "stance": known.stance}, place=user.location_id)
        tally.exposed += 1


async def tend_means(ctx: TickContext) -> MeansTally:
    tally = MeansTally()
    kinds = await peoples(ctx)
    for people in kinds:
        await discover(ctx, people, tally)
    await spread(ctx, kinds, tally)
    await follow_policies(ctx, await people_of_towns(ctx, kinds), tally)
    for people in kinds:
        for row in await means_of(ctx.session, people.id):
            drift(ctx, row)
    await expose(ctx, tally)
    return tally
