from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mass_weapons import ARMED_STAGES, MassHarm, MassReach, Posture
from aerona.engine.mass_weapons.book import ArsenalTally, can_build, technique_for
from aerona.engine.mass_weapons.deterrence import declare
from aerona.engine.mass_weapons.programme import begin
from aerona.engine.mass_weapons.remnants import clear
from aerona.engine.mass_weapons.use import use_weapon
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

BUDGET_MAX = 100000
HOLDERS = frozenset({EntityType.POLITY, EntityType.FACTION, EntityType.CULT, EntityType.LEAGUE})


class BeginMassWeaponInput(ToolInput):
    holder_id: int
    harm: MassHarm
    reach: MassReach


class DeclarePostureInput(ToolInput):
    holder_id: int
    toward_id: int | None = None
    posture: Posture


class UseMassWeaponInput(ToolInput):
    weapon_id: int
    target_id: int


class ClearRemnantsInput(ToolInput):
    region_id: int
    budget: int = Field(ge=PERCENT, le=BUDGET_MAX)


async def holder_of(call: MortalCall, holder_id: int) -> EntityRow:
    holder = await living_entity(call.session, holder_id)
    if holder is None or holder.entity_type not in HOLDERS:
        fail(MortalResult.ARSENAL_REFUSED, why="an arsenal is held by a realm, an organisation, a faith or a league")
    if not await controls(call, holder.id):
        fail(MortalResult.ARSENAL_REFUSED, why="only the one who leads it decides its arsenal")
    if held(holder.id):
        fail(MortalResult.ARSENAL_REFUSED, why="a god holds it as it is")
    return holder


async def begin_mass_weapon_tool(call: MortalCall, args: BeginMassWeaponInput) -> str:
    holder = await holder_of(call, args.holder_id)
    if not await can_build(call.session, holder.id, args.harm, args.reach):
        needed = technique_for(args.harm, args.reach)
        fail(MortalResult.ARSENAL_REFUSED, why=f"it lacks {spoken(needed) if needed is not None else 'the means'} to make such a weapon")
    weapon = await begin(call.tick, holder, args.harm, args.reach, ArsenalTally())
    call.target(holder.id)
    return result(MortalResult.MASS_WEAPON_BEGUN, weapon=weapon.id, harm=spoken(args.harm), reach=spoken(args.reach), stage=spoken(weapon.stage))


async def declare_posture_tool(call: MortalCall, args: DeclarePostureInput) -> str:
    holder = await holder_of(call, args.holder_id)
    toward = await living_entity(call.session, args.toward_id) if args.toward_id is not None else None
    if args.toward_id is not None and (toward is None or toward.id == holder.id):
        fail(MortalResult.ARSENAL_REFUSED, why="a posture is held toward another who still stands, or toward all")
    row = await declare(call.tick, holder, toward.id if toward is not None else None, args.posture, ArsenalTally())
    call.target(toward.id if toward is not None else holder.id)
    return result(MortalResult.POSTURE_DECLARED, posture=spoken(args.posture), credibility=row.credibility)


async def use_mass_weapon_tool(call: MortalCall, args: UseMassWeaponInput) -> str:
    weapon = await call.session.get(MassWeaponRow, args.weapon_id)
    if weapon is None:
        fail(MortalResult.ARSENAL_REFUSED, why="there is no such weapon")
    await holder_of(call, weapon.holder_entity_id)
    if weapon.count < 1 or weapon.stage not in ARMED_STAGES:
        fail(MortalResult.ARSENAL_REFUSED, why=f"it is still at its {spoken(weapon.stage)} stage, with none ready")
    target = await living_entity(call.session, args.target_id)
    if target is None or held(target.id):
        fail(MortalResult.ARSENAL_REFUSED, why="there is no such target, or a god holds it")
    if weapon.reach is MassReach.SETTLEMENT and target.entity_type is not EntityType.SETTLEMENT:
        fail(MortalResult.ARSENAL_REFUSED, why="a weapon of settlement reach strikes a settlement")
    killed = await use_weapon(call.tick, weapon, target, ArsenalTally(), by=call.me.id)
    call.target(target.id)
    return result(MortalResult.MASS_WEAPON_USED, harm=spoken(weapon.harm), target=target.name, killed=killed)


async def clear_remnants_tool(call: MortalCall, args: ClearRemnantsInput) -> str:
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION or held(region.id):
        fail(MortalResult.ARSENAL_REFUSED, why="there is no such land, or a god holds it")
    cleared = await clear(call.tick, call.me, region.id, args.budget, ArsenalTally())
    if not cleared:
        fail(MortalResult.ARSENAL_REFUSED, why="nothing was cleared: there is nothing there to clear, or you cannot pay for it")
    call.target(region.id)
    return result(MortalResult.REMNANTS_CLEARED, region=region.name, cleared=cleared)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BEGIN_MASS_WEAPON, AgentKind.MORTAL, BeginMassWeaponInput, act, begin_mass_weapon_tool),
        ToolSpec(MortalToolId.DECLARE_POSTURE, AgentKind.MORTAL, DeclarePostureInput, act, declare_posture_tool),
        ToolSpec(MortalToolId.USE_MASS_WEAPON, AgentKind.MORTAL, UseMassWeaponInput, act, use_mass_weapon_tool),
        ToolSpec(MortalToolId.CLEAR_REMNANTS, AgentKind.MORTAL, ClearRemnantsInput, act, clear_remnants_tool),
    ]
