from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinDisowningRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kin_dynamics import KinStir, RivalryCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.kin_dynamics.acts import favour, reconcile, rival
from aerona.engine.kin_dynamics.book import KinTally, children_of, dynamic_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
SWAYED = 20


class StirKinInput(ToolInput):
    household_or_house_id: int
    kind: KinStir
    reason: Reason


async def stir(call: SonCall, house: EntityRow, head: int, kind: KinStir) -> bool:
    dynamic = await dynamic_of(call.tick, house=house.id)
    tally = KinTally()
    children = await children_of(call.session, head)
    if kind is KinStir.FAVOUR and children:
        await favour(call.tick, dynamic, head, children[0], tally)
    elif kind is KinStir.RIVALRY and len(children) >= 2:
        await rival(call.tick, dynamic, children[0], children[1], RivalryCause.STANDING, tally=tally)
    elif kind is KinStir.RECONCILE:
        rows = await call.session.scalars(select(KinDisowningRow).where(KinDisowningRow.dynamic_id == dynamic.id, KinDisowningRow.reconciled_epoch.is_(None)))
        return any([await reconcile(call.tick, row, tally) for row in list(rows)])
    elif kind is KinStir.ELDER:
        row = await call.session.scalar(select(ElderSwayRow).where(ElderSwayRow.dynamic_id == dynamic.id, ElderSwayRow.ended_epoch.is_(None)).limit(1))
        if row is None or "sway" in (row.locked or []):
            return False
        row.sway = clamp_int(row.sway + SWAYED, 0, PERCENT)
    else:
        return False
    return True


async def stir_kin(call: SonCall, args: StirKinInput) -> str:
    house = await call.session.get(EntityRow, args.household_or_house_id)
    profile = await call.session.get(HouseProfileRow, args.household_or_house_id)
    if house is None or house.entity_type is not EntityType.HOUSE or profile is None or profile.head_entity_id is None:
        fail(SonResult.KIN_STIR_REFUSED, why="there is no such house with a head")
    await ensure_in_reach(call, house)
    if held(house.id) or not await stir(call, house, profile.head_entity_id, args.kind):
        fail(SonResult.KIN_STIR_REFUSED, why=f"nothing in that family can be stirred toward {spoken(args.kind)}, or a stronger hand holds it")
    call.target(house.id)
    await call.record("kin.stirred", roles={IncidentRole.SUBJECT: house.id}, facts={"kind": args.kind})
    return result(SonResult.KIN_STIRRED, house=house.name, kind=spoken(args.kind))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.STIR_KIN, AgentKind.SON, StirKinInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), stir_kin)]
