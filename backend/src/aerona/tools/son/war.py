from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import WarCause
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.conflict import foreign_god_war
from aerona.engine.services.war import can_open_war, declare_war, has_truce
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, label_of, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, grant, require_essence, rounded, shift_relation, world_name

PERCENT = 100
INCITABLE = frozenset({EntityType.FACTION, EntityType.PEOPLE, EntityType.SETTLEMENT})


class TreatyKind(StrEnum):
    ALLIANCE = "alliance"
    TRADE = "trade"


TREATY_BONDS = {TreatyKind.ALLIANCE: BondKind.ALLY, TreatyKind.TRADE: BondKind.TRADES_WITH}


class InciteInput(ToolInput):
    a_id: int
    b_id: int
    pretext: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class TreatyInput(ToolInput):
    a_id: int
    b_id: int
    kind: TreatyKind
    terms: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ForeignWarInput(ToolInput):
    god_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def _pair(call: SonCall, first_id: int, second_id: int, allowed: frozenset[EntityType], template: SonResult) -> tuple[EntityRow, EntityRow]:
    first = await require_canon(call.session, first_id)
    second = await require_canon(call.session, second_id)
    if first.id == second.id or first.entity_type not in allowed or second.entity_type not in allowed:
        fail(template)
    return first, second


async def incite_war(call: SonCall, args: InciteInput) -> str:
    tools = call.rules.son_tools
    first, second = await _pair(call, args.a_id, args.b_id, INCITABLE, SonResult.INCITE_TARGETS)
    await ensure_in_reach(call, first)
    await ensure_in_reach(call, second)
    require_essence(call, call.rules.costs.incite_war)
    if await BondRepository(call.session).exists_between(first.id, second.id, BondKind.ENEMY):
        fail(SonResult.ALREADY_ENEMIES)
    if await has_truce(call.session, call.rules, first.id, second.id, call.epoch):
        fail(SonResult.TRUCE_HOLDS)
    if await can_open_war(call.session, call.rules, first.id, second.id, call.epoch) is not None:
        fail(SonResult.WAR_BLOCKED, first=first.name, second=second.name)
    chance = max(tools.incite_min_pct, min(tools.incite_max_pct, rounded(tools.incite_base_pct + call.son.cunning / tools.incite_cunning_divisor)))
    call.spend_essence(call.rules.costs.incite_war)
    call.target(first.id)
    roll = call.die(PERCENT, "incite")
    if roll > chance or not await declare_war(call.tick, first.id, second.id, args.pretext, cause=WarCause.INCITED, incited_by_son_id=call.son.id):
        return result(SonResult.INCITE_FAILED, roll=roll, chance=chance)
    bonds = BondRepository(call.session)
    for side in (first, second):
        patron = await bonds.patron(side.id)
        if patron is not None and patron != call.son.id and await call.session.get(SonRow, patron) is not None:
            await shift_relation(call, patron, -tools.incite_patron_relation)
    await call.chronicle(
        ChronicleKind.INTRIGUE, lines.INCITE, entity_ids=[first.id, second.id], son=call.son.name, first=first.name, second=second.name, pretext=args.pretext
    )
    return result(SonResult.INCITE_TOOK, roll=roll, chance=chance, first=first.name, second=second.name)


