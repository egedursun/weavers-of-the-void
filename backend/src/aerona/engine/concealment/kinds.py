from collections.abc import Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.concealment import HiddenTruthRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import DataStoreRow, IntrusionRow
from aerona.db.write_guard import held
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperRole, SeekerAim, TruthAttitude
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.made import IntrusionAim
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.primitives.stats import shift_stat

KIND_SPREAD: Mapping[HiddenTruthKind, int] = total(
    HiddenTruthKind,
    {
        HiddenTruthKind.EXISTENCE: 100,
        HiddenTruthKind.NATURE: 100,
        HiddenTruthKind.PRESENCE: 100,
        HiddenTruthKind.POWER: 110,
        HiddenTruthKind.EVENT: 90,
        HiddenTruthKind.ORIGIN: 80,
        HiddenTruthKind.AWAKENING: 120,
        HiddenTruthKind.PROGRAMME: 70,
        HiddenTruthKind.COSMIC: 60,
    },
)
KIND_STRAIN: Mapping[HiddenTruthKind, int] = total(
    HiddenTruthKind,
    {
        HiddenTruthKind.EXISTENCE: 100,
        HiddenTruthKind.NATURE: 100,
        HiddenTruthKind.PRESENCE: 100,
        HiddenTruthKind.POWER: 100,
        HiddenTruthKind.EVENT: 100,
        HiddenTruthKind.ORIGIN: 120,
        HiddenTruthKind.AWAKENING: 130,
        HiddenTruthKind.PROGRAMME: 110,
        HiddenTruthKind.COSMIC: 200,
    },
)
SCOPE_SPREAD: Mapping[ConcealScope, int] = total(
    ConcealScope,
    {
        ConcealScope.EVERYONE: 100,
        ConcealScope.A_PEOPLE: 100,
        ConcealScope.A_POLITY: 100,
        ConcealScope.THE_UNINITIATED: 90,
        ConcealScope.A_WORLD: 80,
        ConcealScope.THE_COSMOS: 50,
    },
)
ROLE_WEIGHT: Mapping[KeeperRole, int] = total(
    KeeperRole,
    {KeeperRole.ENFORCER: 200, KeeperRole.GUARDIAN: 150, KeeperRole.MEMBER: 100, KeeperRole.PATRON: 50},
)
PAYING_ORDER = (KeeperRole.PATRON, KeeperRole.GUARDIAN, KeeperRole.MEMBER, KeeperRole.ENFORCER)
LOW_TRUST = PERCENT // 4


def spread_of(truth: HiddenTruthRow, spread: int) -> int:
    return spread * KIND_SPREAD[truth.kind] // PERCENT * SCOPE_SPREAD[truth.hidden_from] // PERCENT


def strain_of(truth: HiddenTruthRow) -> int:
    return truth.sanity_cost * KIND_STRAIN[truth.kind] // PERCENT


async def keepers_by_role(ctx: TickContext, truth_id: int) -> list[TruthKeeperRow]:
    rows = list(await ctx.session.scalars(select(TruthKeeperRow).where(TruthKeeperRow.truth_id == truth_id).order_by(TruthKeeperRow.id)))
    return sorted(rows, key=lambda row: PAYING_ORDER.index(row.role))


async def answer_weight(ctx: TickContext, truth_id: int) -> int:
    roles = list(await ctx.session.scalars(select(TruthKeeperRow.role).where(TruthKeeperRow.truth_id == truth_id)))
    return max((ROLE_WEIGHT[role] for role in roles), default=PERCENT)


def denied(trust: int, attitude: TruthAttitude) -> TruthAttitude:
    return TruthAttitude.DENIED if trust < LOW_TRUST else attitude


async def after_seeking(ctx: TickContext, seeker: TruthSeekerRow, truth: HiddenTruthRow) -> None:
    table = ctx.rules.concealment
    finder = await ctx.session.get(EntityRow, seeker.seeker_node_id)
    subject = await ctx.session.get(EntityRow, truth.subject_node_id)
    if finder is None or subject is None or held(subject.id):
        return
    if seeker.aim is SeekerAim.DESTROY_THE_HIDDEN:
        stat = "population" if subject.entity_type is EntityType.PEOPLE else "hp"
        shift_stat(subject, stat, -table.hunt_harm, 0)
    elif seeker.aim is SeekerAim.EXPLOIT and await take_coin(ctx.session, ctx.rules, subject, table.hush_money):
        await give_coin(ctx.session, ctx.rules, finder, table.hush_money)
    elif seeker.aim is SeekerAim.UNDERSTAND and "strength" not in truth.locked:
        truth.strength = max(0, truth.strength - table.tend_gain)


async def leaked(ctx: TickContext, truth: HiddenTruthRow) -> BreachCause | None:
    keepers = select(TruthKeeperRow.keeper_node_id).where(TruthKeeperRow.truth_id == truth.id)
    struck = await ctx.session.scalar(
        select(IntrusionRow.target_node_id)
        .where(IntrusionRow.epoch == ctx.epoch, IntrusionRow.aim.in_([IntrusionAim.READ, IntrusionAim.SEIZE]), IntrusionRow.target_node_id.in_(keepers))
        .limit(1)
    )
    if struck is None:
        return None
    store = await ctx.session.scalar(select(DataStoreRow.id).where(DataStoreRow.holder_node_id == struck).limit(1))
    return BreachCause.RECORD_LEAK if store is not None else BreachCause.INTRUSION


def by_accident(ctx: TickContext, truth: HiddenTruthRow) -> bool:
    chance = ctx.rules.concealment.accident_breach * (PERCENT - truth.strength) // PERCENT
    return ctx.rng(f"truth.accident.{truth.id}.{ctx.epoch}").chance(chance)
