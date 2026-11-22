from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.life.tools import RAISE_CHILD_SOCIALIZATION_TECHNIQUES, TECHNIQUE_AXES
from aerona.catalog.life_traits import LIFE_STAGE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.childhood import PedagogyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.childhood import PedagogyTheory, SocializationTechnique
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.life_traits import LifeStageTrait
from aerona.domain.enums.mind import ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.childhood.life import SCHOOLS
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mortal.kin import parents_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

GROWING = having(LIFE_STAGE_TRAITS, LifeStageTrait.GROWING)
WEIGHTS_MAX = len(SocializationTechnique)


class TechniqueWeight(ToolInput):
    technique: SocializationTechnique
    weight: int = Field(ge=0, le=PERCENT)


class RaiseChildInput(ToolInput):
    child_id: int
    techniques: list[TechniqueWeight] = Field(min_length=1, max_length=WEIGHTS_MAX)


class FoundSchoolMethodInput(ToolInput):
    school_id: int
    theory: PedagogyTheory
    depth: int = Field(default=50, ge=0, le=PERCENT)


async def raises(call: MortalCall, child: EntityRow) -> bool:
    if call.me.id in await parents_of(call.session, child.id):
        return True
    member = await call.session.get(HouseholdMemberRow, child.id)
    household = await call.session.get(HouseholdRow, member.household_id) if member is not None else None
    return household is not None and household.head_node_id == call.me.id


async def raise_child(call: MortalCall, args: RaiseChildInput) -> str:
    child = await call.session.get(EntityRow, args.child_id)
    profile = await call.session.get(MortalProfileRow, args.child_id)
    if child is None or profile is None or child.status is not EntityStatus.CANON or profile.life_stage not in GROWING:
        fail(MortalResult.CHILDHOOD_REFUSED, why="there is no such child to raise")
    if not await raises(call, child):
        fail(MortalResult.CHILDHOOD_REFUSED, why="only a parent or the head of the child's household raises it")
    if held(child.id):
        fail(MortalResult.CHILDHOOD_REFUSED, why="a god holds this child as it is")
    weights = {item.technique: item.weight for item in args.techniques}
    total = sum(weights.values()) or 1
    step = call.rules.childhood.socialize_step
    values = dict(await stored_values(call.session, ValueHolder.PERSONAL, child.id))
    for technique, weight in weights.items():
        axis = TECHNIQUE_AXES[technique]
        values[axis] = values.get(axis, 0) + round_half_up(step * weight / total * WEIGHTS_MAX / 2)
    await write_values(call.session, ValueHolder.PERSONAL, child.id, values)
    harsh = sum(weights.get(technique, 0) for technique in RAISE_CHILD_SOCIALIZATION_TECHNIQUES)
    if "stress" not in (profile.locked or []):
        profile.stress = clamp_int(profile.stress + round_half_up(harsh / total * call.rules.childhood.harsh_stress_pct / 2), 0, PERCENT)
    chief = max(sorted(weights), key=lambda technique: weights[technique])
    call.target(child.id)
    await call.record(
        "childhood.raised_by",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: child.id},
        facts={"technique": chief},
        place=child.location_id,
    )
    return result(MortalResult.CHILD_RAISED, name=child.name, technique=spoken(chief))


async def found_school_method(call: MortalCall, args: FoundSchoolMethodInput) -> str:
    school = await call.session.get(EntityRow, args.school_id)
    profile = await call.session.get(StructureProfileRow, args.school_id)
    if school is None or profile is None or profile.kind not in SCHOOLS or school.status is not EntityStatus.CANON:
        fail(MortalResult.CHILDHOOD_REFUSED, why="that is no school")
    if held(school.id):
        fail(MortalResult.CHILDHOOD_REFUSED, why="a god holds this school as it is")
    pedagogy = await call.session.scalar(select(PedagogyRow).where(PedagogyRow.holder_node_id == school.id).order_by(PedagogyRow.id).limit(1))
    if pedagogy is not None and "theory" in (pedagogy.locked or []):
        fail(MortalResult.CHILDHOOD_REFUSED, why="a god holds the way this school teaches")
    if pedagogy is None:
        pedagogy = PedagogyRow(holder_node_id=school.id, locked=[])
        call.session.add(pedagogy)
    pedagogy.theory, pedagogy.depth, pedagogy.founder_node_id, pedagogy.founded_epoch = args.theory, args.depth, call.me.id, call.epoch
    call.target(school.id)
    await call.record(
        "childhood.method_founded",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: school.id},
        facts={"theory": args.theory},
        place=profile.host_entity_id,
    )
    return result(MortalResult.SCHOOL_METHOD_FOUNDED, school=school.name, theory=spoken(args.theory))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.RAISE_CHILD, AgentKind.MORTAL, RaiseChildInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), raise_child),
        ToolSpec(
            MortalToolId.FOUND_SCHOOL_METHOD,
            AgentKind.MORTAL,
            FoundSchoolMethodInput,
            ToolMeta(ActionKind.DEVELOP_KNOWLEDGE, mortal_standard_action),
            found_school_method,
        ),
    ]
