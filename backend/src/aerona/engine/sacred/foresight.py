from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.sacred import DIVINATION_LAWS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cycles import PolityStressRow
from aerona.db.tables.dominion import MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.sacred import DivinationRow, DivinationSystemRow, ForecastModelRow, ForesightRow
from aerona.db.tables.society import ArchiveHoldingRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ProphecyPredicate, Technique
from aerona.domain.enums.cycles import LongPlanKind
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.sacred import DivinationKind, DivinationQuestion, DivinationValidity, ForesightSource, ForesightStatus, OmenVerdict
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.entity_stats import ProphecyStats
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import new_plan
from aerona.engine.divine.laws import binds
from aerona.engine.lore.prophecy import Foretelling, met, seer_power, typed_condition
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import stat_or
from aerona.engine.renown.currencies import members_of, ruler_of_realm
from aerona.engine.sacred.astrology import real_sky
from aerona.engine.sacred.mysteries import patron_of
from aerona.engine.sacred.places import realm_of_town, region_of
from aerona.engine.services.war import ongoing_wars

MIDDLE = 50
FORESIGHT = "foresight"


@dataclass
class ForesightTally:
    systems: int = 0
    readings: int = 0
    heeded: int = 0
    foresights: int = 0
    clouded: int = 0
    fulfilled: int = 0
    failed: int = 0
    proclaimed: int = 0
    models: int = 0
    plans: int = 0


async def seers_among(ctx: TickContext, people_id: int) -> bool:
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.mortal_role == MortalRole.SEER,
            await folk_among(ctx.session, [people_id]),
        )
        .limit(1)
    )
    return found is not None


async def validity_of(ctx: TickContext, system: DivinationSystemRow) -> DivinationValidity:
    people = await living_entity(ctx.session, system.people_entity_id)
    if people is None:
        return DivinationValidity.NOISE
    god = await patron_of(ctx, people.id)
    son = await ctx.session.get(SonRow, god) if god is not None else None
    if son is not None and await seer_power(ctx, son):
        return DivinationValidity.GOD_ANSWERS
    if await seers_among(ctx, people.id):
        return DivinationValidity.SEER_GIFT
    law = DIVINATION_LAWS.get(system.kind)
    if law is not None and await binds(ctx, law, people):
        return DivinationValidity.NATURAL_LAW
    if system.kind is DivinationKind.ASTROLOGY and await real_sky(ctx, people.world_id):
        return DivinationValidity.NATURAL_LAW
    return DivinationValidity.NOISE


async def take_up(ctx: TickContext, people: EntityRow, kind: DivinationKind) -> DivinationSystemRow:
    row = DivinationSystemRow(people_entity_id=people.id, kind=kind, founded_epoch=ctx.epoch, locked=[])
    row.validity = await validity_of(ctx, row)
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"{people.name} took up {kind.value.replace('_', ' ')} to read what is to come.", key="sacred.divination", ids=[people.id])
    return row


async def take_up_systems(ctx: TickContext, tally: ForesightTally) -> None:
    table = ctx.rules.divination
    counts = dict(
        (people, int(count))
        for people, count in await ctx.session.execute(
            select(DivinationSystemRow.people_entity_id, func.count()).group_by(DivinationSystemRow.people_entity_id)
        )
    )
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id) or counts.get(people.id, 0) >= table.systems_per_people:
            continue
        rng = ctx.rng(f"divination.{people.id}")
        if not rng.chance(table.found_chance):
            continue
        kept = set(await ctx.session.scalars(select(DivinationSystemRow.kind).where(DivinationSystemRow.people_entity_id == people.id)))
        fresh = [kind for kind in DivinationKind if kind not in kept]
        if fresh:
            await take_up(ctx, people, rng.pick(fresh))
            tally.systems += 1


async def might_of(ctx: TickContext, realm_id: int) -> int:
    armies = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.ARMY, EntityRow.status == EntityStatus.CANON, EntityRow.affiliated_entity_id == realm_id)
    )
    return sum(stat_or(army, "size", 0) for army in armies)


async def foe_of(ctx: TickContext, realm_id: int) -> int | None:
    wars = await ongoing_wars(ctx.session, realm_id)
    if wars:
        war = wars[0]
        return war.defender_id if war.attacker_id == realm_id else war.attacker_id
    rival = await ctx.session.scalar(
        select(BondRow.target_node_id).where(BondRow.source_node_id == realm_id, BondRow.kind == BondKind.RIVAL).order_by(BondRow.target_node_id).limit(1)
    )
    return int(rival) if rival is not None else None


