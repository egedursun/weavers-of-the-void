import math
from typing import Any

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.book import effective
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.services.war import ARMY_KINDS, PEOPLES_ARMY, held_captive, ongoing_wars, war_event
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import ArmyInput, CommanderInput
from aerona.tools.mortal.support import MortalCreation, craft_of, create_record, headcount_key, i_know, money_key, name_free, require_target, same_region

PERCENT = 100
HALF = 50
KIN_BONDS = (BondKind.PROTECTS, BondKind.DESCENDS_FROM, BondKind.COMPANION)


async def my_army(call: MortalCall) -> tuple[EntityRow, ArmyRow] | None:
    statement = select(ArmyRow).where(ArmyRow.owner_entity_id == call.me.id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)
    for row in await call.session.scalars(statement):
        army = await call.session.get(EntityRow, row.entity_id)
        if army is not None and army.status is EntityStatus.CANON:
            return army, row
    return None


def _floor(call: MortalCall, key: str | None) -> int:
    limits = call.rules.limits
    if key == "followers":
        return call.rules.mortal_tools.cult_min_followers_kept
    if key is None:
        return 0
    return limits.people_population_floor if call.me.entity_type is EntityType.PEOPLE else limits.population_floor


def _soldiers(call: MortalCall, key: str | None, percent: int | None) -> int:
    tools = call.rules.mortal_tools
    base = stat_or(call.me, key, 0) if key is not None else round((stat(call.me, "strength") or tools.army_default_strength) * tools.army_strength_mult)
    share = tools.raise_army_population_pct / PERCENT
    ceiling = math.floor((base - _floor(call, key)) / share) if key is not None and share > 0 else call.rules.limits.army_soldier_cap
    wanted = round(base * max(1, min(tools.raise_army_max_pct, percent or tools.raise_army_default_pct)) / PERCENT)
    return max(0, min(wanted, ceiling, call.rules.limits.army_soldier_cap))


async def raise_army(call: MortalCall, args: ArmyInput) -> str:
    tools = call.rules.mortal_tools
    if await my_army(call) is not None:
        fail(MortalResult.HAS_ARMY)
    await name_free(call, args.name)
    key = headcount_key(call.me)
    funds = money_key(call.me) if key is None else None
    if key is None and funds is None:
        fail(MortalResult.NO_ARMY_SOURCE)
    if funds is not None and stat_or(call.me, funds, 0) < tools.mercenary_cost:
        fail(MortalResult.MERCENARY_POOR, kind=funds, have=stat_or(call.me, funds, 0), cost=tools.mercenary_cost)
    soldiers = _soldiers(call, key, args.percent)
    if soldiers < tools.army_min_soldiers:
        fail(MortalResult.TOO_FEW_SOLDIERS, minimum=tools.army_min_soldiers, count=soldiers, cap=tools.raise_army_max_pct)
    metallurgy = tools.army_metallurgy_bonus if await i_know(call, KnowledgeBranch.METALLURGY) else 0
    veterans = await i_know(call, KnowledgeBranch.WARFARE)
    morale = max(0, min(PERCENT, tools.army_morale_base + call.die(tools.army_morale_die)))
    equipment = max(0, min(PERCENT, tools.army_equipment_base + metallurgy + round((await craft_of(call)) / tools.army_craft_divisor)))
    stats = {"size": soldiers, "morale": morale, "equipment": equipment, "experience": tools.army_experience_warcraft if veterans else tools.army_experience}
    wars = await ongoing_wars(call.session, call.me.id)
    war = wars[0].war if wars else None
    event = await war_event(call.session, war) if war is not None else None
    origin = lines.ARMY_ORIGINS[key or "mercenary"].format(me=call.me.name)
    state = lines.ARMY_STATE.format(
        equipment=lines.ARMY_EQUIPPED[equipment >= HALF], morale=lines.ARMY_MORALE[morale >= HALF], veterans=lines.ARMY_VETERANS if veterans else ""
    )
    description = lines.ARMY_TEXT.format(
        me=call.me.name, count=soldiers, war=lines.ARMY_WAR.format(war=event.name) if event else "", origin=origin, state=state
    )
    engine_kind, subtype = ARMY_KINDS.get(call.me.entity_type, PEOPLES_ARMY)
    home = call.me.id if call.me.entity_type is EntityType.SETTLEMENT else call.me.location_id
    army = await create_record(
        call, MortalCreation(args.name, EntityType.ARMY, description, subtype=subtype, stats=stats, location_id=home, engine_kind=engine_kind)
    )
    call.session.add(ArmyRow(entity_id=army.id, war_id=war.id if war else None, owner_entity_id=call.me.id, raised_epoch=call.epoch))
    bonds = BondRepository(call.session)
    await bonds.connect(BondDraft(army.id, call.me.id, BondKind.PROTECTS, call.epoch))
    if event is not None and war is not None:
        await bonds.connect(BondDraft(army.id, event.id, BondKind.PART_OF, call.epoch, war_id=war.id))
    if key is not None:
        set_stats(call.me, **{key: max(_floor(call, key), round(stat_or(call.me, key, 0) - soldiers * tools.raise_army_population_pct / PERCENT))})
    elif funds is not None:
        set_stats(call.me, **{funds: max(0, stat_or(call.me, funds, 0) - tools.mercenary_cost)})
    await call.chronicle(ChronicleKind.ARMY, lines.ARMY, entity_ids=[call.me.id, army.id], me=call.me.name, count=soldiers, name=army.name)
    return result(MortalResult.ARMY_RAISED, id=army.id, name=army.name, count=soldiers)


