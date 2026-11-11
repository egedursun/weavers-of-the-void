from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import inspect, select

from aerona.catalog.genetics import CLASS_INCOME_PCT, DWELLINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import DwellingFurnishingRow, DwellingRow, HouseholdAggregateRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.ownership import SiteProfitRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.genetics import DwellingKind, HouseholdDecision, HouseholdRole
from aerona.domain.enums.mind import ActKind, ThoughtKind, ValueHolder
from aerona.domain.enums.mortal import DeathCause, LifeStage, MarriageKind
from aerona.domain.enums.polity import LawKind, OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import preference_bonus
from aerona.engine.demography.kinship import has_room, may_wed
from aerona.engine.factions.guilds import enrol_apprentice
from aerona.engine.genetics.genome import body_marks
from aerona.engine.households.formation import OLD, YOUNG, found_household, join_household
from aerona.engine.households.homes import district_for, dwelling_of, expectation, home_quality, starting_quality
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.ethics import ethic_reading
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kin import children_of, spouses_of
from aerona.engine.mortal.kinship import marry
from aerona.engine.notes import note
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.records import death_path
from aerona.engine.urban.desirability import land_value_of

MEMBERS = "members"
WEALTH = "wealth"
PRESTIGE_SWING = 2
PRESTIGE_MIDPOINT = 5
CLASS_DWELLING: dict[SocialClass, DwellingKind] = {
    SocialClass.NOBLE: DwellingKind.MANOR,
    SocialClass.MERCHANT: DwellingKind.TOWNHOUSE,
    SocialClass.PRIEST: DwellingKind.TOWNHOUSE,
    SocialClass.SCRIBE: DwellingKind.TOWNHOUSE,
    SocialClass.ARTISAN: DwellingKind.TOWNHOUSE,
    SocialClass.WARRIOR: DwellingKind.LONGHOUSE,
    SocialClass.FARMER: DwellingKind.LONGHOUSE,
    SocialClass.MONASTIC: DwellingKind.TOWER,
    SocialClass.SERF_OR_SLAVE: DwellingKind.HUT,
    SocialClass.OUTCAST: DwellingKind.HUT,
}
CRAFT_MASTERS = frozenset({MortalRole.ARTISAN, MortalRole.HEALER, MortalRole.SCRIBE, MortalRole.MERCHANT})


@dataclass
class HouseholdTally:
    pruned: int = 0
    decided: int = 0
    acts: int = 0
    proud: int = 0
    ashamed: int = 0
    aggregates: int = 0


@dataclass
class Member:
    row: HouseholdMemberRow
    mortal: EntityRow
    profile: MortalProfileRow | None

    @property
    def stage(self) -> LifeStage | None:
        return self.profile.life_stage if self.profile is not None else None

    @property
    def grown(self) -> bool:
        return self.stage not in YOUNG and self.stage not in OLD


async def members_of(ctx: TickContext, household: HouseholdRow) -> list[Member]:
    found: list[Member] = []
    for row in await ctx.session.scalars(select(HouseholdMemberRow).where(HouseholdMemberRow.household_id == household.id)):
        mortal = await ctx.session.get(EntityRow, row.member_node_id)
        if mortal is not None:
            found.append(Member(row, mortal, await ctx.session.get(MortalProfileRow, mortal.id)))
    return found


async def prune(ctx: TickContext, members: list[Member], tally: HouseholdTally) -> list[Member]:
    living: list[Member] = []
    for member in members:
        if member.mortal.status is EntityStatus.CANON or held(member.mortal.id):
            living.append(member)
        elif not member.row.locked:
            await ctx.session.delete(member.row)
            tally.pruned += 1
    return living


def pick_head(members: list[Member]) -> Member:
    pool = [member for member in members if member.stage not in YOUNG] or members
    return max(
        pool, key=lambda member: (member.row.role is HouseholdRole.HEIR, member.row.role is HouseholdRole.SPOUSE, -member.mortal.birth_epoch, -member.mortal.id)
    )


