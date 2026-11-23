from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life.customs import KEPT_HOUSE_DUTIES
from aerona.catalog.mind import COMBAT_SKILLS, CRAFT_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.daily_life import HouseworkRow, LeisurePursuitRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionPlaceRow, CollectionRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import AccountKind, AccountMedium
from aerona.domain.enums.daily_life import HouseDuty, LeisureKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import DecisionRule
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.collective.accounts import record as tell_account
from aerona.engine.context import TickContext
from aerona.engine.daily.life import household_load
from aerona.engine.mind.skills import practise_any
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

TEN = 10
AILING = PERCENT // 2
PRACTISED = (*COMBAT_SKILLS, *CRAFT_SKILLS)


@dataclass
class WaysTally:
    tended: int = 0
    rites_kept: int = 0
    neglected: int = 0
    watched: int = 0
    trained: int = 0
    danced: int = 0
    told: int = 0
    hunted: int = 0
    budgets_moved: int = 0


async def duty_rows(ctx: TickContext) -> dict[int, list[HouseworkRow]]:
    found: dict[int, list[HouseworkRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(HouseworkRow).order_by(HouseworkRow.household_id, HouseworkRow.id)):
        found[row.household_id].append(row)
    return found


async def neglect(ctx: TickContext, household: HouseholdRow, duty: HouseDuty, load: int, tally: WaysTally) -> None:
    if household.head_node_id is None:
        return
    await record(ctx, "household.duty_neglected", roles={IncidentRole.TARGET: household.head_node_id}, facts={"duty": duty, "load": load})
    tally.neglected += 1


async def tend_sick(ctx: TickContext, members: list[HouseholdMemberRow], tally: WaysTally) -> None:
    share = ctx.rules.daily_life.sickcare_recovery_pct
    for member in members:
        profile = await ctx.session.get(MortalProfileRow, member.member_node_id)
        if profile is None or profile.health >= AILING or "health" in (profile.locked or []) or held(member.member_node_id):
            continue
        gain = round_half_up((PERCENT - profile.health) * share / PERCENT)
        if gain:
            with explaining():
                term("daily_life.sickcare_recovery_pct", gain, source_node_id=member.member_node_id)
                profile.health = clamp_int(profile.health + gain, 0, PERCENT)
            tally.tended += 1


async def keep_household_duties(ctx: TickContext, tally: WaysTally) -> None:
    heavy = ctx.rules.daily_life.heavy_load
    rites: dict[int, int] = defaultdict(int)
    for household_id, rows in sorted((await duty_rows(ctx)).items()):
        duties = {row.duty for row in rows}
        if not duties & set(KEPT_HOUSE_DUTIES):
            continue
        household = await ctx.session.get(HouseholdRow, household_id)
        if household is None or held(household.head_node_id):
            continue
        members = list(
            await ctx.session.scalars(
                select(HouseholdMemberRow).where(HouseholdMemberRow.household_id == household_id).order_by(HouseholdMemberRow.member_node_id)
            )
        )
        load = await household_load(ctx, household, rows, members)
        lapsed = load >= heavy
        if HouseDuty.SICKCARE in duties:
            if lapsed:
                await neglect(ctx, household, HouseDuty.SICKCARE, load, tally)
            else:
                await tend_sick(ctx, members, tally)
        if HouseDuty.HOUSEHOLD_RITES in duties and household.settlement_node_id is not None:
            rites[household.settlement_node_id] += -1 if lapsed else 1
            if lapsed:
                await neglect(ctx, household, HouseDuty.HOUSEHOLD_RITES, load, tally)
            else:
                tally.rites_kept += 1
    await shift_piety(ctx, rites)


async def shift_piety(ctx: TickContext, rites: dict[int, int]) -> None:
    for town_id, balance in sorted(rites.items()):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or held(town_id):
            continue
        households = await ctx.session.scalar(select(func.count(HouseholdRow.id)).where(HouseholdRow.settlement_node_id == town_id)) or 1
        step = round_half_up(ctx.rules.daily_life.household_rites_piety * balance / households)
        if step:
            with explaining():
                term("daily_life.household_rites_piety", step, source_node_id=town_id)
                set_stats(town, piety=clamp_int(stat_or(town, "piety", 0) + step, 0, PERCENT))


async def adult_budget(ctx: TickContext, people_id: int) -> tuple[int, int]:
    rows = list(
        await ctx.session.scalars(select(TimeBudgetRow).where(TimeBudgetRow.people_entity_id == people_id, TimeBudgetRow.life_stage == LifeStage.ADULT))
    )
    if not rows:
        return 0, 0
    return max(row.civic for row in rows), max(row.training for row in rows)


async def keep_watch(ctx: TickContext, people: EntityRow, civic: int, tally: WaysTally) -> None:
    for town_id in await towns_of_people(ctx.session, people.id):
        town = await ctx.session.get(SettlementProfileRow, town_id)
        if town is None or held(town_id) or "crime" in (town.locked or []):
            continue
        cut = round_half_up(town.crime * ctx.rules.daily_life.civic_watch_pct * civic / (PERCENT * PERCENT))
        if cut:
            with explaining():
                term("daily_life.civic_watch_pct", -cut, source_node_id=town_id)
                town.crime = clamp_int(town.crime - cut, 0, PERCENT)
            tally.watched += 1


async def train(ctx: TickContext, people: EntityRow, training: int, tally: WaysTally) -> None:
    gain = ctx.rules.daily_life.training_skill_gain * training / TEN
    if gain <= 0:
        return
    mortals = await ctx.session.scalars(
        select(MortalProfileRow.entity_id)
        .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
        .where(MortalProfileRow.life_stage == LifeStage.ADULT, EntityRow.status == EntityStatus.CANON)
        .order_by(MortalProfileRow.entity_id)
    )
    towns = set(await towns_of_people(ctx.session, people.id))
    for mortal_id in list(mortals):
        mortal = await ctx.session.get(EntityRow, mortal_id)
        if mortal is None or mortal.location_id not in towns or held(mortal_id):
            continue
        await practise_any(ctx.session, ctx.rules, mortal_id, PRACTISED, gain, epoch=ctx.epoch)
        tally.trained += 1


async def leisure_of(ctx: TickContext, people_id: int) -> dict[LeisureKind, int]:
    rows = await ctx.session.scalars(select(LeisurePursuitRow).where(LeisurePursuitRow.holder_node_id == people_id))
    return {row.kind: row.share for row in rows}


async def dance(ctx: TickContext, people: EntityRow, share: int, tally: WaysTally) -> None:
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    if culture is None or "cohesion" in (culture.locked or []):
        return
    step = round_half_up(ctx.rules.daily_life.dance_cohesion * share / TEN)
    if step:
        with explaining():
            term("daily_life.dance_cohesion", step, source_node_id=people.id)
            culture.cohesion = clamp_int(culture.cohesion + step, 0, PERCENT)
        tally.danced += 1


async def tell_tales(ctx: TickContext, people: EntityRow, share: int, tally: WaysTally) -> None:
    chance = ctx.rules.daily_life.storytelling_legend_pct * share / PERCENT
    if not ctx.rng(f"leisure.tale.{people.id}.{ctx.epoch}").chance(chance):
        return
    towns = await towns_of_people(ctx.session, people.id)
    past = await ctx.session.scalar(
        select(CollectionRow.id)
        .join(CollectionPlaceRow, CollectionPlaceRow.collection_id == CollectionRow.id)
        .where(CollectionPlaceRow.place_entity_id.in_(towns), CollectionRow.start_epoch < ctx.epoch)
        .order_by(CollectionRow.start_epoch, CollectionRow.id)
        .limit(1)
    )
    if past is None:
        return
    account = await tell_account(ctx, people, AccountKind.FOLK_MEMORY, fidelity=PERCENT // 2, stances={}, collection_id=past, medium=AccountMedium.ORAL)
    if account is not None:
        await record(ctx, "daily.tale_told", roles={IncidentRole.SUBJECT: people.id}, facts={"share": share})
        tally.told += 1


async def hunt_for_pleasure(ctx: TickContext, people: EntityRow, share: int, atlas: RegionAtlas, tally: WaysTally) -> None:
    pressure = round_half_up(ctx.rules.daily_life.leisure_hunt_pressure * share / PERCENT * TEN)
    if pressure <= 0:
        return
    regions = sorted({region for town in await towns_of_people(ctx.session, people.id) if (region := atlas.top_region(town)) is not None})
    for region_id in regions:
        game = await ctx.session.scalar(
            select(SpeciesRangeRow)
            .where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0)
            .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.species_entity_id)
            .limit(1)
        )
        if game is None or held(game.species_entity_id):
            continue
        with explaining():
            term("daily_life.leisure_hunt_pressure", -pressure, source_node_id=people.id)
            game.abundance = clamp_int(game.abundance - pressure, 0, PERCENT)
            game.hunted = clamp_int(game.hunted + pressure, 0, PERCENT)
        tally.hunted += 1


