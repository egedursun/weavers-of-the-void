from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import PressureKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.population import PopulationAim, PopulationInstrument
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.folkways.mishaps import made_minds_near
from aerona.engine.loops.delay import lagged
from aerona.engine.mind.book import pressures_of
from aerona.engine.numbers.book import AIM_DIRECTION, force, instruments_of, scope_of, towns_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

PULLS = frozenset({PopulationInstrument.SETTLEMENT_GRANT, PopulationInstrument.MIGRATION_PERMIT, PopulationInstrument.RECRUITMENT_ABROAD})
HARSH = frozenset({PopulationInstrument.EXPULSION, PopulationInstrument.CHILD_LIMIT})
SPARSE_TOWN = 500
PRESSED = 50
TEN = 10
QUARTER = 4
FIRST_STRENGTH = 50


@dataclass
class NumbersTally:
    enforced: int = 0
    resisted: int = 0
    expelled: int = 0
    resettled: int = 0
    met: int = 0
    adopted: int = 0
    repealed: int = 0


def people_in(town: EntityRow) -> int:
    return stat_or(town, "population", 0)


async def move_people(ctx: TickContext, town: EntityRow, amount: int, key: str, source: int) -> int:
    if held(town.id) or amount == 0:
        return 0
    with explaining():
        term(key, amount, source_node_id=source)
        before = people_in(town)
        shift_stat(town, "population", amount, default=0, low=0)
    return people_in(town) - before


async def shift_town(ctx: TickContext, town_id: int, column: str, amount: int, *, key: str, source: int) -> None:
    profile = await ctx.session.get(SettlementProfileRow, town_id)
    if profile is None or held(town_id) or column in (profile.locked or []) or amount == 0:
        return
    with explaining():
        term(key, amount, source_node_id=source)
        setattr(profile, column, clamp_int(getattr(profile, column) + amount, 0, PERCENT))


async def pay_for(ctx: TickContext, policy: PopulationPolicyRow) -> bool:
    holder = await ctx.session.get(EntityRow, policy.holder_node_id)
    cost = policy.enforcement * ctx.rules.population_policy.enforcement_cost_per_point
    return holder is None or await take_coin(ctx.session, ctx.rules, holder, cost)


async def resist(
    ctx: TickContext, policy: PopulationPolicyRow, instrument: PopulationInstrumentRow, towns: list[int], *, soothing: float, tally: NumbersTally
) -> None:
    table = ctx.rules.population_policy
    odds = table.child_limit_resistance * force(policy, instrument) * (1 - soothing)
    if not ctx.rng(f"population_resist.{policy.id}.{instrument.instrument.value}.{ctx.epoch}").chance(odds):
        return
    if "enforcement" not in (policy.locked or []):
        policy.enforcement = clamp_int(policy.enforcement - table.resistance_enforcement_loss, 0, PERCENT)
    for town in towns:
        await shift_town(
            ctx, town, "unrest", round_half_up(table.expulsion_grievance / TEN), key="population_policy.child_limit_resistance", source=policy.holder_node_id
        )
    await record(
        ctx,
        "population.resisted",
        roles={IncidentRole.SUBJECT: policy.holder_node_id},
        facts={"instrument": instrument.instrument, "enforcement": policy.enforcement},
    )
    tally.resisted += 1