async def assign_roles(ctx: TickContext, household: HouseholdRow, members: list[Member]) -> None:
    if MEMBERS in (household.locked or []) or not members:
        return
    head = next((member for member in members if member.mortal.id == household.head_node_id), None) or pick_head(members)
    household.head_node_id = head.mortal.id
    spouses = set(await spouses_of(ctx.session, head.mortal.id))
    children = set(await children_of(ctx.session, head.mortal.id))
    heirs = sorted((member for member in members if member.mortal.id in children), key=lambda member: (member.mortal.birth_epoch, member.mortal.id))
    heir_id = heirs[0].mortal.id if heirs else None
    needing = [member for member in members if not member.grown]
    for member in members:
        if member.row.locked:
            continue
        if member is head:
            member.row.role = HouseholdRole.HEAD
        elif member.mortal.id in spouses:
            member.row.role = HouseholdRole.SPOUSE
        elif member.row.role in (HouseholdRole.SERVANT, HouseholdRole.WARD, HouseholdRole.LODGER):
            continue
        elif not member.grown:
            member.row.role = HouseholdRole.DEPENDENT
        elif member.mortal.id == heir_id:
            member.row.role = HouseholdRole.HEIR
        else:
            member.row.role = HouseholdRole.CARER if needing else HouseholdRole.DEPENDENT
    carers = [member for member in members if member.row.role is HouseholdRole.CARER and not member.row.locked]
    for index, carer in enumerate(carers):
        carer.row.cares_for_node_id = needing[index % len(needing)].mortal.id if needing else None
    if "dependents" not in (household.locked or []):
        household.dependents = sum(1 for member in members if member.row.role is HouseholdRole.DEPENDENT)


async def holdings(ctx: TickContext, member_ids: list[int]) -> int:
    rows = await ctx.session.scalars(select(SiteProfitRow.profit).where(SiteProfitRow.owner_node_id.in_(member_ids), SiteProfitRow.epoch == ctx.epoch))
    return max(0, sum(rows))


async def ruler_draw(ctx: TickContext, household: HouseholdRow) -> int:
    if household.head_node_id is None:
        return 0
    office = await ctx.session.scalar(
        select(OfficeRow).where(OfficeRow.holder_entity_id == household.head_node_id, OfficeRow.kind.in_([OfficeKind.RULER, OfficeKind.REGENT])).limit(1)
    )
    realm = await ctx.session.get(PolityProfileRow, office.polity_entity_id) if office is not None else None
    if realm is None or held(realm.polity_entity_id) or "treasury" in (realm.locked or []):
        return 0
    drawn = min(realm.treasury, ctx.rules.households.ruler_draw)
    realm.treasury -= drawn
    return drawn


def law_rate(laws: LawBook, place: int | None, kind: LawKind, fallback: int) -> int:
    if place is None or laws.in_force(place, kind) is None:
        return fallback
    value = laws.param(place, kind, "rate")
    return int(value) if isinstance(value, int) else fallback


async def keep_purse(ctx: TickContext, household: HouseholdRow, members: list[Member], dwelling: DwellingRow | None, laws: LawBook) -> None:
    table = ctx.rules.households
    locked = set(household.locked or [])
    workers = sum(1 for member in members if member.grown and member.row.role is not HouseholdRole.SERVANT)
    lodgers = sum(1 for member in members if member.row.role is HouseholdRole.LODGER)
    own = sum(member.profile.wealth for member in members if member.profile is not None)
    weight = CLASS_INCOME_PCT.get(household.social_class, PERCENT) if household.social_class is not None else PERCENT
    income = (
        round_half_up(workers * table.worker_income * weight / PERCENT)
        + await ruler_draw(ctx, household)
        + round_half_up(own * table.wealth_income_pct / PERCENT)
        + round_half_up(await holdings(ctx, [member.mortal.id for member in members]) * table.holding_income_pct / PERCENT)
        + lodgers * table.lodger_rent
    )
    upkeep = round_half_up(DWELLINGS[dwelling.kind].upkeep * table.upkeep_pct / PERCENT) if dwelling is not None else 0
    head = household.head_node_id
    faithful = bool(await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[head])) if head is not None else False
    place = household.settlement_node_id
    tithe = round_half_up(income * law_rate(laws, place, LawKind.TITHE, table.tithe_pct) / PERCENT) if faithful else 0
    tax = round_half_up(income * law_rate(laws, place, LawKind.TAX_RATE, table.tax_pct) / PERCENT)
    rent = round_half_up(await land_value_of(ctx.session, place) * ctx.rules.desirability.rent / PERCENT) if place is not None else 0
    expenses = len(members) * table.food_cost + upkeep + tithe + tax + household.servants * table.servant_wage + rent
    if "income" not in locked:
        household.income = income
    if "expenses" not in locked:
        household.expenses = expenses
    if WEALTH not in locked:
        household.wealth = max(0, household.wealth + household.income - household.expenses)
    if dwelling is not None and "quality" not in (dwelling.locked or []) and household.wealth <= 0 and household.income < household.expenses:
        dwelling.quality = clamp_int(dwelling.quality - table.decay, 0, PERCENT)


