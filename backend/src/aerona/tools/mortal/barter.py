from typing import Any

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import DebtStatus
from aerona.engine.phases.civilization import transfer, wealth_key, wealth_of
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import change_relation, relation
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import BarterInput, LendInput, RepayInput
from aerona.tools.mortal.support import enemies, is_community, near, require_target

PERCENT = 100
TRADABLE = frozenset({EntityType.RESOURCE, EntityType.ITEM, EntityType.VESSEL, EntityType.STRUCTURE})
VALUE_KEYS = ("might", "damage", "protection", "splendor", "speed")
JOIN = ", "
BARTER_EVENT = "barter"
LOAN_EVENT = "loan"
REPAY_EVENT = "debt paid"


async def party(call: MortalCall, party_id: int) -> EntityRow:
    other = await require_target(call, party_id)
    if other.id == call.me.id or not (is_community(other) or other.entity_type is EntityType.MORTAL):
        fail(MortalResult.INVALID_PARTY)
    if not await near(call, other):
        fail(MortalResult.PARTY_TOO_FAR, name=other.name)
    if await enemies(call, call.me.id, other.id):
        fail(MortalResult.PARTY_ENEMY, name=other.name)
    return other


def value_of(thing: EntityRow) -> int:
    explicit = stat(thing, "value")
    if explicit is not None:
        return explicit
    return max([0, *[stat(thing, key) or 0 for key in VALUE_KEYS]])


async def _tradable_of(call: MortalCall, owner: EntityRow) -> str:
    found: list[str] = []
    for bond in await BondRepository(call.session).outgoing(owner.id, BondKind.OWNS):
        thing = await call.session.get(EntityRow, bond.target_node_id)
        if thing is not None and thing.status is EntityStatus.CANON and thing.entity_type in TRADABLE:
            found.append(f"#{thing.id} {thing.name}")
    return ", ".join(found) or "nothing yet"


async def _owned(call: MortalCall, ids: list[int], owner: EntityRow, mine: bool) -> list[EntityRow]:
    bonds = BondRepository(call.session)
    things: list[EntityRow] = []
    for thing_id in dict.fromkeys(ids[: call.rules.mortal_tools.barter_max_items]):
        thing = await call.session.get(EntityRow, thing_id)
        valid = thing is not None and thing.status is EntityStatus.CANON and thing.entity_type in TRADABLE
        if thing is None or not valid or not await bonds.exists_between(owner.id, thing.id, BondKind.OWNS):
            name = thing.name if thing is not None else f"#{thing_id}"
            if mine:
                fail(MortalResult.NOT_YOURS_TO_GIVE, name=name, choices=await _tradable_of(call, owner))
            fail(MortalResult.NOT_THEIRS, name=name, owner=owner.name)
        things.append(thing)
    return things


async def _hand_over(call: MortalCall, things: list[EntityRow], new_owner: EntityRow, terms: str) -> None:
    bonds = BondRepository(call.session)
    for thing in things:
        for bond in await bonds.incoming(thing.id, BondKind.OWNS):
            await bonds.deactivate(bond, call.epoch, BARTER_EVENT)
        await bonds.connect(BondDraft(new_owner.id, thing.id, BondKind.OWNS, call.epoch, lines.BARTER_BOND.format(terms=terms)))


async def barter(call: MortalCall, args: BarterInput) -> str:
    tools = call.rules.mortal_tools
    other = await party(call, args.target_id)
    give = await _owned(call, args.give_ids, call.me, True)
    take = await _owned(call, args.take_ids or [], other, False)
    if {thing.id for thing in give} & {thing.id for thing in take}:
        fail(MortalResult.SAME_ON_BOTH_SIDES)
    bond = await relation(call.session, call.rules, call.me.id, other.id)
    score = sum(value_of(thing) for thing in give) + round(bond / tools.barter_relation_scale) + call.die(tools.barter_die, "barter")
    ask = sum(value_of(thing) for thing in take)
    call.target(other.id)
    gift_names, take_names = JOIN.join(thing.name for thing in give), JOIN.join(thing.name for thing in take)
    if take and score < ask:
        await change_relation(call.tick, call.me.id, other.id, -tools.barter_reject_relation, MemoryKind.ILL_WILL, note=BARTER_EVENT)
        await call.chronicle(
            ChronicleKind.TRADE, lines.BARTER_REFUSED, entity_ids=[call.me.id, other.id], me=call.me.name, target=other.name, take=take_names, give=gift_names
        )
        return result(MortalResult.BARTER_REFUSED, name=other.name, score=score, ask=ask)
    await _hand_over(call, give, other, args.terms)
    await _hand_over(call, take, call.me, args.terms)
    await change_relation(call.tick, call.me.id, other.id, tools.barter_relation, MemoryKind.TRADED_WITH, note=BARTER_EVENT)
    if take:
        await call.chronicle(
            ChronicleKind.TRADE,
            lines.BARTERED,
            entity_ids=[call.me.id, other.id],
            me=call.me.name,
            target=other.name,
            give=gift_names,
            take=take_names,
            terms=args.terms,
        )
    else:
        await call.chronicle(
            ChronicleKind.TRADE, lines.GIFTED, entity_ids=[call.me.id, other.id], me=call.me.name, give=gift_names, target=other.name, terms=args.terms
        )
    return result(MortalResult.BARTERED)


