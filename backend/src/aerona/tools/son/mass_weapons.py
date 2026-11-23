from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.mass_weapons import ProgrammeStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class StillWeaponInput(ToolInput):
    weapon_id: int
    reason: Reason


async def still_weapon(call: SonCall, args: StillWeaponInput) -> str:
    weapon = await call.session.get(MassWeaponRow, args.weapon_id)
    holder = await call.session.get(EntityRow, weapon.holder_entity_id) if weapon is not None else None
    if weapon is None or holder is None:
        fail(SonResult.ARSENAL_REFUSED, why="there is no such weapon")
    await ensure_in_reach(call, holder)
    if held(holder.id) or any(field in (weapon.locked or []) for field in ("count", "stage", "readiness")):
        fail(SonResult.ARSENAL_REFUSED, why="that weapon is held as it is")
    weapon.count, weapon.readiness, weapon.stage = 0, 0, ProgrammeStage.SOUGHT
    call.target(holder.id)
    await call.record("war.mass_weapon_stilled", roles={IncidentRole.SUBJECT: holder.id}, facts={"harm": weapon.harm})
    return result(SonResult.WEAPON_STILLED, holder=holder.name, harm=spoken(weapon.harm))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.STILL_WEAPON, AgentKind.SON, StillWeaponInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), still_weapon)]