async def true_omen(ctx: TickContext, question: DivinationQuestion, realm_id: int, ruler: EntityRow) -> OmenVerdict:
    if question in {DivinationQuestion.BATTLE, DivinationQuestion.WAR}:
        foe = await foe_of(ctx, realm_id)
        if foe is None:
            return OmenVerdict.UNCLEAR
        ours, theirs = await might_of(ctx, realm_id), await might_of(ctx, foe)
        return OmenVerdict.AUSPICIOUS if ours > theirs else OmenVerdict.INAUSPICIOUS if ours < theirs else OmenVerdict.UNCLEAR
    profile = await ctx.session.get(MortalProfileRow, ruler.id)
    if question is DivinationQuestion.CORONATION:
        return OmenVerdict.AUSPICIOUS if profile is not None and (profile.legitimacy or 0) >= MIDDLE else OmenVerdict.INAUSPICIOUS
    if question is DivinationQuestion.WEDDING:
        return OmenVerdict.AUSPICIOUS if profile is not None and profile.stress < MIDDLE else OmenVerdict.INAUSPICIOUS
    food = 0
    people = 0
    for town_id in await members_of(ctx.session, realm_id):
        town = await ctx.session.get(EntityRow, town_id)
        if town is not None:
            food += await stock(ctx.session, ctx.rules, town_id, Commodity.FOOD)
            people += stat_or(town, "population", 0)
    return OmenVerdict.AUSPICIOUS if food >= people else OmenVerdict.INAUSPICIOUS


async def question_for(ctx: TickContext, realm_id: int, ruler: EntityRow) -> DivinationQuestion:
    if await ongoing_wars(ctx.session, realm_id):
        return DivinationQuestion.BATTLE
    office = await ctx.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    if office is not None and office.since_epoch == ctx.epoch:
        return DivinationQuestion.CORONATION
    wed = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == ruler.id, BondRow.kind == BondKind.SPOUSE_OF, BondRow.epoch == ctx.epoch).limit(1)
    )
    if wed is not None:
        return DivinationQuestion.WEDDING
    if await foe_of(ctx, realm_id) is not None:
        return DivinationQuestion.WAR
    return DivinationQuestion.HARVEST