async def lend(call: MortalCall, args: LendInput) -> str:
    tools = call.rules.mortal_tools
    debtor = await party(call, args.debtor_id)
    if args.amount > tools.debt_max_amount:
        fail(MortalResult.DEBT_TOO_LARGE, cap=tools.debt_max_amount)
    term = args.term_ages or tools.debt_default_term
    if term > tools.debt_max_term:
        fail(MortalResult.TERM_TOO_LONG, cap=tools.debt_max_term)
    bonds = BondRepository(call.session)
    if await bonds.active_between(debtor.id, call.me.id, [BondKind.OWES]):
        fail(MortalResult.ALREADY_OWES, name=debtor.name)
    key = wealth_key(call.me)
    if key is None:
        fail(MortalResult.NO_MONEY)
    have = wealth_of(call.me) or 0
    if have < args.amount:
        fail(MortalResult.NOT_ENOUGH_MONEY, kind=key, have=have)
    transfer(call.rules, call.me, -args.amount)
    transfer(call.rules, debtor, args.amount)
    due = call.epoch + term
    owes = await bonds.connect(
        BondDraft(
            debtor.id,
            call.me.id,
            BondKind.OWES,
            call.epoch,
            lines.DEBT_TEXT.format(amount=args.amount, what=args.what, due=due),
            debt_amount=args.amount,
            debt_what=args.what,
            debt_due_epoch=due,
        )
    )
    owes.debt_status = DebtStatus.OPEN
    await change_relation(call.tick, call.me.id, debtor.id, call.rules.civilization.loan_relation, MemoryKind.GIFTED_ME, note=LOAN_EVENT)
    call.target(debtor.id)
    await call.chronicle(
        ChronicleKind.DEBT, lines.LENT, entity_ids=[call.me.id, debtor.id], me=call.me.name, amount=args.amount, what=args.what, debtor=debtor.name, due=due
    )
    return result(MortalResult.LENT, name=debtor.name, amount=args.amount, what=args.what, due=due)


async def repay_debt(call: MortalCall, args: RepayInput) -> str:
    creditor = await call.session.get(EntityRow, args.creditor_id)
    bonds = BondRepository(call.session)
    debts = await bonds.active_between(call.me.id, args.creditor_id, [BondKind.OWES]) if creditor is not None else []
    debt = next((bond for bond in debts if bond.source_node_id == call.me.id and bond.debt_amount is not None), None)
    if creditor is None or debt is None:
        fail(MortalResult.OWE_NOTHING, name=creditor.name if creditor is not None else f"#{args.creditor_id}")
    amount = debt.debt_amount or 0
    key = wealth_key(call.me)
    if key is not None and (wealth_of(call.me) or 0) < amount:
        fail(MortalResult.CANNOT_REPAY, kind=key, have=wealth_of(call.me) or 0, amount=amount)
    if key is not None:
        transfer(call.rules, call.me, -amount)
        if wealth_key(creditor) is not None:
            transfer(call.rules, creditor, amount)
    late = debt.debt_status is DebtStatus.OVERDUE or (debt.debt_due_epoch is not None and call.epoch > debt.debt_due_epoch)
    debt.debt_status = DebtStatus.REPAID
    await bonds.deactivate(debt, call.epoch, REPAY_EVENT)
    await change_relation(call.tick, call.me.id, creditor.id, call.rules.civilization.loan_repay_relation, MemoryKind.KEPT_OATH, note=REPAY_EVENT)
    call.target(creditor.id)
    await call.chronicle(
        ChronicleKind.DEBT,
        lines.REPAID,
        entity_ids=[call.me.id, creditor.id],
        me=call.me.name,
        amount=amount,
        what=debt.debt_what or "",
        creditor=creditor.name,
        late=lines.LATE if late else "",
    )
    return result(MortalResult.REPAID, name=creditor.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.BARTER, mortal, BarterInput, ToolMeta(ActionKind.BARTER, lambda rules: rules.mortal_tools.barter_ap), barter),
        ToolSpec(MortalToolId.LEND, mortal, LendInput, ToolMeta(ActionKind.LEND, lambda rules: rules.mortal_tools.debt_ap), lend),
        ToolSpec(MortalToolId.REPAY_DEBT, mortal, RepayInput, ToolMeta(ActionKind.REPAY, lambda rules: rules.mortal_tools.debt_ap), repay_debt),
    ]
