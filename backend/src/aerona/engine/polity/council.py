from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.polity import POWER_SKILLS, TASKS
from aerona.catalog.statecraft import COUNCIL_TASKS
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.db.tables.customs import MeasureStandardRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.intrigue import SchemeRow, SecretRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.statecraft import PolityRegardRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.statecraft import CouncilTask
from aerona.engine.context import TickContext
from aerona.engine.crafts.reckoning import reckoned
from aerona.engine.intrigue.schemes import OPEN
from aerona.engine.lore.research_depth import add_progress, research_choices
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.offices import power_skill, powers_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record
from aerona.engine.relations.book import relation
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.construction import hasten

TASK = "task"
DILIGENCE = "diligence"
CORRUPTION = "corruption"


@dataclass
class CouncilTally:
    tasks: int = 0
    leaks: int = 0


@dataclass(frozen=True)
class Work:
    realm: Realm
    office: OfficeRow
    strength: float


async def diligence_of(ctx: TickContext, realm: Realm, office: OfficeRow) -> int:
    ruler = realm.ruler_id
    if office.holder_entity_id is None or ruler is None or ruler == office.holder_entity_id:
        return PERCENT
    view = await relation(ctx.session, office.holder_entity_id, ruler)
    return clamp_int(PERCENT // 2 + (view.friendship if view is not None else 0) / 2, 0, PERCENT)


async def neighbour_to_soothe(ctx: TickContext, realm: Realm) -> int | None:
    row = await ctx.session.scalar(
        select(PolityRegardRow)
        .where(PolityRegardRow.holder_entity_id != realm.entity.id, PolityRegardRow.subject_entity_id == realm.entity.id)
        .order_by(PolityRegardRow.threat.desc(), PolityRegardRow.holder_entity_id)
    )
    return row.holder_entity_id if row is not None else None


async def least_pious(ctx: TickContext, book: RealmBook, realm: Realm) -> int | None:
    members = [member for member in book.members(realm) if stat(member, "piety") is not None]
    return min(members, key=lambda member: (stat(member, "piety") or 0, member.id)).id if members else None


async def choose(ctx: TickContext, book: RealmBook, realm: Realm, office: OfficeRow) -> None:
    task = TASKS.get(office.kind)
    if task is None or TASK in (office.locked or []):
        return
    if office.task is not task:
        await record(
            ctx,
            "council.task",
            roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.ACTOR: office.holder_entity_id},
            facts={"office": office.kind, "task": task},
        )
    office.task = task
    if task is CouncilTask.IMPROVE_RELATIONS:
        office.task_target_node_id = await neighbour_to_soothe(ctx, realm)
    elif task is CouncilTask.CONVERT_PROVINCE:
        office.task_target_node_id = await least_pious(ctx, book, realm)
    else:
        office.task_target_node_id = None


EFFECTS: Handlers[CouncilTask, Callable[[TickContext, RealmBook, Work], Awaitable[None]]] = Handlers(CouncilTask)


@EFFECTS.on(CouncilTask.IMPROVE_RELATIONS)
async def improve_relations(ctx: TickContext, book: RealmBook, work: Work) -> None:
    other = book.realms.get(work.office.task_target_node_id or -1)
    mine, theirs = work.realm.profile.core_entity_id, other.profile.core_entity_id if other is not None else None
    if mine is None or theirs is None or held(theirs):
        return
    await change_relation(ctx, mine, theirs, ctx.rules.affairs.relations_gain * work.strength, MemoryKind.GOODWILL, note="courted by a chancellor")


@EFFECTS.on(CouncilTask.TRAIN_TROOPS)
async def train_troops(ctx: TickContext, book: RealmBook, work: Work) -> None:
    members = list(work.realm.members)
    if not members:
        return
    gain = round_half_up(ctx.rules.affairs.drill_gain * work.strength)
    armies = await ctx.session.scalars(
        select(ArmyProfileRow)
        .join(ArmyRow, ArmyRow.entity_id == ArmyProfileRow.army_entity_id)
        .where(ArmyRow.owner_entity_id.in_(members), ArmyRow.disbanded_epoch.is_(None))
    )
    for army in armies:
        if not held(army.army_entity_id) and "cohesion" not in (army.locked or []):
            army.cohesion = clamp_int(army.cohesion + gain, 0, PERCENT)


@EFFECTS.on(CouncilTask.COLLECT_TAXES)
async def collect_taxes(ctx: TickContext, book: RealmBook, work: Work) -> None:
    gathered = round_half_up(ctx.rules.affairs.collect_gain * len(work.realm.members) * work.strength)
    standard = await ctx.session.get(MeasureStandardRow, work.realm.entity.id)
    if standard is not None and standard.standard:
        gathered = round_half_up(gathered * (1 + ctx.rules.measures.tax_pct / PERCENT))
    gathered = round_half_up(gathered * await reckoned(ctx.session, ctx.rules, work.realm.entity.id, ctx.rules.numeracy.tax_pct))
    if gathered > 0 and "treasury" not in work.realm.profile.locked:
        spend(ctx, work.realm, gathered, TreasuryEntry.TAX, "gathered by the treasurer")