def transfer(payer: HouseholdRow, payee: HouseholdRow, amount: int) -> bool:
    return move_amount(payer, payee, WEALTH, amount)


async def pay_debts(ctx: TickContext, household: HouseholdRow) -> None:
    if not household.debts or "debts" in (household.locked or []):
        return
    rate = ctx.rules.households.usury_interest_pct
    remaining: dict[str, int] = {}
    for lender_key, principal in sorted(household.debts.items()):
        lender = await ctx.session.get(HouseholdRow, int(lender_key))
        if lender is None or principal <= 0:
            continue
        interest = round_half_up(principal * rate / PERCENT)
        if household.wealth >= principal + interest and transfer(household, lender, principal + interest):
            continue
        paid = min(household.wealth, interest)
        remaining[lender_key] = principal + interest - (paid if transfer(household, lender, paid) else 0)
    household.debts = remaining


async def wounded(ctx: TickContext, mortal_id: int) -> bool:
    _scars, missing = await body_marks(ctx.session, mortal_id)
    return missing > 0


async def bear_burden(ctx: TickContext, household: HouseholdRow, members: list[Member]) -> None:
    table = ctx.rules.households
    cared = {member.row.cares_for_node_id for member in members if member.row.role is HouseholdRole.CARER}
    burden = 0
    for member in members:
        frail = member.stage in OLD or await wounded(ctx, member.mortal.id)
        if member.row.role is HouseholdRole.DEPENDENT and member.mortal.id not in cared:
            burden += table.dependent_burden
        if frail:
            if household.wealth >= table.respected_wealth:
                await think(ctx.session, ctx.rules, member.mortal.id, ThoughtKind.RESPECTED, ctx.epoch)
            else:
                burden += table.maimed_burden
    if "burden" not in (household.locked or []):
        household.burden = clamp_int(burden, 0, PERCENT)
    strain = household.burden * table.burden_stress / PERCENT
    if strain <= 0:
        return
    for member in members:
        if member.profile is not None and member.row.role in (HouseholdRole.HEAD, HouseholdRole.SPOUSE, HouseholdRole.CARER) and not held(member.mortal.id):
            member.profile.stress = clamp_int(member.profile.stress + strain, 0, PERCENT)


async def tolerated(ctx: TickContext, head_id: int, act: ActKind) -> bool:
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, head_id)
    return await ethic_reading(ctx.session, ctx.rules, head_id, act, values) >= ctx.rules.households.tolerated_at


async def decided(ctx: TickContext, household: HouseholdRow, decision: HouseholdDecision, text: str, ids: list[int], *, tally: HouseholdTally) -> bool:
    household.last_decision = decision
    household.decided_epoch = ctx.epoch
    tally.decided += 1
    await note(ctx, text, key=f"households.{decision.value}", ids=ids, kind=ChronicleKind.WORLD)
    return True


async def give_up_infant(ctx: TickContext, household: HouseholdRow, members: list[Member], head: EntityRow, tally: HouseholdTally) -> bool:
    infants = [member for member in members if member.stage is LifeStage.INFANT and not held(member.mortal.id)]
    if not infants or not ctx.rng(f"households.infant.{household.id}.{ctx.epoch}").chance(ctx.rules.households.infanticide_pct):
        return False
    if not await tolerated(ctx, head.id, ActKind.INFANTICIDE):
        return False
    infant = infants[-1].mortal
    await death_path(ctx, infant, "was given up to the cold in a year of want", killer_id=head.id, manner=DeathCause.EXPOSURE)
    await judged(ctx, head.id, infant.id, ActKind.INFANTICIDE, note=f"gave up {infant.name} in a year of want")
    tally.acts += 1
    return True


