from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.catalog.collective import ACT_COLLECTION, ANGRY_ACTS, FAITH_ACTS, TRIGGERS
from aerona.catalog.life.collective import CONFORMING, TRIGGER_MOOD
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.collective import CascadeRow, CrowdMoodRow, MobRow, MovementRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.collective import CascadeOutcome, CollectiveActKind, CollectiveTrigger, MobEnd, MobStatus, MobTarget
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus, StepOutcome
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.belonging.effects import apart_from_ruler
from aerona.engine.belonging.mockery import vent
from aerona.engine.body.hits import Harm
from aerona.engine.collective.book import population_of, realm_of_town, shift, soldiers_of, towns
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import psi_of, realm_of
from aerona.engine.cycles.indenture import indentured_share
from aerona.engine.history.collections import open_collection
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.split import facets_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import church_in
from aerona.engine.urban.coverage import people_of_districts

T = CollectiveTrigger
A = CollectiveActKind
FACET_SPAN = 50
MOOD_SAMPLE = 20
LETHAL = 9999
INCIDENT_TRIGGERS: tuple[tuple[str, CollectiveTrigger], ...] = (
    ("justice.death", T.EXECUTION),
    ("settlement.fire", T.FIRE),
    ("structures.burned", T.FIRE),
    ("monsters.", T.BEAST),
    ("trade_route.beast_raid", T.BEAST),
    ("miracle", T.MIRACLE),
    ("tools.son.miracle", T.MIRACLE),
    ("faction.strike", T.UNPAID_WAGES),
    ("faction.riot", T.PRICE_SPIKE),
    ("disease.quarantine_riot", T.PLAGUE),
    ("disasters.city_plague", T.PLAGUE),
    ("enactment.riot", T.EXECUTION),
)


@dataclass
class CrowdTally:
    stirred: int = 0
    cascades: int = 0
    mobs: int = 0
    panics: int = 0
    movements: int = 0
    lynchings: int = 0
    dispersed: int = 0
    revolts: int = 0
    dead: int = 0
    fled: int = 0


@dataclass(frozen=True)
class Crowd:
    base: float
    cut: float
    deterrence: float
    agitation: float
    conformity: float


def mood_value(mood: CrowdMoodRow, name: str) -> int:
    return int(getattr(mood, name))


