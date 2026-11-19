from typing import Annotated, Any

from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.dominion import DivineCreatureRow, GodImageRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.dominion import BeliefStance, CreatureDeed, CreatureLesson
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.dominion.creatures import raise_creature, teach
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, require_essence

HOMES = frozenset({EntityType.PLACE, EntityType.REGION})


class RaiseCreatureInput(ToolInput):
    home_id: int
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    description: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class TeachCreatureInput(ToolInput):
    creature_id: int
    deed: CreatureDeed
    lesson: CreatureLesson
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ReleaseCreatureInput(ToolInput):
    creature_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ShapeImageInput(ToolInput):
    stance: BeliefStance
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def raise_divine_creature(call: SonCall, args: RaiseCreatureInput) -> str:
    cost = call.rules.divine_creatures.raise_cost
    require_essence(call, cost)
    home = require_type(await require_canon(call.session, args.home_id), HOMES, SonResult.CREATURE_REFUSED, why="it makes its home in a place or a region")
    await ensure_in_reach(call, home)
    row = await raise_creature(call.tick, call.son.id, name=args.name, description=args.description, home_id=home.id)
    call.spend_essence(cost)
    call.target(row.creature_entity_id)
    await call.record(
        "tools.son.raise_creature",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: home.id, IncidentRole.SUBJECT: row.creature_entity_id},
        facts={"name": str(args.name)},
        place=home.id,
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.CREATURE_RAISED, name=args.name, id=row.creature_entity_id)


async def teach_creature(call: SonCall, args: TeachCreatureInput) -> str:
    cost = call.rules.divine_creatures.teach_cost
    require_essence(call, cost)
    row = await call.session.get(DivineCreatureRow, args.creature_id)
    if row is None or row.god_node_id != call.son.id:
        fail(SonResult.CREATURE_REFUSED, why="that creature is not yours")
    await teach(call.tick, row, args.deed, args.lesson)
    call.spend_essence(cost)
    call.target(row.creature_entity_id)
    told = "rewarded" if args.lesson is CreatureLesson.REWARD else "punished"
    return result(SonResult.CREATURE_TAUGHT, told=told, deed=spoken(args.deed))


async def release_creature(call: SonCall, args: ReleaseCreatureInput) -> str:
    row = await call.session.get(DivineCreatureRow, args.creature_id)
    if row is None or row.god_node_id != call.son.id:
        fail(SonResult.CREATURE_REFUSED, why="that creature is not yours")
    beast = await call.session.get(EntityRow, row.creature_entity_id)
    name = beast.name if beast is not None else "your creature"
    await call.session.delete(row)
    await call.session.flush()
    call.target(args.creature_id)
    await call.record(
        "tools.son.release_creature",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: args.creature_id},
        facts={"name": str(name), "reason": str(args.reason)},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.CREATURE_RELEASED, name=name)


async def shape_image(call: SonCall, args: ShapeImageInput) -> str:
    row = await call.session.get(GodImageRow, call.son.id)
    if row is None:
        row = GodImageRow(god_node_id=call.son.id, locked=[])
        call.session.add(row)
    if "stance" in row.locked:
        fail(SonResult.IMAGE_REFUSED, why="your stance toward your image is held by a higher will")
    row.stance = args.stance
    await call.session.flush()
    await call.record(
        "tools.son.shape_image", roles={IncidentRole.ACTOR: call.son.id}, facts={"stance": args.stance, "reason": str(args.reason)}, kind=ChronicleKind.WORLD
    )
    return result(SonResult.IMAGE_SHAPED, stance=spoken(args.stance))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.RAISE_DIVINE_CREATURE, AgentKind.SON, RaiseCreatureInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), raise_divine_creature
        ),
        ToolSpec(SonToolId.TEACH_CREATURE, AgentKind.SON, TeachCreatureInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), teach_creature),
        ToolSpec(SonToolId.RELEASE_CREATURE, AgentKind.SON, ReleaseCreatureInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), release_creature),
        ToolSpec(SonToolId.SHAPE_IMAGE, AgentKind.SON, ShapeImageInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), shape_image),
    ]