async def leave_elder(ctx: TickContext, household: HouseholdRow, members: list[Member], head: EntityRow, tally: HouseholdTally) -> bool:
    elders = [member for member in members if member.stage in OLD and not member.row.locked and not held(member.mortal.id)]
    if not elders or not ctx.rng(f"households.elder.{household.id}.{ctx.epoch}").chance(ctx.rules.households.abandon_pct):
        return False
    if not await tolerated(ctx, head.id, ActKind.ABANDONING_ELDERS):
        return False
    elder = elders[0].mortal
    await ctx.session.delete(elders[0].row)
    await ctx.session.flush()
    alone = await found_household(ctx, elder)
    dwelling = await dwelling_of(ctx.session, alone.id)
    if dwelling is not None:
        dwelling.quality = clamp_int(dwelling.quality // 2, 0, PERCENT)
    await judged(ctx, head.id, elder.id, ActKind.ABANDONING_ELDERS, note=f"left {elder.name} to fend alone")
    await note(ctx, f"In want, {household.name} left {elder.name} to fend alone.", key="households.abandon", ids=[head.id, elder.id])
    tally.acts += 1
    return True


async def richer_place(ctx: TickContext, household: HouseholdRow) -> EntityRow | None:
    here = await ctx.session.get(EntityRow, household.settlement_node_id) if household.settlement_node_id is not None else None
    if here is None or here.location_id is None:
        return None
    prosperity = stat(here, "prosperity") or 0
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == here.location_id)
        .order_by(EntityRow.id)
    )
    best = max(
        (town for town in towns if town.id != here.id and (stat(town, "prosperity") or 0) > prosperity),
        key=lambda town: stat(town, "prosperity") or 0,
        default=None,
    )
    return best if best is not None and not held(best.id) else None


async def migrate(
    ctx: TickContext, household: HouseholdRow, members: list[Member], dwelling: DwellingRow | None, tally: HouseholdTally, *, forced: bool = False
) -> bool:
    table = ctx.rules.households
    if not forced and (household.burden < table.migrate_burden or not ctx.rng(f"households.migrate.{household.id}.{ctx.epoch}").chance(table.migrate_pct)):
        return False
    target = await richer_place(ctx, household)
    if target is None or any(held(member.mortal.id) for member in members):
        return False
    for member in members:
        member.mortal.location_id = target.id
    household.settlement_node_id = target.id
    if dwelling is not None:
        dwelling.settlement_node_id = target.id
        dwelling.district_id = await district_for(ctx.session, target.id, household.social_class)
    return await decided(ctx, household, HouseholdDecision.MIGRATE, f"{household.name} left in want for {target.name}.", [target.id], tally=tally)


async def sell_furnishing(ctx: TickContext, household: HouseholdRow, dwelling: DwellingRow | None, tally: HouseholdTally) -> bool:
    if dwelling is None or WEALTH in (household.locked or []):
        return False
    item = await ctx.session.scalar(
        select(DwellingFurnishingRow).where(DwellingFurnishingRow.dwelling_id == dwelling.id).order_by(DwellingFurnishingRow.item_node_id).limit(1)
    )
    if item is None or held(item.item_node_id):
        return False
    await ctx.session.delete(item)
    household.wealth += ctx.rules.households.renovate_cost // 2
    return await decided(ctx, household, HouseholdDecision.SELL_FURNISHING, f"{household.name} sold a furnishing to get by.", [item.item_node_id], tally=tally)


