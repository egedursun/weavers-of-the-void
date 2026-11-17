from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN, SHORT_DESCRIPTION_MAX
from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import KindAct, KindConcept, KindSpread, KindStance
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.kinds.acts import categories_told, category_named, hold_kind, kind_of, make_kind, spec_of
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


class ShapeKindInput(ToolInput):
    people_id: int
    act: KindAct
    concept: KindConcept
    kind_id: int | None = None
    category: str | None = None
    name: Annotated[str | None, Field(min_length=NAME_MIN, max_length=NAME_MAX)] = None
    description: Annotated[str | None, Field(max_length=SHORT_DESCRIPTION_MAX)] = None
    reason: Reason


async def people_in_reach(call: SonCall, people_id: int) -> EntityRow:
    people = await living_entity(call.session, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE:
        fail(SonResult.KIND_REFUSED, why="there is no such people")
    await ensure_in_reach(call, people)
    if held(people.id):
        fail(SonResult.KIND_REFUSED, why="a stronger hand holds them")
    return people


async def shape_kind(call: SonCall, args: ShapeKindInput) -> str:
    spec = spec_of(args.concept)
    if spec is None:
        fail(SonResult.KIND_REFUSED, why="that kind of thing is not known in this world yet")
    people = await people_in_reach(call, args.people_id)
    table = call.tick.rules.kinds
    told = spec.label.lower()
    if args.act is KindAct.MAKE:
        category = category_named(spec, args.category or "")
        if category is None:
            fail(SonResult.KIND_REFUSED, why=f"{an(told)} is one of: {categories_told(spec)}")
        if not args.name:
            fail(SonResult.KIND_REFUSED, why="a new kind needs a name")
        values = {"name": args.name.strip(), "description": (args.description or "").strip() or None, "category": category}
        row = await make_kind(call.tick, spec, {**values, "world_id": people.world_id, "origin_node_id": people.id})
        await hold_kind(
            call.tick,
            args.concept,
            row.id,
            people.id,
            stance=KindStance.MAKES,
            strength=table.adoption_strength + table.blessing_strength,
            spread=KindSpread.DIVINE,
        )
        await hold_kind(call.tick, args.concept, row.id, call.son.id, stance=KindStance.BLESSES, strength=PERCENT, spread=KindSpread.DIVINE)
        call.target(people.id)
        await call.record(
            "tools.son.made_kind",
            roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
            facts={"concept": told, "name": row.name, "reason": args.reason},
            kind=ChronicleKind.CULTURE,
        )
        return result(SonResult.KIND_MADE, people=people.name, name=row.name, concept=told, category=spec.category_labels[category.value].lower())
    found = await kind_of(call.tick, spec, args.kind_id) if args.kind_id is not None else None
    if found is None:
        fail(SonResult.KIND_REFUSED, why=f"there is no such {told}")
    if args.act is KindAct.BLESS:
        holding = await hold_kind(
            call.tick, args.concept, found.id, people.id, stance=KindStance.FAVOURS, strength=table.adoption_strength, spread=KindSpread.DIVINE
        )
        if "strength" not in holding.locked:
            holding.strength = clamp_int(holding.strength + table.blessing_strength, 0, PERCENT)
        await hold_kind(call.tick, args.concept, found.id, call.son.id, stance=KindStance.BLESSES, strength=PERCENT, spread=KindSpread.DIVINE)
        call.target(people.id)
        await call.record(
            "tools.son.blessed_kind",
            roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
            facts={"name": str(found.name), "reason": args.reason},
            kind=ChronicleKind.CULTURE,
        )
        return result(SonResult.KIND_BLESSED, name=found.name, people=people.name, strength=holding.strength)
    await hold_kind(call.tick, args.concept, found.id, people.id, stance=KindStance.FORBIDS, strength=table.blessing_strength, spread=KindSpread.DIVINE)
    await hold_kind(call.tick, args.concept, found.id, call.son.id, stance=KindStance.FORBIDS, strength=PERCENT, spread=KindSpread.DIVINE)
    call.target(people.id)
    await call.record(
        "tools.son.forbade_kind",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
        facts={"name": str(found.name), "reason": args.reason},
        kind=ChronicleKind.CULTURE,
    )
    return result(SonResult.KIND_FORBIDDEN, name=found.name, people=people.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.SHAPE_KIND, son, ShapeKindInput, meta, shape_kind)]
