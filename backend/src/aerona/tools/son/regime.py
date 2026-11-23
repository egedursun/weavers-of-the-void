from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.regime import SelectorateKind
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import definite
from aerona.engine.regime import control
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
NAME = 200
ANOINTING = 30


class ShapeRuleInput(ToolInput):
    polity_id: int
    selectorate: SelectorateKind
    public_share: int = Field(ge=0, le=PERCENT)
    reason: Reason


class AnointFounderInput(ToolInput):
    polity_id: int
    reason: Reason


class FreeLearningInput(ToolInput):
    structure_id: int
    level: int = Field(ge=0, le=PERCENT)
    reason: Reason


class InspireSchoolInput(ToolInput):
    founder_id: int
    name: str = Field(min_length=1, max_length=NAME)
    reason: Reason


async def reached(call: SonCall, entity_id: int, kinds: frozenset[EntityType], refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None or entity.entity_type not in kinds:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="it is held")
    return entity


async def shape_rule(call: SonCall, args: ShapeRuleInput) -> str:
    realm = await reached(call, args.polity_id, frozenset({EntityType.POLITY}), SonResult.RULE_REFUSED, "there is no such realm")
    await control.set_regime(call.tick, realm.id, {"selectorate": args.selectorate.value, "public_share": args.public_share})
    call.target(realm.id)
    await call.record(
        "tools.son.shape_rule",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: realm.id},
        facts={"realm": str(realm.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.RULE_SHAPED, name=realm.name, selectorate=spoken(args.selectorate), share=args.public_share)


async def anoint_founder(call: SonCall, args: AnointFounderInput) -> str:
    realm = await reached(call, args.polity_id, frozenset({EntityType.POLITY}), SonResult.FOUNDER_REFUSED, "there is no such realm")
    ruler_id = await call.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    ruler = await living_entity(call.session, ruler_id) if ruler_id is not None else None
    if ruler is None:
        fail(SonResult.FOUNDER_REFUSED, why="the realm has no living ruler")
    row = await control.set_regime(call.tick, realm.id, {})
    await control.set_regime(call.tick, realm.id, {"founder_entity_id": ruler.id, "charismatic": min(PERCENT, row.charismatic + ANOINTING)})
    call.target(realm.id)
    await call.record(
        "tools.son.anoint_founder",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.AUTHORITY: ruler.id, IncidentRole.SUBJECT: realm.id},
        facts={"realm": str(realm.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.FOUNDER_ANOINTED, name=ruler.name, realm=realm.name, charisma=row.charismatic)


async def free_learning(call: SonCall, args: FreeLearningInput) -> str:
    house = await reached(call, args.structure_id, frozenset({EntityType.STRUCTURE}), SonResult.LEARNING_REFUSED, "there is no such house of learning")
    row = await control.set_freedom(call.tick, house.id, {"level": args.level})
    call.target(house.id)
    await call.record(
        "tools.son.free_learning",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: house.id},
        facts={"house": str(house.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.LEARNING_FREED, name=house.name, level=row.level)


async def inspire_school(call: SonCall, args: InspireSchoolInput) -> str:
    founder = await reached(call, args.founder_id, frozenset({EntityType.MORTAL}), SonResult.SCHOOL_REFUSED, "there is no such mortal")
    school = await control.found_school(call.tick, founder.id, args.name, None)
    call.target(founder.id)
    await call.record(
        "tools.son.inspire_school",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: founder.id},
        facts={"founder": str(founder.name), "school": definite(school.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.SCHOOL_INSPIRED, name=definite(school.name), founder=founder.name, id=school.id)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.SHAPE_RULE, son, ShapeRuleInput, meta, shape_rule),
        ToolSpec(SonToolId.ANOINT_FOUNDER, son, AnointFounderInput, meta, anoint_founder),
        ToolSpec(SonToolId.FREE_LEARNING, son, FreeLearningInput, meta, free_learning),
        ToolSpec(SonToolId.INSPIRE_SCHOOL, son, InspireSchoolInput, meta, inspire_school),
    ]