async def mood_of(ctx: TickContext, town_id: int) -> CrowdMoodRow:
    row = await ctx.session.get(CrowdMoodRow, town_id)
    if row is None:
        row = CrowdMoodRow(settlement_entity_id=town_id, anger=0, anxiety=0, fervour=0, deterrence=0, agitation=0, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def stir(ctx: TickContext, town_id: int | None, trigger: CollectiveTrigger, *, force: int | None = None) -> CrowdMoodRow | None:
    if town_id is None or held(town_id) or await ctx.session.get(SettlementProfileRow, town_id) is None:
        return None
    mood = await mood_of(ctx, town_id)
    spec = TRIGGERS[trigger]
    shift(mood, spec.mood, ctx.rules.collective_behaviour.heat if force is None else force)
    if "last_trigger" not in mood.locked:
        mood.last_trigger = trigger
    return mood


async def incident_triggers(ctx: TickContext) -> dict[int, set[CollectiveTrigger]]:
    clauses = [IncidentRow.kind.startswith(prefix) for prefix, _ in INCIDENT_TRIGGERS]
    rows = await ctx.session.execute(
        select(IncidentRow.kind, IncidentRow.place_entity_id, EntityRow.id, EntityRow.entity_type, EntityRow.location_id)
        .outerjoin(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .outerjoin(EntityRow, EntityRow.id == IncidentParticipantRow.node_id)
        .where(IncidentRow.epoch >= ctx.epoch - 1, or_(*clauses))
    )
    found: dict[int, set[CollectiveTrigger]] = defaultdict(set)
    for kind, place, node, node_type, location in rows:
        trigger = next(trigger for prefix, trigger in INCIDENT_TRIGGERS if kind.startswith(prefix))
        for town in (place, node if node_type is EntityType.SETTLEMENT else None, location if node_type is EntityType.MORTAL else None):
            if town is not None:
                found[town].add(trigger)
    return found


async def state_triggers(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow) -> set[CollectiveTrigger]:
    table = ctx.rules.collective_behaviour
    found: set[CollectiveTrigger] = set()
    society = await ctx.session.get(CommunitySocietyRow, town.id)
    if society is not None:
        if await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD) < table.famine_food:
            found.add(T.FAMINE)
        if society.price_food >= table.price_spike:
            found.add(T.PRICE_SPIKE)
    if town.location_id is not None:
        sick = await ctx.session.scalar(
            select(OutbreakRow.id).where(OutbreakRow.region_entity_id == town.location_id, OutbreakRow.status == OutbreakStatus.ACTIVE).limit(1)
        )
        if sick is not None:
            found.add(T.PLAGUE)
        else:
            near = await ctx.session.scalar(
                select(OutbreakRow.id)
                .join(EntityRow, EntityRow.id == OutbreakRow.region_entity_id)
                .where(EntityRow.world_id == town.world_id, OutbreakRow.status == OutbreakStatus.ACTIVE)
                .limit(1)
            )
            if near is not None:
                found.add(T.RUMOUR)
    eclipse = await ctx.session.scalar(
        select(SkyEventRow.id).where(SkyEventRow.world_id == town.world_id, SkyEventRow.kind == SkyEventKind.ECLIPSE, SkyEventRow.epoch == ctx.epoch).limit(1)
    )
    if eclipse is not None:
        found.add(T.ECLIPSE)
    unpaid = await ctx.session.scalar(
        select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.home_entity_id == town.id, FactionProfileRow.unpaid_epochs > 0).limit(1)
    )
    if unpaid is not None:
        found.add(T.UNPAID_WAGES)
    zealous = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == town.id)
    )
    if any((stat(cult, "zeal") or 0) >= PERCENT * 3 // 5 for cult in zealous):
        found.add(T.SERMON)
    return found


async def conformity_of(ctx: TickContext, town: EntityRow) -> float:
    everyone = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town.id]))
        .order_by(EntityRow.id)
    )
    mortals = ctx.rng(f"crowd.mood.{town.id}.{ctx.epoch}").sample(list(everyone), MOOD_SAMPLE)
    if not mortals:
        return 0.0
    summed = 0.0
    for mortal_id in mortals:
        facets = await facets_of(ctx.session, mortal_id)
        summed += sum(facets.get(facet, 0) for facet in CONFORMING) / (len(CONFORMING) * FACET_SPAN)
    return max(-1.0, min(1.0, summed / len(mortals)))


async def deterrence_of(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow) -> int:
    soldiers = await soldiers_of(ctx, profile)
    per_hundred = soldiers * PERCENT / max(1, population_of(town))
    return clamp_int(per_hundred * PERCENT / ctx.rules.collective_behaviour.deterrence_full, 0, PERCENT)


def crowd_for(
    ctx: TickContext,
    mood: CrowdMoodRow,
    act: CollectiveActKind,
    conformity: float,
    *,
    stress: int = 0,
    bound: int = 0,
    vented: float = 0.0,
    divided: int = 0,
) -> Crowd:
    table = ctx.rules.collective_behaviour
    spec_mood = TRIGGER_MOOD[act]
    cut = {"anger": table.anger_cut, "anxiety": table.anxiety_cut, "fervour": table.fervour_cut}[spec_mood] * mood_value(mood, spec_mood) / PERCENT
    cut += ctx.rules.structural_demography.threshold_cut * stress / PERCENT
    cut += ctx.rules.labour_regimes.crowd_cut * bound / PERCENT
    cut -= vented
    cut += ctx.rules.identities.revolt_cut * divided / PERCENT
    return Crowd(
        base=table.base_threshold,
        cut=cut,
        deterrence=table.deterrence_lift * mood.deterrence / PERCENT,
        agitation=table.agitation_cut * mood.agitation / PERCENT,
        conformity=conformity,
    )


def thresholds(ctx: TickContext, crowd: Crowd, rng: SeededRandom) -> list[tuple[float, float]]:
    table = ctx.rules.collective_behaviour
    middle = crowd.base - crowd.cut + crowd.deterrence - crowd.agitation
    spread = table.spread_pct
    found: list[tuple[float, float]] = []
    for _ in range(table.sample):
        own = middle + rng.uniform(-spread, spread) + rng.uniform(-spread, spread)
        conformist = max(-1.0, min(1.0, crowd.conformity + rng.uniform(-0.5, 0.5)))
        found.append((own, conformist))
    return found


