from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.catalog.stats import max_essence
from aerona.constants.tool_inputs import ESSENCE_GIFT_MAX, INSPIRATION_MAX, INSPIRATION_MIN, MESSAGE_MAX, MESSAGE_MIN, REASON_MAX, REASON_MIN
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, MessageIntent, PendingJobKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import SonStatus, Stat
from aerona.engine.cosmos.duels import son_duel
from aerona.engine.cycles.gifts import divine_gift
from aerona.engine.primitives.stats import stat
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.ports import BornChild, ChildBirth
from aerona.tools.framework.spec import LongJob, ToolMeta, ToolOutcome, ToolSpec, gate, no_cost, son_standard_action
from aerona.tools.framework.validation import fail, label_of, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import (
    ensure_sibling_in_reach,
    has_covenant,
    progress_notes,
    relation,
    require_essence,
    require_sibling,
    rounded,
    shift_relation,
)

NOTE_SEPARATOR = "; "


class SpokenIntent(StrEnum):
    FRIENDSHIP = "friendship"
    ALLIANCE = "alliance"
    LOVE = "love"
    THREAT = "threat"
    MOCKERY = "mockery"
    WARNING = "warning"
    BARGAIN = "bargain"


class ArenaStat(StrEnum):
    STRENGTH = "strength"
    WISDOM = "wisdom"
    CUNNING = "cunning"
    CHARISMA = "charisma"
    WILL = "will"


class CallSiblingInput(ToolInput):
    son_id: int
    intent: SpokenIntent
    message: Annotated[str, Field(min_length=MESSAGE_MIN, max_length=MESSAGE_MAX)]


class CovenantInput(ToolInput):
    son_id: int
    terms: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class GiftInput(ToolInput):
    son_id: int
    essence: Annotated[int, Field(ge=0, le=ESSENCE_GIFT_MAX)] = 0
    worshipper_id: int | None = None
    words: Annotated[str, Field(min_length=MESSAGE_MIN, max_length=REASON_MAX)]


class ChallengeInput(ToolInput):
    son_id: int
    stat: ArenaStat
    reason: Annotated[str, Field(min_length=MESSAGE_MIN, max_length=REASON_MAX)]


class BirthChildInput(ToolInput):
    inspiration: Annotated[str, Field(min_length=INSPIRATION_MIN, max_length=INSPIRATION_MAX)]
    co_parent_id: int | None = None


def message_delta(call: SonCall, intent: SpokenIntent) -> int:
    return intent_delta(call.rules, call.son.charisma, intent)


def intent_delta(rules: Rules, charisma: int, intent: SpokenIntent) -> int:
    tools = rules.son_tools
    base = rounded(tools.message_relation_base + charisma / tools.message_charisma_divisor)
    deltas = {
        SpokenIntent.FRIENDSHIP: base,
        SpokenIntent.ALLIANCE: base + tools.message_alliance_bonus,
        SpokenIntent.LOVE: base + tools.message_love_bonus,
        SpokenIntent.THREAT: -base - tools.message_threat_penalty,
        SpokenIntent.MOCKERY: -base,
        SpokenIntent.WARNING: -tools.message_warning_penalty,
        SpokenIntent.BARGAIN: tools.message_bargain_effect,
    }
    return deltas[intent]


async def call_sibling(call: SonCall, args: CallSiblingInput) -> str:
    cap = call.rules.son_tools.sibling_message_per_epoch
    await call.within_limit(TurnCounter.SIBLING_MESSAGES, cap, "son_tools.sibling_message_per_epoch", SonResult.MESSAGE_LIMIT)
    sibling = await require_sibling(call, args.son_id)
    if sibling.status is SonStatus.DEAD:
        fail(SonResult.SIBLING_DEAD_WORD, name=sibling.name)
    call.target(sibling.id)
    bond = await shift_relation(call, sibling.id, message_delta(call, args.intent))
    call.session.add(
        MessageRow(epoch=call.epoch, sender_node_id=call.son.id, recipient_node_id=sibling.id, intent=MessageIntent(args.intent.value), text=args.message)
    )
    await call.bump(TurnCounter.SIBLING_MESSAGES)
    phrase = lines.MESSAGE_PHRASES[args.intent.value]
    await call.record(
        "tools.son.message",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.RECEIVER: sibling.id},
        facts={"phrase": str(phrase), "message": str(args.message)},
        kind=ChronicleKind.MESSAGE,
    )
    value, label = (bond.value, bond.label) if bond is not None else (0, "")
    return result(SonResult.MESSAGE_SENT, name=sibling.name, label=label, value=value)


