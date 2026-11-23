from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.identity import SALIENCE_DRIVERS
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.belonging import control
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
COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})


class StirIdentityInput(ToolInput):
    community_id: int
    layer: IdentityLayer
    driver: SalienceDriver = SalienceDriver.GOD
    calm: bool = False
    reason: Reason


async def stir_identity(call: SonCall, args: StirIdentityInput) -> str:
    community = await living_entity(call.session, args.community_id)
    if community is None or community.entity_type not in COMMUNITIES:
        fail(SonResult.IDENTITY_REFUSED, why="there is no such town or people")
    await ensure_in_reach(call, community)
    if held(community.id):
        fail(SonResult.IDENTITY_REFUSED, why="it is held")
    row = await call.session.get(HeldIdentityRow, (community.id, args.layer))
    current = row.salience if row is not None else call.tick.rules.identities.base_salience
    if args.driver is not SalienceDriver.GOD and args.layer not in SALIENCE_DRIVERS[args.driver].layers:
        fail(SonResult.IDENTITY_REFUSED, why=f"{spoken(args.driver)} does not stir the {spoken(args.layer)} layer")
    step = max(call.tick.rules.identities.rhetoric * 2, SALIENCE_DRIVERS[args.driver].rise(call.tick.rules))
    salience = clamp_int(current - step if args.calm else current + step, 0, 100)
    await control.set_record(call.tick, "held_identity", {"holder_entity_id": community.id, "layer": args.layer}, {"salience": salience, "driver": args.driver})
    call.target(community.id)
    told = "quieted" if args.calm else "stirred"
    layer = spoken(args.layer)
    await call.record(
        "tools.son.stir_identity",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: community.id},
        facts={"told": str(told), "layer": str(layer), "reason": args.reason},
        place=community.id,
        kind=ChronicleKind.CIVILIZATION,
    )
    return result(SonResult.IDENTITY_STIRRED, place=community.name, layer=layer, told=told, salience=salience)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.STIR_IDENTITY, son, StirIdentityInput, meta, stir_identity)]
