from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.belonging import control
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})


class StirIdentityInput(ToolInput):
    community_id: int
    layer: IdentityLayer
    calm: bool = False
    reason: Reason


async def stir_identity(call: SonCall, args: StirIdentityInput) -> str:
    community = await living_entity(call.session, args.community_id)
    if community is None or community.entity_type not in COMMUNITIES:
        fail(SonResult.IDENTITY_REFUSED, why="there is no such town or people")
    await ensure_in_reach(call, community)
    if held(community.id):
        fail(SonResult.IDENTITY_REFUSED, why="a stronger hand holds it")
    row = await call.session.get(HeldIdentityRow, (community.id, args.layer))
    current = row.salience if row is not None else call.tick.rules.identities.base_salience
    step = call.tick.rules.identities.rhetoric * 2
    salience = clamp_int(current - step if args.calm else current + step, 0, 100)
    await control.set_record(
        call.tick, "held_identity", {"holder_entity_id": community.id, "layer": args.layer}, {"salience": salience, "driver": SalienceDriver.GOD}
    )
    call.target(community.id)
    told = "quieted" if args.calm else "stirred"
    layer = args.layer.value
    await call.chronicle(
        ChronicleKind.CIVILIZATION,
        lines.STIR_IDENTITY,
        entity_ids=[community.id],
        son=call.son.name,
        told=told,
        layer=layer,
        place=community.name,
        reason=args.reason,
    )
    return result(SonResult.IDENTITY_STIRRED, place=community.name, layer=layer, told=told, salience=salience)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.STIR_IDENTITY, son, StirIdentityInput, meta, stir_identity)]