async def match(ctx: TickContext, household: HouseholdRow, members: list[Member], tally: HouseholdTally) -> bool:
    single: Member | None = None
    for member in members:
        free = member.grown and not held(member.mortal.id) and not await spouses_of(ctx.session, member.mortal.id)
        if free and await has_room(ctx.session, ctx.rules, member.mortal):
            single = member
            break
    if single is None or household.settlement_node_id is None:
        return False
    others = await ctx.session.scalars(
        select(HouseholdRow).where(HouseholdRow.settlement_node_id == household.settlement_node_id, HouseholdRow.id != household.id).order_by(HouseholdRow.id)
    )
    best: tuple[int, HouseholdRow, Member] | None = None
    for other in others:
        if MEMBERS in (other.locked or []) or other.social_class is not household.social_class:
            continue
        for candidate in await members_of(ctx, other):
            if (
                candidate.mortal.status is not EntityStatus.CANON
                or not candidate.grown
                or held(candidate.mortal.id)
                or candidate.row.role is HouseholdRole.HEAD
                or await spouses_of(ctx.session, candidate.mortal.id)
                or not await may_wed(ctx.session, ctx.rules, single.mortal, candidate.mortal)
            ):
                continue
            bonus = await preference_bonus(ctx.session, ctx.rules, single.mortal, candidate.mortal)
            if best is None or bonus > best[0]:
                best = (bonus, other, candidate)
    if best is None:
        return False
    _, other, candidate = best
    await marry(ctx.session, single.mortal, candidate.mortal, ctx.epoch, kind=MarriageKind.MONOGAMOUS, description="matched by their households")
    transfer(other, household, round_half_up(other.wealth * ctx.rules.households.dowry_pct / PERCENT))
    if not candidate.row.locked:
        await join_household(ctx, household, candidate.mortal, HouseholdRole.SPOUSE)
    return await decided(
        ctx,
        household,
        HouseholdDecision.MARRY,
        f"{household.name} matched {single.mortal.name} with {candidate.mortal.name} of {other.name}.",
        [single.mortal.id, candidate.mortal.id],
        tally=tally,
    )


async def apprentice(ctx: TickContext, household: HouseholdRow, members: list[Member], tally: HouseholdTally) -> bool:
    age_at = ctx.rules.households.apprentice_age
    child: Member | None = None
    for member in members:
        if (stat(member.mortal, "age") or 0) < age_at or member.stage not in YOUNG or held(member.mortal.id):
            continue
        if not await active_bonds(ctx.session, [BondKind.APPRENTICE_OF], sources=[member.mortal.id]):
            child = member
            break
    if child is None or household.settlement_node_id is None:
        return False
    master = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, [household.settlement_node_id]),
            EntityRow.mortal_role.in_(list(CRAFT_MASTERS)),
            EntityRow.id != child.mortal.id,
        )
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )
    if master is None:
        return False
    await connect(ctx.session, child.mortal.id, master.id, BondKind.APPRENTICE_OF, ctx.epoch, description="apprenticed by the household")
    await enrol_apprentice(ctx, household.settlement_node_id, child.mortal.id)
    return await decided(
        ctx,
        household,
        HouseholdDecision.APPRENTICE,
        f"{household.name} apprenticed {child.mortal.name} to {master.name}.",
        [child.mortal.id, master.id],
        tally=tally,
    )


async def renovate(ctx: TickContext, household: HouseholdRow, dwelling: DwellingRow | None, tally: HouseholdTally) -> bool:
    table = ctx.rules.households
    blocked = {"quality", "rooms"} & set(dwelling.locked or []) if dwelling is not None else set()
    if dwelling is None or household.wealth < table.renovate_wealth or dwelling.quality >= PERCENT or blocked or WEALTH in (household.locked or []):
        return False
    household.wealth -= table.renovate_cost
    dwelling.quality = clamp_int(dwelling.quality + table.renovate_gain, 0, PERCENT)
    if household.social_class is SocialClass.NOBLE and dwelling.rooms < table.noble_rooms:
        dwelling.rooms += 1
    return await decided(
        ctx, household, HouseholdDecision.RENOVATE, f"{household.name} improved its {DWELLINGS[dwelling.kind].label.lower()}.", [], tally=tally
    )