async def apply_instrument(ctx: TickContext, policy: PopulationPolicyRow, instrument: PopulationInstrumentRow, towns: list[int], tally: NumbersTally) -> None:
    table = ctx.rules.population_policy
    weight = force(policy, instrument)
    kind = instrument.instrument
    for town_id in towns:
        town = await ctx.session.get(EntityRow, town_id)
        if town is None:
            continue
        share = round_half_up(people_in(town) * table.migration_share_pct * weight / PERCENT)
        if kind in PULLS or (kind is PopulationInstrument.MADE_BIRTH and await made_minds_near(ctx, town_id)):
            await move_people(ctx, town, share, "population_policy.migration_share_pct", policy.holder_node_id)
        elif kind is PopulationInstrument.EXPULSION and share:
            moved = await move_people(ctx, town, -share, "population_policy.migration_share_pct", policy.holder_node_id)
            await shift_town(
                ctx,
                town_id,
                "unrest",
                round_half_up(table.expulsion_grievance * weight / TEN),
                key="population_policy.expulsion_grievance",
                source=policy.holder_node_id,
            )
            await record(ctx, "population.expulsion", roles={IncidentRole.ACTOR: policy.holder_node_id, IncidentRole.PLACE: town_id}, facts={"people": -moved})
            tally.expelled += 1
        elif kind is PopulationInstrument.MIGRATION_BAN:
            await shift_town(
                ctx,
                town_id,
                "unrest",
                round_half_up(table.expulsion_grievance * weight / (TEN * QUARTER)),
                key="population_policy.expulsion_grievance",
                source=policy.holder_node_id,
            )
        elif kind is PopulationInstrument.HEALTH_CAMPAIGN:
            await shift_town(
                ctx,
                town_id,
                "sanitation",
                round_half_up(table.health_sanitation * weight),
                key="population_policy.health_sanitation",
                source=policy.holder_node_id,
            )
    if kind is PopulationInstrument.RESETTLEMENT and len(towns) > 1:
        await resettle(ctx, policy, weight, towns, tally)


async def resettle(ctx: TickContext, policy: PopulationPolicyRow, weight: float, towns: list[int], tally: NumbersTally) -> None:
    places = [town for town_id in towns if (town := await ctx.session.get(EntityRow, town_id)) is not None and not held(town.id)]
    if len(places) < 2:
        return
    crowded = max(places, key=lambda town: (people_in(town), town.id))
    empty = min(places, key=lambda town: (people_in(town), town.id))
    share = round_half_up(people_in(crowded) * ctx.rules.population_policy.migration_share_pct * weight / PERCENT)
    if crowded.id == empty.id or not share:
        return
    moved = -await move_people(ctx, crowded, -share, "population_policy.migration_share_pct", policy.holder_node_id)
    await move_people(ctx, empty, moved, "population_policy.migration_share_pct", policy.holder_node_id)
    await record(
        ctx,
        "population.resettlement",
        roles={IncidentRole.ACTOR: policy.holder_node_id, IncidentRole.ORIGIN: crowded.id, IncidentRole.DESTINATION: empty.id},
        facts={"people": moved},
    )
    tally.resettled += 1


async def numbers_of(ctx: TickContext, towns: list[int]) -> int:
    total = 0
    for town_id in towns:
        town = await ctx.session.get(EntityRow, town_id)
        total += people_in(town) if town is not None else 0
    return total


async def review(ctx: TickContext, policy: PopulationPolicyRow, towns: list[int], tally: NumbersTally) -> None:
    table = ctx.rules.population_policy
    if ctx.epoch - policy.reviewed_epoch < table.epochs(table.review_years):
        return
    policy.reviewed_epoch = ctx.epoch
    total = await numbers_of(ctx, towns)
    if policy.baseline <= 0:
        policy.baseline = total
        return
    change = (total - policy.baseline) * PERCENT / policy.baseline
    sign = AIM_DIRECTION[policy.aim]
    met = abs(change) <= table.overshoot_pct if sign == 0 else sign * change > table.overshoot_pct
    against = abs(change) > table.overshoot_pct if sign == 0 else sign * change < 0
    if "strength" not in (policy.locked or []):
        if against:
            policy.strength = clamp_int(policy.strength + table.review_step, 0, PERCENT)
        elif met and sign != 0:
            policy.strength = clamp_int(policy.strength - table.review_step, 0, PERCENT)
    if met:
        await record(
            ctx, "population.target_met", roles={IncidentRole.SUBJECT: policy.holder_node_id}, facts={"aim": policy.aim, "change": round_half_up(change)}
        )
        policy.baseline = total
        tally.met += 1


async def repeal(ctx: TickContext, policy: PopulationPolicyRow, tally: NumbersTally) -> None:
    await record(ctx, "population.policy_repealed", roles={IncidentRole.SUBJECT: policy.holder_node_id}, facts={"aim": policy.aim})
    await ctx.session.delete(policy)
    tally.repealed += 1


