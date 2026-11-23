from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, SHORT_DESCRIPTION_MAX, SHORT_DESCRIPTION_MIN
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.kinds.acts import categories_told, category_named, hold_kind, kind_of, make_kind, spec_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.sacred.places import realm_ruled_by
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

KindName = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
KindDescription = Annotated[str, Field(min_length=SHORT_DESCRIPTION_MIN, max_length=SHORT_DESCRIPTION_MAX)]


class InventKindInput(ToolInput):
    concept: KindConcept
    category: str
    name: KindName
    description: KindDescription


class KindChoiceInput(ToolInput):
    concept: KindConcept
    kind_id: int


async def own_people(call: MortalCall) -> EntityRow:
    people = await people_of(call.session, call.me)
    if people is None:
        fail(MortalResult.KIND_DECLINED, why="you belong to no people")
    if held(people.id):
        fail(MortalResult.KIND_DECLINED, why="your people is held")
    return people


async def invent_kind(call: MortalCall, args: InventKindInput) -> str:
    spec = spec_of(args.concept)
    if spec is None:
        fail(MortalResult.KIND_DECLINED, why="no one in this world makes that kind of thing yet")
    category = category_named(spec, args.category)
    if category is None:
        fail(MortalResult.KIND_DECLINED, why=f"{an(spec.label.lower())} is one of: {categories_told(spec)}")
    people = await own_people(call)
    values = {
        "name": args.name.strip(),
        "description": args.description.strip(),
        "category": category,
        "world_id": people.world_id,
        "origin_node_id": people.id,
    }
    row = await make_kind(call.tick, spec, values)
    await hold_kind(
        call.tick, args.concept, row.id, people.id, stance=KindStance.MAKES, strength=call.tick.rules.kinds.adoption_strength * 2, spread=KindSpread.INVENTED
    )
    call.target(people.id)
    told, sort = spec.label.lower(), spec.category_labels[category.value].lower()
    await call.record(
        "tools.mortal.invented_kind",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BENEFICIARY: people.id},
        facts={"concept": args.concept, "kind_name": row.name},
    )
    return result(MortalResult.KIND_INVENTED, people=people.name, name=row.name, concept=told, category=sort)


async def adopt_kind(call: MortalCall, args: KindChoiceInput) -> str:
    spec = spec_of(args.concept)
    if spec is None:
        fail(MortalResult.KIND_DECLINED, why="no one in this world makes that kind of thing yet")
    row = await kind_of(call.tick, spec, args.kind_id)
    if row is None:
        fail(MortalResult.KIND_DECLINED, why=f"there is no such {spec.label.lower()}")
    people = await own_people(call)
    await hold_kind(
        call.tick, args.concept, row.id, people.id, stance=KindStance.USES, strength=call.tick.rules.kinds.adoption_strength, spread=KindSpread.CONTACT
    )
    call.target(people.id)
    await call.record(
        "tools.mortal.adopted_kind",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BENEFICIARY: people.id},
        facts={"concept": args.concept, "kind_name": row.name},
    )
    return result(MortalResult.KIND_ADOPTED, people=people.name, name=row.name)


async def led_body(call: MortalCall) -> EntityRow | None:
    realm_id = await realm_ruled_by(call.session, call.me.id)
    if realm_id is not None:
        return await call.session.get(EntityRow, realm_id)
    for bond in await active_bonds(call.session, [BondKind.RULES], sources=[call.me.id]):
        body = await call.session.get(EntityRow, bond.target_node_id)
        if body is not None and body.entity_type in (EntityType.CULT, EntityType.POLITY):
            return body
    return None


async def forbid_kind(call: MortalCall, args: KindChoiceInput) -> str:
    spec = spec_of(args.concept)
    if spec is None:
        fail(MortalResult.KIND_DECLINED, why="no one in this world makes that kind of thing yet")
    row = await kind_of(call.tick, spec, args.kind_id)
    if row is None:
        fail(MortalResult.KIND_DECLINED, why=f"there is no such {spec.label.lower()}")
    body = await led_body(call)
    if body is None:
        fail(MortalResult.KIND_DECLINED, why="you rule no realm and lead no cult")
    if held(body.id):
        fail(MortalResult.KIND_DECLINED, why="those you lead are held")
    await hold_kind(
        call.tick, args.concept, row.id, body.id, stance=KindStance.FORBIDS, strength=call.tick.rules.kinds.adoption_strength, spread=KindSpread.DECREE
    )
    call.target(body.id)
    await call.record(
        "tools.mortal.forbade_kind",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: body.id},
        facts={"concept": args.concept, "kind_name": row.name},
    )
    return result(MortalResult.KIND_BANNED, name=row.name, realm=body.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.INVENT_KIND, mortal, InventKindInput, meta, invent_kind),
        ToolSpec(MortalToolId.ADOPT_KIND, mortal, KindChoiceInput, meta, adopt_kind),
        ToolSpec(MortalToolId.FORBID_KIND, mortal, KindChoiceInput, meta, forbid_kind),
    ]