async def servants(ctx: TickContext, household: HouseholdRow, dwelling: DwellingRow | None, tally: HouseholdTally) -> bool:
    table = ctx.rules.households
    if "servants" in (household.locked or []):
        return False
    if household.servants and household.income < household.expenses:
        household.servants -= 1
        return await decided(ctx, household, HouseholdDecision.DISMISS_SERVANT, f"{household.name} let a servant go.", [], tally=tally)
    rooms = dwelling.rooms if dwelling is not None else 1
    if household.wealth >= table.servant_wealth and household.servants < max(1, rooms // 2):
        household.servants += 1
        return await decided(ctx, household, HouseholdDecision.HIRE_SERVANT, f"{household.name} took on a servant.", [], tally=tally)
    return False


async def lodger(
    ctx: TickContext, household: HouseholdRow, members: list[Member], dwelling: DwellingRow | None, tally: HouseholdTally, *, forced: bool = False
) -> bool:
    table = ctx.rules.households
    if dwelling is None or dwelling.rooms <= len(members) or household.settlement_node_id is None:
        return False
    if not forced and not ctx.rng(f"households.lodger.{household.id}.{ctx.epoch}").chance(table.lodger_pct):
        return False
    lonely = await ctx.session.scalars(
        select(HouseholdRow)
        .where(HouseholdRow.settlement_node_id == household.settlement_node_id, HouseholdRow.id != household.id)
        .order_by(HouseholdRow.wealth, HouseholdRow.id)
    )
    for other in lonely:
        if MEMBERS in (other.locked or []):
            continue
        found = await members_of(ctx, other)
        if len(found) != 1 or found[0].row.locked or held(found[0].mortal.id) or not found[0].grown:
            continue
        guest = found[0].mortal
        await join_household(ctx, household, guest, HouseholdRole.LODGER)
        await ctx.session.delete(other)
        return await decided(ctx, household, HouseholdDecision.TAKE_LODGER, f"{household.name} took in {guest.name} as a lodger.", [guest.id], tally=tally)
    return False


async def lend_at_interest(ctx: TickContext, household: HouseholdRow, head: EntityRow, tally: HouseholdTally) -> bool:
    table = ctx.rules.households
    if household.wealth < table.usury_wealth or household.settlement_node_id is None:
        return False
    poorest = await ctx.session.scalar(
        select(HouseholdRow)
        .where(HouseholdRow.settlement_node_id == household.settlement_node_id, HouseholdRow.id != household.id, HouseholdRow.head_node_id.is_not(None))
        .order_by(HouseholdRow.wealth, HouseholdRow.id)
        .limit(1)
    )
    if poorest is None or poorest.head_node_id is None or held(poorest.head_node_id) or "debts" in (poorest.locked or []):
        return False
    lent = household.wealth // 4
    if not transfer(household, poorest, lent):
        return False
    poorest.debts = {**poorest.debts, str(household.id): poorest.debts.get(str(household.id), 0) + lent}
    await judged(ctx, head.id, poorest.head_node_id, ActKind.USURY, note=f"lent at interest to {poorest.name}")
    tally.acts += 1
    return await decided(
        ctx, household, HouseholdDecision.LEND, f"{household.name} lent {lent} at interest to {poorest.name}.", [head.id, poorest.head_node_id], tally=tally
    )


async def decide(ctx: TickContext, household: HouseholdRow, members: list[Member], dwelling: DwellingRow | None, tally: HouseholdTally) -> bool:
    head = next((member.mortal for member in members if member.mortal.id == household.head_node_id), None)
    if head is None or held(head.id) or "decisions" in (household.locked or []):
        return False
    if household.wealth <= 0:
        return (
            await give_up_infant(ctx, household, members, head, tally)
            or await leave_elder(ctx, household, members, head, tally)
            or await migrate(ctx, household, members, dwelling, tally)
            or await sell_furnishing(ctx, household, dwelling, tally)
        )
    return (
        await match(ctx, household, members, tally)
        or await apprentice(ctx, household, members, tally)
        or await renovate(ctx, household, dwelling, tally)
        or await servants(ctx, household, dwelling, tally)
        or await lodger(ctx, household, members, dwelling, tally)
        or await lend_at_interest(ctx, household, head, tally)
    )


async def judge_home(ctx: TickContext, household: HouseholdRow, members: list[Member], dwelling: DwellingRow | None, tally: HouseholdTally) -> int:
    table = ctx.rules.households
    quality = await home_quality(ctx.session, ctx.rules, dwelling)
    wanted = expectation(household.social_class)
    demanding = household.social_class is SocialClass.NOBLE and (dwelling is None or dwelling.rooms < table.noble_rooms or quality < table.noble_quality)
    for member in members:
        if not member.grown or held(member.mortal.id):
            continue
        if quality >= wanted + table.proud_at and not demanding:
            await think(ctx.session, ctx.rules, member.mortal.id, ThoughtKind.PROUD_OF_HOME, ctx.epoch)
            tally.proud += 1
        elif quality <= wanted - table.ashamed_at or demanding:
            await think(ctx.session, ctx.rules, member.mortal.id, ThoughtKind.ASHAMED_OF_HOME, ctx.epoch)
            tally.ashamed += 1
    return quality


async def house_prestige(ctx: TickContext, household: HouseholdRow, quality: int) -> None:
    if household.head_node_id is None:
        return
    member = await ctx.session.scalar(
        select(HouseMemberRow).where(HouseMemberRow.mortal_entity_id == household.head_node_id, HouseMemberRow.by_marriage.is_(False)).limit(1)
    )
    house = await ctx.session.get(HouseProfileRow, member.house_entity_id) if member is not None else None
    if house is None or "prestige" in (house.locked or []) or held(house.house_entity_id):
        return
    if house.head_entity_id != household.head_node_id:
        return
    swing = clamp_int(quality // ctx.rules.households.prestige_quality - PRESTIGE_MIDPOINT, -PRESTIGE_SWING, PRESTIGE_SWING)
    house.prestige = max(0, house.prestige + swing)


async def tend_household(ctx: TickContext, household: HouseholdRow, laws: LawBook, tally: HouseholdTally) -> None:
    state = inspect(household)
    if state.deleted or state.was_deleted or state.detached:
        return
    members = await prune(ctx, await members_of(ctx, household), tally)
    if not members:
        if MEMBERS not in (household.locked or []) and (household.head_node_id is None or not held(household.head_node_id)):
            await ctx.session.delete(household)
        return
    if household.head_node_id is not None and held(household.head_node_id):
        return
    dwelling = await dwelling_of(ctx.session, household.id)
    await assign_roles(ctx, household, members)
    await keep_purse(ctx, household, members, dwelling, laws)
    await pay_debts(ctx, household)
    await bear_burden(ctx, household, members)
    await decide(ctx, household, members, dwelling, tally)
    quality = await judge_home(ctx, household, members, dwelling, tally)
    await house_prestige(ctx, household, quality)


async def tend_aggregates(ctx: TickContext, tally: HouseholdTally) -> None:
    table = ctx.rules.households
    counts: dict[tuple[int, SocialClass], int] = defaultdict(int)
    for cohort in await ctx.session.scalars(select(CohortRow)):
        counts[(cohort.community_entity_id, cohort.social_class)] += cohort.count
    existing = {(row.community_node_id, row.social_class): row for row in await ctx.session.scalars(select(HouseholdAggregateRow))}
    for (community_id, social_class), people in sorted(counts.items(), key=lambda item: (item[0][0], item[0][1].value)):
        community = await ctx.session.get(EntityRow, community_id)
        if community is None or community.entity_type not in COMMUNITY_TYPES or community.status is not EntityStatus.CANON or held(community_id):
            continue
        row = existing.get((community_id, social_class))
        if row is None:
            row = HouseholdAggregateRow(community_node_id=community_id, social_class=social_class, epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
        locked = set(row.locked or [])
        prosperity = stat_or(community, "prosperity", PERCENT // 2)
        kind = CLASS_DWELLING.get(social_class, DwellingKind.HUT) if community.entity_type is EntityType.SETTLEMENT else DwellingKind.TENT
        values = {
            "households": max(0, people // table.mean_size),
            "mean_size": table.mean_size,
            "dwelling_kind": kind,
            "quality": clamp_int(starting_quality(kind, social_class) + (prosperity - PERCENT // 2) // 5, 0, PERCENT),
            "wealth": max(0, round_half_up(prosperity * people / table.mean_size / PERCENT)),
        }
        for key, value in values.items():
            if key not in locked:
                setattr(row, key, value)
        row.epoch = ctx.epoch
        tally.aggregates += 1