async def aggrieve(ctx: TickContext, policy: PopulationPolicyRow, towns: list[int], harsh: bool) -> None:
    table = ctx.rules.population_policy
    if not harsh or not towns or "strength" in (policy.locked or []):
        return
    unrest = await ctx.session.scalar(select(func.avg(SettlementProfileRow.unrest)).where(SettlementProfileRow.settlement_entity_id.in_(towns)))
    felt = await lagged(ctx, BalanceLoop.POLICY_GRIEVANCE, policy.holder_node_id, round_half_up(float(unrest or 0)), subject=policy.id)
    if felt < table.grievance_unrest:
        return
    with explaining():
        term("population_policy.grievance_unrest", -table.review_step, source_node_id=policy.holder_node_id)
        policy.strength = clamp_int(policy.strength - table.review_step, 0, PERCENT)


async def keep_policy(ctx: TickContext, policy: PopulationPolicyRow, tally: NumbersTally) -> None:
    table = ctx.rules.population_policy
    if not await pay_for(ctx, policy) and "enforcement" not in (policy.locked or []):
        policy.enforcement = clamp_int(policy.enforcement - table.resistance_enforcement_loss, 0, PERCENT)
    towns = [town for town in await scope_of(ctx.session, policy) if not held(town)]
    instruments = [] if policy.aim is PopulationAim.NONE else await instruments_of(ctx.session, policy.id)
    teaching = next((force(policy, row) for row in instruments if row.instrument is PopulationInstrument.FAITH_TEACHING), 0.0)
    for instrument in instruments:
        await apply_instrument(ctx, policy, instrument, towns, tally)
        if instrument.instrument in HARSH:
            await resist(ctx, policy, instrument, towns, soothing=teaching, tally=tally)
        await record(
            ctx,
            "population.instrument_enforced",
            roles={IncidentRole.SUBJECT: policy.holder_node_id},
            facts={"instrument": instrument.instrument, "strength": round_half_up(force(policy, instrument) * PERCENT)},
        )
        tally.enforced += 1
    await review(ctx, policy, towns, tally)
    await aggrieve(ctx, policy, towns, bool(instruments) and any(row.instrument in HARSH for row in instruments))
    if policy.strength <= 0 and "strength" not in (policy.locked or []):
        await repeal(ctx, policy, tally)


async def adopt(ctx: TickContext, realm: EntityRow, tally: NumbersTally) -> None:
    towns = await towns_in(ctx.session, realm.id)
    if not towns or not ctx.rng(f"population_adopt.{realm.id}.{ctx.epoch}").chance(ctx.rules.population_policy.adopt_pct):
        return
    hunger = sum([(await pressures_of(ctx.session, town)).get(PressureKind.HUNGER, 0) for town in towns]) / len(towns)
    total = await numbers_of(ctx, towns)
    if hunger >= PRESSED:
        aim, instrument = PopulationAim.SHRINK, PopulationInstrument.BIRTH_TAX
    elif total < SPARSE_TOWN * len(towns):
        aim, instrument = PopulationAim.GROW, PopulationInstrument.BIRTH_REWARD
    else:
        return
    policy = PopulationPolicyRow(
        holder_node_id=realm.id,
        aim=aim,
        strength=FIRST_STRENGTH,
        enforcement=FIRST_STRENGTH,
        baseline=total,
        since_epoch=ctx.epoch,
        reviewed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(policy)
    await ctx.session.flush()
    ctx.session.add(PopulationInstrumentRow(policy_id=policy.id, instrument=instrument, holder_node_id=realm.id, strength=FIRST_STRENGTH, locked=[]))
    await record(ctx, "population.policy_adopted", roles={IncidentRole.SUBJECT: realm.id}, facts={"aim": aim})
    tally.adopted += 1


async def keep_numbers(ctx: TickContext) -> NumbersTally:
    tally = NumbersTally()
    for policy in list(await ctx.session.scalars(select(PopulationPolicyRow).order_by(PopulationPolicyRow.id))):
        if not held(policy.holder_node_id):
            await keep_policy(ctx, policy, tally)
    holders = set(await ctx.session.scalars(select(PopulationPolicyRow.holder_node_id)))
    realms = await ctx.session.scalars(
        select(EntityRow)
        .join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for realm in list(realms):
        if realm.id not in holders and not held(realm.id):
            await adopt(ctx, realm, tally)
    await ctx.session.flush()
    return tally