async def heed(ctx: TickContext, row: DivinationRow, realm_id: int, ruler: EntityRow) -> None:
    table = ctx.rules.divination
    sign = 1 if row.verdict is OmenVerdict.AUSPICIOUS else -1 if row.verdict is OmenVerdict.INAUSPICIOUS else 0
    profile = await ctx.session.get(MortalProfileRow, ruler.id)
    if row.question is DivinationQuestion.CORONATION and profile is not None and "legitimacy" not in profile.locked and sign:
        profile.legitimacy = clamp_int((profile.legitimacy or 0) + sign * table.legitimacy, 0, PERCENT)
    elif row.question is DivinationQuestion.WEDDING and profile is not None and "stress" not in profile.locked and sign:
        profile.stress = max(0, profile.stress - sign * table.wedding_stress)
    elif row.question is DivinationQuestion.HARVEST and sign < 0:
        towns = await members_of(ctx.session, realm_id)
        for town_id in towns:
            if held(town_id):
                continue
            lost = min(table.harvest_food // max(1, len(towns)), await stock(ctx.session, ctx.rules, town_id, Commodity.FOOD))
            if lost:
                await shift_stock(ctx.session, ctx.rules, town_id, Commodity.FOOD, -lost, epoch=ctx.epoch, flow=GoodsFlow.LOSS)


async def consult(
    ctx: TickContext,
    system: DivinationSystemRow,
    ruler: EntityRow,
    realm_id: int,
    question: DivinationQuestion,
    *,
    swayed_by: int | None,
    verdict: OmenVerdict | None,
) -> DivinationRow:
    table = ctx.rules.divination
    rng = ctx.rng(f"reading.{system.id}.{ruler.id}")
    truth = await true_omen(ctx, question, realm_id, ruler)
    if verdict is None:
        valid = system.validity is not DivinationValidity.NOISE and rng.chance(table.valid_truth)
        verdict = truth if valid else rng.pick(list(OmenVerdict))
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, ruler.id)
    heeded = values.get(ValueAxis.SUPERSTITION, 0) >= table.heed_superstition
    diviner = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.mortal_role.in_([MortalRole.SEER, MortalRole.PRIEST]),
            await folk_among(ctx.session, [system.people_entity_id]),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    row = DivinationRow(
        system_id=system.id,
        diviner_entity_id=diviner,
        client_entity_id=ruler.id,
        question=question,
        verdict=verdict,
        true_verdict=truth,
        heeded=heeded,
        swayed_by_node_id=swayed_by,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    if heeded:
        await heed(ctx, row, realm_id, ruler)
        if "trust" not in system.locked:
            system.trust = clamp_int(system.trust + (table.trust_step if verdict is truth else -table.trust_step), 0, PERCENT)
    await ctx.session.flush()
    return row


async def court_systems(ctx: TickContext, realm_id: int) -> list[DivinationSystemRow]:
    capital = await ctx.session.get(EntityRow, realm_id)
    if capital is None:
        return []
    people_ids: set[int] = set()
    for town_id in await members_of(ctx.session, realm_id):
        town = await ctx.session.get(EntityRow, town_id)
        if town is not None and town.affiliated_entity_id is not None:
            people_ids.add(town.affiliated_entity_id)
    if capital.affiliated_entity_id is not None:
        people_ids.add(capital.affiliated_entity_id)
    if not people_ids:
        return []
    rows = await ctx.session.scalars(
        select(DivinationSystemRow)
        .where(DivinationSystemRow.people_entity_id.in_(people_ids))
        .order_by(DivinationSystemRow.trust.desc(), DivinationSystemRow.id)
    )
    return list(rows)


async def keep_divination(ctx: TickContext, tally: ForesightTally) -> None:
    table = ctx.rules.divination
    await take_up_systems(ctx, tally)
    for system in list(await ctx.session.scalars(select(DivinationSystemRow).order_by(DivinationSystemRow.id))):
        if not held(system.people_entity_id) and "validity" not in system.locked:
            system.validity = await validity_of(ctx, system)
    realms = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for realm in list(realms):
        ruler = await living_entity(ctx.session, await ruler_of_realm(ctx.session, realm.id))
        if ruler is None or held(ruler.id) or held(realm.id):
            continue
        systems = await court_systems(ctx, realm.id)
        if not systems or not ctx.rng(f"consult.{realm.id}").chance(table.consult_chance):
            continue
        row = await consult(ctx, systems[0], ruler, realm.id, await question_for(ctx, realm.id, ruler), swayed_by=None, verdict=None)
        tally.readings += 1
        tally.heeded += 1 if row.heeded else 0


def horizon_epochs(ctx: TickContext) -> int:
    return max(1, round_half_up(ctx.rules.prescience.horizon_years / max(1, ctx.rules.time.years_per_epoch)))


async def likely_futures(ctx: TickContext, world_id: int | None) -> list[tuple[ProphecyPredicate, int, int]]:
    futures: list[tuple[ProphecyPredicate, int, int]] = []
    realms = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world_id)
        .order_by(EntityRow.id)
    )
    for realm in list(realms):
        stress = await ctx.session.get(PolityStressRow, realm.id)
        if stress is not None:
            futures.append((ProphecyPredicate.FALLS, realm.id, stress.psi))
        ruler = await living_entity(ctx.session, await ruler_of_realm(ctx.session, realm.id))
        if ruler is not None:
            age, span = stat_or(ruler, "age", 0), max(1, stat_or(ruler, "lifespan", 0))
            futures.append((ProphecyPredicate.DIES, ruler.id, clamp_int(age * PERCENT // span, 0, PERCENT)))
    return futures


def args_for(predicate: ProphecyPredicate, subject: int) -> dict[str, int | str]:
    return {"entity": subject} if predicate is ProphecyPredicate.DIES else {"settlement": subject}


async def rivals_near(ctx: TickContext, seer_id: int, world_id: int | None) -> int:
    count = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.mortal_role == MortalRole.SEER,
            EntityRow.world_id == world_id,
            EntityRow.id != seer_id,
        )
    )
    return int(count or 0)


async def foresee(
    ctx: TickContext,
    seer_id: int,
    source: ForesightSource,
    world_id: int | None,
    *,
    sight: int,
    chosen: tuple[ProphecyPredicate, int, int] | None = None,
    divination_id: int | None = None,
) -> ForesightRow | None:
    table = ctx.rules.prescience
    if chosen is None:
        futures = [item for item in await likely_futures(ctx, world_id) if item[2] >= table.likely_at]
        if not futures:
            return None
        chosen = max(futures, key=lambda item: (item[2], -item[1]))
    predicate, subject, chance = chosen
    certainty = clamp_int((chance + sight) // 2 - table.rival_cloud * await rivals_near(ctx, seer_id, world_id), 0, PERCENT)
    epochs = horizon_epochs(ctx)
    row = ForesightRow(
        seer_node_id=seer_id,
        subject_node_id=subject,
        predicate=predicate,
        args=args_for(predicate, subject),
        horizon=table.horizon_years,
        due_epoch=ctx.epoch + epochs,
        certainty=certainty,
        source=source,
        divination_id=divination_id,
        status=ForesightStatus.CLOUDED if certainty < table.cloud_floor else ForesightStatus.PENDING,
        made_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def proclaim(ctx: TickContext, row: ForesightRow, seer: EntityRow) -> EntityRow:
    prophecy = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PROPHECY,
            name=f"Foresight of {seer.name}",
            body=f"{seer.name} told what was likely to come.",
            stats=ProphecyStats(certainty=row.certainty),
            power=max(1, seer.power_level),
            world_id=seer.world_id,
            subtype=FORESIGHT,
            maker_entity_id=seer.id,
        ),
    )
    await typed_condition(ctx, prophecy, Foretelling(row.predicate, subject_id=row.subject_node_id, within_epochs=max(1, row.due_epoch - ctx.epoch)))
    return prophecy


async def seers(ctx: TickContext) -> list[tuple[int, ForesightSource, int | None, int]]:
    found: list[tuple[int, ForesightSource, int | None, int]] = []
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role == MortalRole.SEER)
        .order_by(EntityRow.id)
    )
    found.extend((mortal.id, ForesightSource.POWER, mortal.world_id, stat_or(mortal, "wisdom", MIDDLE)) for mortal in mortals)
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)):
        if son.current_world_id is not None and await seer_power(ctx, son):
            found.append((son.id, ForesightSource.GOD, son.current_world_id, MIDDLE + ctx.rules.prescience.god_sight))
    return found