@EFFECTS.on(CouncilTask.DISRUPT_SCHEMES)
async def disrupt_schemes(ctx: TickContext, book: RealmBook, work: Work) -> None:
    guarded = {work.realm.entity.id, *work.realm.members, *([work.realm.ruler_id] if work.realm.ruler_id is not None else [])}
    loss = round_half_up(ctx.rules.affairs.disrupt_gain * work.strength)
    for scheme in await ctx.session.scalars(select(SchemeRow).where(SchemeRow.target_node_id.in_(list(guarded)), SchemeRow.phase.in_(list(OPEN)))):
        if not held(scheme.owner_node_id) and "progress" not in (scheme.locked or []):
            scheme.progress = clamp_int(scheme.progress - loss, 0, PERCENT)


@EFFECTS.on(CouncilTask.CONVERT_PROVINCE)
async def convert_province(ctx: TickContext, book: RealmBook, work: Work) -> None:
    target = book.entities.get(work.office.task_target_node_id or -1)
    if target is not None and not held(target.id) and stat(target, "piety") is not None:
        shift_stat(target, "piety", ctx.rules.affairs.convert_gain * work.strength)


@EFFECTS.on(CouncilTask.PURGE_CORRUPTION)
async def purge_corruption(ctx: TickContext, book: RealmBook, work: Work) -> None:
    if CORRUPTION not in work.realm.profile.locked:
        work.realm.profile.corruption = clamp_int(work.realm.profile.corruption - ctx.rules.affairs.purge_gain * work.strength, 0, PERCENT)


@EFFECTS.on(CouncilTask.OVERSEE_WORKS)
async def oversee_works(ctx: TickContext, book: RealmBook, work: Work) -> None:
    share = ctx.rules.council.oversee_works_effect * work.strength
    for member in sorted(work.realm.members):
        if not held(member):
            await hasten(ctx, member, share)


@EFFECTS.on(CouncilTask.PROMOTE_TRADE)
async def promote_trade(ctx: TickContext, book: RealmBook, work: Work) -> None:
    members = list(work.realm.members)
    if not members:
        return
    routes = list(
        await ctx.session.scalars(
            select(TradeRouteProfileRow)
            .where(
                TradeRouteProfileRow.status == TradeRouteStatus.OPEN,
                TradeRouteProfileRow.first_market_id.in_(members) | TradeRouteProfileRow.second_market_id.in_(members),
            )
            .order_by(TradeRouteProfileRow.route_entity_id)
        )
    )
    earned = round_half_up(ctx.rules.council.promote_trade_effect * len(routes) * work.strength)
    if earned > 0 and "treasury" not in work.realm.profile.locked:
        spend(ctx, work.realm, earned, TreasuryEntry.TOLLS, "brought in by an officer promoting trade")
    guard = round_half_up(ctx.rules.council.promote_trade_effect * work.strength)
    for route in routes:
        if not held(route.route_entity_id) and "danger_bandits" not in (route.locked or []):
            route.danger_bandits = clamp_int(route.danger_bandits - guard, 0, PERCENT)


@EFFECTS.on(CouncilTask.ADVANCE_LEARNING)
async def advance_learning(ctx: TickContext, book: RealmBook, work: Work) -> None:
    seat = work.realm.profile.capital_entity_id
    if seat is None or held(seat):
        return
    choices = await research_choices(ctx.session, seat)
    amount = round_half_up(ctx.rules.council.advance_learning_effect * work.strength)
    if choices and amount > 0:
        await add_progress(ctx, seat, choices[0], amount)


async def leak(ctx: TickContext, book: RealmBook, realm: Realm, office: OfficeRow, tally: CouncilTally) -> None:
    ruler = realm.ruler_id
    if office.kind is not OfficeKind.SPYMASTER or ruler is None or office.diligence >= ctx.rules.affairs.leak_below:
        return
    rival = next(
        (other.ruler_id for other in sorted(book.realms.values(), key=lambda item: item.entity.id) if other.entity.id != realm.entity.id and other.ruler_id),
        None,
    )
    secret = await ctx.session.scalar(
        select(SecretRow).where(SecretRow.holder_node_id == ruler, SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.severity.desc()).limit(1)
    )
    if rival is None or secret is None or held(ruler) or "known_by" in (secret.locked or []) or rival in (secret.known_by or []):
        return
    secret.known_by = [*(secret.known_by or []), rival]
    tally.leaks += 1
    await record(
        ctx,
        "affairs.leak",
        roles={IncidentRole.ACTOR: office.holder_entity_id, IncidentRole.VICTIM: ruler, IncidentRole.RECEIVER: rival, IncidentRole.AUTHORITY: realm.entity.id},
        facts={"severity": secret.severity, "diligence": office.diligence},
    )


async def serve(ctx: TickContext, book: RealmBook, realm: Realm, office: OfficeRow, tally: CouncilTally) -> None:
    if office.holder_entity_id is None or held(office.holder_entity_id):
        return
    await choose(ctx, book, realm, office)
    if DILIGENCE not in (office.locked or []):
        office.diligence = await diligence_of(ctx, realm, office)
    await leak(ctx, book, realm, office, tally)
    if office.task is None:
        return
    power = next(iter(powers_of(office)), None)
    skill = await power_skill(ctx, office, power) if power is not None and power in POWER_SKILLS else 0.0
    strength = skill * ctx.rules.affairs.task_skill_pct / PERCENT * office.diligence / PERCENT
    if not COUNCIL_TASKS[office.task].gain:
        strength *= getattr(ctx.rules.council, COUNCIL_TASKS[office.task].effect) / PERCENT
    if strength > 0:
        await EFFECTS[office.task](ctx, book, Work(realm, office, strength))
        tally.tasks += 1


async def tend_council(ctx: TickContext, tally: CouncilTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        for office in realm.offices:
            await serve(ctx, book, realm, office, tally)