def cascade(ctx: TickContext, crowd: Crowd, rng: SeededRandom) -> int:
    table = ctx.rules.collective_behaviour
    people = thresholds(ctx, crowd, rng)
    share = float(table.spark_share)
    for _ in range(table.rounds):
        joined = sum(1 for own, conformist in people if own - table.conformity_weight * conformist * share / PERCENT <= share)
        nxt = max(float(table.spark_share), joined * PERCENT / len(people))
        if abs(nxt - share) < 1:
            share = nxt
            break
        share = nxt
    return clamp_int(share, 0, PERCENT)


def outcome_of(ctx: TickContext, act: CollectiveActKind, share: int) -> CascadeOutcome:
    table = ctx.rules.collective_behaviour
    if share >= table.movement_share and act is not A.PANIC:
        return CascadeOutcome.MOVEMENT
    if share >= table.mob_share:
        return CascadeOutcome.PANIC if act is A.PANIC else CascadeOutcome.MOB
    return CascadeOutcome.FIZZLED


async def choose_district(ctx: TickContext, town: EntityRow, rng: SeededRandom) -> tuple[DistrictRow | None, float]:
    districts = list(await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id).order_by(DistrictRow.id)))
    people = population_of(town)
    if not districts:
        return None, float(people)
    shares = people_of_districts(ctx.rules, people, districts)
    district = rng.weighted(districts, [max(1.0, shares[district.id]) for district in districts])
    return district, shares[district.id]


async def scapegoat(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town.id]))
        .order_by(EntityRow.id)
    )
    candidates = [row for row in rows if not held(row.id)]
    if not candidates:
        return None
    infamy = {
        row.entity_id: row.infamy
        for row in await ctx.session.scalars(select(MortalProfileRow).where(MortalProfileRow.entity_id.in_([row.id for row in candidates])))
    }
    return max(candidates, key=lambda row: (infamy.get(row.id, 0), -stat_or(row, "charisma", 0), -row.id))


async def leader_in(ctx: TickContext, town: EntityRow) -> int | None:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town.id]))
        .order_by(EntityRow.id)
    )
    best = max(list(rows), key=lambda row: (stat_or(row, "charisma", 0), -row.id), default=None)
    return best.id if best is not None and not held(best.id) else None


