from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.daily_shapes import SERVICE_COST_PCT, SERVICE_ENDING
from aerona.constants.units import PERCENT
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.daily_life import CareCustomRow, DomesticServiceRow, HouseworkRow, LeisurePursuitRow, SpaceNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.write_guard import held
from aerona.domain.enums.daily_life import LeisureKind, NormKind, ServiceTerms, WashFrequency, WashPlace, WasteHandling
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.daily.service import engage_servant
from aerona.engine.economy.purse import coin_of, give_coin, take_coin
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

TEN = 10
YOUNG = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH})
CARED_FOR = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.ELDER, LifeStage.ANCIENT})
TRAVEL_PURSUITS = frozenset({LeisureKind.TOURISM, LeisureKind.EXCURSION})
WASH_KEEPING = {WashFrequency.NONE: 0, WashFrequency.BY_RITE: 1, WashFrequency.SEASONAL: 1, WashFrequency.WEEKLY: 2, WashFrequency.DAILY: 3}
WASTE_KEEPING = {
    WasteHandling.NONE: 0,
    WasteHandling.PITS: 1,
    WasteHandling.CARRIED_OUT: 2,
    WasteHandling.BURNED: 2,
    WasteHandling.COMPOSTED: 2,
    WasteHandling.SEWERS: 3,
}
WASH_PLACE_KEEPING = {WashPlace.HOME: 1, WashPlace.BATH_HOUSE: 1, WashPlace.RIVER: 0, WashPlace.RITE: 0}
KEEPING_STEPS = 7


@dataclass
class DailyTally:
    stressed: int = 0
    gladdened: int = 0
    towns_kept: int = 0
    shamed: int = 0
    households: int = 0
    breached_duties: int = 0
    servants_left: int = 0
    helped: int = 0
    tours: int = 0
    breaches: int = 0
    trends: int = 0


async def peoples(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )


