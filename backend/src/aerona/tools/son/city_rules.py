from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.city_rules import LandUseRuleRow, MunicipalServiceRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.city_rules import LandUseRule, MunicipalService
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
BLESSING = 30


class BlessCityInput(ToolInput):
    settlement_id: int
    service_or_rule: MunicipalService | LandUseRule
    reason: Reason


async def bless_city(call: SonCall, args: BlessCityInput) -> str:
    town = await living_entity(call.session, args.settlement_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(SonResult.BLESSING_REFUSED, why="there is no such settlement")
    await ensure_in_reach(call, town)
    if held(town.id):
        fail(SonResult.BLESSING_REFUSED, why="that settlement is held as it is")
    choice = args.service_or_rule
    if isinstance(choice, MunicipalService):
        kept = select(MunicipalServiceRow).where(MunicipalServiceRow.settlement_entity_id == town.id, MunicipalServiceRow.service == choice)
        service = await call.session.scalar(kept.limit(1))
        if service is None or "quality" in (service.locked or []):
            fail(SonResult.BLESSING_REFUSED, why=f"it keeps no {spoken(choice)} service to bless")
        service.quality, service.failed_epoch = clamp_int(service.quality + BLESSING, 0, PERCENT), None
        await call.record("city.blessed", roles={IncidentRole.SUBJECT: town.id}, facts={"service": choice})
    else:
        ruled = select(LandUseRuleRow).where(LandUseRuleRow.settlement_entity_id == town.id, LandUseRuleRow.rule == choice)
        rule = await call.session.scalar(ruled.limit(1))
        if rule is None or "enforcement" in (rule.locked or []):
            fail(SonResult.BLESSING_REFUSED, why=f"it keeps no {spoken(choice)} rule to bless")
        rule.enforcement = clamp_int(rule.enforcement + BLESSING, 0, PERCENT)
        await call.record("city.rule_blessed", roles={IncidentRole.SUBJECT: town.id}, facts={"rule": choice})
    call.target(town.id)
    return result(SonResult.CITY_BLESSED, town=town.name, choice=spoken(choice))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.BLESS_CITY, AgentKind.SON, BlessCityInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), bless_city)]