async def cult_in(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    return await church_in(ctx.session, town)


async def raise_mob(ctx: TickContext, town: EntityRow, row: CascadeRow, *, district: DistrictRow | None, size: int) -> MobRow:
    act, trigger = row.act, row.trigger
    mood = await mood_of(ctx, town.id)
    target = TRIGGERS[trigger].target
    victim = await scapegoat(ctx, town) if target is MobTarget.SCAPEGOAT else None
    if target is MobTarget.SCAPEGOAT and victim is None:
        target = MobTarget.DISTRICT
    mob = MobRow(
        settlement_entity_id=town.id,
        district_id=district.id if district is not None else None,
        act=A.LYNCHING if victim is not None and act in ANGRY_ACTS | {A.PROCESSION} else act,
        size=size,
        anger=clamp_int(max(mood.anger, mood.anxiety, mood.fervour), 10, PERCENT),
        target=target,
        target_entity_id=victim.id if victim is not None else None,
        leader_entity_id=await leader_in(ctx, town),
        status=MobStatus.GATHERING,
        cascade_id=row.id,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(mob)
    await ctx.session.flush()
    return mob


async def flee(ctx: TickContext, town: EntityRow, row: CascadeRow, tally: CrowdTally, *, district_people: float) -> None:
    share = row.share
    table = ctx.rules.collective_behaviour
    acting = district_people * share / PERCENT
    fled = round_half_up(acting * table.panic_flight_pct / PERCENT)
    trampled = round_half_up(acting * table.trample_per_mille / 1000 * (1 + share / PERCENT))
    set_stats(town, population=max(0, population_of(town) - fled - trampled))
    row.fled, row.deaths = fled, trampled
    food = await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD)
    hoarded = round_half_up(food * table.hoard_pct / PERCENT)
    if hoarded:
        await shift_stock(ctx.session, ctx.rules, town.id, Commodity.FOOD, -hoarded, epoch=ctx.epoch, flow=GoodsFlow.LOSS)
    tally.fled += fled
    tally.dead += trampled


async def convert(ctx: TickContext, town: EntityRow, district_people: float, share: int) -> int:
    cult = await cult_in(ctx, town)
    if cult is None or held(cult.id):
        return 0
    won = round_half_up(district_people * share / PERCENT * ctx.rules.collective_behaviour.conversion_pct / PERCENT)
    low, high = headcount_bounds(ctx.rules, cult)
    set_stats(cult, followers=clamp_int((stat(cult, "followers") or 0) + won, low, high))
    return won


async def begin_movement(ctx: TickContext, town: EntityRow, act: CollectiveActKind, trigger: CollectiveTrigger, *, members: int, share: int) -> MovementRow:
    cult = await cult_in(ctx, town) if act in FAITH_ACTS else None
    row = MovementRow(
        settlement_entity_id=town.id,
        act=act,
        trigger=trigger,
        members=members,
        strength=clamp_int(share, 0, PERCENT),
        leader_entity_id=await leader_in(ctx, town),
        cult_entity_id=cult.id if cult is not None else None,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def spark(ctx: TickContext, town: EntityRow, trigger: CollectiveTrigger, tally: CrowdTally, *, forced: bool = False) -> CascadeRow | None:
    if held(town.id):
        return None
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if profile is None:
        return None
    mood = await mood_of(ctx, town.id)
    rng = ctx.rng(f"cascade.{town.id}.{trigger.value}.{ctx.epoch}")
    act = TRIGGERS[trigger].act
    district, district_people = await choose_district(ctx, town, rng)
    bound = await indentured_share(ctx.session, town.id)
    vented = await vent(ctx.session, ctx.rules, await realm_of(ctx.session, town.id), ctx.epoch)
    divided = await apart_from_ruler(ctx.session, ctx.rules, town.id)
    crowd = crowd_for(ctx, mood, act, await conformity_of(ctx, town), stress=await psi_of(ctx.session, town.id), bound=bound, vented=vented, divided=divided)
    share = cascade(ctx, crowd, rng)
    outcome = outcome_of(ctx, act, share)
    participants = round_half_up(district_people * share / PERCENT)
    row = CascadeRow(
        settlement_entity_id=town.id,
        district_id=district.id if district is not None else None,
        trigger=trigger,
        act=act,
        participants=participants,
        share=share,
        outcome=outcome,
        deaths=0,
        fled=0,
        epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.cascades += 1
    if outcome is CascadeOutcome.FIZZLED and not forced:
        return row
    if outcome is CascadeOutcome.PANIC:
        await flee(ctx, town, row, tally, district_people=district_people)
        tally.panics += 1
    elif outcome is CascadeOutcome.MOVEMENT:
        await begin_movement(ctx, town, act, trigger, members=participants, share=share)
        tally.movements += 1
    elif outcome is CascadeOutcome.MOB:
        await raise_mob(ctx, town, row, district=district, size=participants)
        tally.mobs += 1
    if act is A.CONVERSION and outcome is not CascadeOutcome.FIZZLED:
        await convert(ctx, town, district_people, share)
    collection = await open_collection(
        ctx, ACT_COLLECTION[act], world_id=town.world_id, members={town.id: CollectionRole.PLACE}, places=[town.id], source_key=f"collective.{act.value}"
    )
    row.collection_id = collection.id if collection is not None else None
    await record(
        ctx,
        f"collective.{act.value}",
        roles={IncidentRole.PLACE: town.id},
        facts={
            "act": act,
            "trigger": trigger,
            "participants": participants,
            "share": share,
            "outcome": outcome,
            "district": district.kind if district is not None else None,
        },
        steps=(
            StepDraft(
                CROWD_STEPS[outcome],
                amount=participants or None,
                unit=FactUnit.PEOPLE if participants else None,
                locus_kind=StepLocus.DISTRICT if district is not None else StepLocus.SETTLEMENT,
                locus_key=district.kind.value if district is not None else None,
                locus_node=None if district is not None else town.id,
            ),
            *(
                (StepDraft(StepAction.TRAMPLE, parent=0, amount=row.deaths, unit=FactUnit.PEOPLE, outcome=StepOutcome.KILLED),)
                if outcome is CascadeOutcome.PANIC and row.deaths
                else ()
            ),
        ),
        place=town.id,
        world_id=town.world_id,
    )
    return row


CROWD_STEPS: Mapping[CascadeOutcome, StepAction] = total(
    CascadeOutcome,
    {
        CascadeOutcome.FIZZLED: StepAction.WANE,
        CascadeOutcome.MOB: StepAction.SPREAD,
        CascadeOutcome.PANIC: StepAction.FLEE,
        CascadeOutcome.MOVEMENT: StepAction.BEGIN,
    },
)


async def stir_towns(ctx: TickContext, tally: CrowdTally) -> None:
    table = ctx.rules.collective_behaviour
    from_incidents = await incident_triggers(ctx)
    for town, profile in await towns(ctx):
        if held(town.id):
            continue
        mood = await mood_of(ctx, town.id)
        if "deterrence" not in mood.locked:
            mood.deterrence = await deterrence_of(ctx, town, profile)
        triggers = await state_triggers(ctx, town, profile) | from_incidents.get(town.id, set())
        for trigger in sorted(triggers):
            await stir(ctx, town.id, trigger, force=table.heat // 2)
            tally.stirred += 1
        shift(mood, "anger", profile.unrest * table.heat / (PERCENT * 2))
        chosen = mood.last_trigger
        if chosen is None and triggers:
            chosen = max(sorted(triggers), key=lambda trigger: mood_value(mood, TRIGGERS[trigger].mood))
        if chosen is not None and ctx.rng(f"crowd.{town.id}.{ctx.epoch}").chance(table.trigger_pct):
            await spark(ctx, town, chosen, tally)
        if "last_trigger" not in mood.locked:
            mood.last_trigger = None
        for name in ("anger", "anxiety", "fervour", "agitation"):
            shift(mood, name, -table.mood_decay)
    await ctx.session.flush()


async def lynch(ctx: TickContext, mob: MobRow, town: EntityRow, tally: CrowdTally) -> None:
    victim = await ctx.session.get(EntityRow, mob.target_entity_id) if mob.target_entity_id is not None else None
    if victim is None or victim.status is not EntityStatus.CANON or held(victim.id):
        return
    if not ctx.rng(f"lynch.{mob.id}.{ctx.epoch}").chance(ctx.rules.collective_behaviour.lynch_pct * mob.anger / PERCENT):
        return
    await apply_hits(ctx, victim, Harm(LETHAL, HarmCause.PUNISHMENT, f"lynched by a mob in {town.name}", killer_id=mob.leader_entity_id))
    tally.lynchings += 1
    await record(
        ctx,
        "collective.mob_killed",
        roles={IncidentRole.VICTIM: victim.id, IncidentRole.PLACE: town.id, IncidentRole.LEADER: mob.leader_entity_id},
        facts={"anger": mob.anger, "size": mob.size},
        steps=(StepDraft(StepAction.FINISH, actor=mob.leader_entity_id, target=victim.id, outcome=StepOutcome.KILLED),),
        place=town.id,
    )


async def storm(ctx: TickContext, mob: MobRow, town: EntityRow, tally: CrowdTally) -> None:
    table = ctx.rules.collective_behaviour
    harm = table.mob_damage_pct * mob.anger / PERCENT
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if mob.target in {MobTarget.DISTRICT, MobTarget.WORKSHOP} and mob.district_id is not None:
        district = await ctx.session.get(DistrictRow, mob.district_id)
        if district is not None:
            shift(district, "condition", -harm)
    elif mob.target is MobTarget.GRANARY:
        food = await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD)
        taken = round_half_up(food * harm / PERCENT)
        if taken:
            await shift_stock(ctx.session, ctx.rules, town.id, Commodity.FOOD, -taken, epoch=ctx.epoch, flow=GoodsFlow.LOSS)
    elif mob.target is MobTarget.PALACE:
        realm = await realm_of_town(ctx, town.id)
        if realm is not None and not held(realm.polity_entity_id):
            shift(realm, "legitimacy", -harm / 2)
            shift(realm, "stability", -harm / 2)
    elif mob.target is MobTarget.GATE and profile is not None:
        shift(profile, "public_order", -harm)
    elif mob.target is MobTarget.SCAPEGOAT:
        await lynch(ctx, mob, town, tally)
    if profile is not None and mob.act in ANGRY_ACTS:
        shift(profile, "unrest", harm / 2)
        shift(profile, "public_order", -harm / 2)
    shift(mob, "damage", harm, high=PERCENT * 100)


async def end_mob(ctx: TickContext, mob: MobRow, town: EntityRow, by: MobEnd, tally: CrowdTally, *, dead: int = 0) -> None:
    mob.status, mob.ended_by = MobStatus.DISPERSED, by
    tally.dispersed += 1
    await record(
        ctx,
        f"collective.mob_{by.value}",
        roles={IncidentRole.PLACE: town.id, IncidentRole.LEADER: mob.leader_entity_id},
        facts={"end": by, "size": mob.size, "damage": mob.damage, "dead": dead},
        steps=(StepDraft(StepAction.END, amount=dead or None, unit=FactUnit.PEOPLE if dead else None),),
        place=town.id,
    )


async def concede(ctx: TickContext, mob: MobRow, town: EntityRow, tally: CrowdTally) -> bool:
    table = ctx.rules.collective_behaviour
    shift(mob, "anger", -table.concession_calm)
    realm = await realm_of_town(ctx, town.id)
    if realm is not None and not held(realm.polity_entity_id):
        shift(realm, "legitimacy", -table.concession_calm / 5)
    if mob.anger <= 0:
        await end_mob(ctx, mob, town, MobEnd.CONCESSION, tally)
        return True
    return False


async def rage_mobs(ctx: TickContext, tally: CrowdTally) -> None:
    table = ctx.rules.collective_behaviour
    for mob in list(await ctx.session.scalars(select(MobRow).where(MobRow.status != MobStatus.DISPERSED).order_by(MobRow.id))):
        town = await ctx.session.get(EntityRow, mob.settlement_entity_id)
        profile = await ctx.session.get(SettlementProfileRow, mob.settlement_entity_id)
        if town is None or profile is None or held(town.id) or "status" in mob.locked:
            continue
        if mob.status is MobStatus.GATHERING:
            mob.status = MobStatus.RAMPAGING
        await storm(ctx, mob, town, tally)
        soldiers = await soldiers_of(ctx, profile)
        if mob.act in ANGRY_ACTS and soldiers * table.force_pct / PERCENT >= mob.size:
            mood = await mood_of(ctx, town.id)
            shift(mood, "anger", table.heat / 2)
            dead = round_half_up(mob.size * table.trample_per_mille / 1000 * 3)
            set_stats(town, population=max(0, population_of(town) - dead))
            tally.dead += dead
            await end_mob(ctx, mob, town, MobEnd.FORCE, tally, dead=dead)
            continue
        realm = await realm_of_town(ctx, town.id)
        mercy = ctx.rng(f"concede.{mob.id}.{ctx.epoch}").chance(PERCENT // 4) if realm is not None else False
        if mercy and await concede(ctx, mob, town, tally):
            continue
        shift(mob, "anger", -table.fatigue)
        if mob.anger <= 0:
            await end_mob(ctx, mob, town, MobEnd.FATIGUE, tally)
    await ctx.session.flush()


async def tend_movements(ctx: TickContext, tally: CrowdTally) -> None:
    table = ctx.rules.collective_behaviour
    for movement in list(await ctx.session.scalars(select(MovementRow).where(MovementRow.ended_epoch.is_(None)).order_by(MovementRow.id))):
        town = await ctx.session.get(EntityRow, movement.settlement_entity_id)
        if town is None or held(town.id):
            continue
        mood = await mood_of(ctx, town.id)
        feeling = mood_value(mood, TRIGGER_MOOD[movement.act])
        shift(movement, "strength", feeling * table.heat / (PERCENT * 2) - table.movement_decay)
        if movement.strength <= 0 and "ended_epoch" not in movement.locked:
            movement.ended_epoch = ctx.epoch
            await record(
                ctx,
                "collective.movement_faded",
                roles={IncidentRole.PLACE: town.id},
                facts={"act": movement.act, "members": movement.members},
                steps=(StepDraft(StepAction.END),),
                place=town.id,
            )
    await ctx.session.flush()


async def ready_to_arm(ctx: TickContext) -> list[MovementRow]:
    table = ctx.rules.collective_behaviour
    rows = await ctx.session.scalars(
        select(MovementRow)
        .where(MovementRow.ended_epoch.is_(None), MovementRow.faction_entity_id.is_(None), MovementRow.strength >= table.movement_revolt_at)
        .order_by(MovementRow.id)
    )
    return [row for row in rows if not held(row.settlement_entity_id)]