async def budget_for(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> TimeBudgetRow | None:
    folk = await people_of(ctx.session, mortal)
    if folk is None or mortal.social_class is None:
        return None
    exact = await ctx.session.get(TimeBudgetRow, (folk.id, mortal.social_class, profile.life_stage))
    return exact if exact is not None else await ctx.session.get(TimeBudgetRow, (folk.id, mortal.social_class, LifeStage.ADULT))


async def keep_hours(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    usual = ctx.rules.time_budgets
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal, profile in list(rows):
        if held(mortal.id):
            continue
        budget = await budget_for(ctx, mortal, profile)
        if budget is None:
            continue
        strain = round_half_up(max(0, budget.work - usual.usual_work) / TEN * table.overwork_stress_pct / TEN)
        if strain and "stress" not in (profile.locked or []):
            with explaining():
                term("daily_life.overwork_stress_pct", strain)
                profile.stress = clamp_int(profile.stress + strain, 0, PERCENT)
            tally.stressed += 1
        cheer = round_half_up((budget.leisure - usual.usual_leisure) / TEN * table.leisure_happiness_pct / TEN)
        if cheer and "mood_score" not in (profile.locked or []):
            with explaining():
                term("daily_life.leisure_happiness_pct", cheer)
                profile.mood_score = clamp_int(profile.mood_score + cheer, -PERCENT, PERCENT)
            tally.gladdened += 1


def kept_sanitation(custom: CareCustomRow) -> int:
    keeping = WASH_KEEPING[custom.wash_frequency] + WASTE_KEEPING[custom.waste_handling] + WASH_PLACE_KEEPING[custom.wash_place]
    return clamp_int((custom.cleanliness + keeping * PERCENT // KEEPING_STEPS) // 2, 0, PERCENT)


async def keep_care(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    for custom in list(await ctx.session.scalars(select(CareCustomRow).order_by(CareCustomRow.people_entity_id))):
        target = kept_sanitation(custom)
        for town_id in await towns_of_people(ctx.session, custom.people_entity_id):
            profile = await ctx.session.get(SettlementProfileRow, town_id)
            if profile is None or held(town_id) or "sanitation" in (profile.locked or []):
                continue
            step = round_half_up((target - profile.sanitation) * table.care_disease_pct / PERCENT)
            if step:
                with explaining():
                    term("daily_life.care_disease_pct", step, source_node_id=custom.people_entity_id)
                    profile.sanitation = clamp_int(profile.sanitation + step, 0, PERCENT)
                tally.towns_kept += 1


async def shame_the_poor(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    standards = {row.people_entity_id: row.cleanliness for row in await ctx.session.scalars(select(CareCustomRow).order_by(CareCustomRow.people_entity_id))}
    if not standards:
        return
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal, profile in list(rows):
        folk = await people_of(ctx.session, mortal)
        standard = standards.get(folk.id) if folk is not None else None
        if standard is None or held(mortal.id) or profile.wealth >= standard or "honour" in (profile.locked or []):
            continue
        loss = table.cleanliness_honour_loss
        if not loss:
            continue
        with explaining():
            term("daily_life.cleanliness_honour_loss", -loss, source_node_id=folk.id if folk is not None else None)
            profile.honour = clamp_int(profile.honour - loss, 0, PERCENT)
        await record(
            ctx,
            "daily.norm_breach",
            roles={IncidentRole.ACTOR: mortal.id, IncidentRole.TARGET: folk.id if folk else mortal.id},
            facts={"norm": NormKind.CLEANLINESS},
        )
        tally.shamed += 1


async def household_load(ctx: TickContext, household: HouseholdRow, duties: list[HouseworkRow], members: list[HouseholdMemberRow]) -> int:
    table = ctx.rules.daily_life
    load = sum(row.load for row in duties)
    stages = await ctx.session.execute(
        select(MortalProfileRow.life_stage, MortalProfileRow.health).where(MortalProfileRow.entity_id.in_([member.member_node_id for member in members]))
    )
    for stage, health in stages:
        if stage in CARED_FOR or health < PERCENT // 2:
            load += table.dependant_load
    servants = household.servants + int(
        await ctx.session.scalar(select(DomesticServiceRow.servant_node_id).where(DomesticServiceRow.household_id == household.id).limit(1)) is not None
    )
    helpers = {row.doer_node_id for row in duties if row.doer_role is HouseholdRole.SERVANT}
    return clamp_int(load - (servants + len(helpers)) * table.servant_relief_pct, 0, PERCENT)


async def take_help(ctx: TickContext, household: HouseholdRow, load: int, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    felt = await lagged(ctx, BalanceLoop.HOUSEWORK_BURDEN, household.head_node_id, load, subject=household.id)
    if felt < table.heavy_load or household.head_node_id is None or "servants" in (household.locked or []) or household.wealth < table.burdened_hire_wealth:
        return
    if await engage_servant(ctx, household, ServiceTerms.WAGE, table.servant_wage) is None:
        with explaining():
            term("daily_life.burdened_hire_wealth", 1, source_node_id=household.head_node_id)
            household.servants += 1
    await record(ctx, "daily.help_taken", roles={IncidentRole.ACTOR: household.head_node_id}, facts={"load": felt})
    tally.helped += 1


async def keep_houses(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    duties: dict[int, list[HouseworkRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(HouseworkRow).order_by(HouseworkRow.household_id, HouseworkRow.id)):
        duties[row.household_id].append(row)
    if not duties:
        return
    members: dict[int, list[HouseholdMemberRow]] = defaultdict(list)
    for member in await ctx.session.scalars(
        select(HouseholdMemberRow).where(HouseholdMemberRow.household_id.in_(sorted(duties))).order_by(HouseholdMemberRow.member_node_id)
    ):
        members[member.household_id].append(member)
    for household_id in sorted(duties):
        household = await ctx.session.get(HouseholdRow, household_id)
        if household is None or held(household.head_node_id):
            continue
        load = await household_load(ctx, household, duties[household_id], members[household_id])
        tally.households += 1
        present = {member.member_node_id for member in members[household_id]}
        for row in duties[household_id]:
            if row.doer_node_id not in present and row.doer_role is not HouseholdRole.SERVANT and household.head_node_id is not None:
                await record(ctx, "daily.duty_breached", roles={IncidentRole.TARGET: household.head_node_id}, facts={"duty": row.duty})
                tally.breached_duties += 1
        await take_help(ctx, household, load, tally)
        if load < table.heavy_load:
            continue
        for row in duties[household_id]:
            profile = await ctx.session.get(MortalProfileRow, row.doer_node_id)
            if profile is None or held(row.doer_node_id):
                continue
            if profile.life_stage in YOUNG and "education" not in (profile.locked or []) and table.load_schooling_loss:
                with explaining():
                    term("daily_life.load_schooling_loss", -table.load_schooling_loss, source_node_id=household.head_node_id)
                    profile.education = clamp_int(profile.education - table.load_schooling_loss, 0, PERCENT)
            if "stress" not in (profile.locked or []) and table.load_stress:
                with explaining():
                    term("daily_life.load_stress", table.load_stress, source_node_id=household.head_node_id)
                    profile.stress = clamp_int(profile.stress + table.load_stress, 0, PERCENT)


async def pay_servants(ctx: TickContext, tally: DailyTally) -> None:
    for service in list(await ctx.session.scalars(select(DomesticServiceRow).order_by(DomesticServiceRow.servant_node_id))):
        household = await ctx.session.get(HouseholdRow, service.household_id)
        if household is None or held(service.servant_node_id, household.head_node_id):
            continue
        cost = round_half_up(service.wage * SERVICE_COST_PCT[service.terms] / PERCENT)
        if service.terms is ServiceTerms.BOUND:
            if not ctx.rng(f"bound_flight.{service.servant_node_id}.{ctx.epoch}").chance(ctx.rules.daily_life.bound_flight_pct):
                continue
        elif household.wealth >= cost:
            household.wealth -= cost
            continue
        await ctx.session.delete(service)
        if household.head_node_id is not None:
            await record(
                ctx,
                "daily.servant_left",
                roles={IncidentRole.ACTOR: household.head_node_id, IncidentRole.SUBJECT: service.servant_node_id},
                facts={"reason": SERVICE_ENDING[service.terms]},
            )
        tally.servants_left += 1


async def go_travelling(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    rows = await ctx.session.scalars(
        select(LeisurePursuitRow)
        .where(LeisurePursuitRow.kind.in_(sorted(TRAVEL_PURSUITS)), LeisurePursuitRow.venue_node_id.is_not(None))
        .order_by(LeisurePursuitRow.id)
    )
    for pursuit in list(rows):
        traveller = await ctx.session.get(EntityRow, pursuit.holder_node_id)
        place = await ctx.session.get(EntityRow, pursuit.venue_node_id) if pursuit.venue_node_id is not None else None
        if traveller is None or place is None or traveller.status is not EntityStatus.CANON or held(traveller.id, place.id):
            continue
        spend = await coin_of(ctx.session, ctx.rules, traveller) * table.tourism_spend_pct * pursuit.share // (PERCENT * PERCENT)
        if spend < table.tourism_coin_min or not await take_coin(ctx.session, ctx.rules, traveller, spend):
            continue
        await give_coin(ctx.session, ctx.rules, place, spend)
        await record(
            ctx,
            "daily.tourism_season",
            roles={IncidentRole.ACTOR: traveller.id, IncidentRole.DESTINATION: place.id},
            facts={"pursuit": pursuit.kind, "coin": spend},
            place=place.id,
        )
        tally.tours += 1


def differences(first: SpaceNormRow, second: SpaceNormRow) -> list[NormKind]:
    found: list[NormKind] = []
    if first.distance is not second.distance:
        found.append(NormKind.DISTANCE)
    if first.touch is not second.touch:
        found.append(NormKind.TOUCH)
    if first.posture is not second.posture:
        found.append(NormKind.POSTURE)
    return found


async def mind_space(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    norms = {row.people_entity_id: row for row in await ctx.session.scalars(select(SpaceNormRow).order_by(SpaceNormRow.people_entity_id))}
    if len(norms) < 2 or not table.space_breach_trust_loss:
        return
    rows = await ctx.session.scalars(
        select(CommunityRelationRow)
        .where(CommunityRelationRow.entity_a_id.in_(sorted(norms)), CommunityRelationRow.entity_b_id.in_(sorted(norms)))
        .order_by(CommunityRelationRow.entity_a_id, CommunityRelationRow.entity_b_id)
    )
    for relation in list(rows):
        if held(relation.entity_a_id, relation.entity_b_id):
            continue
        broken = differences(norms[relation.entity_a_id], norms[relation.entity_b_id])
        if not broken:
            continue
        loss = table.space_breach_trust_loss * len(broken)
        with explaining():
            term("daily_life.space_breach_trust_loss", -loss)
            relation.value = clamp_int(relation.value - loss, -PERCENT, PERCENT)
        await record(
            ctx,
            "daily.norm_breach",
            roles={IncidentRole.ACTOR: relation.entity_a_id, IncidentRole.TARGET: relation.entity_b_id},
            facts={"norm": broken[0]},
        )
        tally.breaches += 1


async def follow_trends(ctx: TickContext, tally: DailyTally) -> None:
    table = ctx.rules.daily_life
    for folk in await peoples(ctx):
        own = list(await ctx.session.scalars(select(LeisurePursuitRow).where(LeisurePursuitRow.holder_node_id == folk.id).order_by(LeisurePursuitRow.kind)))
        if not own or held(folk.id):
            continue
        before = max(own, key=lambda row: (row.share, -list(LeisureKind).index(row.kind))).kind
        mortals = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        chosen = Counter[LeisureKind]()
        for row in await ctx.session.scalars(select(LeisurePursuitRow).where(LeisurePursuitRow.holder_node_id.in_(mortals)).order_by(LeisurePursuitRow.id)):
            mortal = await ctx.session.get(EntityRow, row.holder_node_id)
            if mortal is not None and (found := await people_of(ctx.session, mortal)) is not None and found.id == folk.id:
                chosen[row.kind] += row.share
        if not chosen:
            continue
        leader = max(sorted(chosen), key=lambda kind: chosen[kind])
        for row in own:
            if "share" in (row.locked or []):
                continue
            step = table.trend_drift if row.kind is leader else -table.trend_drift if row.share > 0 else 0
            if step:
                with explaining():
                    term("daily_life.trend_drift", step, source_node_id=folk.id)
                    row.share = clamp_int(row.share + step, 0, PERCENT)
        after = max(own, key=lambda row: (row.share, -list(LeisureKind).index(row.kind))).kind
        if after is not before:
            await record(ctx, "daily.leisure_trend", roles={IncidentRole.SUBJECT: folk.id}, facts={"before": before, "after": after})
            tally.trends += 1


async def keep_daily_life(ctx: TickContext) -> DailyTally:
    tally = DailyTally()
    await keep_hours(ctx, tally)
    await keep_care(ctx, tally)
    await shame_the_poor(ctx, tally)
    await keep_houses(ctx, tally)
    await pay_servants(ctx, tally)
    await go_travelling(ctx, tally)
    await mind_space(ctx, tally)
    await follow_trends(ctx, tally)
    await ctx.session.flush()
    return tally