async def check_foresights(ctx: TickContext, tally: ForesightTally) -> None:
    table = ctx.rules.prescience
    rows = await ctx.session.scalars(select(ForesightRow).where(ForesightRow.status == ForesightStatus.PENDING).order_by(ForesightRow.id))
    for row in list(rows):
        if held(row.seer_node_id) or "status" in row.locked:
            continue
        came = await met(ctx, row.predicate, row.args, row.made_epoch)
        if not came and ctx.epoch < row.due_epoch:
            continue
        row.status = ForesightStatus.FULFILLED if came else ForesightStatus.FAILED
        row.checked_epoch = ctx.epoch
        tally.fulfilled += 1 if came else 0
        tally.failed += 0 if came else 1
        profile = await ctx.session.get(MortalProfileRow, row.seer_node_id)
        if profile is not None and "renown" not in profile.locked:
            profile.renown = clamp_int(profile.renown + (table.renown_step if came else -table.renown_step), 0, PERCENT)


async def keep_prescience(ctx: TickContext, tally: ForesightTally) -> None:
    table = ctx.rules.prescience
    await check_foresights(ctx, tally)
    for seer_id, source, world_id, sight in await seers(ctx):
        if tally.foresights >= table.foresights_per_epoch:
            break
        if held(seer_id) or not ctx.rng(f"foresee.{seer_id}").chance(table.foresee_chance):
            continue
        row = await foresee(ctx, seer_id, source, world_id, sight=sight)
        if row is None:
            continue
        tally.foresights += 1
        if row.status is ForesightStatus.CLOUDED:
            tally.clouded += 1
            continue
        seer = await living_entity(ctx.session, seer_id)
        if seer is not None and row.certainty >= table.proclaim_at:
            await proclaim(ctx, row, seer)
            tally.proclaimed += 1


async def archive_of(ctx: TickContext, home_id: int | None) -> int:
    if home_id is None:
        return 0
    archives = select(EntityRow.id).where(EntityRow.location_id == home_id)
    count = await ctx.session.scalar(select(func.count()).select_from(ArchiveHoldingRow).where(ArchiveHoldingRow.archive_entity_id.in_(archives)))
    return int(count or 0)


async def counts(ctx: TickContext, home: EntityRow, realm_id: int) -> bool:
    holders = [home.id, home.affiliated_entity_id, realm_id]
    for holder in holders:
        if holder is not None and await has_technique(ctx.session, holder, Technique.CENSUS):
            return True
    return False


