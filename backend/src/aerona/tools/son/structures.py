from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import fill
from aerona.db.tables.structures import StructureDesignRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import STRUCTURE_LEVEL_MAX, StructureKind
from aerona.engine.structures.control import commission
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

COMMUNITIES = (EntityType.SETTLEMENT, EntityType.PEOPLE)


class CommissionInput(ToolInput):
    community_id: int
    structure_kind: StructureKind
    level: Annotated[int, Field(ge=1, le=STRUCTURE_LEVEL_MAX)] = 1
    material: MaterialKind | None = None
    design_id: int | None = None
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)] | None = None


async def commission_structure(call: SonCall, args: CommissionInput) -> str:
    community = require_type(await require_canon(call.session, args.community_id), COMMUNITIES, SonResult.BUILD_TARGET)
    await ensure_in_reach(call, community)
    design = await call.session.get(StructureDesignRow, args.design_id) if args.design_id is not None else None
    cost = call.rules.construction.commission_essence
    require_essence(call, cost)
    try:
        work, _ = await commission(
            call.tick,
            community.id,
            args.structure_kind,
            level=args.level,
            design=design,
            material=args.material,
            name=args.name,
            son_id=call.son.id,
            builder_son_id=call.son.id,
        )
    except ValidationFailedError as error:
        fail(SonResult.STRUCTURE_REFUSED, reason=error.message)
    call.spend_essence(cost)
    kind = args.structure_kind.value.replace("_", " ")
    return result(SonResult.COMMISSIONED, id=work.id, text=fill(lines.COMMISSIONED, site=community.name, name=work.name, kind=kind))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.COMMISSION_STRUCTURE,
            AgentKind.SON,
            CommissionInput,
            ToolMeta(ActionKind.BUILD, son_standard_action, essence_cost=lambda rules: rules.construction.commission_essence),
            commission_structure,
        )
    ]
