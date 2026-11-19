from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.biology import BiologyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.variant_control import set_variant
from aerona.engine.body.variants import HOLDER_TYPES
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ShapeBiologyInput(ToolInput):
    holder_id: int
    variant: BiologyVariant
    gain: bool
    reason: Reason


async def shape_biology(call: SonCall, args: ShapeBiologyInput) -> str:
    holder = await living_entity(call.session, args.holder_id)
    if holder is None or holder.entity_type not in HOLDER_TYPES:
        fail(SonResult.BIOLOGY_REFUSED, why="there is no such people or species")
    await ensure_in_reach(call, holder)
    if held(holder.id):
        fail(SonResult.BIOLOGY_REFUSED, why="a stronger hand holds it")
    row = await call.session.get(BiologyRow, holder.id)
    if row is not None and "variants" in row.locked:
        fail(SonResult.BIOLOGY_REFUSED, why=f"the body of {holder.name} is held fast")
    has = row is not None and args.variant.value in row.variants
    if has == args.gain:
        fail(SonResult.BIOLOGY_REFUSED, why=f"{holder.name} is {'already' if has else 'not'} {args.variant.value.replace('_', ' ')}")
    cost = call.rules.biology_variants.son_cost
    require_essence(call, cost)
    await set_variant(call.tick, holder.id, args.variant, args.gain, hold=False)
    call.spend_essence(cost)
    call.target(holder.id)
    told = spoken(args.variant)
    await call.record(
        "tools.son.shape_biology",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.OWNER: holder.id},
        facts={"variant": str(told), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.BIOLOGY_SHAPED, holder=holder.name, variant=told, gain=args.gain)


def specs() -> list[ToolSpec[SonCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [ToolSpec(SonToolId.SHAPE_BIOLOGY, AgentKind.SON, ShapeBiologyInput, meta, shape_biology)]