async def swear_covenant(call: SonCall, args: CovenantInput) -> str:
    tools = call.rules.son_tools
    sibling = await require_sibling(call, args.son_id)
    if sibling.status is SonStatus.DEAD:
        fail(SonResult.COVENANT_DEAD, name=sibling.name)
    if await has_covenant(call, sibling.id):
        fail(SonResult.COVENANT_EXISTS)
    await ensure_sibling_in_reach(call, sibling)
    current = await relation(call, sibling.id)
    if current.value < tools.covenant_min_relation:
        fail(SonResult.COVENANT_TRUST, name=sibling.name, value=current.value, minimum=tools.covenant_min_relation)
    require_essence(call, call.rules.costs.covenant)
    call.spend_essence(call.rules.costs.covenant)
    call.target(sibling.id)
    await BondRepository(call.session).connect(BondDraft(call.son.id, sibling.id, BondKind.ALLY, call.epoch, args.terms))
    bond = await shift_relation(call, sibling.id, tools.covenant_relation_bonus)
    await call.record(
        "tools.son.covenant",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.RECEIVER: sibling.id},
        facts={"terms": str(args.terms)},
        kind=ChronicleKind.COVENANT,
    )
    return result(SonResult.COVENANT_MADE, label=bond.label if bond else "", value=bond.value if bond else 0)


async def _transfer(call: SonCall, sibling: SonRow, worshipper_id: int) -> bool:
    tools = call.rules.son_tools
    community = await require_canon(call.session, worshipper_id)
    if await BondRepository(call.session).patron(community.id) != call.son.id:
        fail(SonResult.NOT_YOUR_WORSHIPPER, id=community.id)
    call.charge_actions(call.rules.son_tools.standard_action_cost)
    piety = stat(community, "piety")
    piety_value = tools.transfer_default_piety if piety is None else piety
    chance = tools.transfer_base_pct + rounded((sibling.charisma - piety_value / tools.transfer_piety_divisor) / tools.transfer_diff_divisor)
    accepted = call.die(100, "gift") <= chance
    if accepted:
        bonds = BondRepository(call.session)
        await bonds.close_between(community.id, call.son.id, [BondKind.WORSHIPS], call.epoch, "gift")
        await bonds.connect(BondDraft(community.id, sibling.id, BondKind.WORSHIPS, call.epoch, lines.GIFT_BOND.format(son=call.son.name)))
        call.note(result(SonResult.GIFT_TRANSFER_NOTE, community=community.name, name=sibling.name))
    else:
        await call.record(
            "tools.son.gift_refused",
            roles={IncidentRole.SUBJECT: community.id, IncidentRole.ACTOR: call.son.id, IncidentRole.RECEIVER: sibling.id},
            kind=ChronicleKind.GIFT,
        )
        call.note(result(SonResult.GIFT_REFUSED_NOTE, community=community.name))
    return accepted


async def give_gift(call: SonCall, args: GiftInput) -> str:
    tools = call.rules.son_tools
    await call.within_limit(TurnCounter.GIFTS, tools.gift_per_epoch, "son_tools.gift_per_epoch", SonResult.GIFT_LIMIT)
    sibling = await require_sibling(call, args.son_id)
    if sibling.status is SonStatus.DEAD:
        fail(SonResult.INVALID_SIBLING)
    if args.essence <= 0 and args.worshipper_id is None:
        fail(SonResult.GIFT_EMPTY)
    if args.essence > tools.gift_max_essence:
        fail(SonResult.GIFT_TOO_MUCH, cap=tools.gift_max_essence)
    if args.essence > call.son.essence - tools.gift_min_remaining:
        fail(SonResult.GIFT_CANNOT_AFFORD, have=call.son.essence)
    call.target(sibling.id)
    if args.essence > 0:
        call.spend_essence(args.essence)
        sibling.essence = max(sibling.essence, min(max_essence(call.rules, sibling.might), sibling.essence + args.essence))
        call.note(result(SonResult.GIFT_ESSENCE_NOTE, amount=args.essence))
    accepted = await _transfer(call, sibling, args.worshipper_id) if args.worshipper_id is not None else False
    await divine_gift(call.tick, call.son.id, sibling.id, args.essence)
    call.waive_actions()
    await call.bump(TurnCounter.GIFTS)
    delta = tools.gift_relation_base + rounded(args.essence / tools.gift_relation_essence_divisor) + (tools.gift_worshipper_relation if accepted else 0)
    bond = await shift_relation(call, sibling.id, delta)
    notes = NOTE_SEPARATOR.join(call.log.detail)
    await call.record(
        "tools.son.gift",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.RECEIVER: sibling.id},
        facts={"notes": str(notes), "words": str(args.words)},
        kind=ChronicleKind.GIFT,
    )
    return result(SonResult.GIFT_GIVEN, notes=notes, label=bond.label if bond else "", value=bond.value if bond else 0)