async def keep_folk_ways(ctx: TickContext, peoples: list[EntityRow], tally: WaysTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    for people in peoples:
        if held(people.id):
            continue
        civic, training = await adult_budget(ctx, people.id)
        if civic:
            await keep_watch(ctx, people, civic, tally)
        if training:
            await train(ctx, people, training, tally)
        shares = await leisure_of(ctx, people.id)
        if shares.get(LeisureKind.DANCE, 0):
            await dance(ctx, people, shares[LeisureKind.DANCE], tally)
        if shares.get(LeisureKind.STORYTELLING, 0):
            await tell_tales(ctx, people, shares[LeisureKind.STORYTELLING], tally)
        if shares.get(LeisureKind.HUNTING, 0):
            await hunt_for_pleasure(ctx, people, shares[LeisureKind.HUNTING], atlas, tally)


BUDGET_FIXUP = "daily_life.w52"
WARRIOR_TRAINING = 10
ASSEMBLY_CIVIC = 5
GATHERED_RULE = frozenset({DecisionRule.ASSEMBLY, DecisionRule.COUNCIL})


def give_time(row: TimeBudgetRow, field: str, share: int) -> bool:
    if field in (row.locked or []) or getattr(row, field) >= share:
        return False
    need = share - getattr(row, field)
    taken = min(need, row.work)
    row.work -= taken
    row.rest = max(0, row.rest - (need - taken))
    setattr(row, field, share)
    return True


async def gathered_peoples(ctx: TickContext) -> set[int]:
    found: set[int] = set()
    for core in await ctx.session.scalars(
        select(PolityProfileRow.core_entity_id).where(PolityProfileRow.decision_rule.in_(sorted(GATHERED_RULE)), PolityProfileRow.core_entity_id.is_not(None))
    ):
        entity = await ctx.session.get(EntityRow, core)
        folk = (
            entity if entity is not None and entity.entity_type is EntityType.PEOPLE else await people_of(ctx.session, entity) if entity is not None else None
        )
        if folk is not None:
            found.add(folk.id)
    return found


async def backfill_budgets(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, BUDGET_FIXUP) is not None:
        return 0
    gathered = await gathered_peoples(ctx)
    moved = 0
    for row in list(
        await ctx.session.scalars(select(TimeBudgetRow).order_by(TimeBudgetRow.people_entity_id, TimeBudgetRow.social_class, TimeBudgetRow.life_stage))
    ):
        if held(row.people_entity_id):
            continue
        if row.social_class is SocialClass.WARRIOR:
            moved += give_time(row, "training", WARRIOR_TRAINING)
        if row.people_entity_id in gathered:
            moved += give_time(row, "civic", ASSEMBLY_CIVIC)
    ctx.session.add(AppliedFixupRow(key=BUDGET_FIXUP, result={"budgets": moved}))
    await ctx.session.flush()
    return moved


async def keep_ways(ctx: TickContext, peoples: list[EntityRow]) -> WaysTally:
    tally = WaysTally()
    tally.budgets_moved = await backfill_budgets(ctx)
    await keep_household_duties(ctx, tally)
    await keep_folk_ways(ctx, peoples, tally)
    return tally