async def build_models(ctx: TickContext, tally: ForesightTally) -> None:
    table = ctx.rules.psychohistory
    modelled = select(ForecastModelRow.order_entity_id)
    orders = await ctx.session.scalars(
        select(FactionProfileRow)
        .where(FactionProfileRow.kind == FactionKind.SCHOLARS_ACADEMY, FactionProfileRow.faction_entity_id.not_in(modelled))
        .order_by(FactionProfileRow.faction_entity_id)
    )
    for order in list(orders):
        faction = await living_entity(ctx.session, order.faction_entity_id)
        home = await living_entity(ctx.session, order.home_entity_id) if order.home_entity_id is not None else None
        if faction is None or home is None or held(faction.id):
            continue
        realm = await realm_of_town(ctx.session, home.id)
        archive = await archive_of(ctx, home.id)
        if realm is None or archive < table.archive_min or not await counts(ctx, home, realm):
            continue
        if not ctx.rng(f"model.{faction.id}").chance(table.build_chance):
            continue
        await model_realm(ctx, faction.id, realm, archive)
        tally.models += 1


async def model_realm(ctx: TickContext, order_id: int, realm_id: int, archive: int) -> ForecastModelRow:
    table = ctx.rules.psychohistory
    row = ForecastModelRow(
        order_entity_id=order_id,
        subject_entity_id=realm_id,
        archive=archive,
        accuracy=min(table.accuracy_cap, archive * table.accuracy_per_work),
        built_epoch=ctx.epoch,
        horizon=horizon_epochs(ctx),
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    realm = await ctx.session.get(EntityRow, realm_id)
    order = await ctx.session.get(EntityRow, order_id)
    await note(
        ctx,
        f"{order.name if order else 'An order'} began to forecast the course of {realm.name if realm else 'a realm'}.",
        key="sacred.forecast",
        ids=[order_id, realm_id],
    )
    return row


async def disruption_of(ctx: TickContext, realm_id: int) -> tuple[int, int | None]:
    regions: set[int] = set()
    for town_id in await members_of(ctx.session, realm_id):
        town = await ctx.session.get(EntityRow, town_id)
        region = await region_of(ctx.session, town) if town is not None else None
        if region is not None:
            regions.add(region.id)
    if not regions:
        return 0, None
    rows = list(
        await ctx.session.execute(
            select(MiracleRecordRow.god_node_id, func.count())
            .where(MiracleRecordRow.epoch == ctx.epoch, MiracleRecordRow.region_entity_id.in_(regions))
            .group_by(MiracleRecordRow.god_node_id)
        )
    )
    if not rows:
        return 0, None
    total = sum(int(count) for _, count in rows)
    loudest = max(rows, key=lambda item: (int(item[1]), -item[0]))[0]
    return clamp_int(total * ctx.rules.psychohistory.mule_pct, 0, PERCENT), loudest


async def run_model(ctx: TickContext, row: ForecastModelRow, tally: ForesightTally) -> None:
    table = ctx.rules.psychohistory
    if row.subject_entity_id is None or held(row.order_entity_id):
        return
    stress = await ctx.session.get(PolityStressRow, row.subject_entity_id)
    actual = stress.psi if stress is not None else 0
    spread = max(0, (PERCENT - row.accuracy) // 2)
    guess = clamp_int(actual + ctx.rng(f"forecast.{row.id}").integer(-spread, spread), 0, PERCENT)
    row.forecast_psi, row.actual_psi = guess, actual
    if abs(guess - actual) <= table.near_at and "accuracy" not in row.locked:
        row.accuracy = min(table.accuracy_cap, row.accuracy + table.learn_step)
    if "disruption" not in row.locked:
        row.disruption, row.disrupted_by_node_id = await disruption_of(ctx, row.subject_entity_id)
    if row.accuracy >= table.plan_at and row.plan_id is None:
        realm = await ctx.session.get(EntityRow, row.subject_entity_id)
        plan = await new_plan(
            ctx,
            row.order_entity_id,
            LongPlanKind.FORECAST,
            f"Steering of {realm.name if realm else 'the realm'}",
            target_id=row.subject_entity_id,
            carrier_id=None,
            steps=table.plan_steps,
            step_cost=0,
            secrecy=PERCENT - row.accuracy,
        )
        row.plan_id = plan.id
        tally.plans += 1


async def keep_psychohistory(ctx: TickContext, tally: ForesightTally) -> None:
    await build_models(ctx, tally)
    for row in list(await ctx.session.scalars(select(ForecastModelRow).order_by(ForecastModelRow.id))):
        await run_model(ctx, row, tally)


async def keep_foresight(ctx: TickContext, tally: ForesightTally) -> None:
    await keep_divination(ctx, tally)
    await keep_prescience(ctx, tally)
    await keep_psychohistory(ctx, tally)
    await ctx.session.flush()
