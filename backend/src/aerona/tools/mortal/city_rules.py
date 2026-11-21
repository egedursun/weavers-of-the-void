from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.city_rules import ConurbationGovernance, LandUseRule, MunicipalService, RuleMaker
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.city_rules.book import CityTally
from aerona.engine.city_rules.conurbations import conurbation_of, join
from aerona.engine.city_rules.land import set_rule
from aerona.engine.city_rules.services import found_service
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

LEVEL_MAX = 10
BUDGET_MAX = 100000
JOINED_MAX = 8


class RuleValues(BaseModel):
    kinds: list[DistrictKind] = Field(default_factory=list, max_length=len(DistrictKind))
    level: int | None = Field(default=None, ge=1, le=LEVEL_MAX)
    material: BuildMaterial | None = None


class SetLandUseRuleInput(ToolInput):
    settlement_id: int
    district_id: int | None = None
    rule: LandUseRule
    values: RuleValues = Field(default_factory=RuleValues)


class ProvideServiceInput(ToolInput):
    settlement_id: int
    service: MunicipalService
    provider_id: int | None = None
    budget: int = Field(ge=1, le=BUDGET_MAX)


class JoinSettlementsInput(ToolInput):
    settlement_ids: list[int] = Field(min_length=2, max_length=JOINED_MAX)
    governance: ConurbationGovernance


async def governs(call: MortalCall, town_id: int) -> bool:
    if await controls(call, town_id):
        return True
    realms = await call.session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id))
    return any([await controls(call, realm) for realm in realms])


async def governed_town(call: MortalCall, town_id: int) -> EntityRow:
    town = await living_entity(call.session, town_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(MortalResult.CITY_REFUSED, why="there is no such settlement")
    if not await governs(call, town.id):
        fail(MortalResult.CITY_REFUSED, why="only those who rule a settlement set its rules and services")
    if held(town.id):
        fail(MortalResult.CITY_REFUSED, why="a god holds that settlement as it is")
    return town


def rule_values(values: RuleValues) -> dict[str, int | str | list[str]]:
    found: dict[str, int | str | list[str]] = {}
    if values.kinds:
        found["kinds"] = [kind.value for kind in values.kinds]
    if values.level is not None:
        found["level"] = values.level
    if values.material is not None:
        found["material"] = values.material.value
    return found


async def set_land_use_rule_tool(call: MortalCall, args: SetLandUseRuleInput) -> str:
    town = await governed_town(call, args.settlement_id)
    if args.district_id is not None:
        district = await call.session.get(DistrictRow, args.district_id)
        if district is None or district.settlement_entity_id != town.id:
            fail(MortalResult.CITY_REFUSED, why="that district is not part of the settlement")
    maker = RuleMaker.COUNCIL if await controls(call, town.id) else RuleMaker.RULER
    await set_rule(call.tick, town, args.rule, rule_values(args.values), CityTally(), maker=maker, by=call.me.id, district=args.district_id)
    call.target(town.id)
    return result(MortalResult.LAND_RULE_SET, rule=spoken(args.rule), town=town.name)


async def provide_service_tool(call: MortalCall, args: ProvideServiceInput) -> str:
    town = await governed_town(call, args.settlement_id)
    provider = await living_entity(call.session, args.provider_id) if args.provider_id is not None else None
    if args.provider_id is not None and (provider is None or not await controls(call, provider.id)):
        fail(MortalResult.CITY_REFUSED, why="you name as provider only a body you lead, or leave it to the settlement")
    row = await found_service(call.tick, town, args.service, CityTally(), provider=provider.id if provider is not None else None, budget=args.budget)
    call.target(town.id)
    return result(MortalResult.SERVICE_PROVIDED, service=spoken(args.service), town=town.name, budget=row.budget)


async def join_settlements_tool(call: MortalCall, args: JoinSettlementsInput) -> str:
    towns = [await governed_town(call, town_id) for town_id in dict.fromkeys(args.settlement_ids)]
    if len(towns) < 2 or len({town.world_id for town in towns}) > 1:
        fail(MortalResult.CITY_REFUSED, why="settlements grow together only with others of their world")
    if any([await conurbation_of(call.tick, town.id) is not None for town in towns[1:]]):
        fail(MortalResult.CITY_REFUSED, why="one of them already belongs to another city")
    core = towns[0]
    row = await join(call.tick, core, [town for town in towns if town.id != core.id], args.governance, CityTally(), by=call.me.id)
    call.target(core.id)
    return result(MortalResult.SETTLEMENTS_JOINED, core=core.name, members=len(row.members), governance=spoken(args.governance))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SET_LAND_USE_RULE, AgentKind.MORTAL, SetLandUseRuleInput, act, set_land_use_rule_tool),
        ToolSpec(MortalToolId.PROVIDE_SERVICE, AgentKind.MORTAL, ProvideServiceInput, act, provide_service_tool),
        ToolSpec(MortalToolId.JOIN_SETTLEMENTS, AgentKind.MORTAL, JoinSettlementsInput, act, join_settlements_tool),
    ]