async def challenge(call: SonCall, args: ChallengeInput) -> str:
    tools = call.rules.son_tools
    me = call.son
    sibling = await require_sibling(call, args.son_id)
    if sibling.status is not SonStatus.ACTIVE:
        fail(SonResult.CHALLENGE_UNAVAILABLE, name=sibling.name, state=label_of(sibling.status))
    await ensure_sibling_in_reach(call, sibling)
    call.target(sibling.id)
    covenant = await has_covenant(call, sibling.id)
    duel = await son_duel(call.tick, me, sibling, Stat(args.stat.value), args.reason)
    winner = me if duel.winner_id == me.id else sibling
    level = progress_notes(call, winner, duel.progress)
    if covenant:
        me.fame = max(0, me.fame - tools.covenant_break_renown_cost)
        await BondRepository(call.session).close_between(me.id, sibling.id, [BondKind.ALLY], call.epoch, "covenant broken")
        await shift_relation(call, sibling.id, tools.challenge_relation - tools.challenge_covenant_relation)
        await call.record("tools.son.covenant_broken", roles={IncidentRole.ACTOR: me.id, IncidentRole.RECEIVER: sibling.id}, kind=ChronicleKind.COVENANT)
    bond = await relation(call, sibling.id)
    return result(SonResult.CHALLENGE_RESULT, text=duel.text, level=level, label=bond.label, value=bond.value)


async def birth_child(call: SonCall, args: BirthChildInput) -> ToolOutcome:
    port = call.ports.child_birth
    cost = call.rules.costs.bear_child
    points = call.rules.son_tools.bear_child_ap
    require_essence(call, cost)
    if args.co_parent_id is not None:
        partner = await call.session.get(SonRow, args.co_parent_id)
        if partner is None or partner.id == call.son.id or partner.status is SonStatus.DEAD:
            fail(SonResult.CO_PARENT_INVALID)
    if port is None:
        fail(SonResult.CHILD_BIRTH_FAILED)
    birth: ChildBirth = port
    call.spend_essence(cost)
    call.charge_actions(points)
    parent_id, inspiration, partner_id = call.son.id, args.inspiration, args.co_parent_id

    async def run() -> BornChild:
        return await birth.birth_child(parent_id, inspiration, partner_id)

    async def finish(_call: SonCall, child: BornChild) -> str:
        return result(SonResult.CHILD_BORN, id=child.son_id, name=child.name, title=child.title, rarity=child.rarity_label)

    return LongJob(PendingJobKind.CHILD_BIRTH, cost, points, result(SonResult.CHILD_BIRTH_FAILED), run, finish, lambda child: f"son#{child.son_id}")


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.CALL_SIBLING, son, CallSiblingInput, ToolMeta(ActionKind.SPEAK_TO_SIBLING, no_cost), call_sibling),
        ToolSpec(
            SonToolId.SWEAR_COVENANT,
            son,
            CovenantInput,
            ToolMeta(ActionKind.COVENANT, no_cost, essence_cost=lambda rules: rules.costs.covenant),
            swear_covenant,
        ),
        ToolSpec(SonToolId.GIVE_GIFT, son, GiftInput, ToolMeta(ActionKind.GIFT, no_cost, flexible_actions=True), give_gift),
        ToolSpec(SonToolId.CHALLENGE, son, ChallengeInput, ToolMeta(ActionKind.CHALLENGE, son_standard_action), challenge),
        ToolSpec(
            SonToolId.BIRTH_CHILD,
            son,
            BirthChildInput,
            ToolMeta(
                ActionKind.BEAR_CHILD,
                lambda rules: rules.son_tools.bear_child_ap,
                essence_cost=lambda rules: rules.costs.bear_child,
                rarity_gate=gate(Gate.LEGENDARY_TOOLS),
                long_job=PendingJobKind.CHILD_BIRTH,
            ),
            birth_child,
            frozenset({"child_birth"}),
        ),
    ]
