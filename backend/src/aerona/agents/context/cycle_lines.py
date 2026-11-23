from sqlalchemy import or_, select

from aerona.agents.context.scope import Scope
from aerona.catalog.gift_occasions import GIFT_STATES, OCCASIONS, REMEMBERED
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.cycles import (
    AsabiyyaRow,
    CampRow,
    DivineDebtRow,
    GiftRow,
    IndentureRow,
    KinshipSystemRow,
    LegacyTraitRow,
    LongPlanRow,
    ManumissionRow,
    MortalCasteRow,
    PeopleReproductionRow,
    PolityStressRow,
    SlaveMarketRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.cycles import CyclePhase, LongPlanStatus, ReproductiveSystem
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.gifts import OBLIGING, owed_back

GIFT_LINES = 4
DEBT_LINES = 6
PLAN_LINES = 3
TROUBLED = (CyclePhase.CRISIS, CyclePhase.DEPRESSION, CyclePhase.STAGFLATION)
FULL_STANDING = 100


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
        occasion = OCCASIONS[gift.occasion].label.lower()
        if gift.receiver_node_id == me.id:
            due = f" by epoch {gift.due_epoch}" if gift.due_epoch is not None else " at the giver's own need"
            giver = await named(scope, gift.giver_node_id)
            found.append(f"gift {gift.id}: you owe {giver} a return of {owed_back(scope.rules, gift)} for a gift worth {spoken(gift)} ({occasion}){due}")
        else:
            found.append(f"gift {gift.id}: {await named(scope, gift.receiver_node_id)} owes you a return for your gift worth {spoken(gift)} ({occasion})")
    for gift in await scope.session.scalars(
        select(GiftRow)
        .where(
            or_(GiftRow.receiver_node_id == me.id, GiftRow.giver_node_id == me.id),
            GiftRow.state.in_(list(REMEMBERED)),
            GiftRow.settled_epoch >= scope.epoch - 1,
        )
        .order_by(GiftRow.id.desc())
        .limit(GIFT_LINES)
    ):
        other = gift.giver_node_id if gift.receiver_node_id == me.id else gift.receiver_node_id
        found.append(f"a gift between you and {await named(scope, other)} worth {spoken(gift)}: {GIFT_STATES[gift.state].label.lower()}")
    return found


def union_line(people: str, union: UnionCustomRow) -> str:
    parts = [
        f"form {spoken(union.form)}",
        *([f"several partners on the {spoken(union.plural_side)} side"] if union.form.value == "plural" else []),
        f"made for {spoken(union.purpose)}",
        f"the joined live {spoken(union.residence)}",
        f"descent {spoken(union.descent)}",
        "no exchange" if union.exchange.value == "none" else f"exchange {spoken(union.exchange)} worth {union.exchange_value}",
        f"{spoken(union.arrangement)}",
        "never ended" if union.dissolution.value == "none" else f"ended {spoken(union.dissolution)}",
    ]
    if union.endogamy.value != "none":
        parts.append(f"partners from the same {spoken(union.endogamy)}")
    if union.exogamy.value != "none":
        parts.append(f"partners from another {spoken(union.exogamy)}")
    if union.kin_match.value != "none":
        parts.append(f"matches sought among {spoken(union.kin_match)}s")
    return f"the customs of union of {people}: {', '.join(parts)}"


async def people_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    people = await people_of(session, me)
    if people is None:
        return []
    found: list[str] = []
    kin = await session.get(KinshipSystemRow, people.id)
    if kin is not None:
        customs = [f"descent {spoken(kin.descent)}", f"couples live {spoken(kin.residence)}", f"lines grouped as {spoken(kin.descent_group)}"]
        if kin.sibling_union_first or kin.sibling_union_second:
            customs.append("the widowed wed the kin of the dead")
        found.append(f"the ways of kin of {people.name}: {', '.join(customs)}")
    union = await session.get(UnionCustomRow, people.id)
    if union is not None:
        found.append(union_line(people.name, union))
    birth = await session.get(PeopleReproductionRow, people.id)
    if birth is not None and birth.system is not ReproductiveSystem.TWO_SEX:
        found.append(f"{people.name} bear their young by the {spoken(birth.system)} way")
    caste = await session.get(MortalCasteRow, me.id)
    if caste is not None:
        found.append(f"your caste: {spoken(caste.caste)}")
    solidarity = await session.get(AsabiyyaRow, people.id)
    if solidarity is not None:
        found.append(f"the solidarity of {people.name} stands at {spoken(solidarity)}, {solidarity.frontier} frontier lands")
    for legacy in await session.scalars(select(LegacyTraitRow).where(LegacyTraitRow.people_entity_id == people.id).limit(DEBT_LINES)):
        found.append(f"{people.name} keep the {spoken(legacy.kind)} of {await named(scope, legacy.predecessor_entity_id)}")
    return found


async def town_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    if me.location_id is None:
        return []
    found: list[str] = []
    camp = await session.get(CampRow, me.location_id)
    if camp is not None:
        found.append(f"your settlement is {an(spoken(camp.mode))} camp with a herd of {camp.herd}, grazing {camp.grazing}, water {camp.water}")
    for bond in await session.scalars(select(IndentureRow).where(IndentureRow.community_entity_id == me.location_id).limit(GIFT_LINES)):
        newcomers = f", newcomers of {await named(scope, bond.origin_entity_id)}" if bond.origin_entity_id is not None else ""
        found.append(
            f"{several(bond.count, 'labourer here is', 'labourers here are')} bound in {spoken(bond.regime)}{newcomers}, "
            f"debt {bond.debt}, exploited at {bond.exploitation}"
        )
    for freed in await session.scalars(
        select(ManumissionRow)
        .where(ManumissionRow.community_entity_id == me.location_id, ManumissionRow.standing < FULL_STANDING)
        .order_by(ManumissionRow.id)
        .limit(GIFT_LINES)
    ):
        origin = f", folk of {await named(scope, freed.origin_entity_id)}" if freed.origin_entity_id is not None else ""
        found.append(f"{freed.count} freed by {spoken(freed.path)} here{origin} stand at {freed.standing} of {FULL_STANDING} among the freeborn")
    market = await session.get(SlaveMarketRow, me.location_id)
    if market is not None and market.open:
        found.append(f"a market in bound folk sells at {market.price} each, {market.stock} offered")
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id).limit(1))
    stress = await session.get(PolityStressRow, realm) if realm is not None else None
    if stress is not None:
        found.append(
            f"your realm is in {spoken(stress.phase)}: stress {stress.psi}, the poor's misery {stress.immiseration}, "
            f"{several(stress.aspirants, 'aspirant', 'aspirants')} for {several(stress.positions, 'post', 'posts')}, fiscal strain {stress.fiscal_distress}"
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
        steps_counted = several(plan.steps, "step", "steps")
        found.append(f"plan {plan.id}, {plan.name}, {an(spoken(plan.kind))}: {plan.progress} of {steps_counted}{', exposed' if plan.exposed else ''}")
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
        found.append(f"your plan {plan.id}, {plan.name}: {plan.progress} of {several(plan.steps, 'step', 'steps')}{', exposed' if plan.exposed else ''}")
    return [*found, *await realm_lines(scope, son)]


async def realm_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    found: list[str] = []
    for stress, realm in await scope.session.execute(
        select(PolityStressRow, EntityRow)
        .join(EntityRow, EntityRow.id == PolityStressRow.polity_entity_id)
        .where(EntityRow.world_id == son.current_world_id, PolityStressRow.phase.in_(list(TROUBLED)))
        .order_by(PolityStressRow.psi.desc(), PolityStressRow.polity_entity_id)
        .limit(PLAN_LINES)
    ):
        found.append(
            f"realm {realm.name} (polity {realm.id}) is in {spoken(stress.phase)}: stress {stress.psi}, "
            f"{several(stress.aspirants, 'aspirant', 'aspirants')} for {several(stress.positions, 'post', 'posts')}, fiscal strain {stress.fiscal_distress}"
        )
    return found