async def appoint_commander(call: MortalCall, args: CommanderInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(
        TurnCounter.COMMANDER_APPOINTMENTS, tools.appoint_commander_per_epoch, "mortal_tools.appoint_commander_per_epoch", MortalResult.COMMANDER_LIMIT
    )
    found = await my_army(call)
    if found is None:
        fail(MortalResult.NO_ARMY)
    army, row = found
    mortal = await require_target(call, args.mortal_id)
    if mortal.entity_type is not EntityType.MORTAL:
        fail(MortalResult.COMMANDER_NOT_MORTAL)
    if await held_captive(call.session, mortal.id) is not None:
        fail(MortalResult.IS_CAPTIVE, name=mortal.name)
    bonds = BondRepository(call.session)
    if not (await same_region(call, mortal) or await bonds.active_between(call.me.id, mortal.id, KIN_BONDS)):
        fail(MortalResult.NOT_BOUND_TO_YOU, name=mortal.name)
    for bond in await bonds.incoming(army.id, BondKind.COMMANDS):
        await bonds.deactivate(bond, call.epoch, mortal.name)
    await bonds.connect(BondDraft(mortal.id, army.id, BondKind.COMMANDS, call.epoch, lines.COMMANDS))
    row.commander_entity_id = mortal.id
    morale = (stat(army, "morale") or tools.commander_default_morale) + round(
        await effective(call.session, mortal, "charisma", tools.default_stat, Capacity.COMMAND) / tools.commander_charisma_divisor
    )
    set_stats(army, morale=max(0, min(PERCENT, morale)))
    await call.bump(TurnCounter.COMMANDER_APPOINTMENTS)
    call.target(mortal.id)
    await call.chronicle(ChronicleKind.ARMY, lines.COMMANDER, entity_ids=[mortal.id, army.id], mortal=mortal.name, army=army.name)
    return result(MortalResult.COMMANDER_SET, name=mortal.name, army=army.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.RAISE_ARMY, mortal, ArmyInput, ToolMeta(ActionKind.RAISE_ARMY, mortal_standard_action), raise_army),
        ToolSpec(MortalToolId.APPOINT_COMMANDER, mortal, CommanderInput, ToolMeta(ActionKind.APPOINT_COMMANDER, no_cost), appoint_commander),
    ]