async def make_interworld_treaty(call: SonCall, args: TreatyInput) -> str:
    tools = call.rules.son_tools
    first, second = await _pair(call, args.a_id, args.b_id, frozenset(COMMUNITY_TYPES), SonResult.TREATY_TARGETS)
    if first.world_id == second.world_id:
        fail(SonResult.TREATY_SAME_WORLD, first=first.name, second=second.name)
    if call.world_id not in (first.world_id, second.world_id):
        fail(SonResult.TREATY_FOREIGN, world_id=call.world_id)
    if not await WorldRepository(call.session).connected(first.world_id, second.world_id):
        fail(SonResult.TREATY_NO_ROAD, first=first.world_id, second=second.world_id)
    bonds = BondRepository(call.session)
    if await bonds.exists_between(first.id, second.id, BondKind.ENEMY):
        fail(SonResult.TREATY_ENEMIES, first=first.name, second=second.name)
    label = lines.TREATY_LABELS[args.kind.value]
    if await bonds.exists_between(first.id, second.id, TREATY_BONDS[args.kind]):
        fail(SonResult.TREATY_EXISTS, label=label, first=first.name, second=second.name)
    require_essence(call, tools.treaty_cost)
    await bonds.connect(BondDraft(first.id, second.id, TREATY_BONDS[args.kind], call.epoch, lines.TREATY_BOND.format(son=call.son.name, terms=args.terms)))
    await change_relation(call.tick, first.id, second.id, tools.treaty_relation, MemoryKind.ALLIED_WITH, note=lines.TREATY_EVENT)
    call.spend_essence(tools.treaty_cost)
    call.target(first.id)
    await call.chronicle(
        ChronicleKind.DIPLOMACY,
        lines.TREATY,
        entity_ids=[first.id, second.id],
        son=call.son.name,
        treaty=args.kind.value,
        first=first.name,
        first_world=await world_name(call, first.world_id),
        second=second.name,
        second_world=await world_name(call, second.world_id),
        terms=args.terms,
    )
    return result(SonResult.TREATY_MADE, first=first.name, second=second.name, label=label)


async def known_god(call: SonCall, god_id: int) -> ForeignGodRow:
    god = await call.session.get(ForeignGodRow, god_id)
    if god is None or not god.contacted:
        fail(SonResult.NO_FOREIGN_GOD)
    return god


async def ensure_god_in_reach(call: SonCall, god: ForeignGodRow) -> None:
    if call.world_id is not None and not await WorldRepository(call.session).connected(call.world_id, god.world_id):
        fail(SonResult.GOD_OUT_OF_REACH, name=god.name)


async def war_on_foreign_god(call: SonCall, args: ForeignWarInput) -> str:
    tools = call.rules.son_tools
    god = await known_god(call, args.god_id)
    if god.status is not ForeignGodStatus.AWAKE:
        fail(SonResult.GOD_CANNOT_FIGHT, name=god.name, state=label_of(god.status))
    await ensure_god_in_reach(call, god)
    require_essence(call, tools.foreign_war_cost)
    call.target(god.id)
    outcome = await foreign_god_war(call.tick, call.son.id, god.id, args.reason)
    call.log.essence_spent += tools.foreign_war_cost
    level = await grant(call, call.son, 0, 0)
    return result(SonResult.GOD_WAR, text=outcome.text, level=level)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.INCITE_WAR,
            son,
            InciteInput,
            ToolMeta(ActionKind.INCITE_WAR, son_standard_action, essence_cost=lambda rules: rules.costs.incite_war, rarity_gate=gate(Gate.RARE_TOOLS)),
            incite_war,
        ),
        ToolSpec(
            SonToolId.MAKE_INTERWORLD_TREATY,
            son,
            TreatyInput,
            ToolMeta(
                ActionKind.INTERWORLD_TREATY,
                lambda rules: rules.son_tools.treaty_ap,
                essence_cost=lambda rules: rules.son_tools.treaty_cost,
                rarity_gate=gate(Gate.INTERWORLD_TREATY),
            ),
            make_interworld_treaty,
        ),
        ToolSpec(
            SonToolId.WAR_ON_FOREIGN_GOD,
            son,
            ForeignWarInput,
            ToolMeta(
                ActionKind.FOREIGN_GOD_WAR,
                lambda rules: rules.son_tools.foreign_war_ap,
                essence_cost=lambda rules: rules.son_tools.foreign_war_cost,
                rarity_gate=gate(Gate.FOREIGN_GOD_WAR),
            ),
            war_on_foreign_god,
        ),
    ]
