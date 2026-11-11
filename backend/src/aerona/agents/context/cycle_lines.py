from sqlalchemy import or_, select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import an
from aerona.db.tables.cycles import (
    AsabiyyaRow,
    CampRow,
    DivineDebtRow,
    GiftRow,
    IndentureRow,
    KinshipSystemRow,
    LegacyTraitRow,
    LongPlanRow,
    MortalCasteRow,
    PeopleReproductionRow,
    PolityStressRow,
    SlaveMarketRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.cycles import LongPlanStatus, ReproductiveSystem
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.gifts import OBLIGING

GIFT_LINES = 4
DEBT_LINES = 6
PLAN_LINES = 3


def words(value: str) -> str:
    return value.replace("_", " ")


async def named(scope: Scope, node_id: int | None) -> str:
    node = await scope.session.get(NodeRow, node_id) if node_id is not None else None
    return node.name if node is not None else "someone"


async def gift_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    for gift in await scope.session.scalars(
        select(GiftRow)
        .where(or_(GiftRow.receiver_node_id == me.id, GiftRow.giver_node_id == me.id), GiftRow.state.in_(list(OBLIGING)))
        .order_by(GiftRow.due_epoch, GiftRow.id)
        .limit(GIFT_LINES)
    ):
        if gift.receiver_node_id == me.id:
            due = f" by epoch {gift.due_epoch}" if gift.due_epoch is not None else ""
            found.append(
                f"gift {gift.id}: you owe {await named(scope, gift.giver_node_id)} a return for {an(words(gift.occasion.value))} gift worth {gift.value}{due}"
            )
        else:
            found.append(f"{await named(scope, gift.receiver_node_id)} owes you a return for your gift worth {gift.value}")
    return found


async def people_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    people = await people_of(session, me)
    if people is None:
        return []
    found: list[str] = []
    kin = await session.get(KinshipSystemRow, people.id)
    if kin is not None:
        customs = [f"descent {words(kin.descent.value)}", f"couples live {words(kin.residence.value)}", f"lines grouped as {words(kin.descent_group.value)}"]
        if kin.preference.value != "none":
            customs.append(f"marriage by {words(kin.preference.value)}")
        if kin.payment.value != "none":
            customs.append(f"{an(words(kin.payment.value))} of {kin.payment_value} at each marriage")
        if kin.levirate or kin.sororate:
            customs.append("the widowed wed the kin of the dead")
        found.append(f"the ways of kin of {people.name}: {', '.join(customs)}")
    birth = await session.get(PeopleReproductionRow, people.id)
    if birth is not None and birth.system is not ReproductiveSystem.TWO_SEX:
        found.append(f"{people.name} bear their young by the {words(birth.system.value)} way")
    caste = await session.get(MortalCasteRow, me.id)
    if caste is not None:
        found.append(f"your caste: {caste.caste.value}")
    solidarity = await session.get(AsabiyyaRow, people.id)
    if solidarity is not None:
        found.append(f"the solidarity of {people.name} stands at {solidarity.value}, {solidarity.frontier} frontier lands")
    for legacy in await session.scalars(select(LegacyTraitRow).where(LegacyTraitRow.people_entity_id == people.id).limit(DEBT_LINES)):
        found.append(f"{people.name} keep the {words(legacy.kind.value)} of {await named(scope, legacy.predecessor_entity_id)}")
    return found


async def town_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    if me.location_id is None:
        return []
    found: list[str] = []
    camp = await session.get(CampRow, me.location_id)
    if camp is not None:
        found.append(f"your settlement is {an(words(camp.mode.value))} camp with a herd of {camp.herd}, grazing {camp.grazing}, water {camp.water}")
    for bond in await session.scalars(select(IndentureRow).where(IndentureRow.community_entity_id == me.location_id).limit(GIFT_LINES)):
        found.append(f"{bond.count} here are bound in {words(bond.regime.value)}, debt {bond.debt}, exploited at {bond.exploitation}")
    market = await session.get(SlaveMarketRow, me.location_id)
    if market is not None and market.open:
        found.append(f"a market in bound folk sells at {market.price} each, {market.stock} offered")
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id).limit(1))
    stress = await session.get(PolityStressRow, realm) if realm is not None else None
    if stress is not None:
        found.append(
            f"your realm is in {words(stress.phase.value)}: stress {stress.psi}, the poor's misery {stress.immiseration}, "
            f"{stress.aspirants} aspirants for {stress.positions} posts, fiscal strain {stress.fiscal_distress}"
        )
    return found


async def plan_lines(scope: Scope, me: EntityRow) -> list[str]:
    realm = await scope.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    holders = [me.id, *([realm] if realm is not None else [])]
    found: list[str] = []
    for plan in await scope.session.scalars(
        select(LongPlanRow)
        .where(or_(LongPlanRow.holder_node_id.in_(holders), LongPlanRow.carrier_node_id == me.id), LongPlanRow.status == LongPlanStatus.ACTIVE)
        .limit(PLAN_LINES)
    ):
        found.append(f"plan {plan.id}, {plan.name}, {an(words(plan.kind.value))}: {plan.progress} of {plan.steps} steps{', exposed' if plan.exposed else ''}")
    return found


async def mortal_cycle_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await gift_lines(scope, me), *await people_lines(scope, me), *await town_lines(scope, me), *await plan_lines(scope, me)]


async def son_cycle_lines(scope: Scope, son: SonRow) -> list[str]:
    found: list[str] = []
    for debt in await scope.session.scalars(
        select(DivineDebtRow).where(DivineDebtRow.god_node_id == son.id).order_by((DivineDebtRow.offered - DivineDebtRow.answered).desc()).limit(DEBT_LINES)
    ):
        owed = debt.offered - debt.answered
        state = f"you owe them {owed}" if owed > 0 else f"you have given {-owed} beyond their offerings"
        found.append(f"gift debt to {await named(scope, debt.community_entity_id)} (community {debt.community_entity_id}): offered {debt.offered}, {state}")
    for plan in await scope.session.scalars(
        select(LongPlanRow).where(LongPlanRow.holder_node_id == son.id, LongPlanRow.status == LongPlanStatus.ACTIVE).limit(PLAN_LINES)
    ):
        found.append(f"your plan {plan.id}, {plan.name}: {plan.progress} of {plan.steps} steps{', exposed' if plan.exposed else ''}")
    return found
